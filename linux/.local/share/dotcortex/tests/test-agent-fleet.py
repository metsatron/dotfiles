#!/usr/bin/env python3
from __future__ import annotations

import os
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
CHECK = ROOT / "all/.local/bin/agent-fleet-check"
USERS = ROOT / "all/.local/bin/agent-users-bootstrap"


def free_uid() -> int:
    """A uid/gid in the reserved band that nothing on this host holds."""
    for uid in range(2090, 2100):
        taken = subprocess.run(["getent", "passwd", str(uid)], capture_output=True).returncode == 0
        taken |= subprocess.run(["getent", "group", str(uid)], capture_output=True).returncode == 0
        if not taken:
            return uid
    raise unittest.SkipTest("no free test uid in 2090-2099")


class AgentFleetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        conf = Path(self.tmp.name)
        (conf / "fleet.ssv").write_text(f"# alias hostname reach agents warm no-cortex\nself {socket.gethostname()} - all - -\n")
        (conf / "uids.ssv").write_text(
            "# tool uid provision\n"
            f"ghost {free_uid()} yes\n"
            f"clash {os.getuid()} yes\n"
            "parked 2010 no\n"
            "vibe 2013 yes\n"
        )
        self.env = dict(os.environ, AGENT_CLI_CONF=str(conf), AGENT_UIDS_FILE=str(conf / "uids.ssv"))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def run_tool(self, tool: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(tool), *args], env=self.env, text=True, capture_output=True, check=False)

    def test_reports_missing_and_collision(self) -> None:
        out = self.run_tool(CHECK)
        self.assertEqual(out.returncode, 1, out.stdout + out.stderr)
        self.assertIn("MISSING agent-ghost", out.stdout)
        self.assertIn("agent-vibe", out.stdout)
        self.assertIn("2013", out.stdout)
        self.assertIn("COLLISION agent-clash", out.stdout)
        self.assertNotIn("agent-parked", out.stdout, "provision=no agents are not gaps")

    def test_agents_column_narrows_the_host(self) -> None:
        conf = Path(self.env["AGENT_CLI_CONF"])
        (conf / "fleet.ssv").write_text(f"# alias hostname reach agents warm\nself {socket.gethostname()} - ghost -\n")
        out = self.run_tool(CHECK)
        self.assertIn("MISSING agent-ghost", out.stdout)
        self.assertNotIn("agent-clash", out.stdout, "an agent the host does not carry is not expected there")

    def test_apply_needs_provision(self) -> None:
        self.assertEqual(self.run_tool(CHECK, "--apply").returncode, 2)

    def test_users_bootstrap_dry_run_and_guards(self) -> None:
        dry = self.run_tool(USERS, "--only", "ghost,clash")
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("DRY-RUN: sudo useradd --uid", dry.stdout)
        self.assertIn("COLLISION", dry.stdout)
        self.assertNotIn("+ sudo", dry.stdout, "dry-run must not execute")
        bad = self.run_tool(USERS, "--only", "nosuch")
        self.assertEqual(bad.returncode, 1)

    def vibe_bootstrap(self, present_uid: int | None) -> subprocess.CompletedProcess[str]:
        """Run the bootstrap for vibe with id/getent stubbed, so the result never depends on what THIS host holds.
        present_uid None: agent-vibe and uid/gid 2013 are free. Otherwise agent-vibe exists with that uid."""
        stubs = Path(self.tmp.name) / "vibe-stubs"
        stubs.mkdir(exist_ok=True)
        if present_uid is None:
            ident = ('#!/bin/sh\ncase "$*" in "agent-vibe"|"-u agent-vibe"|"-nG agent-vibe") exit 1 ;; esac\n'
                     'exec /usr/bin/id "$@"\n')
            getent = ('#!/bin/sh\ncase "$*" in "passwd 2013"|"group 2013"|"passwd agent-vibe") exit 2 ;; esac\n'
                      'exec /usr/bin/getent "$@"\n')
        else:
            ident = (f'#!/bin/sh\ncase "$*" in "agent-vibe") exit 0 ;; "-u agent-vibe") echo {present_uid}; exit 0 ;; '
                     f'"-nG agent-vibe") echo "agent-vibe cortex"; exit 0 ;; esac\nexec /usr/bin/id "$@"\n')
            getent = '#!/bin/sh\nexec /usr/bin/getent "$@"\n'
        for name, text in (("id", ident), ("getent", getent)):
            (stubs / name).write_text(text)
            (stubs / name).chmod(0o755)
        env = dict(self.env, PATH=f"{stubs}:{self.env['PATH']}")
        return subprocess.run([str(USERS), "--only", "vibe"], env=env, text=True, capture_output=True, check=False)

    def test_vibe_uid_is_accepted_by_users_bootstrap(self) -> None:
        # Create-when-absent, deterministically: the account is stubbed absent, so the creation path runs on ANY host (it used to
        # assert "2013" in output that only appeared where agent-vibe did not exist or had a different uid).
        dry = self.vibe_bootstrap(None)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("DRY-RUN: sudo groupadd -g 2013 agent-vibe", dry.stdout)
        self.assertIn("DRY-RUN: sudo useradd --uid 2013 --gid 2013", dry.stdout)
        self.assertNotIn("exists: agent-vibe", dry.stdout)

    def test_vibe_that_already_exists_with_the_canonical_uid_is_skipped_quietly(self) -> None:
        dry = self.vibe_bootstrap(2013)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("exists: agent-vibe (skip create)", dry.stdout)
        self.assertNotIn("WARNING", dry.stdout)
        self.assertNotIn("useradd", dry.stdout)

    def test_vibe_with_a_non_canonical_uid_is_warned_not_recreated(self) -> None:
        dry = self.vibe_bootstrap(2006)
        self.assertEqual(dry.returncode, 0, dry.stderr)
        self.assertIn("WARNING: agent-vibe has uid 2006, canon is 2013", dry.stdout)
        self.assertIn("exists: agent-vibe (skip create)", dry.stdout)
        self.assertNotIn("useradd", dry.stdout)


