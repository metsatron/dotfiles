#!/usr/bin/env python3
# [[file:../../../../../services-mailcortex-xmpp-rooms.org::*Offline executable fixtures][Offline executable fixtures:1]]
"""Execute worktree service + Python + Lua with an offline stateful admin shell."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
HELPER = ROOT / "all/.local/share/dotcortex/mailcortex/xmpp-rooms.py"
BRIDGE = ROOT / "all/.local/bin/mailcortex-xmpp-bridge"
SERVICE = ROOT / "linux/.local/bin/mailcortex-xmpp-service"
spec = importlib.util.spec_from_file_location("rooms_helper", HELPER)
helper = importlib.util.module_from_spec(spec)
spec.loader.exec_module(helper)

HARNESS = r'''
package.path = "/usr/lib/?.lua;" .. package.path;
package.cpath = "/usr/lib/?.so;" .. package.cpath;
local json = require "prosody.util.json";
local array = require "prosody.util.array";
local function read(path) local f = assert(io.open(path)); local s = f:read("*a"); f:close(); return s; end
local state = json.decode(read(os.getenv("FIXTURE_STATE")));
state.calls = state.calls or array();
local function record(operation) table.insert(state.calls, operation); end
local function mutation(room, operation)
    record(operation);
    if state.fault == "exception" then error("YOUR_PASSWORD_TOKEN"); end
    if not room._data.persistent and next(room.occupants) == nil then
        error("nonpersistent room was destroyed");
    end
end
local function attach(room)
    room._data = room._data or {};
    room.affiliations = room.affiliations or {};
    room.occupants = room.occupants or {};
    for _, key in ipairs({"persistent", "hidden", "whois", "allow_member_invites", "members_only"}) do
        room["get_" .. key] = function(self)
            local value = self._data[key];
            if value ~= nil then return value; end
            if key == "whois" then return "moderators"; end
            return false;
        end;
        room["set_" .. key] = function(self, value)
            if self._data[key] == value then return false; end
            record("set:" .. key);
            if state.fault == "setter" then return nil; end
            self._data[key] = value;
            if key == "members_only" and value then
                for nick, occupant in pairs(self.occupants) do
                    if not self.affiliations[occupant.bare_jid] then self.occupants[nick] = nil; end
                end
            end
            mutation(self, "setting-complete");
            return true;
        end;
    end
    function room:each_affiliation() return next, self.affiliations, nil; end
    function room:get_affiliation(jid) return self.affiliations[jid]; end
    function room:each_occupant() return next, self.occupants, nil; end
    function room:get_role(nick) return self.occupants[nick] and self.occupants[nick].role; end
    function room:set_affiliation(actor, jid, value)
        assert(actor == true);
        if state.fault == "affiliation" then return nil, "YOUR_PASSWORD_TOKEN"; end
        if state.fault == "ignored-affiliation" then return true; end
        self.affiliations[jid] = value ~= "none" and value or nil;
        for nick, occupant in pairs(self.occupants) do
            if occupant.bare_jid == jid then
                if value == "none" and self._data.members_only then self.occupants[nick] = nil;
                elseif value == "admin" or value == "owner" then occupant.role = "moderator"; end
            end
        end
        mutation(self, "affiliation:" .. value);
        self:save(true); -- same unchecked inner save as Prosody
        return true;
    end
    function room:set_role(actor, nick, role)
        assert(actor == true);
        if state.fault == "role" then return nil, "YOUR_PASSWORD_TOKEN"; end
        if not self.occupants[nick] then return nil; end
        if role then self.occupants[nick].role = role; else self.occupants[nick] = nil; end
        mutation(self, "role:" .. (role or "none"));
        return true;
    end
    function room:save(force)
        assert(force == true);
        record("save");
        if state.fault == "save" or self.fail_save then return nil, "YOUR_PASSWORD_TOKEN"; end
        if not self._data.persistent then return nil; end
        return true;
    end
    if state.fault == "api" then room.set_role = nil; end
    return room;
end
for _, room in pairs(state.rooms) do attach(room); end
local muc = {};
function muc.get_room_from_jid(jid)
    if state.fault == "lookup" then return false; end
    return state.rooms[jid];
end
function muc.create_room(jid, config)
    record("create");
    if state.fault == "create" then return nil, "YOUR_PASSWORD_TOKEN"; end
    assert(state.rooms[jid] == nil);
    local room = attach({ _data = config; affiliations = {}; occupants = {} });
    state.rooms[jid] = room;
    return room;
end
prosody = { hosts = {} };
if state.fault ~= "host" then prosody.hosts["rooms.example.test"] = { modules = { muc = muc } }; end
local source = read(os.getenv("FIXTURE_SCRIPT")):gsub("^>", "");
local ok, result = pcall(assert(load(source, "console", "t", _G)));
-- Remove functions, preserving the room state for the next invocation.
for _, room in pairs(state.rooms) do
    for key, value in pairs(room) do if type(value) == "function" then room[key] = nil; end end
end
local f = assert(io.open(os.getenv("FIXTURE_STATE"), "w")); f:write(json.encode(state)); f:close();
if not ok then print("Error: YOUR_PASSWORD_TOKEN"); os.exit(1); end
print("Result: " .. result);
'''

FAKE = r'''#!/usr/bin/env python3
import os, pathlib, subprocess, sys, tempfile
state = pathlib.Path(os.environ["FIXTURE_STATE"])
trace = pathlib.Path(os.environ["FIXTURE_TRACE"])
trace.write_text("invoked")
assert len(sys.argv) == 5 and sys.argv[1] == "--config" and sys.argv[3] == "shell"
script = sys.argv[4]
assert script.startswith(">")
assert "YOUR_PASSWORD_TOKEN" not in script
assert "component_secret_file" not in script and "owner_jids" not in script
mode = os.environ.get("FIXTURE_RUNNER", "normal")
if mode == "disconnect":
    print("YOUR_PASSWORD_TOKEN disconnected"); sys.exit(0)
if mode == "error":
    print("YOUR_PASSWORD_TOKEN", file=sys.stderr); sys.exit(1)
print("warning: YOUR_PASSWORD_TOKEN")
with tempfile.TemporaryDirectory() as directory:
    path = pathlib.Path(directory) / "command.lua"
    path.write_text(script)
    env = os.environ.copy() | {"FIXTURE_SCRIPT": str(path)}
    result = subprocess.run([env["FIXTURE_LUA"], env["FIXTURE_HARNESS"]], env=env,
                            text=True, capture_output=True)
    output = result.stdout
    if mode == "duplicate": output += output
    if mode == "malformed": output = output[:output.find("{")] + "{}\n"
    if mode == "nonce": output = output.replace("MAILCORTEX_ROOMS_", "WRONG_NONCE_")
    if mode == "mode": output = output.replace('"dry_run":false', '"dry_run":true')
    if mode == "nonzero": result.returncode = 1
    print(output, end="")
    print(result.stderr, end="", file=sys.stderr)
    sys.exit(result.returncode)
'''


class EnsureTests(unittest.TestCase):
    def setUp(self):
        lua = shutil.which("lua5.4")
        if not lua or not Path("/usr/lib/prosody/util/json.lua").is_file():
            self.fail("offline fixtures require the declared Prosody/Lua runtime")
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.fakebin = self.home / "fakebin"
        self.fakebin.mkdir()
        fake = self.fakebin / "prosodyctl"
        fake.write_text(FAKE)
        fake.chmod(0o755)
        self.state = self.home / "state.json"
        self.trace = self.home / "trace"
        harness = self.home / "fixture.lua"
        harness.write_text(HARNESS)
        self.site = self.home / ".config/mailcortex/xmpp-private"
        self.site.mkdir(parents=True)
        self.config = self.site / "bridge.json"
        self.data = {
            "component_jid": "seats.example.test", "owner_jids": ["admiral@example.test"],
            "bridge_address": "seat+bridge@fixture.helm",
            "component_secret_file": str(self.home / "YOUR_PASSWORD_TOKEN"),
            "seats": {"lead": "seat+lead@fixture.helm", "worker": "seat+worker@fixture.helm"},
            "rooms": {"squadron": {"jid": "squadron@rooms.example.test", "lead": "lead",
                                     "seats": ["lead", "worker"]}},
            "password": "YOUR_PASSWORD_TOKEN", "token": "YOUR_PASSWORD_TOKEN",
        }
        self.config.write_text(json.dumps(self.data))
        self.write_state({"rooms": {}, "calls": []})
        self.env = os.environ.copy() | {
            "HOME": str(self.home), "PATH": str(self.fakebin) + ":/usr/bin:/bin",
            "MAILCORTEX_XMPP_BRIDGE": str(BRIDGE),
            "MAILCORTEX_XMPP_ROOMS_HELPER": str(HELPER),
            "FIXTURE_STATE": str(self.state), "FIXTURE_TRACE": str(self.trace),
            "FIXTURE_LUA": lua, "FIXTURE_HARNESS": str(harness), "FIXTURE_RUNNER": "normal",
        }
        # A lifecycle action must fail, not silently start a fixture daemon.
        for name in ("prosody", "mailcortex-xmpp-bridge", "ss", "ip", "kill"):
            path = self.fakebin / name
            path.write_text("#!/bin/sh\nprintf forbidden >&2\nexit 99\n")
            path.chmod(0o755)

    def write_state(self, state):
        self.state.write_text(json.dumps(state))

    def read_state(self):
        return json.loads(self.state.read_text())

    def invoke(self, *args):
        result = subprocess.run([str(SERVICE), "rooms", "ensure", *args],
                                env=self.env, text=True, capture_output=True, timeout=10)
        output = result.stdout + result.stderr
        for value in ("YOUR_PASSWORD_TOKEN", "admiral@example.test", str(self.home)):
            self.assertNotIn(value, output)
        self.assertNotIn("forbidden", output)
        return result

    def drift(self):
        return {"_data": {"persistent": False, "hidden": False, "whois": "anyone",
                          "members_only": False, "allow_member_invites": True},
                "affiliations": {"lead@seats.example.test": "member",
                                 "worker@seats.example.test": "owner",
                                 "admiral@example.test": "owner", "outsider@example.test": "member",
                                  "rogue@example.test": "owner",
                                 "blocked@example.test": "outcast", "example.test": "admin"},
                "occupants": {
                    "squadron@rooms.example.test/lead": {
                        "bare_jid": "lead@seats.example.test", "role": "participant"},
                    "squadron@rooms.example.test/outsider": {
                        "bare_jid": "outsider@example.test", "role": "moderator"},
                    "squadron@rooms.example.test/stranger": {
                        "bare_jid": "stranger@example.test", "role": "moderator"}}}

    def compliant(self, room):
        self.assertEqual(room["_data"], {"persistent": True, "hidden": True,
            "whois": "moderators", "members_only": True, "allow_member_invites": False})
        self.assertEqual(room["affiliations"], {
            "admiral@example.test": "owner",
            "lead@seats.example.test": "admin", "worker@seats.example.test": "admin"})
        for occupant in room["occupants"].values():
            self.assertIn(occupant["bare_jid"], room["affiliations"])
            self.assertEqual(occupant["role"], "moderator")

    def test_create_and_idempotent_rerun(self):
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("create", result.stdout)
        self.assertIn("grant_owner=1", result.stdout)
        self.assertIn("grant_admin=2", result.stdout)
        self.compliant(self.read_state()["rooms"]["squadron@rooms.example.test"])
        before = self.read_state()
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("verified: unchanged", result.stdout)
        after = self.read_state()
        self.assertEqual(after["rooms"], before["rooms"])
        self.assertEqual(after["calls"], before["calls"] + ["save"])
        self.assertFalse((self.home / "YOUR_PASSWORD_TOKEN").exists())

    def test_reconcile_and_leave_unlisted_room_untouched(self):
        room = self.drift()
        unlisted = {"_data": {"hidden": False}, "affiliations": {}, "occupants": {}}
        self.write_state({"rooms": {"squadron@rooms.example.test": room,
                                    "unlisted@rooms.example.test": unlisted}, "calls": []})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("clear_affiliations=4", result.stdout)
        state = self.read_state()
        self.compliant(state["rooms"]["squadron@rooms.example.test"])
        self.assertEqual(state["rooms"]["unlisted@rooms.example.test"], unlisted)
        self.assertEqual(state["calls"][0], "set:persistent")

    def test_unaffiliated_seat_occupant_is_preserved_when_membership_tightens(self):
        room = self.drift()
        room["affiliations"].pop("lead@seats.example.test")
        self.write_state({"rooms": {"squadron@rooms.example.test": room}, "calls": []})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_state()
        self.assertIn("squadron@rooms.example.test/lead",
                      state["rooms"]["squadron@rooms.example.test"]["occupants"])
        self.compliant(state["rooms"]["squadron@rooms.example.test"])

    def test_empty_nonpersistent_room_persisted_before_tightening(self):
        room = self.drift()
        room["occupants"] = {}
        self.write_state({"rooms": {"squadron@rooms.example.test": room}, "calls": []})
        self.assertEqual(self.invoke().returncode, 0)
        self.assertEqual(self.read_state()["calls"][0], "set:persistent")

    def test_dry_run_missing_and_drift_execute_no_mutations(self):
        for rooms in ({}, {"squadron@rooms.example.test": self.drift()}):
            with self.subTest(rooms=bool(rooms)):
                before = {"rooms": rooms, "calls": []}
                self.write_state(before)
                result = self.invoke("--dry-run")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("plan:", result.stdout)
                self.assertIn("grant_admin=2", result.stdout)
                if rooms:
                    self.assertNotIn("grant_owner=", result.stdout)
                else:
                    self.assertIn("grant_owner=1", result.stdout)
                self.assertEqual(self.read_state(), before)

    def test_human_owner_grant_preserves_occupant_before_membership_tightens(self):
        for affiliation in (None, "member", "admin", "outcast"):
            with self.subTest(affiliation=affiliation):
                room = self.drift()
                room["affiliations"].pop("admiral@example.test")
                if affiliation:
                    room["affiliations"]["admiral@example.test"] = affiliation
                nick = "squadron@rooms.example.test/admiral"
                room["occupants"][nick] = {"bare_jid": "admiral@example.test", "role": "participant"}
                before = {"rooms": {"squadron@rooms.example.test": room}, "calls": []}
                self.write_state(before)
                plan = self.invoke("--dry-run")
                self.assertEqual(plan.returncode, 0, plan.stderr)
                self.assertIn("grant_owner=1", plan.stdout)
                self.assertEqual(self.read_state(), before)
                result = self.invoke()
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("grant_owner=1", result.stdout)
                state = self.read_state()
                self.assertIn(nick, state["rooms"]["squadron@rooms.example.test"]["occupants"])
                self.compliant(state["rooms"]["squadron@rooms.example.test"])
                self.assertLess(state["calls"].index("affiliation:owner"),
                                state["calls"].index("set:members_only"))
                self.assertLess(state["calls"].index("affiliation:owner"),
                                state["calls"].index("affiliation:none"))

    def test_current_owner_role_is_repaired_without_regrant(self):
        room = self.drift()
        nick = "squadron@rooms.example.test/admiral"
        room["occupants"][nick] = {"bare_jid": "admiral@example.test", "role": "participant"}
        self.write_state({"rooms": {"squadron@rooms.example.test": room}, "calls": []})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("grant_owner=", result.stdout)
        self.assertNotIn("affiliation:owner", self.read_state()["calls"])
        self.assertEqual(self.read_state()["rooms"]["squadron@rooms.example.test"]["occupants"][nick]["role"],
                         "moderator")

    def test_owner_overlap_wins_and_duplicate_owner_entries_count_once(self):
        self.data["owner_jids"] = ["lead@seats.example.test", "lead@seats.example.test"]
        self.config.write_text(json.dumps(self.data))
        request = helper.registry(BRIDGE, self.config)
        self.assertEqual(request, [{"jid": "squadron@rooms.example.test",
            "owners": ["lead@seats.example.test"], "admins": ["worker@seats.example.test"]}])
        before = {"rooms": {}, "calls": []}
        self.write_state(before)
        result = self.invoke("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("grant_owner=1", result.stdout)
        self.assertIn("grant_admin=1", result.stdout)
        self.assertEqual(self.read_state(), before)
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.read_state()["rooms"]["squadron@rooms.example.test"]["affiliations"],
                         {"lead@seats.example.test": "owner", "worker@seats.example.test": "admin"})
        before = self.read_state()
        self.assertIn("verified: unchanged", self.invoke().stdout)
        self.assertEqual(self.read_state()["rooms"], before["rooms"])

    def test_ambiguous_owner_allowlist_fails_before_shell_without_broadening(self):
        self.data["owner_jids"].append("second@example.test")
        self.config.write_text(json.dumps(self.data))
        for args in ((), ("--dry-run",)):
            result = self.invoke(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("exactly one registry owner identity", result.stderr)
            self.assertNotIn("second@example.test", result.stderr)
            self.assertFalse(self.trace.exists())
            self.assertEqual(self.read_state(), {"rooms": {}, "calls": []})

    def test_changed_private_owner_identity_does_not_leave_previous_owner(self):
        self.assertEqual(self.invoke().returncode, 0)
        self.data["owner_jids"] = ["replacement@example.test"]
        self.config.write_text(json.dumps(self.data))
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("grant_owner=1", result.stdout)
        self.assertIn("clear_affiliations=1", result.stdout)
        self.assertNotIn("replacement@example.test", result.stdout + result.stderr)
        self.assertEqual(self.read_state()["rooms"]["squadron@rooms.example.test"]["affiliations"],
                         {"replacement@example.test": "owner", "lead@seats.example.test": "admin",
                          "worker@seats.example.test": "admin"})

    def test_owner_grant_and_persistence_failures_are_loud(self):
        for fault, code in (("affiliation", "affiliation-failed"), ("ignored-affiliation", "verify-failed"),
                            ("save", "save-failed")):
            with self.subTest(fault=fault):
                room = {"_data": {"persistent": True, "hidden": True, "whois": "moderators",
                                  "members_only": True, "allow_member_invites": False},
                        "affiliations": {"lead@seats.example.test": "admin",
                                         "worker@seats.example.test": "admin"}, "occupants": {}}
                self.write_state({"rooms": {"squadron@rooms.example.test": room},
                                  "calls": [], "fault": fault})
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn(code, result.stderr)
                self.assertIn("no completion claim", result.stderr)

    def test_missing_owner_count_evidence_is_rejected(self):
        rooms = [{"jid": "squadron@rooms.example.test", "owners": ["admiral@example.test"], "admins": []}]
        row = {"index": 1, "created": True, "verified": True, "settings": [],
               "grant_admin": 0, "clear_affiliations": 0, "repair_moderators": 0, "remove_occupants": 0}
        result = {"ok": True, "dry_run": False, "rooms": [row]}
        with self.assertRaisesRegex(helper.RoomError, "failed validation"):
            helper.response("Result: NONCE:" + json.dumps(result), "NONCE:", rooms, False)

    def test_missing_empty_invalid_registry_never_invokes_shell(self):
        for value in (None, {}, [], {"bad": {"jid": "YOUR_PASSWORD_TOKEN"}}):
            with self.subTest(value=value):
                data = dict(self.data)
                if value is None: data.pop("rooms")
                else: data["rooms"] = value
                self.config.write_text(json.dumps(data))
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.trace.exists())

    def test_adversarial_config_diagnostics_are_redacted(self):
        self.data["seats"] = {"YOUR_PASSWORD_TOKEN": "YOUR_PASSWORD_TOKEN"}
        self.config.write_text(json.dumps(self.data))
        self.assertNotEqual(self.invoke().returncode, 0)
        self.config.write_text('{"YOUR_PASSWORD_TOKEN":')
        self.assertNotEqual(self.invoke().returncode, 0)

    def test_current_admin_with_drifted_role_is_repaired(self):
        room = self.drift()
        room["affiliations"]["lead@seats.example.test"] = "admin"
        self.write_state({"rooms": {"squadron@rooms.example.test": room}, "calls": []})
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("role:moderator", self.read_state()["calls"])
        self.compliant(self.read_state()["rooms"]["squadron@rooms.example.test"])

    def test_locked_tombstone_and_broken_room_are_not_overwritten(self):
        for data in ({"locked": 1}, {"destroyed": True}, {"locked": True}):
            with self.subTest(data=data):
                room = self.drift()
                room["_data"].update(data)
                self.write_state({"rooms": {"squadron@rooms.example.test": room}, "calls": []})
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(self.read_state()["calls"], [])
                self.assertIn("room-protected", result.stderr)

    def test_all_room_preflight_precedes_first_mutation(self):
        self.data["rooms"]["z-last"] = {"jid": "last@rooms.example.test", "lead": "lead",
                                       "seats": ["lead"]}
        self.config.write_text(json.dumps(self.data))
        self.write_state({"rooms": {"last@rooms.example.test": {
            "_data": {"locked": 1}, "affiliations": {}, "occupants": {}}}, "calls": []})
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.read_state()["calls"], [])

    def test_mutation_lookup_api_and_persistence_failures_are_loud(self):
        cases = {"host": "host-unavailable", "lookup": "lookup-failed",
                 "create": "create-failed", "api": "api-unavailable",
                 "setter": "setting-failed", "affiliation": "affiliation-failed",
                 "ignored-affiliation": "verify-failed", "role": "role-failed",
                 "save": "save-failed", "exception": "operation-failed"}
        for fault, expected_code in cases.items():
            with self.subTest(fault=fault):
                room = self.drift()
                room["affiliations"]["lead@seats.example.test"] = "admin"
                rooms = {} if fault == "create" else {"squadron@rooms.example.test": room}
                self.write_state({"rooms": rooms, "calls": [], "fault": fault})
                result = self.invoke()
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertIn("no completion claim", result.stderr)
                self.assertIn(expected_code, result.stderr)

    def test_failed_save_is_retried_when_in_memory_policy_is_already_correct(self):
        self.write_state({"rooms": {}, "calls": [], "fault": "save"})
        self.assertNotEqual(self.invoke().returncode, 0)
        state = self.read_state()
        state.pop("fault")
        self.write_state(state)
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("unchanged", result.stdout)
        self.assertEqual(self.read_state()["calls"], state["calls"] + ["save"])

    def test_unconfirmed_malformed_duplicate_wrong_mode_and_nonzero_results_fail(self):
        for mode in ("disconnect", "error", "duplicate", "malformed", "nonce", "mode", "nonzero"):
            with self.subTest(mode=mode):
                self.env["FIXTURE_RUNNER"] = mode
                self.write_state({"rooms": {}, "calls": []})
                self.assertNotEqual(self.invoke().returncode, 0)

    def test_distinct_room_identities_and_admin_sets_are_not_cross_applied(self):
        self.data["rooms"] = {
            "z-worker": {"jid": "worker-room@rooms.example.test", "lead": "worker", "seats": ["worker"]},
            "a-lead": {"jid": "lead-room@rooms.example.test", "lead": "lead", "seats": ["lead"]}}
        self.config.write_text(json.dumps(self.data))
        result = self.invoke()
        self.assertEqual(result.returncode, 0, result.stderr)
        state = self.read_state()
        self.assertEqual(set(state["rooms"]), {"lead-room@rooms.example.test", "worker-room@rooms.example.test"})
        for name in ("lead", "worker"):
            self.assertEqual(state["rooms"][name + "-room@rooms.example.test"]["affiliations"],
                             {name + "@seats.example.test": "admin", "admiral@example.test": "owner"})
        self.assertEqual(len(result.stdout.splitlines()), 2)

    def test_later_room_save_failure_reports_partial_apply_not_success(self):
        self.data["rooms"]["z-last"] = {"jid": "last@rooms.example.test", "lead": "lead", "seats": ["lead"]}
        self.config.write_text(json.dumps(self.data))
        room = self.drift()
        room["fail_save"] = True
        self.write_state({"rooms": {"last@rooms.example.test": room}, "calls": []})
        result = self.invoke()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.assertIn("room 2; apply", result.stderr)
        self.assertIn("apply may be partial", result.stderr)
        self.compliant(self.read_state()["rooms"]["squadron@rooms.example.test"])

    def test_response_validation_rejects_wrong_identity_shape_and_contract_evidence(self):
        rooms = [{"jid": "squadron@rooms.example.test", "owners": ["admiral@example.test"],
                  "admins": ["lead@seats.example.test"]}]
        row = {"index": 1, "created": False, "verified": True, "settings": [],
               "grant_owner": 0, "grant_admin": 0, "clear_affiliations": 0,
               "repair_moderators": 0, "remove_occupants": 0}
        for changes in ({"index": 2}, {"index": True}, {"verified": False},
                        {"settings": ["YOUR_PASSWORD_TOKEN"]}, {"grant_admin": 2},
                        {"grant_admin": True}, {"grant_owner": 2}, {"grant_owner": True},
                        {"grant_owner": -1}, {"grant_owner": "1"}, {"remove_occupants": -1}):
            with self.subTest(changes=changes):
                result = {"ok": True, "dry_run": False, "rooms": [row | changes]}
                with self.assertRaisesRegex(helper.RoomError, "failed validation"):
                    helper.response("Result: NONCE:" + json.dumps(result), "NONCE:", rooms, False)
        with self.assertRaisesRegex(helper.RoomError, "failed validation"):
            helper.response('Result: NONCE:{"ok":true,"dry_run":false,"rooms":[]}',
                            "NONCE:", rooms, False)

    def test_timeout_is_redacted(self):
        with patch.object(helper.subprocess, "run", side_effect=subprocess.TimeoutExpired(
                "YOUR_PASSWORD_TOKEN", 30, output="YOUR_PASSWORD_TOKEN")):
            with self.assertRaisesRegex(helper.RoomError, "timed out"):
                helper.ensure([{"jid": "squadron@rooms.example.test", "owners": [], "admins": []}], False,
                              Path("YOUR_PASSWORD_TOKEN"))

    def test_argument_errors_and_help_are_safe_and_do_not_run_shell(self):
        self.assertNotEqual(self.invoke("--YOUR_PASSWORD_TOKEN").returncode, 0)
        result = self.invoke("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--dry-run", result.stdout)
        self.assertFalse(self.trace.exists())

    def test_lua_string_escaping_cannot_execute_injected_registry_text(self):
        value = '"; error("YOUR_PASSWORD_TOKEN"); --\n\\\x00é'
        lua = self.env["FIXTURE_LUA"]
        result = subprocess.run([lua, "-e", "io.write(" + helper.lua_quote(value) + ")"],
                                capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, value.encode("utf-8"))


if __name__ == "__main__":
    unittest.main()
# Offline executable fixtures:1 ends here
