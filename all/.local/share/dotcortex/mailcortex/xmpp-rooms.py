# [[file:../../../../../services-mailcortex-xmpp-rooms.org::*Python adapter][Python adapter:1]]
"""Private room registry to a bounded local Prosody admin-shell operation."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import uuid

SETTINGS = ("persistent", "hidden", "whois", "allow_member_invites", "members_only")
COUNTS = ("grant_admin", "clear_affiliations", "repair_moderators", "remove_occupants")
ERRORS = {
    "host-unavailable", "lookup-failed", "room-protected", "api-unavailable",
    "create-failed", "setting-failed", "affiliation-failed", "role-failed",
    "verify-failed", "save-failed", "operation-failed",
}


class RoomError(Exception):
    """Only fixed, value-free diagnostics cross the stdout/stderr boundary."""


class Parser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default includes untrusted argument values.
        super().error("invalid arguments (use --help)")


def registry(bridge_path: Path, config_path: Path) -> list[dict]:
    try:
        bridge = runpy.run_path(str(bridge_path))
        cfg = bridge["load_config"](config_path)
    except Exception:
        raise RoomError("bridge configuration invalid or unavailable") from None
    if not cfg["rooms"]:
        raise RoomError("rooms map is missing or empty")
    # No other private config fields, including secret paths, enter the request.
    return [
        {"jid": room["jid"], "admins": sorted(
            local + "@" + cfg["component_jid"] for local in room["seats"])}
        for _, room in sorted(cfg["rooms"].items())
    ]


def lua_quote(value: str) -> str:
    # Decimal byte escapes are valid Lua (JSON's Unicode escapes are not).
    return '"' + "".join(f"\\{byte:03d}" for byte in value.encode("utf-8")) + '"'


def command(rooms: list[dict], dry_run: bool, nonce: str) -> str:
    try:
        body = Path(__file__).with_suffix(".lua").read_text(encoding="utf-8")
    except OSError:
        raise RoomError("room Lua implementation unavailable") from None
    request = json.dumps({"rooms": rooms, "dry_run": dry_run}, separators=(",", ":"))
    script = ("> local request_json = " + lua_quote(request) + ";\n"
              + "local response_marker = " + lua_quote(nonce) + ";\n" + body)
    if len(script.encode("utf-8")) > 96 * 1024:
        raise RoomError("room registry exceeds the bounded shell request size")
    return script


def response(stdout: str, nonce: str, rooms: list[dict], dry_run: bool) -> list[dict]:
    prefix = "Result: " + nonce
    matches = [line.strip()[len(prefix):] for line in stdout.splitlines()
               if line.strip().startswith(prefix)]
    if len(matches) != 1:
        raise RoomError("admin shell did not return a unique confirmed response")
    try:
        result = json.loads(matches[0])
        if not isinstance(result, dict) or type(result.get("ok")) is not bool:
            raise ValueError
        if not result["ok"]:
            code = result.get("code")
            index = result.get("room")
            phase = result.get("phase")
            if (code not in ERRORS or type(index) is not int
                    or not 0 <= index <= len(rooms) or phase not in ("preflight", "apply")):
                raise ValueError
            raise RoomError(f"room operation failed: {code}; room {index}; {phase}")
        rows = result["rooms"]
        if (type(result.get("dry_run")) is not bool or result["dry_run"] != dry_run
                or not isinstance(rows, list) or len(rows) != len(rooms)):
            raise ValueError
        for index, row in enumerate(rows, 1):
            if (not isinstance(row, dict) or type(row.get("index")) is not int
                    or row["index"] != index or type(row.get("created")) is not bool
                    or type(row.get("verified")) is not bool or row["verified"] != (not dry_run)
                    or not isinstance(row.get("settings"), list)
                    or any(key not in SETTINGS for key in row["settings"])
                    or len(row["settings"]) != len(set(row["settings"]))
                    or any(type(row.get(key)) is not int or row[key] < 0 for key in COUNTS)
                    or row["grant_admin"] > len(rooms[index - 1]["admins"])):
                raise ValueError
        return rows
    except (ValueError, KeyError, TypeError):
        raise RoomError("admin shell response failed validation") from None


def ensure(rooms: list[dict], dry_run: bool, prosody_config: Path) -> list[dict]:
    nonce = "MAILCORTEX_ROOMS_" + uuid.uuid4().hex + ":"
    script = command(rooms, dry_run, nonce)
    try:
        result = subprocess.run(
            ["prosodyctl", "--config", str(prosody_config), "shell", script],
            stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=30,
            check=False, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        raise RoomError("admin shell timed out") from None
    except OSError:
        raise RoomError("admin shell runner unavailable") from None
    if result.returncode != 0:
        raise RoomError("admin shell runner failed")
    return response(result.stdout, nonce, rooms, dry_run)


def report(rows: list[dict], dry_run: bool) -> None:
    values = {"persistent": "true", "hidden": "true", "whois": "moderators",
              "allow_member_invites": "false", "members_only": "true"}
    for row in rows:
        actions = (["create"] if row["created"] else [])
        actions += [key + "=" + values[key] for key in row["settings"]]
        actions += [key + "=" + str(row[key]) for key in COUNTS if row[key]]
        label = "plan" if dry_run else "verified"
        print(f"room {row['index']}: {label}: " + ("; ".join(actions) or "unchanged"))


def main(argv: list[str] | None = None) -> int:
    parser = Parser(prog="mailcortex-xmpp-service rooms ensure",
                    description="Reconcile private squadron rooms on the running local Prosody.")
    parser.add_argument("--dry-run", action="store_true", help="plan without policy mutation")
    parser.add_argument("--config", type=Path, default=Path(os.environ.get(
        "MAILCORTEX_XMPP_CONFIG", "~/.config/mailcortex/xmpp-private/bridge.json")).expanduser())
    parser.add_argument("--prosody-config", type=Path,
                        default=Path("~/.config/mailcortex/xmpp/prosody.cfg.lua").expanduser())
    args = parser.parse_args(argv)
    bridge = Path(os.environ.get("MAILCORTEX_XMPP_BRIDGE",
                                "~/.local/bin/mailcortex-xmpp-bridge")).expanduser()
    try:
        rooms = registry(bridge, args.config)
        report(ensure(rooms, args.dry_run, args.prosody_config), args.dry_run)
        return 0
    except RoomError as error:
        print(f"mailcortex-xmpp-service: {error}; no completion claim; "
              "apply may be partial, inspect before rerunning", file=sys.stderr)
        return 1
    except Exception:
        print("mailcortex-xmpp-service: room operation failed; no completion claim; "
              "apply may be partial, inspect before rerunning", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
# Python adapter:1 ends here
