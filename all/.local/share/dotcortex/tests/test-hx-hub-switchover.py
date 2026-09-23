#!/usr/bin/env python3
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[5]
SCRIPT = ROOT / "all/.local/bin/hx-hub-switchover"
loader = importlib.machinery.SourceFileLoader("hx_hub_switchover", str(SCRIPT))
spec = importlib.util.spec_from_loader(loader.name, loader)
hx = importlib.util.module_from_spec(spec)
loader.exec_module(hx)


def manifest():
    hooks = {phase: [{"ssh_alias": "local", "path": "/bin/true"}]
             for phase in hx.REQUIRED_HOOKS}
    return {
        "schema": hx.SCHEMA,
        "id": "x230-to-titan",
        "source": {"machine_key": "x230", "ssh_alias": "x230",
                   "root": "/srv/helmcortex"},
        "target": {"machine_key": "titan", "ssh_alias": "titan",
                   "root": "/srv/helmcortex", "stow_target": "titan",
                   "state_root": "/var/tmp/hx-state"},
        "clients": [{"ssh_alias": "local", "stow_target": "t480s"},
                    {"ssh_alias": "titan", "stow_target": "titan"}],
        "hooks": hooks,
        "excludes": ["CORE/anaconda3/**"],
    }


class SwitchoverTests(unittest.TestCase):
    def test_manifest_contract(self):
        value = hx.validate_manifest(manifest())
        self.assertEqual(value["target"]["machine_key"], "titan")

    def test_manifest_rejects_parent_traversal(self):
        value = manifest()
        value["excludes"] = ["../escape"]
        with self.assertRaises(hx.Refusal):
            hx.validate_manifest(value)

    def test_manifest_requires_target_client(self):
        value = manifest()
        value["clients"] = [{"ssh_alias": "local", "stow_target": "t480s"}]
        with self.assertRaises(hx.Refusal):
            hx.validate_manifest(value)

    def test_manifest_rejects_nested_state(self):
        value = manifest()
        value["target"]["state_root"] = "/srv/helmcortex/.state"
        with self.assertRaises(hx.Refusal):
            hx.validate_manifest(value)

    def test_approval_binds_manifest_and_plan(self):
        self.assertNotEqual(hx.approval_token(b"a", b"plan"),
                            hx.approval_token(b"b", b"plan"))
        self.assertNotEqual(hx.approval_token(b"a", b"plan"),
                            hx.approval_token(b"a", b"changed"))

    def test_declaration_changes_exact_two_owners(self):
        fleet = '"hub_machine_key": "x230"\n"hub_ssh_alias": "x230"\n'
        machines = ('  {"key": "x230", "ssh_alias": "x230", "role": "hub"}\n'
                    '  {"key": "titan", "ssh_alias": "titan", "role": "client"}\n')
        fleet, machines = hx.declaration_text(
            fleet, machines, "x230", "x230", "titan", "titan")
        self.assertIn('"hub_machine_key": "titan"', fleet)
        self.assertIn('"key": "x230", "ssh_alias": "x230", "role": "client"', machines)
        self.assertIn('"key": "titan", "ssh_alias": "titan", "role": "hub"', machines)

    def test_declaration_refuses_ambiguous_source(self):
        with self.assertRaises(hx.Refusal):
            hx.declaration_text("", "", "x230", "x230", "titan", "titan")

    def test_client_tokens_are_bounded(self):
        self.assertEqual(hx.parse_client("local:t480s")["stow_target"], "t480s")
        with self.assertRaises(hx.Refusal):
            hx.parse_client("bad alias:t480s")


if __name__ == "__main__":
    unittest.main()
