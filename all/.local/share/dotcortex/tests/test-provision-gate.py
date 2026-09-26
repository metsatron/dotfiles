#!/usr/bin/env python3
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
GATE = ROOT / "all/.local/bin/provision-gate"
NALA_APPLY = ROOT / "debian/.local/bin/nala-apply"
HOST_EXCLUDES = ROOT / "all/.local/bin/host-excludes"
NALA_MK = ROOT / "all/.mk/nala.mk"
LANE_SCRIPTS = {
    "npm": ROOT / "all/.local/bin/npm-apply",
    "cargo": ROOT / "all/.local/bin/cargo-apply",
    "bun": ROOT / "all/.local/bin/bun-apply",
    "flatpak": ROOT / "linux/.local/bin/flatpak-apply",
}
# The pre-gate nala-apply (origin/master 8bf00b9467) and nala.mk, pinned in git so
# "other hosts unchanged" is checked against the real old behaviour.
BASE_REV = "8bf00b9467"

STUB = textwrap.dedent("""\
    #!/usr/bin/env bash
    printf '%s %s\\n' "$(basename "$0")" "$*" >> "$STUB_LOG"
    name="$(basename "$0")"
    case "$name" in
      dpkg)
        [ "${1:-}" = "-s" ] || exit 0
        for p in $FAKE_INSTALLED; do [ "$p" = "${2:-}" ] && exit 0; done
        exit 1 ;;
      dpkg-query)
        pkg="${@: -1}"
        for p in $FAKE_INSTALLED; do [ "$p" = "$pkg" ] && { printf 'ii '; exit 0; }; done
        exit 1 ;;
      apt-cache)
        for p in $FAKE_MISSING; do [ "$p" = "${2:-}" ] && exit 100; done
        exit 0 ;;
      apt-get)
        case " $* " in *" -s "*) printf '%b' "${FAKE_SIM:-}"; exit "${FAKE_SIM_RC:-0}" ;; esac
        exit 0 ;;
      *) exit 0 ;;
    esac
""")


class Sandbox:
    def __init__(self, gated: bool, installed="git stow", missing="", sim="", sim_rc=0,
                 excludes="", manifest_rows=None):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.home = base / "home"
        self.bin = base / "bin"
        self.log = base / "stub.log"
        (self.home / ".local/bin").mkdir(parents=True)
        self.bin.mkdir()
        for name in ("sudo", "apt-get", "apt-cache", "dpkg", "dpkg-query", "nala", "npm"):
            stub = self.bin / name
            stub.write_text(STUB)
            stub.chmod(0o755)
        # Helpers nala-apply resolves under $HOME/.local/bin: real host-excludes and
        # provision-gate, logging stubs for the side-channel installers.
        os.symlink(HOST_EXCLUDES, self.home / ".local/bin/host-excludes")
        os.symlink(GATE, self.home / ".local/bin/provision-gate")
        for side in ("nala-release-sync", "brave-canary-gate", "nala-repos-setup"):
            stub = self.home / ".local/bin" / side
            stub.write_text(STUB)
            stub.chmod(0o755)
        rows = manifest_rows or ['git "" bootstrap shared ""', 'tree "" bootstrap shared ""',
                                 'keychain "" bootstrap shared ""']
        self.manifest = base / "manifest.ssv"
        self.manifest.write_text("# PKG VERSION CATEGORY SCOPE EXTRA\n" + "\n".join(rows) + "\n")
        self.gates = base / "host-gates.ssv"
        self.gates.write_text(f'testhost additive {self.manifest} "fixture"\n' if gated else "# empty\n")
        self.excludes = base / "host-excludes.ssv"
        self.excludes.write_text("".join(f"testhost nala {p} \"fixture\"\n" for p in excludes.split()))
        self.env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.home),
            "DOTCORTEX_ROOT": str(ROOT),
            "STUB_LOG": str(self.log),
            "FAKE_INSTALLED": installed,
            "FAKE_MISSING": missing,
            "FAKE_SIM": sim,
            "FAKE_SIM_RC": str(sim_rc),
            "PROVISION_GATES": str(self.gates),
            "PROVISION_GATE_HOSTNAME": "testhost",
            "HOST_EXCLUDES": str(self.excludes),
            "HOST_EXCLUDES_HOSTNAME": "testhost",
        }
        if not gated:
            self.env["NALA_SSV"] = str(self.manifest)

    def run(self, script, *args, **extra):
        env = dict(self.env, **extra)
        result = subprocess.run(["bash", str(script), *args], capture_output=True, text=True, env=env)
        calls = self.log.read_text().splitlines() if self.log.exists() else []
        self.log.unlink(missing_ok=True)
        return result, calls

    def close(self):
        self.tmp.cleanup()


