# [[file:../../../../agents-hermes-escalation.org::plugin-escalation-ledger-init][plugin-escalation-ledger-init]]
"""Escalation ledger. Source: agents-hermes-escalation.org.

Deterministic facts only. Not a sandbox: a claimed terminal can bypass the publish refusal.
Record a rejection:  python3 <this file> record-rejection --area AREA --evidence "verbatim words"
Record a review:     python3 <this file> record-review --area AREA --reviewer NAME --screenshot PATH --spec PATH --verdict pass
"""
import argparse
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import time

HOME = pathlib.Path(os.environ.get("HERMES_HOME", str(pathlib.Path.home() / ".hermes")))
STATE_DB = HOME / "state.db"
STATE_DIR = HOME / "state" / "escalation"
REPOS = [pathlib.Path("/home/metsatron/HelmCortex"), pathlib.Path.home() / "DotCortex"]
AUTHORS = ("Hermes", "Hermes Agent")
SELF = "hermes-agent"
USAGE_CMD = [str(pathlib.Path.home() / ".local/bin/ai-usage"), "--json"]
USAGE_MAX_AGE = 900
WRITE_TOOLS = {"write_file", "writefile", "patch", "create_file"}
PUBLISH_MARKERS = ("centre-apps/publish.py", "stage_apps", "pokemon-centre render", "centre_app_dock")
POLICY = {"window_hours": 24, "churn_window_hours": 12, "churn_commits": 5, "review_strikes": 2,
          "stop_strikes": 3, "cost_cap_usd": 3.0, "tool_call_cap": 400, "min_headroom_pct": 15}
# Cheapest-first proposal; the operator rules on order, entries and the headroom floor.
LADDER = [
    {"name": "gemini-flash", "model": "gemini-3.8-flash", "provider": "gemini", "flat_rate": False},
    {"name": "codex-gpt", "model": "gpt-6.1-sol", "provider": "codex", "flat_rate": True},
    {"name": "claude-sonnet", "model": "claude-sonnet-5-5", "provider": "claude", "flat_rate": True},
    {"name": "claude-opus", "model": "claude-opus-5-5", "provider": "claude", "flat_rate": True},
]


def _policy():
    policy = dict(POLICY)
    try:
        override = json.loads((STATE_DIR / "policy.json").read_text())
        if isinstance(override, dict):
            policy.update({k: v for k, v in override.items() if k in POLICY})
    except (OSError, ValueError):
        pass
    return policy


def area_of(path):
    parts = [p for p in str(path).split("/") if p]
    if len(parts) >= 3 and parts[0] == "FORGE" and parts[1] == "centre-apps":
        return "/".join(parts[:3])
    return "/".join(parts[:2]) if len(parts) > 2 else (parts[0] if parts else "")


def _commits(since):
    rows = []
    for repo in REPOS:
        run = subprocess.run(["git", "-C", str(repo), "log", "--since=@%d" % int(since), "--name-only",
                              "--format=%x1e%an%x1f%ct%x1f%s"], capture_output=True, text=True, timeout=30)
        if run.returncode == 128 and "does not have any commits yet" in run.stderr:
            continue
        if run.returncode != 0:
            raise RuntimeError("git log failed in %s: %s" % (repo, run.stderr.strip()[:120]))
        out = run.stdout
        for block in out.split("\x1e")[1:]:
            head, _, files = block.partition("\n")
            author, stamp, subject = (head.split("\x1f") + ["", "", ""])[:3]
            rows.append({"author": author, "ts": float(stamp), "subject": subject,
                         "areas": sorted({area_of(f) for f in files.split("\n") if f.strip()})})
    return rows


def _events():
    path = STATE_DIR / "events.jsonl"
    try:
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    except (OSError, ValueError):
        return []


def record_rejection(area, evidence, now=None):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / "events.jsonl").open("a") as handle:
        handle.write(json.dumps({"kind": "operator-rejection", "area": area, "evidence": evidence,
                                 "ts": now if now is not None else time.time()}) + "\n")


def _slug(area):
    return re.sub(r"[^A-Za-z0-9._-]+", "_", area)


def record_review(area, reviewer, author, screenshot, spec, verdict, ts=None):
    folder = STATE_DIR / "reviews"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / (_slug(area) + ".json")).write_text(json.dumps(
        {"area": area, "reviewer": reviewer, "author": author, "screenshot": screenshot, "spec": spec,
         "verdict": verdict, "ts": ts if ts is not None else time.time()}))