CANON = ROOT / "all/.config/agent-cli"
STUB_ID = """#!/bin/sh
# test stub: agent-deepseek exists and is already in cortex; everything else is the real id
case "$*" in
  "-nG agent-deepseek") echo "agent-deepseek cortex"; exit 0 ;;
  "agent-deepseek") exit 0 ;;
esac
exec /usr/bin/id "$@"
"""
STUB_GETENT = """#!/bin/sh
# test stub: a local agent-ghost (uid 2099) and a cortex group; everything else is the real getent
case "$*" in
  "passwd agent-ghost") echo "agent-ghost:x:2099:2099::/nonexistent:/usr/sbin/nologin"; exit 0 ;;
  "group cortex") echo "cortex:x:2000:"; exit 0 ;;
esac
exec /usr/bin/getent "$@"
"""


class CortexGrantTests(unittest.TestCase):
    """The cortex grant is host-conditional data (fleet.ssv no-cortex), and only that row changes anything."""

    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.stubs = self.dir / "stubs"
        self.stubs.mkdir()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def stub(self, name: str, text: str) -> None:
        path = self.stubs / name
        path.write_text(text)
        path.chmod(0o755)

    def as_host(self, host: str) -> None:
        self.stub("hostname", f"#!/bin/sh\necho {host}\n")

    def bootstrap(self, conf: Path, *args: str) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, PATH=f"{self.stubs}:{os.environ['PATH']}", AGENT_UIDS_FILE=str(conf / "uids.ssv"))
        return subprocess.run([str(USERS), *args], env=env, text=True, capture_output=True, check=False)

    def scratch(self, fleet: str | None) -> Path:
        conf = self.dir / "conf"
        conf.mkdir(exist_ok=True)
        (conf / "uids.ssv").write_text("# tool uid provision\ncodex 2001 yes\ndeepseek 2012 yes\nparked 2010 no\n")
        (conf / "fleet.ssv").unlink(missing_ok=True)
        if fleet is not None:
            (conf / "fleet.ssv").write_text(fleet)
        return conf

    @staticmethod
    def granted(out: subprocess.CompletedProcess[str], tool: str) -> bool:
        return f"DRY-RUN: sudo usermod -aG cortex agent-{tool}" in out.stdout

    def canonical_rows(self) -> list[tuple[str, str]]:
        rows = []
        for line in (CANON / "fleet.ssv").read_text().splitlines():
            if line.strip() and not line.startswith("#"):
                cols = line.split()
                rows.append((cols[0], cols[1]))
        return rows

    def canonical_tools(self) -> list[str]:
        return [l.split()[0] for l in (CANON / "uids.ssv").read_text().splitlines() if l.split()[2:3] == ["yes"]]

    def test_only_the_honey_row_exempts_only_deepseek(self) -> None:
        exempt = []
        for alias, host in self.canonical_rows():
            self.as_host(host)
            for tool in self.canonical_tools():
                out = self.bootstrap(CANON, "--only", tool)
                self.assertEqual(out.returncode, 0, out.stderr)
                if not self.granted(out, tool):
                    exempt.append((host, tool))
        self.assertEqual(exempt, [("beelink", "deepseek")], "the cortex grant is withheld from exactly one (host, agent) pair")

    def assert_refused(self, out: subprocess.CompletedProcess[str], why: str, needle: str = "FATAL") -> None:
        self.assertEqual(out.returncode, 1, (why, out.stdout, out.stderr))
        self.assertIn(needle, out.stderr, why)
        self.assertEqual(out.stdout, "", f"{why}: nothing may be planned or printed before the refusal")

    def test_an_unregistered_or_renamed_host_is_refused_not_granted(self) -> None:
        for host in ("not-in-the-fleet", "BEELINK", "beelink.", "beelink2", "Beelink", "honey"):
            self.as_host(host)
            for tool in self.canonical_tools():
                out = self.bootstrap(CANON, "--only", tool)
                self.assert_refused(out, f"{host}/{tool}", "no row in")
                self.assertIn("unresolved host identity", out.stderr)

    def test_the_valid_honey_control_survives_the_refusals_around_it(self) -> None:
        self.as_host("beelink")
        out = self.bootstrap(CANON, "--only", "deepseek")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(self.granted(out, "deepseek"))
        self.assertIn("no cortex grant: agent-deepseek", out.stdout)

    def test_the_independent_probe_reds_remove_fleet_ssv_or_the_host_row(self) -> None:
        import shutil
        for variant in ("no-fleet-file", "no-host-row", "fleet-file-is-a-directory", "fleet-file-unreadable", "fleet-file-empty"):
            conf = self.dir / variant
            shutil.copytree(CANON, conf)
            self.as_host("beelink")
            fleet = conf / "fleet.ssv"
            if variant == "no-fleet-file":
                fleet.unlink()
            elif variant == "no-host-row":
                fleet.write_text("".join(l for l in fleet.read_text().splitlines(True) if "beelink" not in l))
            elif variant == "fleet-file-is-a-directory":
                fleet.unlink()
                fleet.mkdir()
            elif variant == "fleet-file-unreadable":
                fleet.chmod(0)
            else:
                fleet.write_text("")
            out = self.bootstrap(conf, "--only", "deepseek")
            if variant == "fleet-file-unreadable" and os.access(fleet, os.R_OK):
                continue  # running as root: the mode bits do not bind
            self.assert_refused(out, variant)
            self.assertNotIn("usermod", out.stdout + out.stderr)

    def test_unresolved_host_identity_refuses(self) -> None:
        self.stub("hostname", "#!/bin/sh\nexit 1\n")
        self.assert_refused(self.bootstrap(CANON, "--only", "deepseek"), "hostname fails", "name is unresolved")
        self.stub("hostname", "#!/bin/sh\necho\n")
        self.assert_refused(self.bootstrap(CANON, "--only", "deepseek"), "hostname empty", "name is unresolved")

    def test_a_failing_hostname_with_partial_output_is_refused_not_trusted(self) -> None:
        # Hermes's measured edge: a stub that prints the valid Honey name AND exits 1 must not plan the grant (nor the exemption)
        for body, why in (("echo beelink; exit 1", "valid name, exit 1"), ("printf beelink; exit 2", "no newline, exit 2"),
                          ("echo beelink >&2; echo beelink; kill -9 $$", "killed after printing")):
            self.stub("hostname", f"#!/bin/sh\n{body}\n")
            for tool in ("codex", "deepseek"):
                self.assert_refused(self.bootstrap(CANON, "--only", tool), f"{why}/{tool}", "name is unresolved")
        for text, why in (("beelink\\nother", "two lines"), ("bee link", "space"), ("-beelink", "leading dash"), ("beelink;id", "metacharacter"),
                          ("$(id)", "substitution"), (".beelink", "leading dot")):
            self.stub("hostname", f"#!/bin/sh\nprintf '%b\\n' '{text}'\n")
            self.assert_refused(self.bootstrap(CANON, "--only", "deepseek"), why, "name is unresolved")
        self.as_host("beelink")  # the positive control still passes after all of the above
        self.assertFalse(self.granted(self.bootstrap(CANON, "--only", "deepseek"), "deepseek"))
        self.assertTrue(self.granted(self.bootstrap(CANON, "--only", "codex"), "codex"))

    def test_an_explicit_dash_row_exempts_nobody_but_missing_policy_is_not_a_dash(self) -> None:
        self.as_host("h1")
        for fleet in ("x h1 - all - -\n", "# alias host\nx h1 - all - - # a trailing comment\n"):
            out = self.bootstrap(self.scratch(fleet), "--only", "codex,deepseek")
            self.assertEqual(out.returncode, 0, (fleet, out.stderr))
            self.assertTrue(self.granted(out, "codex") and self.granted(out, "deepseek"), fleet)
        for fleet, why, needle in ((None, "no file", "missing or unreadable"), ("# alias host\n", "comments only", "no row in"),
                                   ("x h1\n", "hostname only", "no no-cortex column"), ("x h1 - all -\n", "row without the column", "no no-cortex column"),
                                   ("x h1 - all\n", "row without warm or column", "no no-cortex column"),
                                   ("x other - all - deepseek\n", "only another host", "no row in")):
            self.assert_refused(self.bootstrap(self.scratch(fleet), "--only", "codex,deepseek"), why, needle)

    def test_the_exemption_names_the_host_and_never_removes_a_membership(self) -> None:
        self.as_host("beelink")
        self.stub("id", STUB_ID)
        out = self.bootstrap(CANON, "--only", "deepseek")
        self.assertIn("no cortex grant: agent-deepseek (fleet.ssv no-cortex for beelink)", out.stdout)
        self.assertIn("NOTE: agent-deepseek is already in cortex; this script never removes it", out.stdout)
        self.assertNotIn("gpasswd", out.stdout.replace("gpasswd -d agent-deepseek cortex is a separate", ""))
        self.assertFalse(self.granted(out, "deepseek"))

    def test_the_exemption_does_not_leak_to_the_other_agents_of_the_same_host(self) -> None:
        self.as_host("beelink")
        out = self.bootstrap(CANON, "--only", "codex,deepseek")
        self.assertTrue(self.granted(out, "codex"))
        self.assertFalse(self.granted(out, "deepseek"))

    def test_refusals_ambiguous_malformed_or_unknown_never_grant_or_exempt_quietly(self) -> None:
        self.as_host("h1")
        for fleet, why in (("x h1 - all - deepseek\ny h1 - all - -\n", "two rows"),
                           ("x h1 - all -\ny h1 - all -\n", "two rows, neither with the column"),
                           ("x h1 - all - -\ny h1 - all - -\n", "two identical dash rows"),
                           ("x h1 - all - nosuchtool\n", "unknown tool"), ("x h1 - all - deepseek;rm\n", "shell metacharacter"),
                           ("x h1 - all - deepseek,,\n", "trailing double comma (Hermes's measured edge)"), ("x h1 - all - deepseek,\n", "trailing comma"),
                           ("x h1 - all - ,deepseek\n", "leading comma"), ("x h1 - all - codex,,deepseek\n", "repeated comma inside"),
                           ("x h1 - all - deepseek,-\n", "mixed dash token after"), ("x h1 - all - -,deepseek\n", "mixed dash token before"),
                           ("x h1 - all - --\n", "double dash"), ("x h1 - all - -deepseek\n", "dash prefix"), ("x h1 - all - deepseek-\n", "dash suffix"),
                           ("x h1 - all - *\n", "glob"), ("x h1 - all - ,\n", "bare comma"), ("x h1 - all - Deepseek\n", "uppercase"), ("x h1 - all - $(id)\n", "substitution")):
            out = self.bootstrap(self.scratch(fleet), "--only", "deepseek")
            self.assert_refused(out, why, "more than one row" if why.startswith("two") else "no-cortex")

    def test_a_canonical_comma_list_still_exempts_each_named_tool(self) -> None:
        self.as_host("h1")
        out = self.bootstrap(self.scratch("x h1 - all - codex,deepseek\n"), "--only", "codex,deepseek")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertFalse(self.granted(out, "codex") or self.granted(out, "deepseek"))
        self.assertEqual(out.stdout.count("no cortex grant:"), 2)

    def test_whitespace_in_the_list_never_silently_truncates_it(self) -> None:
        # Hermes's requested cases. awk field splitting trims leading/trailing space and tabs between columns (harmless, asserted equal to the clean row);
        # whitespace INSIDE the list used to split it and drop the tail (rev10: "codex , deepseek" exempted only codex and granted deepseek cortex).
        self.as_host("h1")
        clean = self.bootstrap(self.scratch("x h1 - all - deepseek\n"), "--only", "codex,deepseek")
        self.assertEqual(clean.returncode, 0, clean.stderr)
        self.assertTrue(self.granted(clean, "codex") and not self.granted(clean, "deepseek"))
        for fleet, why in (("x h1 - all -  deepseek\n", "leading space"), ("x h1 - all - deepseek \n", "trailing space"),
                           ("x\th1\t-\tall\t-\tdeepseek\n", "tab-separated row"), ("  x h1 - all - deepseek\n", "indented row")):
            out = self.bootstrap(self.scratch(fleet), "--only", "codex,deepseek")
            self.assertEqual((out.returncode, out.stdout), (0, clean.stdout), why)
        for fleet, why in (("x h1 - all - codex , deepseek\n", "space around a comma (deepseek would be GRANTED)"), ("x h1 - all - deepseek ,codex\n", "space before a comma"),
                           ("x h1 - all - deepseek, codex\n", "space after a comma"), ("x h1 - all - deepseek\tcodex\n", "tab inside the list"),
                           ("x h1 - all - deepseek codex\n", "space-separated list"), ("x h1 - all - - deepseek\n", "dash then a tool"),
                           ("x h1 - all - deepseek extra\n", "text after the list"), ("x h1 - all - deepseek\r\n", "carriage return")):
            out = self.bootstrap(self.scratch(fleet), "--only", "codex,deepseek")
            self.assert_refused(out, why, "no-cortex" if why in ("space after a comma", "carriage return") else "extra columns")
        # a newline ends the row: a list on the NEXT line is a different (host-less) line and never part of the decision
        out = self.bootstrap(self.scratch("x h1 - all - -\ndeepseek\n"), "--only", "codex,deepseek")
        self.assertTrue(out.returncode == 0 and self.granted(out, "codex") and self.granted(out, "deepseek"), "an orphan line cannot exempt anything")

    def test_hostname_valid_but_unknown_host_is_refused_not_trusted(self) -> None:
        # a well-formed name that is the wrong host (policy rows are keyed on beelink): shape validation cannot catch it, the cross-check against the rows must
        for host in ("honey", "Honey", "kikin-kushi2", "beelink-2", "gille", "localhost", "a"):
            self.as_host(host)
            for tool in self.canonical_tools():
                out = self.bootstrap(CANON, "--only", tool)
                self.assert_refused(out, f"{host}/{tool}", "no row in")
                self.assertIn("unresolved host identity", out.stderr)
                self.assertNotIn("usermod", out.stdout + out.stderr)
        self.as_host("beelink")
        self.assertFalse(self.granted(self.bootstrap(CANON, "--only", "deepseek"), "deepseek"))

    def test_scratch_exemption_is_per_host_and_per_tool(self) -> None:
        conf = self.scratch("a h1 - all - deepseek\nb h2 - all - -\n")
        self.as_host("h1")
        out = self.bootstrap(conf, "--only", "codex,deepseek")
        self.assertTrue(self.granted(out, "codex") and not self.granted(out, "deepseek"))
        self.as_host("h2")
        out = self.bootstrap(conf, "--only", "codex,deepseek")
        self.assertTrue(self.granted(out, "codex") and self.granted(out, "deepseek"))

    def fleet_check(self, fleet: str, groups: str) -> subprocess.CompletedProcess[str]:
        conf = self.dir / "fc"
        conf.mkdir(exist_ok=True)
        (conf / "uids.ssv").write_text("# tool uid provision\nghost 2099 yes\n")
        (conf / "fleet.ssv").write_text(fleet)
        self.stub("hostname", "#!/bin/sh\necho h1\n")
        self.stub("getent", STUB_GETENT)
        self.stub("id", f'#!/bin/sh\ncase "$*" in "-nG agent-ghost") echo "{groups}"; exit 0 ;; esac\nexec /usr/bin/id "$@"\n')
        env = dict(os.environ, PATH=f"{self.stubs}:{os.environ['PATH']}", AGENT_CLI_CONF=str(conf))
        return subprocess.run([str(CHECK)], env=env, text=True, capture_output=True, check=False)

    def test_fleet_check_expects_the_exempt_tool_out_of_cortex_and_others_in(self) -> None:
        plain = self.fleet_check("x h1 - ghost -\n", "agent-ghost")
        self.assertIn("DRIFT agent-ghost not-in-cortex", plain.stdout)
        exempt_out = self.fleet_check("x h1 - ghost - ghost\n", "agent-ghost")
        self.assertIn("OK agent-ghost uid 2099", exempt_out.stdout)
        self.assertNotIn("not-in-cortex", exempt_out.stdout)
        exempt_in = self.fleet_check("x h1 - ghost - ghost\n", "agent-ghost cortex")
        self.assertIn("DRIFT agent-ghost in-cortex(host-exempt)", exempt_in.stdout)
        other = self.fleet_check("x h1 - ghost - -\n", "agent-ghost cortex")
        self.assertIn("OK agent-ghost uid 2099", other.stdout)

    def test_fleet_check_refuses_a_malformed_list_before_it_reaches_a_shell(self) -> None:
        out = self.fleet_check("x h1 - ghost - ghost;touch/tmp/pwn\n", "agent-ghost")
        self.assertIn("REFUSED x: malformed no-cortex list", out.stdout)
        self.assertEqual(out.returncode, 2)
        self.assertNotIn("agent-ghost", out.stdout)
        for split in ("ghost , ghost2", "ghost ,ghost2", "ghost extra"):
            out = self.fleet_check(f"x h1 - ghost - {split}\n", "agent-ghost")
            self.assertIn("REFUSED x: extra columns after no-cortex", out.stdout, split)
            self.assertEqual(out.returncode, 2, split)
        out = self.fleet_check("x h1 - ghost - ghost # note\n", "agent-ghost")
        self.assertIn("OK agent-ghost uid 2099", out.stdout)
        for bad in ("ghost,,", "ghost,", ",ghost", "-,ghost"):
            out = self.fleet_check(f"x h1 - ghost - {bad}\n", "agent-ghost")
            self.assertIn("REFUSED x: malformed no-cortex list", out.stdout, bad)
            self.assertEqual(out.returncode, 2, bad)


if __name__ == "__main__":
    unittest.main()