def mutating(calls):
    return [c for c in calls if c.startswith(("sudo ", "nala ", "nala-release-sync", "brave-canary-gate",
                                              "nala-repos-setup"))]


class GateHelperTests(unittest.TestCase):
    def gate(self, *args, gated=True, **env):
        with tempfile.TemporaryDirectory() as tmp:
            gates = Path(tmp) / "g.ssv"
            gates.write_text('testhost additive debian/x.ssv "f"\nother weird - "f"\n' if gated else "")
            full = dict(os.environ, PROVISION_GATES=str(gates), PROVISION_GATE_HOSTNAME="testhost",
                        DOTCORTEX_ROOT="/repo")
            full.update(env)
            return subprocess.run(["bash", str(GATE), *args], capture_output=True, text=True, env=full)

    def test_modes(self):
        self.assertEqual(self.gate("mode", "nala", gated=False).stdout.strip(), "open")
        self.assertEqual(self.gate("mode", "nala").stdout.strip(), "dry-run")
        self.assertEqual(self.gate("mode", "nala", PROVISION_APPLY="1").stdout.strip(), "additive")

    def test_removal_refused_only_when_gated(self):
        self.assertEqual(self.gate("allow-removal", "nala", gated=False).returncode, 0)
        refused = self.gate("allow-removal", "nala", "foo", PROVISION_APPLY="1")
        self.assertEqual(refused.returncode, 1)
        self.assertIn("REFUSED", refused.stderr)

    def test_manifest_is_resolved_against_the_checkout(self):
        self.assertEqual(self.gate("manifest").stdout.strip(), "/repo/debian/x.ssv")
        self.assertEqual(self.gate("manifest", gated=False).stdout.strip(), "")

    def test_lane_prefers_the_account_lane(self):
        with tempfile.TemporaryDirectory() as tmp:
            hosts = Path(tmp) / "hosts"
            hosts.mkdir()
            (hosts / "testhost.ssv").write_text("")
            self.assertEqual(self.gate("lane", tmp, PROVISION_GATE_ACCOUNT="someone").stdout.strip(),
                             f"{tmp}/hosts/testhost.ssv")
            (hosts / "testhost@someone.ssv").write_text("")
            self.assertEqual(self.gate("lane", tmp, PROVISION_GATE_ACCOUNT="someone").stdout.strip(),
                             f"{tmp}/hosts/testhost@someone.ssv")
            self.assertEqual(self.gate("lane", tmp, PROVISION_GATE_ACCOUNT="other").stdout.strip(),
                             f"{tmp}/hosts/testhost.ssv")

    def test_unknown_gate_name_fails_safe(self):
        result = self.gate("gate", PROVISION_GATE_HOSTNAME="other")
        self.assertEqual(result.stdout.strip(), "additive")

    def test_repo_honey_row_is_gated(self):
        env = dict(os.environ, PROVISION_GATE_HOSTNAME="beelink", DOTCORTEX_ROOT=str(ROOT), HOME="/nonexistent")
        env.pop("PROVISION_GATES", None)
        result = subprocess.run(["bash", str(GATE), "mode", "nala"], capture_output=True, text=True, env=env)
        self.assertEqual(result.stdout.strip(), "dry-run")
        manifest = subprocess.run(["bash", str(GATE), "manifest"], capture_output=True, text=True, env=env)
        self.assertTrue(Path(manifest.stdout.strip()).is_file(), manifest.stdout)


