import importlib.util
from importlib.machinery import SourceFileLoader
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

def load(path, name):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeSupervisor:
    def __init__(self, module):
        self.module = module
        self.obj = module.Supervisor.__new__(module.Supervisor)
        self.obj.enabled = True
        self.obj.status = "idle"
        self.obj.compacting = False
        self.obj.session_id = "123e4567-e89b-12d3-a456-426614174000"
        self.obj.channel = "claude-test"
        self.obj.dirty = True
        self.obj.usage_limit_until = time.time() + 600
        self.obj.last_normal_stop = time.time() - 100
        self.obj.last_lifecycle_activity = None
        self.obj.last_local_input = None
        self.obj.transcript_activity_at = None
        self.obj.transcript_gate_blocked = False
        self.obj.transcript_gate_blocked_at = None
        self.obj.transcript_quiescence_deadline = None
        self.obj.recovery_pending = False
        self.obj.current_tokens = 100_000
        self.obj.post_compact_baseline_tokens = 0
        self.obj.cache_ttl_seconds = 3600
        self.obj.watched_servers = ()
        self.obj.recovery_command = None
        self.obj.preservation_state = None
        self.obj.timer_generation = 0
        self.obj.last_gate_rejection_reason = None
        self.obj.last_cancellation_reason = None
        self.obj.last_state_transition = None
        self.obj.last_injection_result = None
        self.obj.timer_deadline = None
        self.obj.timer_kind = None
        self.obj.compaction_requested_at = None
        self.obj.compaction_ignore_next_stop = False
        self.obj.mailcortex_input_dirty = False
        self.obj._pty_still_owned = lambda: True
        self.obj._injection_idle_boundary = lambda purpose: self.obj.last_normal_stop
        self.obj._idle_window_open = lambda: False
        self.obj._read_snapshot = lambda: ({}, None)
        self.obj._refresh_cache_policy_for_action = lambda: True
        self.obj._guard_log = lambda *args, **kwargs: None
        self.obj._write_state = lambda: None
        self.obj._debug = lambda *args, **kwargs: None
        self.obj.rearm = lambda *args, **kwargs: None



class DeciderWarmTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.module = load(Path(__file__).parents[3] / "bin/claude-warm", "decider_warm_test")

    def make(self):
        obj = FakeSupervisor(self.module).obj
        obj._decider_summary_ready = lambda: True
        return obj

    def test_usage_exhausted_timer_path_injects_one_native_local_compact(self):
        obj = self.make()
        read_fd, write_fd = os.pipe()
        obj.master_fd = write_fd
        try:
            self.assertTrue(obj.attempt(command="/compact", purpose="compact"))
            self.assertEqual(os.read(read_fd, 128), b"/compact decider-local-only\r")
            self.assertTrue(obj.compacting)
            self.assertEqual(obj._gate_reason("decider-compact"), "already-compacting")
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_missing_native_load_receipt_preserves_usage_hold(self):
        obj = self.make()
        obj._decider_summary_ready = lambda: False
        self.assertEqual(obj._gate_reason("compact"), "usage-limited")
        self.assertEqual(obj._gate_reason("decider-compact"), "decider-mod-not-ready")
        self.assertFalse(obj.attempt(command="/compact", purpose="compact"))

    def test_local_path_retains_human_input_gate(self):
        obj = self.make()
        obj._idle_window_open = lambda: True
        obj.last_local_input = time.time()
        self.assertEqual(obj._gate_reason("decider-compact"), "user-input")

    def test_receipt_requires_exact_supervisor_channel_and_session(self):
        obj = FakeSupervisor(self.module).obj
        with tempfile.TemporaryDirectory() as directory:
            obj.session_dir = Path(directory)
            receipt = obj.session_dir / "decider-summary-ready.json"
            good = {"protocol": "decider-summary.v1", "channel": obj.channel, "session_id": obj.session_id}
            for patch, expected in [({}, True), ({"session_id": "other"}, False), ({"channel": "other"}, False), ({"protocol": "other"}, False)]:
                receipt.write_text(json.dumps({**good, **patch}))
                self.assertEqual(obj._decider_summary_ready(), expected)
            receipt.write_text("[]")
            self.assertFalse(obj._decider_summary_ready())

    def test_ordinary_no_mod_compact_and_manual_controls_remain_guarded(self):
        obj = self.make()
        obj._decider_summary_ready = lambda: False
        obj.usage_limit_until = None
        read_fd, write_fd = os.pipe()
        obj.master_fd = write_fd
        try:
            self.assertTrue(obj.attempt(command="/compact", purpose="compact"))
            self.assertEqual(os.read(read_fd, 128), b"/compact\r")
        finally:
            os.close(read_fd)
            os.close(write_fd)
        obj = self.make()
        self.assertFalse(obj.attempt(command="/compact decider-local-only", purpose="manual"))

if __name__ == "__main__":
    unittest.main()
