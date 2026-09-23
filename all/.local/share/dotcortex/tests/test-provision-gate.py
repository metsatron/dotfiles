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
# The pre-gate nala-apply (origin/master 5b101ea25) and nala.mk, pinned in git so
# "other hosts unchanged" is checked against the real old behaviour.
BASE_REV = "5b101ea25"

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
