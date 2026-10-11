#!/usr/bin/env python3
from __future__ import annotations

import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
CLEANUP = ROOT / "all/.local/bin/dotcortex-storage-maintenance"
INSTALLER = ROOT / "linux/.local/bin/dotcortex-storage-maintenance-cron-apply"


class StorageMaintenanceTests(unittest.TestCase):
    def fixture(self, root: Path) -> tuple[dict[str, str], Path, Path, Path, Path]:
        fake_guix = root / "guix"
        dead = root / "dead-store-item"
        dead.mkdir()
        (dead / "payload").write_bytes(b"x" * 4096)
        marker = root / "guix-gc-ran"
        fake_guix.write_text(
            "#!/bin/sh\n"
            f"if [ \"$*\" = 'gc --list-dead' ]; then printf '%s\\n' '{dead}'; exit 0; fi\n"
            f"if [ \"$*\" = 'gc' ]; then : >'{marker}'; "
            "printf '%s\\n' detail-1 detail-2 detail-3 summary-1 summary-2; exit 0; fi\n"
            "exit 2\n",
            encoding="utf-8",
        )
        fake_guix.chmod(0o755)

        package_calls = root / "package-calls"
        package_bins: dict[str, Path] = {}
        for name in ("nala", "flatpak", "brew", "uv"):
            executable = root / name
            executable.write_text(
                "#!/bin/sh\n"
                f"printf '%s %s\\n' '{name}' \"$*\" >>'{package_calls}'\n",
                encoding="utf-8",
            )
            executable.chmod(0o755)
            package_bins[name] = executable
        fake_sudo = root / "sudo"
        fake_sudo.write_text(
            "#!/bin/sh\n"
            "[ \"${1:-}\" = -n ] && shift\n"
            "exec \"$@\"\n",
            encoding="utf-8",
        )
        fake_sudo.chmod(0o755)

        runaway = root / ".local/share/dotcortex/guests/test/home/.cache/redstone-9x/clipmenud.log"
        runaway.parent.mkdir(parents=True)
        with runaway.open("wb") as handle:
            handle.truncate(17 * 1024 * 1024)

        candidates = root / ".cache/ductor-candidates"
        old = candidates / "old"
        fresh = candidates / "fresh"
        old.mkdir(parents=True)
        fresh.mkdir()
        old_time = time.time() - (20 * 86400)
        os.utime(old, (old_time, old_time))

        unrelated = root / ".cache/must-survive"
        unrelated.write_text("keeper", encoding="utf-8")
        telegram_state = root / ".local/state/telegram-agents"
        claude_state = root / ".local/state/claude-idle-compaction"
        telegram_state.mkdir(parents=True)
        claude_state.mkdir()
        (telegram_state / "agent.log").write_text("large", encoding="utf-8")
        (claude_state / "diagnostic.log").write_text("large", encoding="utf-8")
        (root / ".local/state/caddy-refresh.log").write_text("large", encoding="utf-8")
        env = os.environ.copy()
        env.update(
            {
                "STORAGE_MAINTENANCE_HOME": str(root),
                "STORAGE_MAINTENANCE_HOSTNAME": "kikin-kushi",
                "STORAGE_MAINTENANCE_GUIX": str(fake_guix),
                "STORAGE_MAINTENANCE_NALA": str(package_bins["nala"]),
                "STORAGE_MAINTENANCE_FLATPAK": str(package_bins["flatpak"]),
                "STORAGE_MAINTENANCE_BREW": str(package_bins["brew"]),
                "STORAGE_MAINTENANCE_UV": str(package_bins["uv"]),
                "STORAGE_MAINTENANCE_SUDO": str(fake_sudo),
                "STORAGE_MAINTENANCE_APT_ARCHIVE_DIR": str(root / "apt-archives"),
                "STORAGE_MAINTENANCE_TELEGRAM_STATE_MAX_BYTES": "1",
                "STORAGE_MAINTENANCE_CLAUDE_STATE_MAX_BYTES": "1",
                "STORAGE_MAINTENANCE_CADDY_LOG_MAX_BYTES": "1",
            }
        )
        return env, marker, runaway, old, package_calls

    def test_help(self) -> None:
        result = subprocess.run([CLEANUP, "--help"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("narrow DotCortex cleanup allowlist", result.stdout)

    def test_host_guard(self) -> None:
        env = os.environ.copy()
        env["STORAGE_MAINTENANCE_HOSTNAME"] = "not-kikin"
        result = subprocess.run(
            [CLEANUP, "--expected-host", "kikin-kushi", "--dry-run"],
            env=env,
            text=True,
            capture_output=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("refusing", result.stderr)

    def test_dry_run_is_non_mutating(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env, marker, runaway, old, package_calls = self.fixture(root)
            result = subprocess.run(
                [CLEANUP, "--expected-host", "kikin-kushi", "--dry-run"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(runaway.stat().st_size, 17 * 1024 * 1024)
            self.assertTrue(old.exists())
            self.assertIn("would truncate", result.stdout)
            self.assertIn("would remove", result.stdout)
            self.assertEqual(result.stdout.count("WARNING runtime-log high-water exceeded"), 3)
            self.assertEqual(
                package_calls.read_text(encoding="utf-8").splitlines(),
                ["brew cleanup --dry-run --prune=30"],
            )

    def test_real_run_changes_only_allowlisted_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env, marker, runaway, old, package_calls = self.fixture(root)
            result = subprocess.run(
                [CLEANUP, "--expected-host", "kikin-kushi"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(marker.exists())
            self.assertEqual(runaway.stat().st_size, 0)
            self.assertFalse(old.exists())
            self.assertTrue((root / ".cache/ductor-candidates/fresh").exists())
            self.assertEqual((root / ".cache/must-survive").read_text(), "keeper")
            self.assertNotIn("detail-1", result.stdout)
            self.assertIn("summary-2", result.stdout)
            self.assertEqual(
                package_calls.read_text(encoding="utf-8").splitlines(),
                [
                    "nala clean",
                    "flatpak uninstall --user --unused --assumeyes --noninteractive",
                    "brew cleanup --prune=30",
                    "uv cache prune",
                ],
            )

    def test_cron_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = os.environ.copy()
            env.update(
                {
                    "STORAGE_MAINTENANCE_HOME": str(root),
                    "STORAGE_MAINTENANCE_HOSTNAME": "kikin-kushi",
                    "STORAGE_MAINTENANCE_USER": "test-user",
                    "STORAGE_MAINTENANCE_UID": "1234",
                }
            )
            result = subprocess.run(
                [INSTALLER, "--host", "kikin-kushi", "--dry-run"],
                env=env,
                text=True,
                capture_output=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("30 6 * * * test-user", result.stdout)
            self.assertIn("--expected-host kikin-kushi", result.stdout)
            self.assertIn(str(root / ".local/state/dotcortex-storage-maintenance/cron.log"), result.stdout)

    def test_worktree_reaper_removes_only_old_merged_clean_worktrees(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            fake_guix = root / "guix"
            fake_guix.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
            fake_guix.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "HOME": str(root),
                    "STORAGE_MAINTENANCE_HOME": str(root),
                    "STORAGE_MAINTENANCE_HOSTNAME": "kikin-kushi",
                    "STORAGE_MAINTENANCE_GUIX": str(fake_guix),
                    "STORAGE_MAINTENANCE_NALA": str(root / "missing-nala"),
                    "STORAGE_MAINTENANCE_FLATPAK": str(root / "missing-flatpak"),
                    "STORAGE_MAINTENANCE_BREW": str(root / "missing-brew"),
                    "STORAGE_MAINTENANCE_UV": str(root / "missing-uv"),
                    "STORAGE_MAINTENANCE_DOTCORTEX_REPO": str(root / "DotCortex"),
                    "STORAGE_MAINTENANCE_DOTCORTEX_WORKTREE_ROOT": str(root / "DotCortex-wt-kikin"),
                    "STORAGE_MAINTENANCE_HELMCORTEX_REPO": str(root / "HelmCortex"),
                    "STORAGE_MAINTENANCE_HELMCORTEX_WORKTREE_ROOT": str(root / "HelmCortex-wt-kikin"),
                    "STORAGE_MAINTENANCE_WORKTREE_MIN_AGE_SECONDS": "21600",
                }
            )

            def git(repo: Path, *args: str) -> str:
                result = subprocess.run(
                    ["git", "-C", str(repo), *args],
                    check=True,
                    text=True,
                    capture_output=True,
                    env=env,
                )
                return result.stdout

            def make_repo(repo: Path) -> None:
                repo.mkdir()
                subprocess.run(
                    ["git", "init", "--initial-branch=master", str(repo)],
                    check=True,
                    text=True,
                    capture_output=True,
                    env=env,
                )
                git(repo, "config", "user.email", "test@example.invalid")
                git(repo, "config", "user.name", "Storage Test")
                (repo / "README").write_text("root\n", encoding="utf-8")
                git(repo, "add", "README")
                git(repo, "commit", "-m", "initial")

            def candidate(repo: Path, worktree_root: Path, name: str, merged: bool, old: bool = False) -> Path:
                branch = f"candidate-{name}"
                git(repo, "switch", "-c", branch)
                (repo / name).write_text(f"{name}\n", encoding="utf-8")
                git(repo, "add", name)
                commit_env = env.copy()
                if old:
                    old_timestamp = int(time.time() - (2 * 86400))
                    commit_env["GIT_AUTHOR_DATE"] = f"@{old_timestamp}"
                    commit_env["GIT_COMMITTER_DATE"] = f"@{old_timestamp}"
                subprocess.run(
                    ["git", "-C", str(repo), "commit", "-m", name],
                    check=True,
                    text=True,
                    capture_output=True,
                    env=commit_env,
                )
                git(repo, "switch", "master")
                if merged:
                    git(repo, "merge", "--no-ff", "--no-edit", branch)
                path = worktree_root / name
                worktree_root.mkdir(parents=True, exist_ok=True)
                subprocess.run(
                    ["git", "-C", str(repo), "worktree", "add", str(path), branch],
                    check=True,
                    text=True,
                    capture_output=True,
                    env=env,
                )
                if old:
                    old_time = time.time() - (2 * 86400)
                    os.utime(path, (old_time, old_time))
                return path

            dot = root / "DotCortex"
            helm = root / "HelmCortex"
            make_repo(dot)
            make_repo(helm)
            removed = candidate(dot, root / "DotCortex-wt-kikin", "merged-clean", True, old=True)
            helm_removed = candidate(helm, root / "HelmCortex-wt-kikin", "merged-clean", True, old=True)
            unmerged = candidate(dot, root / "DotCortex-wt-kikin", "unmerged", False)
            dirty = candidate(dot, root / "DotCortex-wt-kikin", "dirty", True)
            (dirty / "dirty-file").write_text("changed\n", encoding="utf-8")
            untracked = candidate(dot, root / "DotCortex-wt-kikin", "untracked", True)
            (untracked / "untracked-file").write_text("untracked\n", encoding="utf-8")
            busy = candidate(dot, root / "DotCortex-wt-kikin", "busy", True)
            busy_process = subprocess.Popen(["sleep", "30"], cwd=busy)
            young = candidate(dot, root / "DotCortex-wt-kikin", "young", True)

            try:
                result = subprocess.run(
                    [CLEANUP, "--expected-host", "kikin-kushi"],
                    env=env,
                    text=True,
                    capture_output=True,
                )
            finally:
                busy_process.terminate()
                busy_process.wait(timeout=5)

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(removed.exists())
            self.assertFalse(helm_removed.exists())
            for kept, reason in (
                (unmerged, "unmerged"),
                (dirty, "dirty"),
                (untracked, "dirty"),
                (busy, "busy"),
                (young, "too young"),
            ):
                self.assertTrue(kept.exists())
                self.assertIn(f"path={kept} reason={reason}", result.stdout)
            self.assertIn("pruned worktree metadata", result.stdout)
            for repo, branch in (
                (dot, "candidate-merged-clean"),
                (helm, "candidate-merged-clean"),
            ):
                self.assertTrue(git(repo, "show-ref", "--verify", f"refs/heads/{branch}"))


if __name__ == "__main__":
    unittest.main()
