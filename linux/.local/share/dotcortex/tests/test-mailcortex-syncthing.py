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

    def test_package_requires_manifest_and_help_has_no_effect(self) -> None:
        result = self.run_cmd(PACKAGE, "--apply", env=self.env | {"MAILCORTEX_TEST_MANIFEST": str(self.base / "absent")})
        self.assertEqual(result.returncode, 1)
        self.assertFalse(self.calls.exists())
        result = self.run_cmd(PACKAGE, "-h")
        self.assertEqual(result.returncode, 0)
        self.assertFalse(self.calls.exists())

    def test_service_render_and_init_selection(self) -> None:
        result = self.run_cmd(SERVICE)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("@reboot", result.stdout)
        self.assertIn("*/3 * * * *", result.stdout)
        self.assertIn("--run", result.stdout)
        self.assertFalse((self.base / "cron").exists())
        systemd = self.env | {"MAILCORTEX_TEST_INIT": "systemd"}
        result = self.run_cmd(SERVICE, "--dry-run", env=systemd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("systemctl --user enable --now mailcortex-syncthing.service", result.stdout)
        refused = self.run_cmd(SERVICE, "--dry-run", env=self.env | {"MAILCORTEX_TEST_INIT": "unknown"})
        self.assertEqual(refused.returncode, 2)
        init = self.run_cmd(SERVICE, "--dry-run", env=self.env | {"MAILCORTEX_TEST_INIT": "init"})
        self.assertEqual(init.returncode, 0)
        self.assertIn("@reboot", init.stdout)

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
        systemd = env | {"MAILCORTEX_TEST_INIT": "systemd"}
        result = self.run_cmd(SERVICE, "--apply", env=systemd)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.calls.read_text()
        self.assertIn("sudo -n loginctl enable-linger", calls)
        self.assertIn("systemctl --user daemon-reload", calls)
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
        owner = self.base / ".local/bin/mailcortex-syncthing-service"
        owner.parent.mkdir(parents=True)
        owner.symlink_to(SERVICE)
        applied = self.run_cmd(SERVICE, "--apply", env=env)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        absent = self.run_cmd(SERVICE, "--check", env=env)
        self.assertEqual(absent.returncode, 1)
        first = subprocess.Popen([str(SERVICE), "--run"], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            for _ in range(40):
                if self.calls.exists():
                    break
                time.sleep(0.05)
            self.assertTrue(self.calls.exists(), "first owner did not start")
            checked = self.run_cmd(SERVICE, "--check", env=env)
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertIn("private daemon verified", checked.stdout)
            owned_pid = (self.base / ".local/state/mailcortex/syncthing.pid").read_text().split()[0]
            fragment = self.base / ".config/systemd/user/mailcortex-syncthing.service"
            fragment.parent.mkdir(parents=True, exist_ok=True)
            fragment.write_text("[Install]\nWantedBy=default.target\n")
            wants = self.base / ".config/systemd/user/default.target.wants/mailcortex-syncthing.service"
            wants.parent.mkdir(parents=True)
            wants.symlink_to(fragment)
            systemctl = self.fakebin / "systemctl"
            systemctl.write_text(
                "#!/bin/sh\n"
                f'case " $* " in *" is-enabled "*) echo linked; exit 1 ;; '
                f'*" show -P FragmentPath "*) echo {fragment} ;; '
                f'*" show -P MainPID "*) echo {owned_pid} ;; esac\n'
            )
            systemctl.chmod(0o755)
            loginctl = self.fakebin / "loginctl"
            loginctl.write_text("#!/bin/sh\necho yes\n")
            loginctl.chmod(0o755)
            systemd_env = env | {"MAILCORTEX_TEST_INIT": "systemd"}
            systemd_check = self.run_cmd(SERVICE, "--check", env=systemd_env)
            self.assertEqual(systemd_check.returncode, 0, systemd_check.stderr)
            wants.unlink()
            disabled_linked_unit = self.run_cmd(SERVICE, "--check", env=systemd_env)
            self.assertEqual(disabled_linked_unit.returncode, 1)
            self.assertIn("not enabled for default.target", disabled_linked_unit.stderr)
            wants.symlink_to(fragment)
            systemctl.write_text(systemctl.read_text().replace(f"echo {owned_pid}", "echo 1"))
            wrong_unit_pid = self.run_cmd(SERVICE, "--check", env=systemd_env)
            self.assertEqual(wrong_unit_pid.returncode, 1)
            second = self.run_cmd(SERVICE, "--run", env=env)
            self.assertEqual(second.returncode, 0, second.stderr)
            starts = self.calls.read_text().splitlines()
            self.assertEqual(len(starts), 1)
            self.assertIn("serve --home=", starts[0])
        finally:
            first.terminate()
            first.wait(timeout=5)
        stale = self.run_cmd(SERVICE, "--check", env=env)
        self.assertEqual(stale.returncode, 1)

    def test_runtime_rechecks_readiness_and_rejects_unrelated_process(self) -> None:
        (self.base / "Mail").mkdir()
        config = self.base / ".config/mailcortex/syncthing"
        config.mkdir(parents=True)
        for name in ("config.xml", "cert.pem", "key.pem"):
            (config / name).write_text(name)
        binary = self.base / "syncthing"
        binary.write_text('#!/bin/sh\necho launched >> "$CALLS"\nsleep 20\n')
        binary.chmod(0o755)
        env = self.env | {"MAILCORTEX_TEST_SYNCTHING_BIN": str(binary)}
        blocked = self.run_cmd(SERVICE, "--run", env=env)
        self.assertEqual(blocked.returncode, 1)
        self.assertFalse(self.calls.exists())
        systemd_blocked = self.run_cmd(SERVICE, "--run", env=env | {"MAILCORTEX_TEST_INIT": "systemd"})
        self.assertEqual(systemd_blocked.returncode, 1)
        ready = self.base / ".config/mailcortex/syncthing-ready"
        ready.touch()
        pgrep = self.fakebin / "pgrep"
        pgrep.write_text("#!/bin/sh\nexit 0\n")
        pgrep.chmod(0o755)
        unrelated = self.run_cmd(SERVICE, "--run", env=env)
        self.assertEqual(unrelated.returncode, 3)
        self.assertFalse(self.calls.exists())
        record = self.base / ".local/state/mailcortex/syncthing.pid"
        record.parent.mkdir(parents=True, exist_ok=True)
        record.write_text(f"{os.getpid()} 0\n")
        owner = self.base / ".local/bin/mailcortex-syncthing-service"
        owner.parent.mkdir(parents=True)
        owner.symlink_to(SERVICE)
        applied = self.run_cmd(SERVICE, "--apply", env=env)
        self.assertEqual(applied.returncode, 0, applied.stderr)
        checked = self.run_cmd(SERVICE, "--check", env=env)
        self.assertEqual(checked.returncode, 1)
        self.assertIn("private Syncthing owner absent", checked.stderr)


if __name__ == "__main__":
    unittest.main()
