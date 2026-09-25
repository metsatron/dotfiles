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


# Redacted fixture: the real 2026-09-25 /v1/quota shape (including the
# undocumented legacy/new credit fields), synthetic values, key name removed.
NEURALWATT_FIXTURE = {
    "snapshot_at": "2026-09-25T02:50:00Z",
    "balance": {
        "credits_remaining_usd": 12.5,
        "total_credits_usd": 20.0,
        "credits_used_usd": 7.5,
        "accounting_method": "token",
        "legacy_credits_usd": 0.0,
        "new_credits_usd": 12.5,
    },
    "usage": {
        "lifetime": {"cost_usd": 7.5, "requests": 900, "tokens": 4000000, "energy_kwh": 1.2},
        "current_month": {"cost_usd": 1.25, "requests": 100, "tokens": 500000, "energy_kwh": 0.2},
    },
    "limits": {"overage_limit_usd": None, "rate_limit_tier": "standard"},
    "subscription": None,
    "key": {"name": "REDACTED", "allowance": None},
}


class NeuralWattObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()
        cls.now = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)

    def ok(self, raw):
        return {"provider": "neuralwatt", "label": "NeuralWatt", "state": "ok", "source": "api", "summary": "", "raw": raw}

    def test_credit_account_fixture(self):
        result = self.ai_usage.apply_neuralwatt_observation(self.ok(NEURALWATT_FIXTURE), self.now)
        self.assertEqual(result["state"], "ok")
        obs = result["observation"]
        self.assertEqual(obs["schema"], "neuralwatt.quota.v1")
        self.assertEqual(obs["observed_at"], "2026-09-25T02:50:00Z")
        self.assertEqual(obs["collected_at"], "2026-09-25T03:00:00+00:00")
        self.assertEqual(obs["balance"]["remaining_usd"], 12.5)
        self.assertIsNone(obs["subscription"])
        self.assertIsNone(obs["key_allowance"])
        self.assertEqual(result["summary"], "balance $12.50; month $1.25; no subscription")

    def test_subscription_and_key_allowance_stay_separate(self):
        raw = dict(NEURALWATT_FIXTURE)
        raw["subscription"] = {
            "plan": "pro", "status": "active", "billing_interval": "month",
            "current_period_start": "2026-09-01T00:00:00Z", "current_period_end": "2026-10-01T00:00:00Z",
            "auto_renew": True, "kwh_included": 10.0, "kwh_used": 4.0, "kwh_remaining": 6.0, "in_overage": False,
        }
        raw["key"] = {"name": "REDACTED", "allowance": {
            "limit_usd": 5.0, "period": "daily", "spent_usd": 1.0, "remaining_usd": 4.0, "blocked": False}}
        result = self.ai_usage.apply_neuralwatt_observation(self.ok(raw), self.now)
        obs = result["observation"]
        self.assertEqual(obs["subscription"]["kwh_remaining"], 6.0)
        self.assertEqual(obs["key_allowance"]["remaining_usd"], 4.0)
        self.assertEqual(obs["balance"]["remaining_usd"], 12.5)
        self.assertEqual(result["summary"], "balance $12.50; month $1.25; pro active 4/10 kWh; key daily $4.00 left")

    def test_schema_drift_is_an_error_not_a_guess(self):
        raw = {k: v for k, v in NEURALWATT_FIXTURE.items() if k != "balance"}
        result = self.ai_usage.apply_neuralwatt_observation(self.ok(raw), self.now)
        self.assertEqual(result["state"], "error")
        self.assertIn("missing balance", result["summary"])
        self.assertNotIn("observation", result)

    def test_non_ok_probe_passes_through(self):
        failed = {"provider": "neuralwatt", "label": "NeuralWatt", "state": "error", "source": "api",
                  "summary": "https://api.neuralwatt.com/v1/quota returned HTTP 429", "raw": None}
        self.assertIs(self.ai_usage.apply_neuralwatt_observation(failed, self.now), failed)


if __name__ == "__main__":
    unittest.main()
