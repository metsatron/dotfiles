#!/usr/bin/env python3
from __future__ import annotations

import os
import signal
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
LAUNCHER = ROOT / "all/.local/bin/herdr-web-tailnet"
INSTALLER = ROOT / "linux/.local/bin/herdr-web-boot-install"


class HerdrWebBootTests(unittest.TestCase):
    def make_fake_stack(self, root: Path, empty_ip_calls: int = 0) -> tuple[dict[str, str], Path]:
        bin_dir = root / "bin"
        bin_dir.mkdir()
        counter = root / "tailscale-count"
        marker = root / "bridge-calls"
        tailscale = bin_dir / "tailscale"
        tailscale.write_text(
            "#!/bin/sh\n"
            f"n=$(cat '{counter}' 2>/dev/null || echo 0)\n"
            "n=$((n + 1))\n"
            f"printf '%s\\n' \"$n\" > '{counter}'\n"
            f"[ \"$n\" -le {empty_ip_calls} ] || printf '%s\\n' 100.64.0.1\n",
            encoding="utf-8",
        )
        herdr = bin_dir / "herdr"
        herdr.write_text(
            "#!/bin/sh\n"
            "[ \"${1:-}\" = status ] && { printf '%s\\n' 'status: running'; exit 0; }\n"
            "exit 1\n",
            encoding="utf-8",
        )
        bridge = bin_dir / "bridge"
        bridge.write_text(
            "#!/bin/sh\n"
            f"printf '%s\\n' \"$*\" >> '{marker}'\n"
            "sleep 30\n",
            encoding="utf-8",
        )
        for path in (tailscale, herdr, bridge):
            path.chmod(0o755)
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(root),
                "HERDR_WEB_TAILSCALE_BIN": str(tailscale),
                "HERDR_WEB_HERDR_BIN": str(herdr),
                "HERDR_WEB_APP": str(bridge),
                "HERDR_WEB_RETRY_SECONDS": "0.01",
            }
        )
        return env, marker

    def wait_for(self, path: Path, timeout: float = 3.0) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return
            time.sleep(0.02)
        self.fail(f"timed out waiting for {path}")

    def stop(self, proc: subprocess.Popen[str]) -> None:
        if proc.poll() is None:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=3)

    def test_supervisor_waits_for_tailscale_without_expiring(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env, marker = self.make_fake_stack(root, empty_ip_calls=35)
            proc = subprocess.Popen(
                [str(LAUNCHER), "--autostart"],
                env=env,
                text=True,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                self.wait_for(marker)
                self.assertGreaterEqual(int((root / "tailscale-count").read_text()), 36)
            finally:
                self.stop(proc)

    def test_supervisor_lock_rejects_duplicate_owner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env, marker = self.make_fake_stack(root)
            first = subprocess.Popen(
                [str(LAUNCHER), "--autostart"],
                env=env,
                text=True,
                start_new_session=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            try:
                self.wait_for(marker)
                second = subprocess.run(
                    [str(LAUNCHER), "--autostart"],
                    env=env,
                    text=True,
                    capture_output=True,
                    timeout=2,
                    check=False,
                )
                self.assertEqual(second.returncode, 0)
                self.assertEqual(marker.read_text().splitlines().__len__(), 1)
            finally:
                self.stop(first)

    def test_installer_renders_boot_and_self_heal_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            launcher = root / ".local/bin/herdr-web-tailnet"
            launcher.parent.mkdir(parents=True)
            launcher.write_text("#!/bin/sh\n", encoding="utf-8")
            launcher.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "HERDR_WEB_BOOT_HOME": str(root),
                    "HERDR_WEB_BOOT_USER": "tester",
                    "HERDR_WEB_BOOT_UID": "1234",
                }
            )
            result = subprocess.run(
                [str(INSTALLER), "--dry-run"],
                env=env,
                text=True,
                capture_output=True,
                check=True,
            )
            self.assertIn("@reboot tester HOME=", result.stdout)
            self.assertIn("*/3 * * * * tester HOME=", result.stdout)
            self.assertEqual(result.stdout.count("--autostart"), 2)


if __name__ == "__main__":
    unittest.main()