def _costs(since):
    try:
        con = sqlite3.connect("file:%s?mode=ro" % STATE_DB, uri=True, timeout=2)
    except sqlite3.Error as exc:
        return None, None, "session store unreadable: %s" % exc
    try:
        cost, calls = con.execute("SELECT COALESCE(SUM(COALESCE(actual_cost_usd, estimated_cost_usd, 0)), 0), "
                                  "COALESCE(SUM(tool_call_count), 0) FROM sessions WHERE started_at >= ?", (since,)).fetchone()
        return float(cost), int(calls), None
    except sqlite3.Error as exc:
        return None, None, "session store unreadable: %s" % exc
    finally:
        con.close()


def status(now=None):
    now = now if now is not None else time.time()
    policy = _policy()
    window = now - policy["window_hours"] * 3600
    churn_window = now - policy["churn_window_hours"] * 3600
    areas, unavailable, reasons = {}, [], []

    def bump(area, reason):
        entry = areas.setdefault(area, {"strikes": 0, "reasons": []})
        entry["strikes"] += 1
        entry["reasons"].append(reason)

    churn = {}
    for row in _commits(window):
        if row["author"] not in AUTHORS:
            continue
        for area in row["areas"]:
            if re.match(r"(?i)^revert", row["subject"]):
                bump(area, "revert: %s" % row["subject"][:80])
            if row["ts"] >= churn_window:
                churn[area] = churn.get(area, 0) + 1
    for area, count in churn.items():
        if count > policy["churn_commits"]:
            for _ in range(1 + (count - policy["churn_commits"] - 1) // 3):
                bump(area, "churn: %d commits in %dh" % (count, policy["churn_window_hours"]))
    for event in _events():
        if event.get("kind") == "operator-rejection" and event.get("ts", 0) >= window:
            bump(event["area"], "operator rejection: %s" % str(event.get("evidence", ""))[:80])
    for entry in areas.values():
        entry["level"] = ("stop" if entry["strikes"] >= policy["stop_strikes"]
                          else "review" if entry["strikes"] >= policy["review_strikes"] else "ok")
    level = max((e["level"] for e in areas.values()), key=("ok", "review", "stop").index, default="ok")
    cost, calls, problem = _costs(window)
    if problem:
        unavailable.append(problem)
    else:
        if cost > policy["cost_cap_usd"]:
            reasons.append("cost: $%.2f in %dh exceeds the $%.2f cap" % (cost, policy["window_hours"], policy["cost_cap_usd"]))
        if calls > policy["tool_call_cap"]:
            reasons.append("tool calls: %d in %dh exceeds %d" % (calls, policy["window_hours"], policy["tool_call_cap"]))
        if reasons and level == "ok":
            level = "review"
    return {"level": level, "areas": {a: e for a, e in areas.items() if e["strikes"]}, "reasons": reasons,
            "unavailable": unavailable, "cost_usd": cost, "tool_calls": calls}


def headroom(items):
    """Remaining percent per provider from an ai-usage --json list; None where no number was reported."""
    result = {}
    for item in items or []:
        key = item.get("provider")
        value = None
        if item.get("state") == "ok":
            usage = (item.get("raw") or {}).get("usage") or {}
            used = [usage[w].get("usedPercent") for w in ("primary", "secondary")
                    if isinstance(usage.get(w), dict) and isinstance(usage[w].get("usedPercent"), (int, float))]
            if used:
                value = 100 - max(used)
        result[key] = value
    return result


def next_rung(current, room, policy=None):
    """The next ladder rung above `current` that has live headroom; flat-rate capacity wins over metered."""
    floor = (policy or _policy())["min_headroom_pct"]
    why, flat, metered = [], None, None
    for index, rung in enumerate(LADDER):
        if index <= current:
            continue
        value = room.get(rung["provider"])
        if value is None:
            why.append("%s: no live headroom evidence for %s" % (rung["name"], rung["provider"]))
        elif value < floor:
            why.append("%s: %s headroom %d%% is below the %d%% floor" % (rung["name"], rung["provider"], value, floor))
        elif rung["flat_rate"] and flat is None:
            flat = rung
        elif not rung["flat_rate"] and metered is None:
            metered = rung
    return (flat or metered), why


def _usage_items(now):
    cache = STATE_DIR / "usage.json"
    try:
        data = json.loads(cache.read_text())
        if now - float(data.get("fetched", 0)) <= USAGE_MAX_AGE:
            return data.get("items")
    except (OSError, ValueError):
        pass
    if not USAGE_CMD:
        return None
    try:
        items = json.loads(subprocess.run(USAGE_CMD, capture_output=True, text=True, timeout=30).stdout)
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps({"fetched": now, "items": items}))
        return items
    except (OSError, ValueError, subprocess.SubprocessError):
        return None