class GatedNalaTests(unittest.TestCase):
    def test_dry_run_is_the_default(self):
        box = Sandbox(gated=True, sim="Inst tree (2.2.1-1 Devuan)\\nInst keychain (2.8.5-5 Devuan)\\n")
        try:
            result, calls = box.run(NALA_APPLY)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("dry-run", result.stdout)
            self.assertIn("satisfied (1): git", result.stdout)
            self.assertIn("to install (2): tree keychain", result.stdout)
            self.assertEqual(mutating(calls), [], calls)
            self.assertTrue(any(c.startswith("apt-get -s") and "--no-remove" in c for c in calls), calls)
        finally:
            box.close()

    def test_simulated_removal_is_refused(self):
        box = Sandbox(gated=True, sim="Remv samba [2:4.22.8]\\nInst tree (2.2.1-1 Devuan)\\n")
        try:
            result, calls = box.run(NALA_APPLY, PROVISION_APPLY="1")
            self.assertEqual(result.returncode, 3, result.stdout + result.stderr)
            self.assertIn("REFUSED", result.stdout + result.stderr)
            self.assertEqual(mutating(calls), [], calls)
        finally:
            box.close()

    def test_failed_simulation_is_refused(self):
        box = Sandbox(gated=True, sim="E: Packages need to be removed but remove is disabled.\\n", sim_rc=100)
        try:
            result, calls = box.run(NALA_APPLY, PROVISION_APPLY="1")
            self.assertEqual(result.returncode, 3)
            self.assertEqual(mutating(calls), [], calls)
        finally:
            box.close()

    def test_apply_is_additive_only(self):
        box = Sandbox(gated=True, installed="git stow samba", excludes="samba",
                      sim="Inst tree (2.2.1-1 Devuan)\\n")
        try:
            result, calls = box.run(NALA_APPLY, PROVISION_APPLY="1")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            sudo = [c for c in calls if c.startswith("sudo ")]
            self.assertEqual(len(sudo), 1, calls)
            self.assertIn("apt-get install -y --no-remove -o APT::Get::AutomaticRemove=false", sudo[0])
            joined = "\n".join(calls)
            for verb in (" remove", " purge", "autoremove", " upgrade", "full-upgrade", "dpkg -i", "dpkg -r"):
                self.assertNotIn(verb, joined)
            self.assertFalse(any(c.startswith(("nala ", "nala-release-sync", "brave-canary-gate")) for c in calls), calls)
            self.assertIn("samba", result.stdout)  # host-excluded + installed: reported, not removed
            self.assertIn("never removed", result.stdout)
        finally:
            box.close()

    def test_gated_host_never_bootstraps_nala(self):
        box = Sandbox(gated=True, sim="Inst tree\\n")
        try:
            (box.bin / "nala").unlink()
            result, calls = box.run(NALA_APPLY, PROVISION_APPLY="1")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(any("install -y nala" in c for c in calls), calls)
        finally:
            box.close()

    def test_other_lanes_stop_in_dry_run(self):
        for lane, script in LANE_SCRIPTS.items():
            box = Sandbox(gated=True)
            try:
                result, calls = box.run(script)
                self.assertEqual(result.returncode, 0, f"{lane}: {result.stdout}{result.stderr}")
                self.assertIn("dry-run", result.stdout + result.stderr, lane)
                self.assertEqual(calls, [], f"{lane}: {calls}")
            finally:
                box.close()

    def test_other_lanes_force_uninstall_off_when_applying(self):
        for lane, script in LANE_SCRIPTS.items():
            text = script.read_text()
            self.assertIn('additive) UNINSTALL=0; MAN="$HOST_MAN"', text, lane)

    def test_gated_lane_without_host_lane_installs_nothing_even_when_applying(self):
        for lane, script in LANE_SCRIPTS.items():
            box = Sandbox(gated=True)
            try:
                result, calls = box.run(script, PROVISION_APPLY="1")
                self.assertEqual(result.returncode, 0, f"{lane}: {result.stdout}{result.stderr}")
                self.assertIn("no " + lane + " host lane", result.stdout, lane)
                self.assertEqual(calls, [], f"{lane}: {calls}")
            finally:
                box.close()

    def test_gated_npm_dry_run_reads_only_the_host_lane(self):
        box = Sandbox(gated=True)
        try:
            lane_dir = box.home / "DotCortex/all/.npm/manifest/hosts"
            lane_dir.mkdir(parents=True)
            (lane_dir.parent / "global.ssv").write_text('fleet-only "" "" "global" "registry" "" "" ""\n')
            (lane_dir / "testhost.ssv").write_text('# lane\na "" "" "global" "registry" "" "" ""\n'
                                                   'b "" "" "global" "registry" "" "" ""\n')
            result, calls = box.run(LANE_SCRIPTS["npm"])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("declares 2 package(s)", result.stdout)
            self.assertEqual(calls, [])
        finally:
            box.close()

    def test_gated_npm_dry_run_uses_the_account_lane(self):
        box = Sandbox(gated=True)
        try:
            lane_dir = box.home / "DotCortex/all/.npm/manifest/hosts"
            lane_dir.mkdir(parents=True)
            (lane_dir.parent / "global.ssv").write_text('fleet-only "" "" "global" "registry" "" "" ""\n')
            (lane_dir / "testhost.ssv").write_text('hers "" "" "global" "registry" "" "" ""\n')
            (lane_dir / "testhost@guest.ssv").write_text('mine "" "" "global" "registry" "" "" ""\n')
            result, calls = box.run(LANE_SCRIPTS["npm"], PROVISION_GATE_ACCOUNT="guest")
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn("testhost@guest.ssv declares 1 package(s): mine", result.stdout)
            self.assertNotIn("hers", result.stdout)
            self.assertEqual(calls, [])
            result, _calls = box.run(LANE_SCRIPTS["npm"], PROVISION_GATE_ACCOUNT="owner")
            self.assertIn("testhost.ssv declares 1 package(s): hers", result.stdout)
        finally:
            box.close()

    def test_beelink_scoped_rows_apply_on_honey_only(self):
        rows = ['honeyonly "" stack beelink ""', 'git "" bootstrap shared ""']
        for host, expected in (("testhost", "to install (0)"), ("beelink", "to install (1): honeyonly")):
            box = Sandbox(gated=True, installed="git", manifest_rows=rows, sim="Inst honeyonly\\n")
            # beelink is a known host because a provisioning registry lists it.
            box.gates.write_text(box.gates.read_text() + 'beelink additive - "fixture"\n')
            try:
                result, _calls = box.run(NALA_APPLY, NALA_HOSTNAME=host)
                self.assertIn(expected, result.stdout, host)
            finally:
                box.close()


