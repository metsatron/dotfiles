from __future__ import annotations

import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import unittest


HERE = Path(__file__).resolve()
BIN = HERE.parents[3] / "bin"
MANAGER = BIN / "telegram-agent-host"
DASHBOARD_OWNER = BIN / "hermes-dashboard-owner"
DSH_WEB_URL = BIN / "deepseek-harness-web-url"


class WebUiOwnershipTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.state = self.root / "state"
        self.agents = self.root / "agents"
        self.fake_bin = self.root / "bin"
        for path in (self.home, self.state, self.agents, self.fake_bin):
            path.mkdir(parents=True)
        self.capture = self.root / "dashboard-env"
        hermes = self.fake_bin / "hermes"
        hermes.write_text(
            "#!/bin/sh\n"
            "{\n"
            "  printf '%s\\n' \"${HERMES_DASHBOARD_PUBLIC_URL:-}\"\n"
            "  printf '%s\\n' \"${HERMES_DASHBOARD_BASIC_AUTH_USERNAME:-}\"\n"
            "  printf '%s\\n' \"${HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH:-}\"\n"
            "  printf '%s\\n' \"${HERMES_DASHBOARD_BASIC_AUTH_SECRET:-}\"\n"
            f"}} > {str(self.capture)!r}\n"
            "trap 'exit 0' TERM INT\n"
            "while :; do sleep 1; done\n",
            encoding="utf-8",
        )
        hermes.chmod(hermes.stat().st_mode | stat.S_IXUSR)

    def tearDown(self) -> None:
        owner = self.state / "telegram-agents/hermes-dashboard.json"
        if owner.exists():
            subprocess.run(
                [str(DASHBOARD_OWNER), "stop", "--state", str(owner)],
                text=True,
                capture_output=True,
                env=self.environment(),
                timeout=5,
            )
        self.temp.cleanup()

    def environment(self) -> dict[str, str]:
        env = os.environ.copy()
        env.update({
            "HOME": str(self.home),
            "XDG_STATE_HOME": str(self.state),
            "DOTCORTEX_AGENTS_DIR": str(self.agents),
            "DOTCORTEX_BIN_DIR": str(BIN),
            "HERMES_DASHBOARD_BIN": str(self.fake_bin / "hermes"),
            "HERMES_DASHBOARD_SKIP_DISCOVERY": "1",
            "HERMES_TEST_CAPTURE": str(self.capture),
            "PATH": str(self.fake_bin) + os.pathsep + "/usr/local/bin:/usr/bin:/bin",
        })
        return env

    def run_manager(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(MANAGER), *args],
            text=True,
            capture_output=True,
            env=self.environment(),
            timeout=8,
        )

    def write_dashboard_env(self, values: list[str], mode: int = 0o600) -> Path:
        path = self.home / ".hermes/dashboard.env"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(values) + "\n", encoding="utf-8")
        path.chmod(mode)
        return path

    def test_dashboard_start_stop_and_intentional_stop_use_one_owner(self) -> None:
        result = self.run_manager("start", "hermes-dashboard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.capture.read_text(encoding="utf-8").splitlines(), ["http://localhost", "", "", ""])
        status = self.run_manager("status", "hermes-dashboard")
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertIn("hermes dashboard: RUNNING", status.stdout)

        stopped = self.run_manager("stop", "hermes-dashboard")
        self.assertEqual(stopped.returncode, 0, stopped.stderr)
        marker = self.state / "telegram-agents/intentional-stop/hermes-dashboard"
        self.assertTrue(marker.exists())

        restarted = self.run_manager("start", "hermes-dashboard")
        self.assertEqual(restarted.returncode, 0, restarted.stderr)
        self.assertFalse(marker.exists())

    def test_dashboard_placeholders_and_bad_permissions_fall_back_local(self) -> None:
        self.write_dashboard_env([
            "HERMES_DASHBOARD_PUBLIC_URL=https://YOUR_TAILNET_HOST:YOUR_HERMES_DASHBOARD_PORT",
            "HERMES_DASHBOARD_BASIC_AUTH_USERNAME=YOUR_HERMES_DASHBOARD_BASIC_AUTH_USERNAME",
            "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=YOUR_HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH",
        ], mode=0o644)
        result = self.run_manager("start", "hermes-dashboard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("mode 0600", result.stdout)
        self.assertEqual(self.capture.read_text(encoding="utf-8").splitlines()[0], "http://localhost")

    def test_dashboard_provisioned_hash_arms_public_url_without_plaintext(self) -> None:
        self.write_dashboard_env([
            "HERMES_DASHBOARD_PUBLIC_URL=https://fixture.invalid",
            "HERMES_DASHBOARD_BASIC_AUTH_USERNAME=fixture-user",
            "HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH=scrypt$fixture-hash",
            "HERMES_DASHBOARD_BASIC_AUTH_SECRET=fixture-secret",
        ])
        result = self.run_manager("start", "hermes-dashboard")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("authentication armed", result.stdout)
        self.assertEqual(
            self.capture.read_text(encoding="utf-8").splitlines(),
            ["https://fixture.invalid", "fixture-user", "scrypt$fixture-hash", "fixture-secret"],
        )

    def test_dsh_auth_path_is_private_and_service_output_is_redacted(self) -> None:
        state = self.root / "dsh-auth-path"
        fake_token = "fixture-token"
        capture = subprocess.run(
            [str(DSH_WEB_URL), "capture", "--state-file", str(state)],
            input=f"dsh web: http://localhost/?token={fake_token}\n",
            text=True,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(capture.returncode, 0, capture.stderr)
        self.assertNotIn(fake_token, capture.stdout)
        self.assertIn("token=[REDACTED]", capture.stdout)
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o600)

        private_env = self.root / "deepseek.env"
        private_env.write_text("DSH_WEB_TRUSTED_HOST=fixture.invalid\n", encoding="utf-8")
        private_env.chmod(0o600)
        shown = subprocess.run(
            [str(DSH_WEB_URL), "show", "--env-file", str(private_env), "--state-file", str(state)],
            text=True,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(shown.returncode, 0, shown.stderr)
        self.assertEqual(shown.stdout.strip(), f"https://fixture.invalid/?token={fake_token}")

    def test_dsh_placeholder_authority_fails_closed(self) -> None:
        state = self.root / "dsh-auth-path"
        state.write_text("/?token=fixture-token\n", encoding="utf-8")
        state.chmod(0o600)
        private_env = self.root / "deepseek.env"
        private_env.write_text("DSH_WEB_TRUSTED_HOST=YOUR_TAILNET_HOST:YOUR_DSH_WEB_PORT\n", encoding="utf-8")
        private_env.chmod(0o600)
        result = subprocess.run(
            [str(DSH_WEB_URL), "show", "--env-file", str(private_env), "--state-file", str(state)],
            text=True,
            capture_output=True,
            timeout=5,
        )
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("fixture-token", result.stderr)

    def test_public_templates_hold_placeholders_only(self) -> None:
        templates = HERE.parents[3] / "../.bots/templates"
        dashboard = (templates / "hermes-dashboard.env").resolve().read_text(encoding="utf-8")
        deepseek = (templates / "deepseek-harness-telegram.env").resolve().read_text(encoding="utf-8")
        self.assertIn("YOUR_TAILNET_HOST", dashboard)
        self.assertIn("YOUR_HERMES_DASHBOARD_BASIC_AUTH_PASSWORD_HASH", dashboard)
        self.assertIn("DSH_WEB_TRUSTED_HOST=YOUR_TAILNET_HOST:YOUR_DSH_WEB_PORT", deepseek)
        self.assertNotIn(".ts.net", dashboard + deepseek)


if __name__ == "__main__":
    unittest.main()