def _refusal(tool, reason):
    return json.dumps({"error": "ESCALATION LEDGER REFUSED %s: %s" % (tool, reason), "protocol": "escalation-ledger",
                       "next": "get an independent review: a different agent judges a before/after screenshot against the "
                               "operator's verbatim spec, then record it with record-review"})


def _unreviewed(now):
    """Areas Hermes changed in the window that lack a passing, independent, newer, screenshot-backed receipt."""
    window = now - _policy()["window_hours"] * 3600
    latest = {}
    for row in _commits(window):
        if row["author"] in AUTHORS:
            for area in row["areas"]:
                latest[area] = max(latest.get(area, 0), row["ts"])
    missing = []
    for area, changed in sorted(latest.items()):
        try:
            receipt = json.loads((STATE_DIR / "reviews" / (_slug(area) + ".json")).read_text())
            shot = pathlib.Path(receipt["screenshot"])
            valid = (receipt["verdict"] == "pass" and receipt["reviewer"] not in (SELF, "hermes", "Hermes")
                     and receipt["ts"] >= changed and shot.is_file() and shot.stat().st_size > 0)
        except (OSError, ValueError, KeyError, TypeError):
            valid = False
        if not valid:
            missing.append(area)
    return missing


def gate(tool_name, args, next_call, **ctx):
    name = tool_name.rsplit(".", 1)[-1]
    args = args or {}
    try:
        now = ctx.get("now") or time.time()
        if name == "terminal" and any(marker in str(args.get("command", "")) for marker in PUBLISH_MARKERS):
            missing = _unreviewed(now)
            if missing:
                raise PermissionError("changed areas without an independent passing screenshot receipt: %s" % ", ".join(missing))
        elif name in WRITE_TOOLS:
            target = str(args.get("path") or args.get("file_path") or args.get("target") or "")
            stopped = [a for a, e in status(now)["areas"].items() if e["level"] == "stop" and a and a in target]
            if stopped:
                raise PermissionError("area %s is at the stop level: hand it to an independent reviewer instead of editing" % stopped[0])
    except Exception as exc:
        return _refusal(name, "%s: %s" % (type(exc).__name__, exc))
    return next_call(args)


def inject_state(now=None, **ctx):
    now = now if now is not None else time.time()
    try:
        state = status(now)
    except Exception as exc:
        return {"context": "[ESCALATION LEDGER] unavailable: %s: %s" % (type(exc).__name__, exc)}
    if state["level"] == "ok" and not state["unavailable"]:
        return {"context": ""}
    lines = ["[ESCALATION LEDGER] level=%s. Counted facts, not opinion." % state["level"]]
    for area, entry in sorted(state["areas"].items()):
        lines.append("- %s: %d strikes (%s) -> %s" % (area, entry["strikes"], "; ".join(entry["reasons"][-3:]), entry["level"]))
    lines += ["- " + r for r in state["reasons"]] + ["- unavailable: " + u for u in state["unavailable"]]
    if state["level"] in ("review", "stop"):
        items = _usage_items(now)
        rung, why = next_rung(-1, headroom(items) if items else {})
        if rung:
            lines.append("Next rung: %s (model %s, provider %s). Dispatch an independent reviewer there." % (rung["name"], rung["model"], rung["provider"]))
        else:
            lines.append("No rung has live headroom evidence; ask the operator which rung to use. " + " ".join(why[:3]))
        lines.append("First act of a review: write the operator's verbatim words into a one-page spec and have him confirm it once. "
                     "Publishing needs a different agent's passing screenshot receipt. Do not keep editing the stricken area yourself.")
    return {"context": "\n".join(lines)}


def register(ctx):
    ctx.register_middleware("tool_execution", gate)
    ctx.register_hook("pre_llm_call", inject_state)


def _main(argv):
    parser = argparse.ArgumentParser(description="Escalation ledger records")
    sub = parser.add_subparsers(dest="verb", required=True)
    rej = sub.add_parser("record-rejection")
    rej.add_argument("--area", required=True)
    rej.add_argument("--evidence", required=True)
    rev = sub.add_parser("record-review")
    for flag in ("area", "reviewer", "screenshot", "spec"):
        rev.add_argument("--" + flag, required=True)
    rev.add_argument("--verdict", choices=("pass", "fail"), required=True)
    rev.add_argument("--author", default=SELF)
    sub.add_parser("status")
    args = parser.parse_args(argv)
    if args.verb == "record-rejection":
        record_rejection(args.area, args.evidence)
    elif args.verb == "record-review":
        record_review(args.area, args.reviewer, args.author, args.screenshot, args.spec, args.verdict)
    else:
        print(json.dumps(status(), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
# plugin-escalation-ledger-init ends here
