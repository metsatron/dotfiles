#!/usr/bin/env python3
"""Flying Fox entrypoint for the provider-aware rollout watcher.

The honey-voice-fox unit exports HONEY_FOX_HOME (the Flying Fox agent
account's home) and HONEY_FOX_READ_AS (the account its private files are read
as).  This maps them onto the generic watcher's settings and runs
provider-rollout-watcher.py from this directory by path, so the engine needs
no second, importable copy of the watcher.  Explicit HONEY_VOICE_* values win.
"""
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WATCHER = os.path.join(HERE, "provider-rollout-watcher.py")


def configure(env=os.environ):
    fox_home = env.get("HONEY_FOX_HOME", "")
    if not fox_home:
        raise SystemExit("codex_rollout_watcher: HONEY_FOX_HOME is not set (see /etc/conf.d/honey-voice-fox)")
    env.setdefault("HONEY_VOICE_BOT", "fox")
    env.setdefault("HONEY_VOICE_PROVIDER", "codex")
    env.setdefault("HONEY_VOICE_DUCTOR_HOME", os.path.join(fox_home, ".ductor-codex"))
    env.setdefault("HONEY_VOICE_ROLLOUT_HOME", fox_home)
    read_as = env.get("HONEY_FOX_READ_AS", "")
    if read_as:
        env.setdefault("HONEY_VOICE_READ_AS", read_as)
    return env


def load_watcher(path=WATCHER):
    # The watcher reads its settings at import time, so configure() runs first.
    spec = importlib.util.spec_from_file_location("provider_rollout_watcher", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    configure()
    try:
        raise SystemExit(load_watcher().main())
    except KeyboardInterrupt:
        sys.exit(0)
