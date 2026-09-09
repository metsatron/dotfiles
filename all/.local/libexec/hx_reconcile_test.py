"""Offline contract tests for caller-owned source reconciliation."""
import base64
import copy
import hashlib
import importlib.machinery
import importlib.util
import io
import itertools
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import hx_reconcile as rc


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.caller = self.base / "caller"
        self.hub = self.base / "hub"
        self.root = self.caller / "DotCortex"
        self.root.mkdir(parents=True)
        (self.hub / "DotCortex").mkdir(parents=True)
        (self.root / "a.org").write_bytes(b"caller dirty\n")
        (self.root / "untracked.org").write_bytes(b"caller untracked\x00\xff\n")
        (self.hub / "DotCortex/a.org").write_bytes(b"WRONG HUB SOURCE")
        (self.root / "agents.org").write_bytes(b"EXCLUDED LAW")
        (self.root / "agents-skills-extra.org").write_bytes(b"EXCLUDED SKILLS")
        (self.root / "claude.org").write_bytes(b"EXCLUDED RETIRED")
        (self.root / "nested").mkdir()
        (self.root / "nested/private.org").write_bytes(b"EXCLUDED NESTED")
        # A fixture-only index names old committed bytes; capture must not use it.
        (self.root / ".git").mkdir()
        (self.root / ".git/HEAD").write_text("fixture old revision")
        for home in (self.caller, self.hub):
            runtime = home / ".local/libexec"
            runtime.mkdir(parents=True)
            for name in ("hx-router", "hx_reconcile.py"):
                shutil.copy2(HERE / name, runtime / name)
        self.registry = self.base / "router.json"
        self.config = json.loads((HERE.parents[1] / ".config/agent-session/fleet-router.json").read_text())
        self.registry.write_text(json.dumps(self.config))
        self.machines = self.base / "machines.json"
        self.machines.write_text(json.dumps({"machines": [{"key": self.config["transport"]["hub_machine_key"],
                                                          "role": "hub", "hostnames": ["fixture-hub"]}]}))
        self.reporter = self.hub / "real-export"
        self.reporter.write_text('''#!/usr/bin/env python3
import base64,json,os,sys
sys.dont_write_bytecode=True
sys.path.insert(0,os.path.expanduser("~/.local/libexec"))
import hx_reconcile as rc
raw=sys.stdin.buffer.read()
out={"argv":sys.argv[1:],"caller_pwd":os.environ.get("HX_CALLER_PWD"),
     "stack":os.environ.get("HX_ROUTER_STACK"),"stdin":base64.b64encode(raw).decode()}
if sys.argv[1:4]==["hub-finalize","--snapshot-protocol",rc.PROTOCOL]:
    manifest,contents,_=rc.decode_frame(__import__("io").BytesIO(raw))
    out["manifest"]=manifest
    out["contents"]={r["path"]:base64.b64encode(b).decode() for r,b in contents}
sys.stdout.buffer.write(json.dumps(out,ensure_ascii=True).encode()+b"\\n")
sys.stderr.buffer.write(b"exact-stderr:\\x00\\xff\\n")
sys.exit(int(os.environ.get("FIXTURE_APP_STATUS","37")))
''')
        self.reporter.chmod(0o755)
        self.ssh = self.base / "ssh"
        self.ssh.write_text('''#!/usr/bin/env python3
import json,os,subprocess,sys
with open(os.environ["FIXTURE_SSH_LOG"],"w") as f: json.dump(sys.argv[1:],f)
if "FIXTURE_SSH_STATUS" in os.environ: sys.exit(int(os.environ["FIXTURE_SSH_STATUS"]))
os.environ["HOME"]=os.environ["FIXTURE_HUB_HOME"]
if "FIXTURE_FRAME_DAMAGE" in os.environ:
    raw=sys.stdin.buffer.read()
    raw=raw[:-1] if os.environ["FIXTURE_FRAME_DAMAGE"]=="truncate" else raw[:-32]+bytes(32)
    sys.exit(subprocess.run(["/bin/sh","-c",sys.argv[-1]],input=raw).returncode)
os.execv("/bin/sh",["sh","-c",sys.argv[-1]])
''')
        self.ssh.chmod(0o755)
        self.env = dict(os.environ, HOME=str(self.caller), HX_ROUTER_TEST="1", HX_SSH_BIN=str(self.ssh),
                        HX_ROUTER_HOSTNAME="fixture-client", HELM_ROUTER_MACHINE_REGISTRY=str(self.machines),
                        HX_CALLER_PWD=str(self.caller), HX_ROUTER_STACK="",
                        FIXTURE_SSH_LOG=str(self.base / "ssh.json"), FIXTURE_HUB_HOME=str(self.hub),
                        PYTHONDONTWRITEBYTECODE="1")
        for key in ("FIXTURE_SSH_STATUS", "FIXTURE_APP_STATUS", "FIXTURE_FRAME_DAMAGE"):
            self.env.pop(key, None)

    def command(self, argv, tool="dotcortex-export", local=None):
        return [sys.executable, "-B", str(self.caller / ".local/libexec/hx-router"), str(self.registry),
                tool, str(local or self.base / "NEVER-PROBE-NFS/real"), str(self.reporter), *argv]

    def run_router(self, argv, **kwargs):
        return subprocess.run(self.command(argv, **kwargs), input=b"CALLER STDIN MUST SURVIVE\n",
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env, timeout=15)

    def decode(self, frame):
        return rc.decode_frame(io.BytesIO(frame))

    def changed_frame(self, frame, change):
        manifest, contents, _ = self.decode(frame)
        change(manifest)
        header = rc.canonical(manifest)
        body = rc.MAGIC + len(header).to_bytes(8, "big") + header + b"".join(b for _, b in contents)
        return body + hashlib.sha256(body).digest()

    def test_divergent_dirty_untracked_and_exact_transport(self):
        strange = "checkout space;'$()`☃\nnext"
        target = self.caller / strange
        self.root.rename(target)
        args = ["--skip-validate", "--source-root", strange, "--dry-run", "--source-only"]
        result = self.run_router(args)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertEqual(result.stderr, b"exact-stderr:\x00\xff\n")
        out = json.loads(result.stdout)
        self.assertEqual(out["argv"], ["hub-finalize", "--snapshot-protocol", rc.PROTOCOL, "--", *args])
        self.assertEqual(out["caller_pwd"], str(self.caller))
        self.assertEqual(out["stack"], "dotcortex-export")
        self.assertEqual(out["manifest"]["source"]["checkout"], str(target))
        self.assertEqual(out["manifest"]["source"]["mode"], "working-tree")
        self.assertEqual(out["manifest"]["source"]["host"], rc.socket.gethostname())
        self.assertEqual({k:base64.b64decode(v) for k,v in out["contents"].items()},
                         {"a.org": b"caller dirty\n", "untracked.org": b"caller untracked\x00\xff\n"})
        ssh = json.loads((self.base / "ssh.json").read_text())
        for option in ("BatchMode=yes", "PasswordAuthentication=no", "KbdInteractiveAuthentication=no",
                       "PreferredAuthentications=publickey", "ConnectTimeout=10", "ConnectionAttempts=1"):
            self.assertIn(option, ssh)
        self.assertIn("-T", ssh)
        self.assertEqual(ssh[-2], self.config["transport"]["hub_ssh_alias"])

    def test_exact_one_content_read_and_determinism(self):
        calls = []
        original = os.fdopen
        class Reader:
            def __init__(self, stream): self.stream = stream
            def __enter__(self): return self
            def __exit__(self, *args): self.stream.close()
            def fileno(self): return self.stream.fileno()
            def read(self, count):
                calls.append((self.fileno(), count))
                return self.stream.read(count)
        with mock.patch.object(rc.os, "fdopen", side_effect=lambda *a, **k: Reader(original(*a, **k))):
            first = rc.snapshot(str(self.root), str(self.caller))
        self.assertEqual(len(calls), 2)
        self.assertEqual([count for _, count in calls], [rc.MAX_FILE + 1] * 2)
        self.assertEqual(first, rc.snapshot(str(self.root), str(self.caller)))
        (self.root / "a.org").write_bytes(b"edited after capture")
        self.assertEqual(dict((r["path"], b) for r,b in self.decode(first)[1])["a.org"], b"caller dirty\n")

    def test_source_change_during_read_refused(self):
        original = os.fstat
        calls = 0
        def mutate(fd):
            nonlocal calls
            calls += 1
            if calls == 2:
                (self.root / "a.org").write_bytes(b"changed during read")
            return original(fd)
        with mock.patch.object(rc.os, "fstat", side_effect=mutate), self.assertRaises(rc.Refusal):
            rc.snapshot(str(self.root), str(self.caller))

    def test_missing_symlink_nonregular_oversize_and_escape(self):
        for path in (str(self.base / "missing"), str(self.root / "../DotCortex")):
            with self.subTest(path=path), self.assertRaises(rc.Refusal):
                rc.snapshot(path, str(self.caller))
        link = self.base / "link"
        link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(rc.Refusal): rc.snapshot(str(link), str(self.caller))
        bad = self.root / "bad.org"
        bad.symlink_to(self.hub / "DotCortex/a.org")
        with self.assertRaises(rc.Refusal): rc.snapshot(str(self.root), str(self.caller))
        bad.unlink()
        os.mkfifo(bad)
        with self.assertRaises(rc.Refusal): rc.snapshot(str(self.root), str(self.caller))
        bad.unlink()
        bad.mkdir()
        with self.assertRaises(rc.Refusal): rc.snapshot(str(self.root), str(self.caller))
        bad.rmdir()
        with bad.open("wb") as f: f.truncate(rc.MAX_FILE + 1)
        with self.assertRaises(rc.Refusal): rc.snapshot(str(self.root), str(self.caller))

    def test_bounds_and_empty(self):
        with mock.patch.object(rc, "MAX_CONTENT", 1), self.assertRaises(rc.Refusal):
            rc.snapshot(str(self.root), str(self.caller))
        with mock.patch.object(rc, "MAX_FILES", 1), self.assertRaises(rc.Refusal):
            rc.snapshot(str(self.root), str(self.caller))
        with mock.patch.object(rc, "MAX_MANIFEST", 1), self.assertRaises(rc.Refusal):
            rc.snapshot(str(self.root), str(self.caller))
        empty = self.base / "empty"
        empty.mkdir()
        with self.assertRaises(rc.Refusal): rc.snapshot(str(empty), str(self.caller))

    def test_remote_mount_refused_before_open(self):
        mounts = b"1 0 0:1 / / rw - ext4 none rw\n2 1 0:2 / " + str(self.root).encode() + b" rw - nfs4 none rw\n"
        with mock.patch("builtins.open", return_value=io.BytesIO(mounts)), \
             mock.patch.object(rc, "open_root", side_effect=AssertionError("source probed")), \
             self.assertRaises(rc.Refusal) as caught:
            rc.snapshot(str(self.root), str(self.caller))
        self.assertEqual(caught.exception.code, 78)

    def test_integrity_truncation_unknown_and_path_validation(self):
        frame = rc.snapshot(str(self.root), str(self.caller))
        for broken in (frame[:1], frame[:-1], frame + b"junk", frame[:-32] + bytes(32)):
            with self.subTest(length=len(broken)), self.assertRaises(rc.Refusal): self.decode(broken)
        changes = [lambda m: m.update(protocol="future"), lambda m: m.update(admission="future"),
                   lambda m: m.update(extra=1), lambda m: m["files"][0].update(path="../escape.org"),
                   lambda m: m["files"][0].update(path="/absolute.org"),
                   lambda m: m["files"][0].update(path="agents.org"),
                   lambda m: m["files"][0].update(bytes=rc.MAX_FILE + 1),
                   lambda m: m["files"][0].update(sha256="0" * 64),
                   lambda m: m["files"][1].update(path=m["files"][0]["path"])]
        for change in changes:
            with self.subTest(change=change), self.assertRaises(rc.Refusal):
                self.decode(self.changed_frame(frame, change))
        damaged = bytearray(frame)
        damaged[-33] ^= 1
        with self.assertRaises(rc.Refusal): self.decode(bytes(damaged))
        with mock.patch.object(rc, "MAX_FRAME", 5), self.assertRaises(rc.Refusal): self.decode(frame)

    def test_flags_any_order_and_fail_before_transport(self):
        for args in itertools.permutations(["--source-only", "--dry-run", "--skip-validate"]):
            self.assertEqual(rc.classify(list(args))[0], "client-fanout-reconcile")
        for args in itertools.permutations(["--logs-only", "--dry-run", "--skip-validate"]):
            self.assertEqual(rc.classify(list(args))[0], "hub")
        for args in (["--dry-run", "hub-finalize"], ["hub-finalize", "--dry-run"]):
            self.assertEqual(rc.classify(args)[0], "hub")
        for args in (["--logs-only", "--source-only"], ["--source-only", "--dry-run", "--logs-only"],
                     ["--source-root"], ["--source-root="], ["--unknown"],
                     ["hub-finalize", "--source-only"], ["--logs-only", "--source-root=x"],
                     ["--source-root=x", "--source-root", "y"]):
            with self.subTest(args=args):
                result = self.run_router(args)
                self.assertEqual(result.returncode, 2, result.stderr)
                self.assertFalse((self.base / "ssh.json").exists())

    def test_source_default_and_hub_local(self):
        self.assertEqual(self.run_router([]).returncode, 37)
        (self.base / "ssh.json").unlink()
        self.env["HX_ROUTER_HOSTNAME"] = "fixture-hub"
        result = self.run_router(["--source-only"], local=self.reporter)
        self.assertEqual(result.returncode, 37, result.stderr)
        self.assertFalse((self.base / "ssh.json").exists())
        self.assertEqual(json.loads(result.stdout)["manifest"]["source"]["checkout"], str(self.root))

    def test_no_nfs_guard_and_recursion(self):
        loader = importlib.machinery.SourceFileLoader("fixture_router", str(HERE / "hx-router"))
        spec = importlib.util.spec_from_loader(loader.name, loader)
        router = importlib.util.module_from_spec(spec)
        loader.exec_module(router)
        with mock.patch.dict(os.environ, self.env, clear=True), \
             mock.patch.object(sys, "argv", self.command(["--source-only"])[2:]), \
             mock.patch.object(router, "guard_local", side_effect=AssertionError("NFS probe")), \
             mock.patch.object(rc, "dispatch", return_value=37), self.assertRaises(SystemExit) as result:
            router.main()
        self.assertEqual(result.exception.code, 37)
        self.env["HX_ROUTER_STACK"] = "dotcortex-export"
        self.assertEqual(self.run_router([]).returncode, 125)
        self.assertFalse((self.base / "ssh.json").exists())

    def test_ordinary_hub_stdin_and_direct_finalize(self):
        for args in (["--dry-run", "--logs-only"], ["--skip-validate", "hub-finalize"]):
            result = self.run_router(args)
            self.assertEqual(result.returncode, 37, result.stderr)
            out = json.loads(result.stdout)
            self.assertEqual(out["argv"], args)
            self.assertEqual(out["stdin"], "")

    def test_caller_stdin_not_consumed(self):
        import shlex
        script = shlex.join(self.command(["--source-only"])) + ' >/dev/null 2>/dev/null; IFS= read -r rest; printf "%s" "$rest"'
        result = subprocess.run(["/bin/bash", "-c", script], input=b"following command input\n",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=self.env, timeout=15)
        self.assertEqual(result.stdout, b"following command input")

    def test_ssh_failure_and_missing_receiver_no_fallback(self):
        self.env["FIXTURE_SSH_STATUS"] = "255"
        result = self.run_router([])
        self.assertEqual(result.returncode, 255)
        self.assertEqual(result.stdout, b"")
        del self.env["FIXTURE_SSH_STATUS"]
        (self.hub / ".local/libexec/hx_reconcile.py").unlink()
        result = self.run_router([])
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b"")

    def test_damaged_transfer_refused_without_finalizer_output(self):
        for damage in ("truncate", "digest"):
            self.env["FIXTURE_FRAME_DAMAGE"] = damage
            result = self.run_router([])
            self.assertEqual(result.returncode, 65, result.stderr)
            self.assertEqual(result.stdout, b"")
            self.assertNotIn(b"exact-stderr", result.stderr)

    def test_refuse_unsupported_registry_and_reconcile(self):
        for transform in (lambda c: c.update(schema="dotcortex.fleet-router.v1"),
                          lambda c: c["tools"]["dotcortex-export"]["reconcile"].update(protocol="future"),
                          lambda c: c["tools"]["dotcortex-export"]["reconcile"].update(extra=True)):
            config = copy.deepcopy(self.config)
            transform(config)
            self.registry.write_text(json.dumps(config))
            self.assertEqual(self.run_router([]).returncode, 78)
            self.assertFalse((self.base / "ssh.json").exists())
        self.registry.write_text(json.dumps(self.config))
        self.assertEqual(self.run_router([], tool="telegram-export-pipeline").returncode, 78)

    def test_receiver_rejects_bad_frame_before_application(self):
        payload = {"protocol": rc.PROTOCOL, "tool": "dotcortex-export", "real": str(self.reporter),
                   "argv": ["--source-only"], "caller_pwd": str(self.caller), "router_stack": "dotcortex-export"}
        with mock.patch.object(rc, "run_bounded", side_effect=AssertionError("application executed")), \
             self.assertRaises(rc.Refusal):
            rc.finalize(payload, io.BytesIO(b"truncated"))
        with mock.patch.object(rc.subprocess, "run", side_effect=subprocess.TimeoutExpired("fake", 600)), \
             self.assertRaises(rc.Refusal) as caught:
            rc.run_bounded(["fake"], b"")
        self.assertEqual(caught.exception.code, 124)


if __name__ == "__main__":
    unittest.main()