HONEY_NALA_LANE = ROOT / "debian/.nala/manifest/hosts/beelink.ssv"
HONEY_NPM_LANE = ROOT / "all/.npm/manifest/hosts/beelink.ssv"
HONEY_METSATRON_NPM_LANE = ROOT / "all/.npm/manifest/hosts/beelink@metsatron.ssv"
HONEY_TO_INSTALL = {"python3-venv", "keychain", "tree", "pkg-config", "libfreetype-dev", "libfontconfig-dev",
                    "python3-cryptography"}


def declared(path):
    return {line.split()[0] for line in path.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")}


def on_honey():
    import socket
    return socket.gethostname().split(".", 1)[0] == "beelink"


class HoneyLaneTests(unittest.TestCase):
    """Drift checks for Honey's host lanes. The live ones only run on Honey itself."""

    def test_every_honey_nala_row_is_scoped_beelink_and_unique(self):
        rows = [line.split() for line in HONEY_NALA_LANE.read_text().splitlines()
                if line.strip() and not line.startswith("#")]
        names = [row[0] for row in rows]
        self.assertEqual(len(names), len(set(names)), "duplicate rows")
        self.assertEqual({row[3] for row in rows}, {"beelink"})

    def test_metsatron_lane_is_claude_code_and_bun_only(self):
        self.assertEqual(declared(HONEY_METSATRON_NPM_LANE), {"@anthropic-ai/claude-code", "bun"})
        self.assertIn("python3-cryptography", declared(HONEY_NALA_LANE))
        # Node >= 22 comes from Guix in this fleet, never from Honey's apt lane.
        self.assertFalse({"nodejs", "npm"} & declared(HONEY_NALA_LANE))

    @unittest.skipUnless(on_honey() and shutil.which("apt-mark"), "live drift check runs on Honey only")
    def test_every_manual_package_on_honey_is_declared(self):
        manual = set(subprocess.run(["apt-mark", "showmanual"], capture_output=True, text=True,
                                    check=True).stdout.split())
        missing = sorted(manual - declared(HONEY_NALA_LANE))
        self.assertEqual(missing, [], f"undeclared manual packages on Honey: {missing}")

    @unittest.skipUnless(on_honey() and shutil.which("npm"), "live drift check runs on Honey only")
    def test_every_global_npm_package_on_honey_is_declared(self):
        import json
        out = subprocess.run(["npm", "ls", "-g", "--depth=0", "--json"], capture_output=True, text=True).stdout
        live = set(json.loads(out or "{}").get("dependencies", {}))
        self.assertEqual(sorted(live - declared(HONEY_NPM_LANE)), [])

    @unittest.skipUnless(on_honey(), "live dry-run runs on Honey only")
    def test_honey_dry_run_installs_only_the_seven_and_removes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            trap = Path(tmp) / "sudo"
            log = Path(tmp) / "sudo.log"
            trap.write_text(f'#!/bin/sh\necho "sudo $*" >> {log}\nexit 99\n')
            trap.chmod(0o755)
            # Plan from this checkout's manifest, not whatever ~/DotCortex has checked out.
            env = dict(os.environ, PATH=f"{tmp}:{os.environ['PATH']}", DOTCORTEX_ROOT=str(ROOT))
            for key in ("PROVISION_APPLY", "NALA_SSV", "PROVISION_GATES", "PROVISION_GATE_HOSTNAME",
                        "HOST_EXCLUDES", "HOST_EXCLUDES_HOSTNAME", "NALA_HOSTNAME"):
                env.pop(key, None)
            result = subprocess.run(["bash", str(NALA_APPLY)], capture_output=True, text=True, env=env)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertFalse(log.exists(), "sudo was called during a gated dry-run")
            line = next(l for l in result.stdout.splitlines() if l.strip().startswith("to install ("))
            self.assertEqual(set(line.split(":", 1)[1].split()), HONEY_TO_INSTALL, line)
            self.assertIn("0 removed", result.stdout)
            self.assertIn("dry-run", result.stdout)


REAL_EXCLUDES = ROOT / "all/.provision/host-excludes.ssv"
FLEET_MANIFEST = ROOT / "debian/.nala/manifest/packages.ssv"


def install_set(calls):
    for call in calls:
        if call.startswith("sudo ") and " install -y " in call:
            return set(call.split(" install -y ", 1)[1].split())
    return set()


class HostScopeTests(unittest.TestCase):
    """SCOPE naming a known host applies on that host only (the kikin-kushi fix)."""

    def resolve(self, script, manifest, host):
        box = Sandbox(gated=False, installed="")
        try:
            box.env["NALA_SSV"] = str(manifest)
            result, calls = box.run(script, NALA_HOSTNAME=host, HOST_EXCLUDES=str(REAL_EXCLUDES),
                                    HOST_EXCLUDES_HOSTNAME=host)
            return result, install_set(calls)
        finally:
            box.close()

    def test_firmware_row_only_on_kikin_kushi_and_other_hosts_unchanged(self):
        self.assertIn('firmware-amd-graphics "" system kikin-kushi ""', FLEET_MANIFEST.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            old_script = Path(tmp) / "nala-apply.master"
            old_manifest = Path(tmp) / "packages.master.ssv"
            for rel, out in (("debian/.local/bin/nala-apply", old_script),
                             ("debian/.nala/manifest/packages.ssv", old_manifest)):
                out.write_text(subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_REV}:{rel}"],
                                              capture_output=True, text=True, check=True).stdout)
            for host in ("x230", "t480s", "t480", "kikin-kushi", "beelink", "some-new-box"):
                new_result, new_set = self.resolve(NALA_APPLY, FLEET_MANIFEST, host)
                _old_result, old_set = self.resolve(old_script, old_manifest, host)
                self.assertEqual(new_result.returncode, 0, new_result.stderr)
                self.assertNotIn("unknown SCOPE", new_result.stderr, host)
                self.assertTrue(old_set, host)
                if host == "kikin-kushi":
                    self.assertEqual(new_set, old_set | {"firmware-amd-graphics"}, host)
                else:
                    self.assertEqual(new_set, old_set, f"{host}: install set changed vs master")

    def test_unknown_scope_still_installs_but_warns(self):
        rows = ['mystery-pkg "" cli someday-maybe ""', 'git "" bootstrap shared ""']
        box = Sandbox(gated=False, installed="", manifest_rows=rows)
        try:
            result, calls = box.run(NALA_APPLY, NALA_HOSTNAME="x230")
            self.assertIn("mystery-pkg", install_set(calls))
            self.assertIn("unknown SCOPE 'someday-maybe'", result.stderr)
        finally:
            box.close()


