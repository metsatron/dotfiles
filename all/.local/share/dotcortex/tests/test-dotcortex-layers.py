#!/usr/bin/env python3
from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
HELPER = ROOT / "all/.local/bin/dotcortex-layers"
GUARD = ROOT / "all/.local/bin/dotcortex-stow-target-guard"
MAAK = ROOT / "all/.config/maak/maak.scm"
HOSTS = ROOT / "all/.config/dotcortex/hosts.ssv"
USERS = ROOT / "all/.config/dotcortex/users.ssv"
# Verbs that are not host stacks: platform-only verbs and the sanctuary projection.
NON_HOST_VERBS = {"stow", "stow:linux", "stow:debian", "stow:devuan", "stow:cortex"}


def run(cmd, **env):
    full_env = dict(os.environ)
    for key in ("DOTCORTEX_ROOT", "DOTCORTEX_HOSTS_SSV", "DOTCORTEX_USERS_SSV",
                "DOTCORTEX_LAYERS_HOSTNAME", "DOTCORTEX_LAYERS_ACCOUNT", "DOTCORTEX_LOCAL_PKGS"):
        full_env.pop(key, None)
    full_env.update(env)
    return subprocess.run(cmd, capture_output=True, text=True, env=full_env, cwd=ROOT)


def rows(path):
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(shlex.split(line))
    return out


def legacy_verbs():
    """Independent parse of every stow verb in the tangled maak.scm."""
    text = MAAK.read_text(encoding="utf-8")
    verbs = {}
    for match in re.finditer(r"\(task '(stow(?::[A-Za-z0-9_-]+)?)\s(.*?)(?=\(task '|\Z)", text, re.S):
        body = match.group(2)
        if "make safe-stow" not in body:
            continue
        pkgs = re.search(r"STOW_PKGS='([^']*)'", body)
        verbs[match.group(1)] = pkgs.group(1).split() if pkgs else ["all"]
    return verbs


class RegistryTests(unittest.TestCase):
    def test_check_passes(self):
        result = run([sys.executable, str(HELPER), "check"])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("layers:check passed", result.stdout)

    def test_stow_auto_matches_every_legacy_verb_for_every_alias(self):
        verbs = legacy_verbs()
        checked = 0
        for row in rows(HOSTS):
            host, aliases, status, *_rest, users, legacy, _note = row
            if status != "active" or legacy == "-":
                continue
            self.assertIn(legacy, verbs, f"{host}: {legacy} missing from maak.scm")
            for name in [host] + aliases.split(","):
                result = run([sys.executable, str(HELPER), "resolve"],
                             DOTCORTEX_LAYERS_HOSTNAME=name,
                             DOTCORTEX_LAYERS_ACCOUNT=users.split(",")[0])
                self.assertEqual(result.returncode, 0, f"{name}: {result.stderr}")
                self.assertEqual(result.stdout.split(), verbs[legacy],
                                 f"{name}: stow:auto diverges from {legacy}")
                checked += 1
        self.assertGreaterEqual(checked, 6)

    def test_every_host_stow_verb_has_a_registry_row(self):
        covered = {row[8] for row in rows(HOSTS)}
        for verb in legacy_verbs():
            if verb in NON_HOST_VERBS:
                continue
            self.assertIn(verb, covered, f"{verb} has no hosts.ssv row")


class RefusalTests(unittest.TestCase):
    def resolve(self, *args, **env):
        return run([sys.executable, str(HELPER), "resolve", *args], **env)

    def test_unregistered_host_is_refused(self):
        result = self.resolve(DOTCORTEX_LAYERS_HOSTNAME="no-such-host", DOTCORTEX_LAYERS_ACCOUNT="metsatron")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not registered", result.stderr)

    def test_planned_honey_is_refused(self):
        result = self.resolve(DOTCORTEX_LAYERS_HOSTNAME="beelink", DOTCORTEX_LAYERS_ACCOUNT="gille")
        self.assertEqual(result.returncode, 3, result.stderr)
        self.assertIn("planned", result.stderr)
        self.assertEqual(result.stdout, "")

    def test_planned_honey_shows_its_intended_stack(self):
        result = run([sys.executable, str(HELPER), "show", "--allow-planned"],
                     DOTCORTEX_LAYERS_HOSTNAME="beelink", DOTCORTEX_LAYERS_ACCOUNT="gille")
        # honey/ does not exist yet, so even inspection stops at the missing layer.
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn("'honey'", result.stderr)

    def test_user_not_assigned_to_host_is_refused(self):
        result = self.resolve("--user", "gille", DOTCORTEX_LAYERS_HOSTNAME="x230")
        self.assertEqual(result.returncode, 2)
        self.assertIn("not assigned", result.stderr)

    def test_unknown_account_is_refused(self):
        result = self.resolve(DOTCORTEX_LAYERS_HOSTNAME="x230", DOTCORTEX_LAYERS_ACCOUNT="nobody-here")
        self.assertEqual(result.returncode, 2)
        self.assertIn("maps to no user", result.stderr)


class OrderTests(unittest.TestCase):
    def test_active_user_layer_lands_after_host_and_before_local(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for pkg in ("all", "linux", "debian", "devuan", "t480s", "user-metsatron", "local-t480s"):
                (root / pkg).mkdir()
            (root / "hosts.ssv").write_text(
                't480s t480s active linux debian devuan t480s metsatron stow:t480s "fixture"\n')
            (root / "users.ssv").write_text('metsatron metsatron active metsatron "fixture"\n')
            result = run([sys.executable, str(HELPER), "resolve", "--explain"],
                         DOTCORTEX_ROOT=str(root),
                         DOTCORTEX_HOSTS_SSV=str(root / "hosts.ssv"),
                         DOTCORTEX_USERS_SSV=str(root / "users.ssv"),
                         DOTCORTEX_LAYERS_HOSTNAME="t480s",
                         DOTCORTEX_LAYERS_ACCOUNT="metsatron",
                         DOTCORTEX_LOCAL_PKGS="local-t480s")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.split(),
                             ["all", "linux", "debian", "devuan", "t480s", "user-metsatron", "local-t480s"])


class SkeletonTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stow"), "GNU Stow not installed")
    def test_user_skeletons_stow_nothing(self):
        with tempfile.TemporaryDirectory() as target:
            result = run(["stow", "--simulate", "-v", "-d", str(ROOT), "-t", target,
                          "user-metsatron", "user-gille"])
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertNotIn("LINK", result.stdout + result.stderr)
            self.assertEqual(os.listdir(target), [])

    def test_validator_sees_no_files_in_skeletons(self):
        for user in ("metsatron", "gille"):
            result = run([sys.executable, str(HELPER), "validate",
                          "--packages", f"all linux debian user-{user}", "--account", user])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertNotIn("overlaps", result.stderr)
            self.assertIn("inactive", result.stderr)


if __name__ == "__main__":
    unittest.main()
