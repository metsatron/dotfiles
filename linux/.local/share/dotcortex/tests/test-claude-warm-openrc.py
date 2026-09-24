#!/usr/bin/env python3
from __future__ import annotations

import os
import pwd
import re
import socket
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HELPER = ROOT / "linux/.local/bin/claude-warm-openrc-apply"
USER = pwd.getpwuid(os.getuid()).pw_name
STUB = "#!/bin/sh\nprintf '%s %s\\n' \"$(basename \"$0\")\" \"$*\" >> \"$STUB_LOG\"\n"


def functional(text: str) -> list[str]:
    lines = []
    for index, line in enumerate(text.splitlines()):
        if index == 0:
            lines.append(line)
            continue
        if line.lstrip().startswith("#"):
            continue
        line = re.sub(r'(["\'])\s+#\s.*$', r"\1", line).rstrip()
        if line:
            lines.append(line)
    return lines


class OpenRCBootOwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.bin = base / "bin"
        self.bin.mkdir()
        self.log = base / "stub.log"
        self.target = base / "init.d"
        self.target.mkdir()
        self.runlevel = base / "runlevels"
        self.runlevel.mkdir()
        (self.bin / "sudo").write_text('#!/bin/sh\nprintf "sudo %s\\n" "$*" >> "$STUB_LOG"\n[ "$1" = -n ] && shift\nexec "$@"\n')
        (self.bin / "rc-update").write_text(
            STUB + '[ "$1" = add ] && [ "${RC_STUB_LINK:-1}" = 1 ] && ln -sf "$CLAUDE_WARM_OPENRC_TARGET/$2" "$CLAUDE_WARM_OPENRC_RUNLEVEL/$2"\nexit 0\n')
        for name in ("rc-service", "su", "tmux", "pkill", "service"):
            (self.bin / name).write_text(STUB)
        for stub in self.bin.iterdir():
            stub.chmod(0o755)
        self.env = dict(os.environ, PATH=f"{self.bin}:/usr/bin:/bin", STUB_LOG=str(self.log),
                        CLAUDE_WARM_OPENRC_TARGET=str(self.target),
                        CLAUDE_WARM_OPENRC_RUNLEVEL=str(self.runlevel),
                        CLAUDE_WARM_OPENRC_PROBE="openrc")

    def tearDown(self):
        self.tmp.cleanup()

    def helper(self, *args, **extra):
        env = dict(self.env, **extra)
        base = ["--user", USER, "--cwd", "/srv/warm", "--agent", "fixture-opus"]
        return subprocess.run(["bash", str(HELPER), *base, *args], capture_output=True, text=True, env=env)

    def calls(self):
        return self.log.read_text().splitlines() if self.log.exists() else []

    def test_dry_run_is_default_and_renders_the_contract(self):
        result = self.helper("--", "--model", "claude-opus-4-8")
        self.assertEqual(result.returncode, 0, result.stderr)
        text = result.stdout
        self.assertTrue(text.startswith("#!/sbin/openrc-run\n"))
        for needle in ('name="claude-warm"', f'warm_user="{USER}"', 'warm_cwd="/srv/warm"',
                       'warm_agent="fixture-opus"', 'xdg="/run/warm"', 'warm_log="/var/log/claude-warm.log"',
                       "claude-warm --model claude-opus-4-8 >>"):
            self.assertIn(needle, text)
        self.assertNotIn("/run/user/", text.replace("/run/user/<uid>", ""))
        self.assertEqual(list(self.target.iterdir()), [])
        self.assertEqual(self.calls(), [])

    def test_check_detects_drift(self):
        rendered = self.helper("--", "--model", "m").stdout
        (self.target / "claude-warm").write_text(rendered)
        self.assertEqual(self.helper("--check", "--", "--model", "m").returncode, 0)
        (self.target / "claude-warm").write_text(rendered.replace("use net dns", "need net"))
        self.assertEqual(self.helper("--check", "--", "--model", "m").returncode, 1)

    def test_apply_refusals(self):
        self.assertEqual(self.helper("--apply").returncode, 2)
        wrong = self.helper("--apply", "--host", "not-" + socket.gethostname())
        self.assertEqual(wrong.returncode, 1)
        none = self.helper("--apply", "--host", socket.gethostname(), CLAUDE_WARM_OPENRC_PROBE="none")
        self.assertEqual(none.returncode, 3)
        self.assertIn("not OpenRC", none.stderr)
        self.assertEqual(list(self.target.iterdir()), [])

    def test_apply_installs_verifies_link_and_starts_nothing(self):
        result = self.helper("--apply", "--host", socket.gethostname(), "--", "--model", "m")
        self.assertEqual(result.returncode, 0, result.stderr)
        script = self.target / "claude-warm"
        self.assertTrue(script.is_file())
        self.assertEqual(oct(script.stat().st_mode & 0o777), "0o755")
        self.assertTrue((self.runlevel / "claude-warm").exists())
        verbs = " ".join(self.calls())
        self.assertIn("rc-update add claude-warm default", verbs)
        for forbidden in ("rc-service", "su ", "tmux", "pkill", "service "):
            self.assertNotIn(forbidden, verbs)

    def test_apply_fails_when_rc_update_lies(self):
        result = self.helper("--apply", "--host", socket.gethostname(), "--", "--model", "m", RC_STUB_LINK="0")
        self.assertEqual(result.returncode, 1)
        self.assertIn("would not start at boot", result.stderr)

    def test_unsafe_values_refused(self):
        self.assertEqual(self.helper("--", "--model", "m; rm -rf /").returncode, 2)
        env = dict(self.env)
        bad = subprocess.run(["bash", str(HELPER), "--user", USER, "--cwd", "/srv/a b", "--agent", "x"],
                             capture_output=True, text=True, env=env)
        self.assertEqual(bad.returncode, 2)

    @unittest.skipUnless(socket.gethostname().split(".")[0] == "beelink"
                         and Path("/etc/init.d/claude-warm").is_file(), "live parity runs on Honey only")
    def test_rendered_script_matches_honeys_live_boot_owner(self):
        result = subprocess.run(
            ["bash", str(HELPER), "--user", "gille", "--cwd", "/home/gille/metsatron-peer", "--session", "warm",
             "--agent", "honey-opus", "--", "--model", "claude-opus-4-8"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(functional(result.stdout), functional(Path("/etc/init.d/claude-warm").read_text()))


if __name__ == "__main__":
    unittest.main()
