#!/usr/bin/env python3
# Deterministic tests


# [[file:../../../../../services-network-dns.org::*Deterministic tests][Deterministic tests:1]]
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import runpy
import shutil
import subprocess
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[5]
SCRIPT = REPO / "linux/.local/bin/tailscale-dns-setup"
MODULE = runpy.run_path(str(SCRIPT), run_name="dns_test_module")
Setup, ContractError = MODULE["Setup"], MODULE["ContractError"]
EXPECTED, TS_HEADER, NM_HEADER = (MODULE[key] for key in ("EXPECTED", "TS_HEADER", "NM_HEADER"))


class FakeHost:
    def __init__(self, root):
        self.root = root
        self.calls = []
        self.accept = True
        self.running = True
        self.magic = True
        self.plugin = "default"
        self.override = False
        self.reenabled_fails = False
        self.disable_fails = False
        self.rewrite = False
        self.health = []
        self.target = root / "etc/NetworkManager/conf.d/90-dotcortex-tailscale-dns.conf"
        self.resolver = root / "etc/resolv.conf"
        self.resolver.parent.mkdir(parents=True)
        self.resolver.write_text(NM_HEADER + "\n")
        self.template = root / "template.conf"
        self.template.write_text(EXPECTED)

    def __call__(self, argv, privileged=False):
        self.calls.append((argv, privileged))
        if argv == ["tailscale", "status", "--json"]:
            return json.dumps({"BackendState": "Running" if self.running else "Stopped", "Health": self.health})
        if argv == ["tailscale", "dns", "status", "--json"]:
            return json.dumps({"TailscaleDNS": self.accept, "CurrentTailnet": {"MagicDNSEnabled": self.magic}})
        if argv == ["NetworkManager", "--print-config"]:
            if self.target.exists() and not self.override:
                return EXPECTED
            return f"[main]\ndns={self.plugin}\nrc-manager=auto\n"
        if argv[:2] == ["install", "-d"]:
            Path(argv[-1]).mkdir(parents=True, exist_ok=True)
        elif argv[:2] == ["install", "-m"] or argv[:2] == ["cp", "-a"]:
            shutil.copyfile(argv[-2], argv[-1])
        elif argv == ["nmcli", "general", "reload", "dns-rc"]:
            if self.rewrite:
                self.resolver.write_text(NM_HEADER + "\nchanged\n")
        elif argv == ["nmcli", "general", "reload", "conf"]:
            pass
        elif argv == ["tailscale", "set", "--accept-dns=false"]:
            self.accept = False
            if self.disable_fails:
                raise ContractError("fixture failure after disabling DNS")
        elif argv == ["tailscale", "set", "--accept-dns=true"]:
            if self.reenabled_fails:
                raise ContractError("fixture re-enable failure")
            self.accept = True
            self.health = []
            self.resolver.write_text(TS_HEADER + "\n")
        else:
            raise AssertionError(f"Unexpected command: {argv}")
        return ""


class DnsOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.host = FakeHost(self.root)
        self.setup = Setup(self.root, self.host, self.host.template)
        self.output = contextlib.redirect_stdout(io.StringIO())
        self.output.__enter__()
        self.addCleanup(self.output.__exit__, None, None, None)

    def mutation_calls(self):
        return [argv for argv, _ in self.host.calls if argv[0] in ("install", "cp", "nmcli") or argv[:2] == ["tailscale", "set"]]

    def test_plan_is_read_only(self):
        self.assertEqual(self.setup.preflight(), "direct")
        self.assertEqual(self.mutation_calls(), [])

    def test_repair_checkpoints_before_mutation_and_reloads_without_restart(self):
        before = self.host.resolver.read_bytes()
        self.setup.apply()
        self.assertEqual((self.setup.checkpoint / "resolv.conf").read_bytes(), before)
        self.assertEqual(self.host.target.read_text(), EXPECTED)
        self.assertTrue(self.host.accept)
        calls = self.mutation_calls()
        self.assertLess(next(i for i, cmd in enumerate(calls) if cmd[:2] == ["cp", "-a"]), next(i for i, cmd in enumerate(calls) if cmd[:2] == ["install", "-m"]))
        self.assertIn(["nmcli", "general", "reload", "conf"], calls)
        self.assertIn(["nmcli", "general", "reload", "dns-rc"], calls)
        self.assertLess(calls.index(["nmcli", "general", "reload", "conf"]), calls.index(["tailscale", "set", "--accept-dns=false"]))
        self.assertFalse(any("restart" in cmd or "down" in cmd for cmd in calls))

    def test_healthy_direct_host_is_protected_without_dns_toggle(self):
        self.host.resolver.write_text(TS_HEADER + "\n")
        self.setup.apply()
        self.assertFalse(any(cmd[:2] == ["tailscale", "set"] for cmd in self.mutation_calls()))
        self.assertEqual(self.host.target.read_text(), EXPECTED)

    def test_repeat_apply_does_not_rewrite_files_or_create_checkpoint(self):
        self.setup.apply()
        checkpoint_dirs = list((self.root / "var/lib/dotcortex/network-dns/checkpoints").iterdir())
        self.host.calls.clear()
        self.setup.apply()
        self.assertFalse(any(cmd[0] in ("install", "cp") or cmd[:2] == ["tailscale", "set"] for cmd in self.mutation_calls()))
        self.assertEqual(list((self.root / "var/lib/dotcortex/network-dns/checkpoints").iterdir()), checkpoint_dirs)

    def test_check_is_read_only(self):
        self.setup.apply()
        self.host.calls.clear()
        self.setup.verify()
        self.assertEqual(self.mutation_calls(), [])

    def test_uninstalled_check_fails(self):
        with self.assertRaisesRegex(ContractError, "not installed"):
            self.setup.verify()

    def test_integrated_resolvers_are_preserved(self):
        for name in ("systemd/resolve", "resolvconf"):
            with self.subTest(name=name):
                self.host.resolver.unlink()
                target = self.root / "run" / name / "resolv.conf"
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text("integration fixture\n")
                self.host.resolver.symlink_to(target)
                self.host.calls.clear()
                self.setup.apply()
                self.assertEqual(self.mutation_calls(), [])
                self.assertFalse(self.host.target.exists())
                self.assertTrue(self.host.resolver.is_symlink())

    def test_unknown_symlink_fails_before_mutation(self):
        self.host.resolver.unlink()
        self.host.resolver.symlink_to(self.host.template)
        with self.assertRaisesRegex(ContractError, "Unknown resolver symlink"):
            self.setup.apply()
        self.assertEqual(self.mutation_calls(), [])

    def test_unknown_file_owner_fails_before_mutation(self):
        self.host.resolver.write_text("operator-owned fixture\n")
        with self.assertRaisesRegex(ContractError, "Unknown direct-file"):
            self.setup.apply()
        self.assertEqual(self.mutation_calls(), [])

    def test_disabled_dns_and_magicdns_are_not_overridden(self):
        for field in ("accept", "magic", "running"):
            with self.subTest(field=field):
                setattr(self.host, field, False)
                with self.assertRaises(ContractError):
                    self.setup.apply()
                setattr(self.host, field, True)
        self.assertEqual(self.mutation_calls(), [])

    def test_existing_caching_plugin_is_preserved(self):
        self.host.plugin = "dnsmasq"
        with self.assertRaisesRegex(ContractError, "DNS plugin"):
            self.setup.apply()
        self.assertEqual(self.mutation_calls(), [])

    def test_unexpected_dropin_is_preserved(self):
        self.host.target.parent.mkdir(parents=True)
        self.host.target.write_text("operator-owned drop-in\n")
        with self.assertRaisesRegex(ContractError, "unexpected content"):
            self.setup.apply()
        self.assertEqual(self.mutation_calls(), [])
        self.assertEqual(self.host.target.read_text(), "operator-owned drop-in\n")

    def test_bad_template_fails_before_mutation(self):
        self.host.template.write_text(EXPECTED + "extra=bad\n")
        with self.assertRaisesRegex(ContractError, "Canonical template"):
            self.setup.apply()
        self.assertEqual(self.mutation_calls(), [])

    def test_overriding_config_aborts_before_dns_toggle(self):
        self.host.override = True
        with self.assertRaisesRegex(ContractError, "Effective NetworkManager"):
            self.setup.apply()
        self.assertFalse(any(cmd[:2] == ["tailscale", "set"] for cmd in self.mutation_calls()))
        self.assertTrue((self.setup.checkpoint / "resolv.conf").exists())

    def test_writer_challenge_detects_resolver_overwrite(self):
        self.host.rewrite = True
        with self.assertRaisesRegex(ContractError, "still changed"):
            self.setup.apply()

    def test_failed_reenable_is_reported_without_automatic_restore(self):
        self.host.reenabled_fails = True
        with self.assertRaisesRegex(ContractError, "accept-DNS may be off"):
            self.setup.apply()
        self.assertFalse(self.host.accept)
        self.assertTrue((self.setup.checkpoint / "resolv.conf").exists())
        self.assertEqual(self.host.target.read_text(), EXPECTED)

    def test_disable_failure_still_reenables_dns_and_fails_loud(self):
        self.host.disable_fails = True
        with self.assertRaisesRegex(ContractError, "disable failed; re-enable command succeeded"):
            self.setup.apply()
        self.assertTrue(self.host.accept)
        self.assertTrue((self.setup.checkpoint / "resolv.conf").exists())

    def test_help_does_not_touch_host(self):
        result = subprocess.run([str(SCRIPT), "--help"], text=True, capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--apply", result.stdout)


if __name__ == "__main__":
    unittest.main()
# Deterministic tests:1 ends here
