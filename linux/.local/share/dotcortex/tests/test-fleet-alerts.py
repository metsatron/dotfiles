#!/usr/bin/env python3
#!/usr/bin/env python3
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
import runpy

ROOT = Path(__file__).resolve().parents[5]
COLLECTOR = ROOT / "all/.local/bin/fleet-health-alerts"
INSTALLER = ROOT / "linux/.local/bin/fleet-health-alerts-cron-apply"


class FleetAlertsTests(unittest.TestCase):
    def test_small_filesystem_reserves_are_capacity_capped(self) -> None:
        classify = runpy.run_path(str(COLLECTOR))["classify"]
        for capacity in (5_242_880, 2_500_000_000, 12_000_000_000):
            with self.subTest(capacity=capacity):
                metric = {"total_bytes": capacity, "available_bytes": capacity * 9 // 10,
                          "free_percent": 90, "inode_percent": 1}
                self.assertEqual(classify(metric), "normal")
                for free_percent, expected in ((19, "warning"), (10, "critical"), (5, "emergency")):
                    metric.update(available_bytes=capacity * free_percent // 100, free_percent=free_percent)
                    self.assertEqual(classify(metric), expected)
                metric.update(available_bytes=capacity, free_percent=100, inode_percent=96)
                self.assertEqual(classify(metric), "emergency")

    def run_collector(self, root: Path, bytes_free: int, used_percent: int, inode_percent: int, stale: bool = False) -> subprocess.CompletedProcess[str]:
        df = root / "df.txt"
        inode = root / "df-inode.txt"
        df.write_text(
            "Filesystem 1024-blocks Used Available Capacity Mounted on\n"
            "fixture 100000000000 0 %d %d%% /\n" % (bytes_free, 100 - used_percent),
            encoding="utf-8",
        )
        inode.write_text(
            "Filesystem Inodes IUsed IFree IUse%% Mounted on\n"
            "fixture 100000 0 100000 %d%% /\n" % inode_percent,
            encoding="utf-8",
        )
        telemetry = root / "telemetry.json"
        stamp = "2020-01-01T00:00:00+00:00" if stale else dt.datetime.now(dt.timezone.utc).isoformat()
        telemetry.write_text(json.dumps({"timestamp": stamp}), encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "HOME": str(root),
                "FLEET_ALERTS_HOSTNAME": "kikin-kushi",
                "FLEET_ALERTS_DF_FILE": str(df),
                "FLEET_ALERTS_DF_INODE_FILE": str(inode),
                "FLEET_ALERTS_TELEMETRY_FILE": str(telemetry),
                "FLEET_ALERTS_TELEMETRY_MAX_AGE": "900",
                "FLEET_ALERTS_SPOOL": str(root / "spool"),
                "FLEET_ALERTS_HEARTBEAT_DIR": str(root / "heartbeat"),
                "FLEET_ALERTS_STATE_FILE": str(root / "fleet-state.json"),
            }
        )
        return subprocess.run([COLLECTOR, "--once"], env=env, text=True, capture_output=True)

    def events(self, root: Path) -> list[dict]:
        return [json.loads(path.read_text()) for path in sorted((root / "spool").glob("*.json"))]

    def test_transitions_and_hysteresis(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(self.run_collector(root, 30_000_000_000, 70, 20).returncode, 0)
            self.assertEqual(self.events(root), [])
            self.assertEqual(self.run_collector(root, 15_000_000_000, 80, 20).returncode, 0)
            self.assertEqual(len(self.events(root)), 2)
            self.assertEqual(self.run_collector(root, 15_000_000_000, 80, 20).returncode, 0)
            self.assertEqual(len(self.events(root)), 2)
            self.assertEqual(self.run_collector(root, 8_000_000_000, 90, 20).returncode, 0)
            self.assertEqual(len(self.events(root)), 4)
            self.assertEqual(self.run_collector(root, 4_000_000_000, 96, 20).returncode, 0)
            events = self.events(root)
            self.assertEqual(len(events), 6)
            kinds = {event["kind"] for event in events}
            self.assertIn("disk_emergency", kinds)
            self.assertIn("tmp_emergency", kinds)
            self.assertEqual(self.run_collector(root, 30_000_000_000, 70, 20).returncode, 0)
            events = self.events(root)
            self.assertEqual(len(events), 8)
            kinds = {event["kind"] for event in events}
            self.assertIn("disk_recovered", kinds)
            self.assertIn("tmp_recovered", kinds)
            self.assertTrue((root / "heartbeat/fleet_health.json").exists())
            self.assertFalse(list((root / "spool").glob(".tmp-*.json")))

    def test_stale_telemetry_and_recovery(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(self.run_collector(root, 30_000_000_000, 70, 20, stale=True).returncode, 0)
            self.assertEqual(self.events(root)[0]["kind"], "telemetry_stale")
            self.assertEqual(self.run_collector(root, 30_000_000_000, 70, 20, stale=True).returncode, 0)
            self.assertEqual(len(self.events(root)), 1)
            self.assertEqual(self.run_collector(root, 30_000_000_000, 70, 20).returncode, 0)
            self.assertIn("telemetry_recovered", {event["kind"] for event in self.events(root)})

    def test_failed_probe_has_source_failed_and_no_heartbeat(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            df = root / "empty"
            inode = root / "inode"
            df.write_text("Filesystem 1024-blocks Used Available Capacity Mounted on\n", encoding="utf-8")
            inode.write_text("Filesystem Inodes IUsed IFree IUse%% Mounted on\n", encoding="utf-8")
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(root),
                    "FLEET_ALERTS_HOSTNAME": "kikin-kushi",
                    "FLEET_ALERTS_DF_FILE": str(df),
                    "FLEET_ALERTS_DF_INODE_FILE": str(inode),
                    "FLEET_ALERTS_SPOOL": str(root / "spool"),
                    "FLEET_ALERTS_HEARTBEAT_DIR": str(root / "heartbeat"),
                    "FLEET_ALERTS_STATE_FILE": str(root / "fleet-state.json"),
                }
            )
            result = subprocess.run([COLLECTOR], env=env, text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            events = self.events(root)
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["kind"], "source_failed")
            self.assertFalse((root / "heartbeat/fleet_health.json").exists())

    def test_installer_check_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "cron-entry"
            path = "%s/.guix-extra-profiles/core/core/bin:%s/.local/bin:/usr/local/bin:/usr/bin:/bin" % (root, root)
            target.write_text(
                "# HelmCortex fleet health; managed by fleet-health-alerts-cron-apply.\n"
                "SHELL=/bin/sh\nPATH=%s\n"
                "*/5 * * * * test-user umask 077; mkdir -p %s/.local/state/helmcortex-notifications/fleet && HOME=%s PATH=%s %s --once >>%s/.local/state/helmcortex-notifications/fleet/cron.log 2>&1\n"
                % (path, root, root, path, COLLECTOR, root),
                encoding="utf-8",
            )
            before = target.read_bytes()
            env = os.environ.copy()
            env.update(
                {
                    "FLEET_ALERTS_CRON_TARGET": str(target),
                    "FLEET_ALERTS_HOSTNAME": "kikin-kushi",
                    "FLEET_ALERTS_HOME": str(root),
                    "FLEET_ALERTS_USER": "test-user",
                    "FLEET_ALERTS_UID": "1234",
                    "FLEET_ALERTS_COLLECTOR": str(COLLECTOR),
                }
            )
            result = subprocess.run([INSTALLER, "--check"], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(target.read_bytes(), before)
            self.assertFalse((root / ".local/state").exists())

    def test_cron_command_bootstraps_log_directory(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            env = os.environ.copy()
            env.update(FLEET_ALERTS_HOSTNAME="kikin-kushi", FLEET_ALERTS_HOME=str(root),
                       FLEET_ALERTS_COLLECTOR="/bin/true", FLEET_ALERTS_USER="test-user")
            result = subprocess.run([INSTALLER, "--dry-run"], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            command = result.stdout.splitlines()[-1].split(maxsplit=6)[6]
            result = subprocess.run(["/bin/sh", "-c", command], env=env, text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            log = root / ".local/state/helmcortex-notifications/fleet/cron.log"
            self.assertTrue(log.exists())
            self.assertEqual(log.stat().st_mode & 0o777, 0o600)


if __name__ == "__main__":
    unittest.main()
