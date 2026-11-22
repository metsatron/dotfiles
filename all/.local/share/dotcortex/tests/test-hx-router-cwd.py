#!/usr/bin/env python3
"""hx-router must not ask for a working directory that its caller already supplied, or that cannot exist."""
from __future__ import annotations

import importlib.machinery
import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

ROUTER = Path(__file__).resolve().parents[5] / "all/.local/libexec/hx-router"


def load():
    loader = importlib.machinery.SourceFileLoader("hx_router_cwd", str(ROUTER))
    spec = importlib.util.spec_from_loader("hx_router_cwd", loader)
    module = importlib.util.module_from_spec(spec)
    sys.modules["hx_router_cwd"] = module
    loader.exec_module(module)
    return module


router = load()


class CallerCwdTests(unittest.TestCase):
    def test_the_exported_directory_wins_and_getcwd_is_never_asked(self):
        with mock.patch.dict(os.environ, {"HX_CALLER_PWD": "/exported/dir"}), \
                mock.patch.object(router.os, "getcwd", side_effect=FileNotFoundError):
            self.assertEqual(router.caller_cwd(), "/exported/dir")

    def test_a_cwd_that_no_longer_resolves_falls_back_to_home_instead_of_crashing(self):
        env = {k: v for k, v in os.environ.items() if k != "HX_CALLER_PWD"}
        with mock.patch.dict(os.environ, env, clear=True), \
                mock.patch.object(router.os, "getcwd", side_effect=FileNotFoundError):
            self.assertEqual(router.caller_cwd(), os.path.expanduser("~"))

    def test_without_an_export_the_real_cwd_is_used(self):
        env = {k: v for k, v in os.environ.items() if k != "HX_CALLER_PWD"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertEqual(router.caller_cwd(), os.getcwd())

    def test_run_local_survives_a_stale_cwd_and_passes_the_exported_directory_on(self):
        seen = {}
        with mock.patch.dict(os.environ, {"HX_CALLER_PWD": "/exported/dir"}), \
                mock.patch.object(router.os, "getcwd", side_effect=FileNotFoundError), \
                mock.patch.object(router.os, "chdir"), \
                mock.patch.object(router.os, "execvpe", side_effect=lambda real, argv, env: seen.update(real=real, env=env)):
            router.run_local("/bin/true", "tool", [], guarded=False)
        self.assertEqual(seen["real"], "/bin/true")
        self.assertEqual(seen["env"]["HX_CALLER_PWD"], "/exported/dir")


if __name__ == "__main__":
    unittest.main()
