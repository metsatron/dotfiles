#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import io
import re
import unittest
from contextlib import redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[3] / "bin" / "ai-usage"


def load_ai_usage():
    loader = importlib.machinery.SourceFileLoader("dotcortex_ai_usage", str(SCRIPT))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


class CodexAllowanceWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_monthly_window_uses_monthly_summary(self):
        reset_at = datetime.now(timezone.utc) + timedelta(days=25, hours=12)
        result = self.ai_usage.build_codex_native_result(
            next(spec for spec in self.ai_usage.PROVIDERS if spec.key == "codex"),
            {
                "plan_type": "go",
                "rate_limit": {
                    "secondary_window": {
                        "used_percent": 7,
                        "limit_window_seconds": 30 * 24 * 60 * 60,
                        "reset_at": reset_at.timestamp(),
                    }
                },
            },
        )

        self.assertEqual(result["summary"], "30d 7%; plan=go")
        self.assertEqual(result["raw"]["usage"]["secondary"]["windowMinutes"], 43200)

    def test_monthly_pacing_scales_over_full_cycle(self):
        now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        reset_at = now + timedelta(days=25)
        line = self.ai_usage.format_window_left_line("pace", reset_at.isoformat(), 43200, now)
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", line)

        self.assertRegex(plain, re.compile(r"pace\s+.*83% of 30d cycle"))

    def test_weekly_pacing_keeps_week_semantics(self):
        now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        reset_at = now + timedelta(days=3, hours=12)
        line = self.ai_usage.format_window_left_line("wk", reset_at.isoformat(), 10080, now)
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", line)

        self.assertRegex(plain, re.compile(r"wk\s+.*50% of week \d+"))
        fallback = self.ai_usage.format_window_left_line("wk", reset_at.isoformat(), now=now)
        fallback_plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", fallback)
        self.assertRegex(fallback_plain, re.compile(r"wk\s+.*50% of week \d+"))

        result = self.ai_usage.build_codex_native_result(
            next(spec for spec in self.ai_usage.PROVIDERS if spec.key == "codex"),
            {
                "rate_limit": {
                    "secondary_window": {
                        "used_percent": 7,
                        "limit_window_seconds": 7 * 24 * 60 * 60,
                        "reset_at": reset_at.timestamp(),
                    }
                },
            },
        )
        self.assertEqual(result["summary"], "weekly 7%")

    def test_renderer_never_calls_monthly_allowance_a_week(self):
        fixed_now = datetime(2026, 9, 15, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz else fixed_now.replace(tzinfo=None)

        item = {
            "provider": "codex",
            "label": "Codex",
            "state": "ok",
            "source": "codex-native",
            "summary": "30d 7%; plan=go",
            "raw": {
                "usage": {
                    "secondary": {
                        "usedPercent": 7,
                        "windowMinutes": 43200,
                        "resetsAt": (fixed_now + timedelta(days=25)).isoformat(),
                    },
                    "identity": {"plan": "go"},
                },
                "resetCredits": {"availableCount": 0, "credits": []},
            },
        }

        output = io.StringIO()
        with patch.object(self.ai_usage, "datetime", FixedDateTime), redirect_stdout(output):
            self.ai_usage.render_text([item])
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", output.getvalue())

        self.assertRegex(plain, re.compile(r"30d\s+.*93%"))
        self.assertRegex(plain, re.compile(r"pace\s+.*83% of 30d cycle"))
        self.assertNotRegex(plain, re.compile(r"wk\s+.*100%"))


if __name__ == "__main__":
    unittest.main()