class UngatedHostsUnchangedTests(unittest.TestCase):
    def base_file(self, path, tmp):
        out = Path(tmp) / Path(path).name
        blob = subprocess.run(["git", "-C", str(ROOT), "show", f"{BASE_REV}:{path}"],
                              capture_output=True, text=True, check=True).stdout
        out.write_text(blob)
        return out

    def test_nala_apply_issues_the_same_commands_as_before(self):
        cases = [
            dict(installed="git stow", sim=""),
            dict(installed="git stow samba", excludes="samba"),
            dict(installed="git", missing="keychain"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            old = self.base_file("debian/.local/bin/nala-apply", tmp)
            for case in cases:
                box = Sandbox(gated=False, **case)
                try:
                    before = box.run(old)
                    after = box.run(NALA_APPLY)
                    self.assertEqual(after[0].returncode, before[0].returncode, case)
                    self.assertEqual(after[1], before[1], f"{case}: command sequence changed")
                    self.assertEqual(after[0].stdout, before[0].stdout, case)
                finally:
                    box.close()

    @unittest.skipUnless(shutil.which("make"), "make not installed")
    def test_make_targets_still_upgrade_on_ungated_hosts(self):
        box = Sandbox(gated=False)
        try:
            (box.home / ".local/bin/nala-apply").symlink_to(NALA_APPLY)
            result = subprocess.run(["make", "-s", "-f", str(NALA_MK), "nala-apply"],
                                    capture_output=True, text=True, env=dict(box.env))
            calls = box.log.read_text().splitlines()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(calls[0], "nala-repos-setup ")
            self.assertEqual(calls[1], "sudo nala upgrade")
        finally:
            box.close()

    @unittest.skipUnless(shutil.which("make"), "make not installed")
    def test_make_targets_skip_upgrade_and_repos_on_gated_hosts(self):
        box = Sandbox(gated=True, sim="Inst tree\\n")
        try:
            (box.home / ".local/bin/nala-apply").symlink_to(NALA_APPLY)
            result = subprocess.run(["make", "-s", "-f", str(NALA_MK), "nala-apply-auto"],
                                    capture_output=True, text=True, env=dict(box.env))
            calls = box.log.read_text().splitlines()
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(mutating(calls), [], calls)
            self.assertIn("skipped on gated host", result.stdout)
        finally:
            box.close()


if __name__ == "__main__":
    unittest.main()
