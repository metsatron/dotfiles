#!/usr/bin/env python3
from __future__ import annotations

import os
import pathlib
import subprocess
import tempfile
import time
import unittest


ROOT = pathlib.Path(__file__).resolve().parents[5]
PACKAGE = ROOT / "debian/.local/bin/mailcortex-syncthing-package"
SERVICE = ROOT / "linux/.local/bin/mailcortex-syncthing-service"


class MailCortexSyncthingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = pathlib.Path(self.temp.name)
        self.fakebin = self.base / "bin"
        self.fakebin.mkdir()
        self.manifest = self.base / "mailcortex.ssv"
        self.manifest.write_text('syncthing "" network mailcortex ""\n')
        self.calls = self.base / "calls"
        self.env = os.environ.copy()
        self.env.update(
            HOME=str(self.base),
            PATH=f"{self.fakebin}:/usr/bin:/bin",
            MAILCORTEX_TEST_HOSTNAME="kikin-kushi",
            MAILCORTEX_TEST_INIT="sysv",
            MAILCORTEX_TEST_MANIFEST=str(self.manifest),
            MAILCORTEX_TEST_CRON_TARGET=str(self.base / "cron"),
            CALLS=str(self.calls),
        )
        for name, body in {
            "apt-get": """case " $* " in *' -s '*) printf '%s\\n' "${SIMULATION:-Inst syncthing (1.0)}" ;; *) echo "apt-get $*" >> "$CALLS" ;; esac""",
            "dpkg-query": """name="${@: -1}"; if [ "${INSTALLED_NAME:-}" = "$name" ] || { [ "${POST_INSTALLED:-}" = "$name" ] && [ -e "$CALLS" ]; }; then printf 'ii '; else exit 1; fi""",
            "sudo": 'echo "sudo $*" >> "$CALLS"',
            "pgrep": "exit 1",
        }.items():
            path = self.fakebin / name
            path.write_text("#!/usr/bin/env bash\n" + body + "\n")
            path.chmod(0o755)

    def run_cmd(self, path: pathlib.Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run([str(path), *args], env=env or self.env, text=True, capture_output=True)

    def test_package_dry_run_and_explicit_apply(self) -> None:
        result = self.run_cmd(PACKAGE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("dry-run only", result.stdout)
        self.assertFalse(self.calls.exists())
        env = self.env | {"POST_INSTALLED": "syncthing"}
        result = self.run_cmd(PACKAGE, "--apply", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text()
        self.assertIn("apt-get install -y --no-remove --no-upgrade --no-install-recommends", calls)
        self.assertNotIn("upgrade", calls.replace("--no-upgrade", ""))
        self.assertNotIn("remove -y", calls)

    def test_package_refuses_removal_upgrade_and_extra_manifest_row(self) -> None:
        for simulation in ("Remv unrelated", "Purg unrelated"):
            result = self.run_cmd(PACKAGE, "--apply", env=self.env | {"SIMULATION": simulation})
            self.assertEqual(result.returncode, 3)
            self.assertFalse(self.calls.exists())
        result = self.run_cmd(PACKAGE, "--apply", env=self.env | {"INSTALLED_NAME": "syncthing"})
        self.assertEqual(result.returncode, 3)
        self.manifest.write_text(self.manifest.read_text() + 'unrelated "" network mailcortex ""\n')
        result = self.run_cmd(PACKAGE, "--apply")
        self.assertEqual(result.returncode, 2)

    def test_package_refuses_unknown_host_and_help_has_no_effect(self) -> None:
        result = self.run_cmd(PACKAGE, "--apply", env=self.env | {"MAILCORTEX_TEST_HOSTNAME": "other"})
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.calls.exists())
        result = self.run_cmd(PACKAGE, "-h")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_service_render_and_host_refusal(self) -> None:
        result = self.run_cmd(SERVICE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("@reboot", result.stdout)
        self.assertIn("*/3 * * * *", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertFalse((self.base / "cron").exists())
        x230 = self.env | {"MAILCORTEX_TEST_HOSTNAME": "ThinkPad-X230", "MAILCORTEX_TEST_INIT": "systemd"}
        result = self.run_cmd(SERVICE, "--dry-run", env=x230)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("systemctl --user enable --now mailcortex-syncthing.service", result.stdout)
        refused = self.run_cmd(SERVICE, "--dry-run", env=self.env | {"MAILCORTEX_TEST_HOSTNAME": "unknown"})
        self.assertEqual(refused.returncode, 2)
        mismatch = self.run_cmd(SERVICE, "--dry-run", env=self.env | {"MAILCORTEX_TEST_INIT": "systemd"})
        self.assertEqual(mismatch.returncode, 2)

    def test_service_apply_paths_are_fixture_bound(self) -> None:
        (self.base / "Mail").mkdir()
        ready = self.base / ".config/mailcortex/syncthing-ready"
        ready.parent.mkdir(parents=True)
        ready.touch()
        config = self.base / ".config/mailcortex/syncthing"
        config.mkdir()
        for name in ("config.xml", "cert.pem", "key.pem"):
            (config / name).write_text(name)
        binary = self.base / "syncthing"
        binary.write_text("#!/bin/sh\nexit 0\n")
        binary.chmod(0o755)
        owner = self.base / ".local/bin/mailcortex-syncthing-service"
        owner.parent.mkdir(parents=True)
        owner.symlink_to(SERVICE)
        env = self.env | {"MAILCORTEX_TEST_SYNCTHING_BIN": str(binary)}
        result = self.run_cmd(SERVICE, "--apply", env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        cron = (self.base / "cron").read_text()
        self.assertIn("@reboot", cron)
        self.assertIn(str(owner) + " --run", cron)
        systemctl = self.fakebin / "systemctl"
        systemctl.write_text(
            '#!/bin/sh\n'
            'echo "systemctl $*" >> "$CALLS"\n'
            f'case " $* " in *" show "*) echo {self.base}/.config/systemd/user/mailcortex-syncthing.service ;; esac\n'
        )
        systemctl.chmod(0o755)
        x230 = env | {"MAILCORTEX_TEST_HOSTNAME": "ThinkPad-X230", "MAILCORTEX_TEST_INIT": "systemd"}
        result = self.run_cmd(SERVICE, "--apply", env=x230)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text()
        self.assertIn("sudo -n loginctl enable-linger", calls)
        self.assertIn("systemctl --user enable --now mailcortex-syncthing.service", calls)

    def test_sysv_singleton_owner(self) -> None:
        (self.base / "Mail").mkdir()
        ready = self.base / ".config/mailcortex/syncthing-ready"
        ready.parent.mkdir(parents=True)
        ready.touch()
        config = self.base / ".config/mailcortex/syncthing"
        config.mkdir()
        for name in ("config.xml", "cert.pem", "key.pem"):
            (config / name).write_text(name)
        binary = self.base / "syncthing"
        binary.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$CALLS"\nsleep 20\n')
        binary.chmod(0o755)
        env = self.env | {"MAILCORTEX_TEST_SYNCTHING_BIN": str(binary)}
        first = subprocess.Popen([str(SERVICE), "--run"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(40):
                if self.calls.exists():
                    break
                time.sleep(0.05)
            self.assertTrue(self.calls.exists(), "first owner did not start")
            second = self.run_cmd(SERVICE, "--run", env=env)
            self.assertEqual(second.returncode, 0, second.stderr)
            starts = self.calls.read_text().splitlines()
            self.assertEqual(len(starts), 1)
            self.assertIn("serve --home=", starts[0])
        finally:
            first.terminate()
            first.wait(timeout=5)


if __name__ == "__main__":
    unittest.main()
