#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import io
import json
import os
import re
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
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

    def test_weekly_pacing_uses_pace_label_and_keeps_week_semantics(self):
        now = datetime(2026, 9, 15, tzinfo=timezone.utc)
        reset_at = now + timedelta(days=3, hours=12)
        line = self.ai_usage.format_window_left_line("pace", reset_at.isoformat(), 10080, now)
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", line)

        self.assertRegex(plain, re.compile(r"pace\s+.*50% of week \d+"))
        fallback = self.ai_usage.format_window_left_line("pace", reset_at.isoformat(), now=now)
        fallback_plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", fallback)
        self.assertRegex(fallback_plain, re.compile(r"pace\s+.*50% of week \d+"))

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

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return now if tz else now.replace(tzinfo=None)

        output = io.StringIO()
        with patch.object(self.ai_usage, "datetime", FixedDateTime), redirect_stdout(output):
            self.ai_usage.render_text([result])
        rendered = self.ai_usage.ANSI_ESCAPE_RE.sub("", output.getvalue())
        self.assertRegex(rendered, re.compile(r"1w\s+.*93%"))
        self.assertRegex(rendered, re.compile(r"pace\s+.*50% of week \d+"))

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


# Redacted fixture: the real 2026-09-25 GET /zen/go/v1/usage shape (keys/types
# confirmed live), synthetic values, no identifiers. There is no per-model or
# dollar field in this API: each window is percent used + ISO reset + status.
OPENCODE_GO_FIXTURE = {
    "usage": {
        "rolling": {"percent": 17, "resetsAt": "2026-09-25T07:30:00Z", "status": "ok"},
        "weekly": {"percent": 75, "resetsAt": "2026-09-28T00:00:00Z", "status": "ok"},
        "monthly": {"percent": 91, "resetsAt": "2026-10-01T00:00:00Z", "status": "ok"},
    }
}


class OpenCodeGoObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()
        cls.now = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)

    def ok(self, raw):
        return {"provider": "opencode-go", "label": "OpenCode Go", "state": "ok",
                "source": "api", "summary": "", "raw": raw}

    def test_window_fixture(self):
        result = self.ai_usage.apply_opencode_go_observation(self.ok(OPENCODE_GO_FIXTURE), self.now)
        self.assertEqual(result["state"], "ok")
        obs = result["observation"]
        self.assertEqual(obs["schema"], "opencode-go.usage.v1")
        self.assertEqual(obs["collected_at"], "2026-09-25T03:00:00+00:00")
        self.assertEqual(obs["windows"]["rolling"]["used_percent"], 17)
        self.assertEqual(obs["windows"]["rolling"]["remaining_percent"], 83)
        self.assertEqual(obs["windows"]["monthly"]["resets_at"], "2026-10-01T00:00:00Z")
        self.assertEqual(result["summary"], "tightest 30d 91% used")

    def test_window_at_limit(self):
        raw = json.loads(json.dumps(OPENCODE_GO_FIXTURE))
        raw["usage"]["rolling"] = {"percent": 100, "resetsAt": "2026-09-25T07:30:00Z", "status": "ok"}
        result = self.ai_usage.apply_opencode_go_observation(self.ok(raw), self.now)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["observation"]["windows"]["rolling"]["remaining_percent"], 0)
        self.assertEqual(result["summary"], "tightest 5h 100% used")

    def test_non_ok_status_is_surfaced(self):
        raw = json.loads(json.dumps(OPENCODE_GO_FIXTURE))
        raw["usage"]["monthly"]["status"] = "blocked"
        result = self.ai_usage.apply_opencode_go_observation(self.ok(raw), self.now)
        self.assertEqual(result["summary"], "tightest 30d 91% used; 30d status=blocked")

    def test_schema_drift_missing_window_is_an_error(self):
        raw = json.loads(json.dumps(OPENCODE_GO_FIXTURE))
        del raw["usage"]["weekly"]
        result = self.ai_usage.apply_opencode_go_observation(self.ok(raw), self.now)
        self.assertEqual(result["state"], "error")
        self.assertIn("missing usage.weekly", result["summary"])
        self.assertNotIn("observation", result)

    def test_out_of_range_percent_is_an_error(self):
        raw = json.loads(json.dumps(OPENCODE_GO_FIXTURE))
        raw["usage"]["rolling"]["percent"] = 170
        result = self.ai_usage.apply_opencode_go_observation(self.ok(raw), self.now)
        self.assertEqual(result["state"], "error")
        self.assertIn("outside 0-100", result["summary"])

    def test_non_ok_probe_passes_through(self):
        failed = {"provider": "opencode-go", "label": "OpenCode Go", "state": "error",
                  "source": "api", "summary": "HTTP 429", "raw": None}
        self.assertIs(self.ai_usage.apply_opencode_go_observation(failed, self.now), failed)

    def test_renderer_draws_all_three_windows(self):
        fixed_now = datetime(2026, 9, 25, 3, 0, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed_now if tz else fixed_now.replace(tzinfo=None)

        result = self.ai_usage.apply_opencode_go_observation(self.ok(OPENCODE_GO_FIXTURE), fixed_now)
        output = io.StringIO()
        with patch.object(self.ai_usage, "datetime", FixedDateTime), redirect_stdout(output):
            self.ai_usage.render_text([result])
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", output.getvalue())

        self.assertRegex(plain, re.compile(r"5h\s+.*83%"))
        self.assertRegex(plain, re.compile(r"wk\s+.*25%"))
        self.assertRegex(plain, re.compile(r"wk pace\s+.*41% of week \d+"))
        self.assertRegex(plain, re.compile(r"30d\s+.*9%"))
        self.assertRegex(plain, re.compile(r"30d pace\s+.*20% of 30d cycle"))


class OpenCodeGoCredentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_env_key_wins_over_auth_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = Path(tmp) / "auth.json"
            auth.write_text(json.dumps({"opencode-go": {"type": "api", "key": "file-key"}}), encoding="utf-8")
            captured = {}

            def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
                captured["provider"] = provider
                captured["token"] = token
                captured["url"] = url
                return {"provider": provider, "label": label, "state": "error", "source": "api",
                        "summary": "stub", "raw": None}

            with patch.dict(os.environ, {"OPENCODE_API_KEY": "env-key"}), \
                 patch.object(self.ai_usage, "OPENCODE_AUTH_FILE", auth), \
                 patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe):
                result = self.ai_usage.fetch_opencode_go(1.0)

            self.assertEqual(captured["token"], "env-key")
            self.assertEqual(captured["provider"], "opencode-go")
            self.assertEqual(result["state"], "error")

    def test_auth_file_key_used_when_env_absent(self):
        with tempfile.TemporaryDirectory() as tmp:
            auth = Path(tmp) / "auth.json"
            auth.write_text(
                json.dumps({"openai": {}, "opencode-go": {"type": "api", "key": "file-key"}}),
                encoding="utf-8",
            )
            captured = {}

            def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
                captured["token"] = token
                return {"provider": provider, "label": label, "state": "ok", "source": "api",
                        "summary": "", "raw": json.loads(json.dumps(OPENCODE_GO_FIXTURE))}

            with patch.dict(os.environ, {"OPENCODE_API_KEY": ""}), \
                 patch.object(self.ai_usage, "OPENCODE_AUTH_FILE", auth), \
                 patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe):
                result = self.ai_usage.fetch_opencode_go(1.0)

            self.assertEqual(captured["token"], "file-key")
            self.assertEqual(result["state"], "ok")

    def test_no_credential_reports_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "auth.json"
            with patch.dict(os.environ, {"OPENCODE_API_KEY": ""}), \
                 patch.object(self.ai_usage, "OPENCODE_AUTH_FILE", missing):
                result = self.ai_usage.fetch_opencode_go(1.0)
        self.assertEqual(result["state"], "missing")
        self.assertNotIn("token", result)


class ResultOrderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_provider_grouping_puts_local_before_remote(self):
        items = [
            {"provider": "codex", "label": "Codex"},
            {"provider": "claude", "label": "Claude Code"},
            {"provider": "opencode-go", "label": "OpenCode Go"},
            {"provider": "openrouter", "label": "OpenRouter"},
            {"provider": "mistral", "label": "Mistral"},
            {"provider": "neuralwatt", "label": "NeuralWatt"},
            {"provider": "codex", "label": "the operator · Codex", "remote": "the operator"},
            {"provider": "claude", "label": "the operator · Claude Code", "remote": "the operator"},
        ]
        # 2026-10-09: mistral above the reserve tank, which groups openrouter +
        # neuralwatt beneath the subscription gauges (Admiral's panel order).
        self.assertEqual(
            [item["label"] for item in self.ai_usage.order_results(items)],
            ["Codex", "the operator · Codex", "Claude Code", "the operator · Claude Code",
             "OpenCode Go", "Mistral", "OpenRouter", "NeuralWatt"],
        )

    def test_remote_panels_keep_file_order_and_unknowns_go_last(self):
        items = [
            {"provider": "neuralwatt", "label": "NeuralWatt"},
            {"provider": "codex", "label": "the operator · Codex", "remote": "the operator"},
            {"provider": "codex", "label": "X230 · Codex", "remote": "X230"},
            {"provider": "codex", "label": "Codex"},
        ]
        self.assertEqual(
            [item["label"] for item in self.ai_usage.order_results(items)],
            ["Codex", "the operator · Codex", "X230 · Codex", "NeuralWatt"],
        )


MISTRAL_WHOAMI_FIXTURE = {
    "plan_type": "API",
    "plan_name": "FREE",
    "prompt_switching_to_pro_plan": True,
    "organization_kind": "S",
    "customer_id": "25587b01-3447-483d-b6ac-7bc2caf053f3",
    "api_base": "https://api.mistral.ai",
    "vibe_base": "https://chat.mistral.ai",
    "primitive_access_scope": "personal_and_shared",
}

MISTRAL_BUDGET_FIXTURE = {
    "usage_percentage": 61.051076,
    "initial_budget": 30,
    "currency": "USD",
    "reset_at": "2026-11-01T00:00:00Z",
    "api_budget": {
        "usage_percentage": 61.051076,
        "initial_budget": 30,
        "currency": "USD",
        "reset_at": "2026-11-01T00:00:00Z",
    },
    "vibe_budget": {
        "usage_percentage": 0.53698893,
        "initial_budget": 300,
        "currency": "USD",
        "reset_at": "2026-11-01T00:00:00Z",
    },
}


def _no_cookie_jar(ai_usage):
    """Patch helper: disable the admin-trpc cookie path for whoami-era tests."""
    return patch.object(ai_usage, "_mistral_cookie_header", return_value="")


class MistralProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_no_credential_reports_missing(self):
        with patch.dict(os.environ, {"MISTRAL_API_KEY": "", "MISTRAL_VIBE_API_KEY": ""}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             _no_cookie_jar(self.ai_usage):
            result = self.ai_usage.fetch_mistral(1.0)
        self.assertEqual(result["state"], "missing")
        self.assertEqual(result["provider"], "mistral")
        self.assertIn("MISTRAL_API_KEY", result["summary"])

    def test_whoami_success_reports_plan_and_never_fabricates_percentage(self):
        captured = {}

        def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
            captured["token"] = token
            captured["url"] = url
            payload = json.loads(json.dumps(MISTRAL_WHOAMI_FIXTURE))
            summary = summarize(payload) if summarize else ""
            return {"provider": provider, "label": label, "state": "ok", "source": "api",
                    "summary": summary, "raw": payload}

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key", "MISTRAL_VIBE_API_KEY": ""}), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe), \
             _no_cookie_jar(self.ai_usage):
            result = self.ai_usage.fetch_mistral(1.0)

        self.assertEqual(captured["token"], "test-key")
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["identity"]["plan_name"], "FREE")
        self.assertEqual(result["identity"]["customer_id"], "25587b01-3447-483d-b6ac-7bc2caf053f3")
        # The fallback summary must stay truthful: no percentage number, explicit
        # pointer to the console/Admin API for the actual usage figure.
        self.assertIn("plan=FREE", result["summary"])
        self.assertIn("usage % needs console session or Admin API key", result["summary"])
        self.assertNotRegex(result["summary"], r"\d+(\.\d+)?%")

    def test_budget_from_cookie_jar_reports_real_percentages(self):
        """The admin-trpc path reports the console's real budget numbers."""
        captured = {}

        def fake_trpc(endpoint, params, timeout_seconds):
            captured["endpoint"] = endpoint
            return json.loads(json.dumps(MISTRAL_BUDGET_FIXTURE))

        with patch.object(self.ai_usage, "_mistral_trpc", side_effect=fake_trpc):
            result = self.ai_usage.fetch_mistral(1.0)

        self.assertEqual(captured["endpoint"], "billing.budget")
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["source"], "admin-trpc")
        self.assertEqual(result["identity"]["plan_name"], "Pro")
        # Standard quota shape (2026-10-09): budgets render as gauges like every
        # other panel — primary=Vibe, secondary=API, each with usedPercent,
        # windowMinutes (30d), resetsAt, label.
        primary = result["usage"]["primary"]
        secondary = result["usage"]["secondary"]
        self.assertAlmostEqual(primary["usedPercent"], 0.53698893)
        self.assertAlmostEqual(secondary["usedPercent"], 61.051076)
        self.assertEqual(primary["label"], "Vibe")
        self.assertEqual(secondary["label"], "API")
        self.assertEqual(primary["windowMinutes"], 30 * 24 * 60)
        self.assertEqual(secondary["resetsAt"], "2026-11-01T00:00:00Z")
        self.assertIn("$18.32/$30", result["summary"])
        self.assertIn("61.1%", result["summary"])
        self.assertIn("Vibe", result["summary"])
        self.assertIn("resets 2026-11-01", result["summary"])

    def test_budget_trpc_failure_falls_back_to_whoami(self):
        """No cookie session -> whoami identity only, never a fabricated number."""
        def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
            payload = json.loads(json.dumps(MISTRAL_WHOAMI_FIXTURE))
            summary = summarize(payload) if summarize else ""
            return {"provider": provider, "label": label, "state": "ok", "source": "api",
                    "summary": summary, "raw": payload}

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "test-key", "MISTRAL_VIBE_API_KEY": ""}), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe), \
             _no_cookie_jar(self.ai_usage):
            result = self.ai_usage.fetch_mistral(1.0)

        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["identity"]["plan_name"], "FREE")
        self.assertNotIn("usage", result)

    def test_no_jar_configured_skips_budget_probe_and_says_so(self):
        """MISTRAL_COOKIE_JAR unset => budget probe skipped, output says why,
        and the fallback never fabricates a budget number."""
        def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
            payload = json.loads(json.dumps(MISTRAL_WHOAMI_FIXTURE))
            summary = summarize(payload) if summarize else ""
            return {"provider": provider, "label": label, "state": "ok", "source": "api",
                    "summary": summary, "raw": payload}

        def fail_http(*args, **kwargs):
            raise AssertionError("budget probe must not touch the network when the jar is unset")

        # Empty cookie header => real _mistral_trpc returns None before any HTTP,
        # so urlopen staying untouched proves the probe was skipped.
        # load_dotenv_exports patched empty + vibe key cleared: the jar path is
        # resolved at call time (2026-10-09), so host env must not leak in.
        with patch.dict(os.environ, {"MISTRAL_COOKIE_JAR": "", "MISTRAL_API_KEY": "test-key", "MISTRAL_VIBE_API_KEY": ""}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_mistral_cookie_header", return_value=""), \
             patch.object(self.ai_usage.urllib.request, "urlopen", side_effect=fail_http), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe):
            result = self.ai_usage.fetch_mistral(1.0)

        self.assertEqual(result["state"], "ok")
        self.assertIn("MISTRAL_COOKIE_JAR not set", result["summary"])
        # Plan identity still surfaces; no budget percentage is invented.
        self.assertEqual(result["identity"]["plan_name"], "FREE")
        self.assertNotIn("usage", result)

    def test_tangled_script_has_no_home_paths(self):
        """DotCortex is public: no username/host path may leak into the tangled
        script. Fails if any '/home/' literal appears in ai-usage source."""
        script = Path(self.ai_usage.__file__).read_text()
        self.assertNotIn("/home/", script)

    def test_http_error_surfaces_status_without_crashing(self):
        def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
            return {"provider": provider, "label": label, "state": "error", "source": "api",
                    "summary": f"{url} returned HTTP 401", "raw": None}

        with patch.dict(os.environ, {"MISTRAL_API_KEY": "bad-key", "MISTRAL_VIBE_API_KEY": ""}), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe), \
             _no_cookie_jar(self.ai_usage):
            result = self.ai_usage.fetch_mistral(1.0)

        self.assertEqual(result["state"], "error")
        self.assertIn("HTTP 401", result["summary"])
        self.assertNotIn("identity", result)

    def test_mistral_is_registered_and_default_visible(self):
        keys = [spec.key for spec in self.ai_usage.PROVIDERS]
        self.assertIn("mistral", keys)
        self.assertIn("mistral", self.ai_usage.DEFAULT_PROVIDER_KEYS)
        self.assertIn("mistral", self.ai_usage.PROVIDER_DISPLAY_ORDER)

    def test_renderer_shows_mistral_plan_line(self):
        result = {
            "provider": "mistral",
            "label": "Mistral",
            "state": "ok",
            "source": "api",
            "summary": "plan=FREE; type=API; usage % needs console session or Admin API key",
            "raw": dict(MISTRAL_WHOAMI_FIXTURE),
            "identity": {"plan_name": "FREE", "organization_kind": "S"},
        }
        output = io.StringIO()
        with redirect_stdout(output):
            self.ai_usage.render_text([result])
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", output.getvalue())
        self.assertIn("Mistral", plain)
        self.assertIn("Plan: FREE", plain)
        self.assertIn("usage % needs console session or Admin API key", plain)

    def test_whoami_prefers_vibe_key_over_api_key(self):
        """Fix 2026-10-09: whoami must report the Vibe subscription, so
        MISTRAL_VIBE_API_KEY wins when both keys exist. The Studio
        MISTRAL_API_KEY reports the free API plan and masks the sub."""
        captured = {}

        def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
            captured["token"] = token
            payload = json.loads(json.dumps(MISTRAL_WHOAMI_FIXTURE))
            payload["plan_name"] = "INDIVIDUAL"
            payload["plan_type"] = "CHAT"
            summary = summarize(payload) if summarize else ""
            return {"provider": provider, "label": label, "state": "ok", "source": "api",
                    "summary": summary, "raw": payload}

        with patch.dict(os.environ, {"MISTRAL_VIBE_API_KEY": "vibe-key", "MISTRAL_API_KEY": ""}), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe), \
             _no_cookie_jar(self.ai_usage):
            result = self.ai_usage.fetch_mistral(1.0)

        self.assertEqual(captured["token"], "vibe-key")
        self.assertEqual(result["identity"]["plan_name"], "INDIVIDUAL")

    def test_mistral_budgets_render_as_standard_quotas(self):
        """Admiral pattern conformance (2026-10-09): the budget dicts must land
        in raw.usage.primary/secondary in the same shape _codex_window_to_quota
        emits ({usedPercent, windowMinutes, resetsAt ISO}), so the existing
        format_compact_quota_line renderer draws bars and countdowns with no
        bespoke Mistral path."""
        def fake_trpc(endpoint, params, timeout_seconds):
            return json.loads(json.dumps(MISTRAL_BUDGET_FIXTURE))

        with patch.object(self.ai_usage, "_mistral_trpc", side_effect=fake_trpc):
            result = self.ai_usage.fetch_mistral(1.0)

        for slot in ("primary", "secondary"):
            quota = result["usage"][slot]
            self.assertIn("usedPercent", quota)
            self.assertIsInstance(quota["windowMinutes"], int)
            self.assertIn("resetsAt", quota)
            self.assertIn(quota["resetsAt"], "2026-11-01T00:00:00Z")
            # The existing renderer must produce a bar line from it.
            label = quota.get("label") or ("Vibe" if slot == "primary" else "API")
            line = self.ai_usage.format_compact_quota_line(label, quota)
            self.assertIsNotNone(line, f"{slot} quota did not render")
            self.assertIn("%", line)

    def test_cookie_jar_resolved_from_dotenv_at_call_time(self):
        """Fix 2026-10-09: the jar path used to be baked in at import time, so a
        MISTRAL_COOKIE_JAR deployed only in ~/.env (untracked env file, not
        exported by shells since 2026-09-25) was invisible outside login
        shells. Call-time resolution must see the dotenv value."""
        with patch.dict(os.environ, {"MISTRAL_COOKIE_JAR": ""}, clear=False), \
             patch.object(self.ai_usage, "load_dotenv_exports",
                          return_value={"MISTRAL_COOKIE_JAR": "/tmp/fake-jar.path"}):
            path = self.ai_usage._mistral_cookie_jar_path()
        self.assertEqual(path, "/tmp/fake-jar.path")


class OpenRouterProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_openrouter_spec_is_native_not_codexbar(self):
        """Fix 2026-10-09: codexbar's openrouter fetch needs cookie auth (web
        session), which no Linux host has. The spec must be the native kind."""
        spec = next(s for s in self.ai_usage.PROVIDERS if s.key == "openrouter")
        self.assertEqual(spec.kind, "openrouter")

    def test_openrouter_native_reads_credits_and_key_endpoints(self):
        """The native probe hits OpenRouter's own /credits and /auth/key with
        the OPENROUTER_API_KEY bearer and reports the real balance."""
        captured = []

        def fake_probe(provider, label, url, token, timeout_seconds, summarize=None):
            captured.append(url)
            if url.endswith("/credits"):
                return {"provider": provider, "label": label, "state": "ok", "source": "api",
                        "summary": "", "raw": {"data": {"total_credits": 50, "total_usage": 0.5}}}
            return {"provider": provider, "label": label, "state": "ok", "source": "api",
                    "summary": "", "raw": {"data": {"usage": 0.000413, "label": "sk-or-v1-test"}}}

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "or-key"}), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=fake_probe):
            result = self.ai_usage.fetch_openrouter(1.0)

        self.assertIn("https://openrouter.ai/api/v1/credits", captured)
        self.assertIn("https://openrouter.ai/api/v1/auth/key", captured)
        self.assertEqual(result["state"], "ok")
        self.assertEqual(result["summary"], "balance=$49.5; keyUsage=$0.000413; loginMethod=Balance: $49.5")
        self.assertEqual(result["raw"]["usage"]["openRouterUsage"]["balance"], 49.5)

    def test_openrouter_missing_key_reports_missing(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "", "AI_USAGE_FLEET_SNAPSHOT": "/nonexistent/ai-usage-basis.json"}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}):
            result = self.ai_usage.fetch_openrouter(1.0)
        self.assertEqual(result["state"], "missing")
        self.assertIn("OPENROUTER_API_KEY", result["summary"])


class NeuralWattAddendumTests(unittest.TestCase):
    """2026-10-09 addendum: console session, 7-day burn, reserve grouping,
    offer alert from the coordinator feed."""

    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_console_session_unset_falls_back_to_api_key(self):
        """NEURALWATT_COOKIE_JAR unset -> API-key numbers, no console note."""
        with patch.dict(os.environ, {"NEURALWATT_COOKIE_JAR": ""}, clear=False), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_neuralwatt_console_usage", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_seven_day_burn", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_active_offer", return_value=None):
            # _env_token must find no key -> patch it too, plus the bearer probe
            with patch.dict(os.environ, {"NEURALWATT_API_KEY": "nw-key"}), \
                 patch.object(self.ai_usage, "_bearer_json_probe", side_effect=lambda *a, **k: {
                     "provider": "neuralwatt", "label": "NeuralWatt", "state": "ok",
                     "source": "api", "summary": "", "raw": NEURALWATT_FIXTURE}):
                result = self.ai_usage.fetch_neuralwatt(1.0)
        self.assertEqual(result["state"], "ok")
        self.assertNotIn("console session", result["summary"])

    def test_console_session_failure_says_so(self):
        """Jar set but session fails -> summary says so, numbers stay API-key."""
        raw = json.loads(json.dumps(NEURALWATT_FIXTURE))
        with patch.dict(os.environ, {"NEURALWATT_COOKIE_JAR": "/tmp/nw.jar", "NEURALWATT_API_KEY": "nw-key"}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_neuralwatt_console_usage", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_seven_day_burn", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_active_offer", return_value=None), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=lambda *a, **k: {
                 "provider": "neuralwatt", "label": "NeuralWatt", "state": "ok",
                 "source": "api", "summary": "", "raw": raw}):
            result = self.ai_usage.fetch_neuralwatt(1.0)
        self.assertEqual(result["state"], "ok")
        self.assertIn("console session failed (NEURALWATT_COOKIE_JAR set)", result["summary"])

    def test_console_session_live_is_reported(self):
        raw = json.loads(json.dumps(NEURALWATT_FIXTURE))
        console_payload = {"balance_usd": 141.59, "spend_usd": 34.41}
        with patch.dict(os.environ, {"NEURALWATT_COOKIE_JAR": "/tmp/nw.jar", "NEURALWATT_API_KEY": "nw-key"}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_neuralwatt_console_usage", return_value=console_payload), \
             patch.object(self.ai_usage, "_neuralwatt_seven_day_burn", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_active_offer", return_value=None), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=lambda *a, **k: {
                 "provider": "neuralwatt", "label": "NeuralWatt", "state": "ok",
                 "source": "api", "summary": "", "raw": raw}):
            result = self.ai_usage.fetch_neuralwatt(1.0)
        self.assertEqual(result["console"], console_payload)
        self.assertIn("console session live", result["summary"])

    def test_seven_day_burn_surfaces(self):
        raw = json.loads(json.dumps(NEURALWATT_FIXTURE))
        with patch.dict(os.environ, {"NEURALWATT_API_KEY": "nw-key"}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_neuralwatt_console_usage", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_seven_day_burn", return_value=1.267258), \
             patch.object(self.ai_usage, "_neuralwatt_active_offer", return_value=None), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=lambda *a, **k: {
                 "provider": "neuralwatt", "label": "NeuralWatt", "state": "ok",
                 "source": "api", "summary": "", "raw": raw}):
            result = self.ai_usage.fetch_neuralwatt(1.0)
        self.assertAlmostEqual(result["seven_day_burn_usd"], 1.267258)

    def test_active_offer_surfaces_from_coordinator_feed(self):
        raw = json.loads(json.dumps(NEURALWATT_FIXTURE))
        offer = {
            "id": "neuralwatt:x:payasyougo", "provider": "neuralwatt",
            "title": "Free Flash weekend", "starts_at": "2026-10-09T00:00:00Z",
            "expires_at": "2026-10-12T00:00:00Z", "amount_wh": 250.0,
            "next_reset_at": "2026-10-10T00:00:00Z",
        }
        with patch.dict(os.environ, {"NEURALWATT_API_KEY": "nw-key"}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_neuralwatt_console_usage", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_seven_day_burn", return_value=None), \
             patch.object(self.ai_usage, "_neuralwatt_active_offer", return_value=offer), \
             patch.object(self.ai_usage, "_bearer_json_probe", side_effect=lambda *a, **k: {
                 "provider": "neuralwatt", "label": "NeuralWatt", "state": "ok",
                 "source": "api", "summary": "", "raw": raw}):
            result = self.ai_usage.fetch_neuralwatt(1.0)
        self.assertEqual(result["active_offer"]["title"], "Free Flash weekend")
        self.assertEqual(result["active_offer"]["amount_wh"], 250.0)

    ["Codex", "the operator · Codex", "Claude Code", "the operator · Claude Code",
             "OpenCode Go", "Mistral", "OpenRouter", "NeuralWatt"],

    def test_offer_feed_reader_validates_format_and_window(self):
        """The feed reader only accepts centre-provider-bonuses.v1 offers whose
        window covers now, from the env-var path only."""
        import tempfile as _tempfile
        now_iso = datetime.now(timezone.utc).isoformat()
        expired = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        feed = {
            "format": "centre-provider-bonuses.v1",
            "offers": [
                {"provider": "neuralwatt", "title": "expired one",
                 "starts_at": expired, "expires_at": expired, "amount_wh": 1.0},
                {"provider": "neuralwatt", "title": "live one",
                 "starts_at": "2026-01-01T00:00:00Z", "expires_at": "2099-01-01T00:00:00Z",
                 "amount_wh": 250.0},
                {"provider": "other", "title": "wrong provider",
                 "starts_at": "2026-01-01T00:00:00Z", "expires_at": "2099-01-01T00:00:00Z"},
            ],
        }
        with _tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(feed, fh)
            feed_path = fh.name
        try:
            with patch.dict(os.environ, {"NEURALWATT_OFFERS_FEED": feed_path}), \
                 patch.object(self.ai_usage, "load_dotenv_exports", return_value={}):
                offer = self.ai_usage._neuralwatt_active_offer(1.0)
        finally:
            os.unlink(feed_path)
        self.assertIsNotNone(offer)
        self.assertEqual(offer["title"], "live one")

    def test_no_host_paths_in_new_console_code(self):
        """Tracked source may not hardcode jar or feed paths — env only."""
        script = Path(self.ai_usage.__file__).read_text()
        self.assertNotIn("NEURALWATT_COOKIE_JAR = os.path.expanduser(", script)
        self.assertNotIn("NEURALWATT_OFFERS_FEED = os.path.expanduser(", script)


class BankedResetTests(unittest.TestCase):
    """Banked limit resets: local inventory (fbl / wk), never a quota window."""

    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()
        cls.now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

    def store(self, payload=None, text=None):
        """A throwaway store path; callers apply the env override themselves."""
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        path = Path(tmpdir.name) / "banked-resets.json"
        if text is not None:
            path.write_text(text, encoding="utf-8")
        elif payload is not None:
            path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def loaded(self, payload=None, text=None, now=None):
        path = self.store(payload, text)
        return self.ai_usage.load_banked_resets(path, now or self.now)

    def claude_raw(self, payload):
        path = self.store(payload)
        entries, reason = self.ai_usage.banked_resets_for("claude", path, self.now)
        self.assertIsNone(reason)
        return {"usage": {"primary": {}, "secondary": {}}, "banked": entries}

    def claude_item(self, raw):
        return {
            "provider": "claude",
            "label": "Claude Code",
            "state": "ok",
            "source": "oauth",
            "summary": "Claude usage",
            "raw": raw,
        }

    def assert_cli_refusal(self, spec, message):
        path = self.store()
        err = io.StringIO()
        with patch.dict(os.environ, {"AI_USAGE_BANKED_RESETS": str(path)}), redirect_stderr(err):
            code = self.ai_usage.cmd_bank_set(spec)
        self.assertEqual(code, 2, spec)
        self.assertIn(message, err.getvalue(), spec)
        self.assertFalse(path.exists(), "a refused --bank-set must not create the store")

    def test_absent_store_means_no_banked_resets_not_an_error(self):
        tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(tmpdir.cleanup)
        missing = Path(tmpdir.name) / "banked-resets.json"
        self.assertFalse(missing.exists())
        accounts, reason = self.ai_usage.load_banked_resets(missing, self.now)
        self.assertEqual(accounts, {})
        self.assertIsNone(reason)

    def test_malformed_store_degrades_to_empty_with_a_reason(self):
        accounts, reason = self.loaded(text="{ this is not json")
        self.assertEqual(accounts, {})
        self.assertIsInstance(reason, str)
        self.assertIn("malformed store", reason)
        # ... and reading it never raises into the panel path.
        self.assertIsNone(self.ai_usage.format_banked_resets_line({"banked": []}))

    def test_bad_entry_shapes_are_dropped_with_a_reason(self):
        accounts, reason = self.loaded(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00"},
                        {"kind": "month", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00"},
                        {"kind": "wk", "count": 0, "expiresAt": "2030-12-11T12:00:00+00:00"},
                        {"kind": "wk", "count": 1, "expiresAt": "next tuesday"},
                        # naive stamp: refused, never assumed UTC
                        {"kind": "wk", "count": 1, "expiresAt": "2030-12-11T12:00:00"},
                    ]
                }
            }
        )
        self.assertEqual(list(accounts), ["cc-main"])
        self.assertEqual([entry["kind"] for entry in accounts["cc-main"]], ["fbl"])
        self.assertIn("ignored", reason)

    def test_fbl_and_wk_are_distinguished(self):
        accounts, reason = self.loaded(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "wk", "count": 1, "expiresAt": "2030-12-11T12:00:00+00:00",
                         "source": "manual"},
                        {"kind": "fbl", "count": 2, "expiresAt": "2030-11-17T12:00:00+00:00",
                         "source": "collector"},
                    ]
                }
            }
        )
        self.assertIsNone(reason)
        entries = accounts["cc-main"]
        self.assertEqual([entry["kind"] for entry in entries], ["fbl", "wk"])
        self.assertEqual([entry["label"] for entry in entries], ["Fable", "Weekly"])
        self.assertEqual([entry["count"] for entry in entries], [2, 1])
        self.assertEqual([entry["source"] for entry in entries], ["collector", "manual"])
        self.assertEqual([entry["expired"] for entry in entries], [False, False])
        self.assertEqual(self.ai_usage.banked_available_count(entries, "fbl"), 2)
        self.assertEqual(self.ai_usage.banked_available_count(entries), 3)

    def test_count_and_expiry_are_rendered_on_one_line(self):
        raw = self.claude_raw(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00",
                         "source": "manual"},
                        {"kind": "wk", "count": 1, "expiresAt": "2030-12-11T12:00:00+00:00",
                         "source": "manual"},
                    ]
                }
            }
        )
        rows = [
            self.ai_usage.ANSI_ESCAPE_RE.sub("", row)
            for row in self.ai_usage.format_banked_resets_lines(raw)
        ]
        self.assertEqual(len(rows), 2, rows)
        # codex's own reset credits render as "bank N  [bar]  pct  <hourglass> countdown  kind";
        # the claude inventory speaks the same shape instead of its own sentence.
        self.assertTrue(rows[0].startswith("  bank 1 "), rows[0])
        self.assertTrue(rows[1].startswith("  bank 2 "), rows[1])
        self.assertIn("Fable", rows[0])
        self.assertIn("Weekly", rows[1])
        # the countdown is the whole story; the wall clock is gone
        self.assertNotIn("Nov", rows[0])
        self.assertNotIn("Dec", rows[1])

    def test_expired_entry_is_reported_and_never_available(self):
        raw = self.claude_raw(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2026-11-10T12:00:00+00:00",
                         "source": "manual"},
                        {"kind": "wk", "count": 2, "expiresAt": "2030-12-11T12:00:00+00:00",
                         "source": "manual"},
                    ]
                }
            }
        )
        entries = raw["banked"]
        self.assertTrue(entries[0]["expired"])
        self.assertEqual(entries[0]["expiresIn"], 0)
        self.assertFalse(entries[1]["expired"])
        self.assertEqual(self.ai_usage.banked_available_count(entries), 2)
        self.assertEqual(self.ai_usage.banked_available_count(entries, "fbl"), 0)
        rows = [
            self.ai_usage.ANSI_ESCAPE_RE.sub("", row)
            for row in self.ai_usage.format_banked_resets_lines(raw)
        ]
        # The expired Fable entry is hidden; only the spendable weekly bank shows.
        self.assertEqual(len(rows), 1, rows)
        self.assertTrue(rows[0].startswith("  bank 1 "), rows[0])
        self.assertNotIn("Fable", rows[0])
        self.assertNotIn("expired", rows[0])
        self.assertIn("Weekly", rows[0])
        self.assertIn("2 available", rows[0])

    def test_all_expired_banked_entries_show_no_rows(self):
        raw = self.claude_raw(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2026-11-10T12:00:00+00:00",
                         "source": "manual"},
                    ]
                }
            }
        )
        self.assertEqual(self.ai_usage.format_banked_resets_lines(raw), [])

    def test_codex_reset_credits_at_zero_are_hidden(self):
        soon = (datetime.now(timezone.utc) + timedelta(seconds=30)).isoformat()
        later = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        rows = self.ai_usage.format_codex_reset_credit_lines(
            {"resetCredits": {"availableCount": 2, "credits": [
                {"status": "available", "expiresAt": soon},
                {"status": "available", "expiresAt": later},
            ]}}
        )
        plain = [self.ai_usage.ANSI_ESCAPE_RE.sub("", row) for row in rows]
        self.assertEqual(len(plain), 1, plain)
        self.assertTrue(plain[0].startswith("  bank 1 "), plain[0])
        self.assertEqual(
            self.ai_usage.format_codex_reset_credit_lines(
                {"resetCredits": {"availableCount": 0, "credits": []}}
            ),
            [],
        )

    def test_banked_store_prefers_shared_then_legacy_then_new_shared(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name)
        shared = root / "HelmCortex" / "ROOTS" / "JSON" / "ai-usage" / "banked-resets.json"
        legacy = root / ".config" / "ai-usage" / "banked-resets.json"
        env = {k: v for k, v in os.environ.items() if k != "AI_USAGE_BANKED_RESETS"}
        with patch.dict(os.environ, env, clear=True), \
             patch.object(self.ai_usage, "BANKED_RESETS_SHARED_DEFAULT", shared), \
             patch.object(self.ai_usage, "BANKED_RESETS_STORE_DEFAULT", legacy):
            # no shared tree, no files: the per-host default
            self.assertEqual(self.ai_usage.banked_resets_path(), legacy)
            # the shared ROOTS/JSON tree exists: new records go to the shared file
            shared.parent.parent.mkdir(parents=True)
            self.assertEqual(self.ai_usage.banked_resets_path(), shared)
            # a legacy per-host file is read until the shared one exists
            legacy.parent.mkdir(parents=True)
            legacy.write_text("{}")
            self.assertEqual(self.ai_usage.banked_resets_path(), legacy)
            # once the shared file exists it wins everywhere
            shared.parent.mkdir(parents=True)
            shared.write_text("{}")
            self.assertEqual(self.ai_usage.banked_resets_path(), shared)
            # an explicit override beats both
            with patch.dict(os.environ, {"AI_USAGE_BANKED_RESETS": str(root / "x.json")}):
                self.assertEqual(self.ai_usage.banked_resets_path(), root / "x.json")

    def _fleet_file(self, source="api", credits=50, age_seconds=60, state="ok"):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        stamp = (datetime.now(timezone.utc) - timedelta(seconds=age_seconds)).isoformat()
        path = Path(tmp.name) / "ai-usage-basis.json"
        path.write_text(json.dumps({
            "generated_at": stamp,
            "entries": [{
                "provider": "openrouter", "state": state,
                "raw": {"source": source, "usage": {"openRouterUsage": {
                    "balance": credits, "keyUsage": 0, "totalCredits": credits}}},
            }],
        }))
        return path

    def test_fleet_openrouter_taken_only_when_fresh_live_and_funded(self):
        fn = self.ai_usage.fleet_openrouter_usage
        self.assertEqual(fn(self._fleet_file())["balance"], 50)
        self.assertIsNone(fn(self._fleet_file(age_seconds=7200)))
        self.assertIsNone(fn(self._fleet_file(source="fleet-snapshot")))
        self.assertIsNone(fn(self._fleet_file(credits=0)))
        self.assertIsNone(fn(self._fleet_file(state="missing")))
        self.assertIsNone(fn(Path("/nonexistent/ai-usage-basis.json")))

    def test_openrouter_uses_fleet_when_local_account_has_no_credits(self):
        fleet = self._fleet_file()
        old_env = os.environ.get("AI_USAGE_FLEET_SNAPSHOT")
        os.environ["AI_USAGE_FLEET_SNAPSHOT"] = str(fleet)
        self.addCleanup(
            lambda: os.environ.__setitem__("AI_USAGE_FLEET_SNAPSHOT", old_env)
            if old_env is not None else os.environ.pop("AI_USAGE_FLEET_SNAPSHOT", None)
        )
        empty = {"provider": "openrouter", "state": "ok", "source": "api", "raw": {
            "usage": {"openRouterUsage": {"balance": -0.000413, "keyUsage": 0.000413, "totalCredits": 0}}}}
        funded = {"provider": "openrouter", "state": "ok", "source": "api", "raw": {
            "usage": {"openRouterUsage": {"balance": 12.0, "keyUsage": 1.0, "totalCredits": 13}}}}
        missing = {"provider": "openrouter", "state": "missing", "source": "env", "raw": None}
        original = self.ai_usage._fetch_openrouter_local
        self.addCleanup(lambda: setattr(self.ai_usage, "_fetch_openrouter_local", original))
        for local, expect_source, expect_balance in (
            (empty, "fleet-snapshot", 50), (missing, "fleet-snapshot", 50), (funded, "api", 12.0)
        ):
            self.ai_usage._fetch_openrouter_local = lambda timeout, _l=local: _l
            result = self.ai_usage.fetch_openrouter(5)
            self.assertEqual(result["source"], expect_source)
            self.assertEqual(result["raw"]["usage"]["openRouterUsage"]["balance"], expect_balance)

    def test_two_accounts_are_named_not_pooled(self):
        raw = self.claude_raw(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00",
                         "source": "manual"},
                    ],
                    "cc-alt": [
                        {"kind": "fbl", "count": 4, "expiresAt": "2030-11-18T12:00:00+00:00",
                         "source": "manual"},
                    ],
                }
            }
        )
        rows = [
            self.ai_usage.ANSI_ESCAPE_RE.sub("", row)
            for row in self.ai_usage.format_banked_resets_lines(raw)
        ]
        self.assertEqual(len(rows), 2, rows)
        self.assertIn("@cc-main", rows[0])
        self.assertIn("@cc-alt", rows[1])
        self.assertIn("4 available", rows[1])
        self.assertNotIn("@cc-alt", rows[0])

    def test_no_entries_renders_no_line(self):
        self.assertIsNone(self.ai_usage.format_banked_resets_line({"usage": {"primary": {}}}))
        self.assertIsNone(self.ai_usage.format_banked_resets_line({"banked": []}))

    def test_panel_prints_one_banked_line_and_no_dollar_line(self):
        raw = self.claude_raw(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00",
                         "source": "manual"},
                    ]
                }
            }
        )
        raw["usage"] = {
            "primary": {"label": "5h", "usedPercent": 12, "windowMinutes": 300,
                        "resetsAt": "2030-11-17T12:00:00+00:00"},
            "secondary": {"label": "wk", "usedPercent": 41, "windowMinutes": 10080,
                          "resetsAt": "2030-11-20T12:00:00+00:00"},
        }
        output = io.StringIO()
        with redirect_stdout(output):
            self.ai_usage.render_text([self.claude_item(raw)])
        plain = self.ai_usage.ANSI_ESCAPE_RE.sub("", output.getvalue())
        self.assertIn("bank 1", plain)
        self.assertIn("Fable", plain)
        self.assertEqual(plain.count("bank 1"), 1, plain)
        self.assertNotIn("$", plain)

    def test_cli_refuses_a_bad_kind(self):
        self.assert_cli_refusal(
            "claude:cc-main:month:1:2030-11-17T18:59:00+11:00", "kind must be one of"
        )
        self.assert_cli_refusal(
            "nosuch:cc-main:fbl:1:2030-11-17T18:59:00+11:00", "unknown provider"
        )

    def test_cli_refuses_a_bad_count(self):
        for spec in (
            "claude:cc-main:fbl:0:2030-11-17T18:59:00+11:00",
            "claude:cc-main:fbl:-2:2030-11-17T18:59:00+11:00",
            "claude:cc-main:fbl:many:2030-11-17T18:59:00+11:00",
        ):
            self.assert_cli_refusal(spec, "count must be a positive integer")

    def test_cli_refuses_a_bad_date(self):
        for spec in (
            "claude:cc-main:fbl:1:next tuesday",
            "claude:cc-main:fbl:1:2030-11-17T18:59:00",
            "claude:cc-main:fbl:1:2030-13-40T18:59:00+11:00",
        ):
            self.assert_cli_refusal(spec, "timezone-aware ISO-8601")

    def test_cli_bank_set_roundtrip_and_correction(self):
        path = self.store()
        out = io.StringIO()
        err = io.StringIO()
        with patch.dict(os.environ, {"AI_USAGE_BANKED_RESETS": str(path)}), \
             redirect_stdout(out), redirect_stderr(err):
            first = self.ai_usage.cmd_bank_set("claude:cc-main:fbl:1:2030-11-17T12:00:00+00:00")
            second = self.ai_usage.cmd_bank_set("claude:cc-main:fbl:3:2030-11-17T12:00:00+00:00")
        self.assertEqual((first, second), (0, 0))
        self.assertEqual(err.getvalue(), "")

        accounts, reason = self.ai_usage.load_banked_resets(path, self.now)
        self.assertIsNone(reason)
        entries = accounts["cc-main"]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["count"], 3)
        self.assertEqual(entries[0]["source"], "manual")
        self.assertEqual(entries[0]["provider"], "claude")
        self.assertEqual(entries[0]["kind"], "fbl")

        stored = json.loads(path.read_text())
        self.assertEqual(sorted(stored["accounts"]["cc-main"][0]),
                         ["count", "expiresAt", "kind", "provider", "source"])
        self.assertEqual(stored["accounts"]["cc-main"][0]["count"], 3)

    def test_bank_set_warns_before_rewriting_a_damaged_store(self):
        path = self.store(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "wk", "count": 1, "expiresAt": "2030-12-11T12:00:00+00:00",
                         "source": "collector"},
                        {"kind": "month", "count": 9, "expiresAt": "2030-12-11T12:00:00+00:00"},
                    ]
                }
            }
        )
        err = io.StringIO()
        with patch.dict(os.environ, {"AI_USAGE_BANKED_RESETS": str(path)}), \
             redirect_stdout(io.StringIO()), redirect_stderr(err):
            code = self.ai_usage.cmd_bank_set("claude:cc-main:fbl:1:2030-11-17T12:00:00+00:00")
        self.assertEqual(code, 0)
        self.assertIn("ignored", err.getvalue())
        accounts, reason = self.ai_usage.load_banked_resets(path, self.now)
        self.assertIsNone(reason)
        self.assertEqual([entry["kind"] for entry in accounts["cc-main"]], ["fbl", "wk"])
        self.assertEqual(accounts["cc-main"][1]["count"], 1)

    def test_bank_list_honours_json(self):
        path = self.store(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00",
                         "source": "manual"},
                    ]
                }
            }
        )
        output = io.StringIO()
        with patch.dict(os.environ, {"AI_USAGE_BANKED_RESETS": str(path)}), \
             redirect_stdout(output):
            code = self.ai_usage.cmd_bank_list(as_json=True)
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        self.assertIsNone(payload["error"])
        self.assertEqual(payload["accounts"]["cc-main"][0]["kind"], "fbl")

    def test_json_envelope_carries_raw_banked_kinds(self):
        path = self.store(
            {
                "accounts": {
                    "cc-main": [
                        {"kind": "fbl", "count": 1, "expiresAt": "2030-11-17T12:00:00+00:00",
                         "source": "manual"},
                        {"kind": "wk", "count": 2, "expiresAt": "2030-12-11T12:00:00+00:00",
                         "source": "collector"},
                    ]
                }
            }
        )
        fetched = {
            "provider": "claude",
            "label": "Claude Code",
            "state": "ok",
            "source": "oauth",
            "summary": "Claude usage",
            "raw": {
                "usage": {
                    "primary": {"label": "5h", "usedPercent": 10, "windowMinutes": 300,
                                "resetsAt": "2030-11-17T12:00:00+00:00"},
                    "secondary": {"label": "wk", "usedPercent": 40, "windowMinutes": 10080,
                                  "resetsAt": "2030-11-20T12:00:00+00:00"},
                },
                "scoped": [],
            },
        }
        output = io.StringIO()
        with patch.dict(os.environ, {"AI_USAGE_BANKED_RESETS": str(path)}), \
             patch.object(self.ai_usage, "load_dotenv_exports", return_value={}), \
             patch.object(self.ai_usage, "_cache_read", return_value={}), \
             patch.object(self.ai_usage, "_cache_write"), \
             patch.object(self.ai_usage, "_fetch_provider_uncached", return_value=fetched), \
             patch.object(sys, "argv",
                          ["ai-usage", "--json", "--providers", "claude", "--no-remote"]), \
             redirect_stdout(output):
            code = self.ai_usage.main()
        self.assertEqual(code, 0)
        payload = json.loads(output.getvalue())
        banked = payload[0]["raw"]["banked"]
        self.assertEqual([entry["kind"] for entry in banked], ["fbl", "wk"])
        self.assertEqual([entry["label"] for entry in banked], ["Fable", "Weekly"])
        self.assertEqual([entry["count"] for entry in banked], [1, 2])
        self.assertEqual([entry["expired"] for entry in banked], [False, False])
        self.assertIsNone(payload[0]["raw"].get("bankedError"))


class AntigravityPoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def test_antigravity_is_default_visible(self):
        self.assertIn("antigravity", self.ai_usage.DEFAULT_PROVIDER_KEYS)
        self.assertIn("antigravity", self.ai_usage.PROVIDER_DISPLAY_ORDER)

    def test_consolidate_pools_collapses_into_three_shared_pools(self):
        summary = {
            "groups": [
                {
                    "displayName": "Gemini Models",
                    "buckets": [
                        {"bucketId": "gemini-weekly", "window": "weekly", "resetTime": "2026-10-31T03:00:02Z", "remainingFraction": 1.0},
                        {"bucketId": "gemini-5h", "window": "5h", "resetTime": "2026-10-24T08:00:02Z", "remainingFraction": 1.0},
                    ],
                },
                {
                    "displayName": "Claude and GPT models",
                    "buckets": [
                        {"bucketId": "3p-weekly", "window": "weekly", "resetTime": "2026-10-31T03:00:02Z", "remainingFraction": 0.9},
                        {"bucketId": "3p-5h", "window": "5h", "resetTime": "2026-10-24T08:00:02Z", "remainingFraction": 0.8},
                    ],
                },
                {
                    "displayName": "Gemini 4 Argon",
                    "buckets": [
                        {"bucketId": "gemini-argon-wtu-weekly", "window": "weekly", "resetTime": "2026-10-31T00:03:20Z", "remainingFraction": 0.77},
                    ],
                },
            ]
        }
        pools, weekly_reset = self.ai_usage.consolidate_antigravity_pools(summary, None)
        self.assertEqual([p["label"] for p in pools], ["Argon", "Flash", "Claude"])
        self.assertEqual([p["percentage"] for p in pools], [77, 100, 80])
        self.assertEqual(weekly_reset, "2026-10-31T00:03:20Z")


class ClaudeNoCrossAccountFallbackTests(unittest.TestCase):
    """A logged-out Claude login must read as logged out.

    2026-11-25: Gillean's Honey login had ended, and the tool quietly read
    Kikin's token over ssh, so her row showed Mètsàtron's account under her name.
    A row names ONE person's account; another machine's login is never borrowed
    unless someone opts in with AI_USAGE_CLAUDE_CREDENTIAL_HOSTS.
    """

    def load_without_opt_in(self):
        env = {k: v for k, v in os.environ.items() if k != "AI_USAGE_CLAUDE_CREDENTIAL_HOSTS"}
        with patch.dict(os.environ, env, clear=True):
            return load_ai_usage()

    def test_default_borrows_no_other_machines_login(self):
        module = self.load_without_opt_in()
        self.assertEqual(module.CLAUDE_CREDENTIAL_HOSTS, [])

    def test_an_ended_login_reports_logged_out_and_never_reads_another_host(self):
        module = self.load_without_opt_in()
        spec = next(item for item in module.PROVIDERS if item.key == "claude")
        with tempfile.TemporaryDirectory() as tmp:
            creds = Path(tmp) / "credentials.json"
            creds.write_text(
                json.dumps({"claudeAiOauth": {"accessToken": "", "refreshToken": "", "expiresAt": 0, "loginEnded": "2026-11-23"}}),
                encoding="utf-8",
            )

            def borrowed(host):
                raise AssertionError("borrowed another machine's login: " + host)

            with patch.object(module, "CLAUDE_CREDENTIALS", str(creds)), \
                 patch.object(module, "_claude_remote_oauth", side_effect=borrowed):
                result = module.fetch_claude_oauth(spec, 1.0)
        self.assertEqual(result["state"], "missing")
        self.assertIsNone(result["raw"])
        self.assertIn("No usable Claude OAuth token", result["summary"])
        self.assertIn("local-empty", result["summary"])

    def test_a_cached_result_from_another_origin_is_never_served_without_a_login(self):
        module = self.load_without_opt_in()
        spec = next(item for item in module.PROVIDERS if item.key == "claude")
        stale = {"result": {"provider": "claude", "state": "ok", "source": "oauth", "credential_origin": "kikin", "raw": {}}, "fetched_at": 1e12}
        with patch.object(module, "claude_oauth_token", return_value=None), \
             patch.object(module, "_cache_read", side_effect=AssertionError("cache consulted before the login was checked")) as cache:
            result = module.fetch_provider(spec, 1.0)
        self.assertEqual(result["state"], "missing")
        cache.assert_not_called()

    def test_a_missing_login_never_asks_the_web_session(self):
        module = self.load_without_opt_in()
        spec = next(item for item in module.PROVIDERS if item.key == "claude")
        with patch.object(module, "claude_oauth_token", return_value=None), \
             patch.object(module, "fetch_fuelcheck", side_effect=AssertionError("web session borrowed")):
            result = module._fetch_provider_uncached(spec, 1.0)
        self.assertEqual(result["state"], "missing")

    def test_an_expiry_that_is_not_a_number_is_not_a_usable_login(self):
        module = self.load_without_opt_in()
        for bad in (None, "later", True, float("inf"), -1):
            token, reason = module._claude_token_from_oauth({"accessToken": "t", "expiresAt": bad})
            self.assertIsNone(token, bad)
            self.assertEqual(reason, "malformed-expiry")

    def test_an_explicit_opt_in_still_works(self):
        with patch.dict(os.environ, {"AI_USAGE_CLAUDE_CREDENTIAL_HOSTS": "kikin"}):
            module = load_ai_usage()
        self.assertEqual(module.CLAUDE_CREDENTIAL_HOSTS, ["kikin"])


class SamePersonsOtherLoginTests(unittest.TestCase):
    """her own UNIX user is logged out; the agent user her seats run under is her
    account too.  The remotes file names that user, and only that user is tried."""

    @classmethod
    def setUpClass(cls):
        cls.ai_usage = load_ai_usage()

    def fake_run(self, outputs, calls):
        def run(cmd, **kwargs):
            calls.append(cmd[-2] if len(cmd) > 1 else cmd)
            target = next((c for c in cmd if c in outputs), None)
            body = outputs.get(target, "[]")
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(body), stderr="")
        return run

    PRIMARY_MISSING = [{"provider": "claude", "label": "Claude Code", "state": "missing", "raw": None, "summary": "logged out"}]
    OTHER_OK = [{"provider": "claude", "label": "Claude Code", "state": "ok", "credential_origin": "local", "raw": {"usage": {"primary": {"usedPercent": 0.0}, "secondary": {"usedPercent": 25.0}}}}]
    BORROWED = [dict(OTHER_OK[0], credential_origin="kikin")]
    FAILED = [{"provider": "claude", "label": "Claude Code", "state": "error", "raw": None, "summary": "timed out"}]

    def entry(self, **extra):
        item = {"label": "Gillean", "ssh": "honey", "providers": "claude"}
        item.update(extra)
        return item

    def test_a_logged_out_panel_is_filled_from_the_named_other_login(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING, "agent-claude@honey": self.OTHER_OK}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(also_ssh=["agent-claude@honey"]), 5.0)
        self.assertEqual(panels[0]["state"], "ok")
        self.assertEqual(panels[0]["label"], "Gillean \u00b7 Claude Code")
        self.assertEqual(panels[0]["credential_origin"], "local")
        self.assertEqual(panels[0]["fetched_via"], "agent-claude@honey")
        self.assertEqual(panels[0]["raw"]["usage"]["secondary"]["usedPercent"], 25.0)

    def test_without_also_ssh_nothing_is_borrowed(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING, "agent-claude@honey": self.OTHER_OK}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(), 5.0)
        self.assertEqual(panels[0]["state"], "missing")
        self.assertNotIn("agent-claude@honey", calls)

    def test_if_no_named_login_works_the_panel_stays_missing(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING, "agent-claude@honey": self.PRIMARY_MISSING}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(also_ssh=["agent-claude@honey"]), 5.0)
        self.assertEqual(panels[0]["state"], "missing")

    def test_an_alternate_that_borrowed_from_a_third_machine_is_refused(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING, "agent-claude@honey": self.BORROWED}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(also_ssh=["agent-claude@honey"]), 5.0)
        self.assertEqual(panels[0]["state"], "missing")

    def test_an_error_panel_is_shown_not_covered_over(self):
        calls = []
        outputs = {"honey": self.FAILED, "agent-claude@honey": self.OTHER_OK}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(also_ssh=["agent-claude@honey"]), 5.0)
        self.assertEqual(panels[0]["state"], "error")
        self.assertNotIn("agent-claude@honey", calls)

    def test_unsafe_or_odd_targets_are_never_run(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING}
        bad = ["-oProxyCommand=touch /tmp/x", 5, {"h": 1}, "a b", ""]
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(also_ssh=bad), 5.0)
        self.assertEqual(panels[0]["state"], "missing")
        self.assertEqual(len(calls), 1)

    def test_a_timeout_that_is_not_finite_never_crashes_the_feed(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING}
        for bad in ("nan", "inf", "-5", "0", [1]):
            with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
                panels = self.ai_usage.fetch_one_remote(self.entry(timeout=bad, also_ssh=["agent-claude@honey"]), 5.0)
            self.assertEqual(panels[0]["state"], "missing", bad)

    def test_a_nan_default_timeout_and_a_boolean_timeout_never_crash_the_feed(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING}
        for default, entry_timeout in ((float("nan"), None), (float("inf"), None), (5.0, True), (None, None)):
            entry = self.entry(also_ssh=["agent-claude@honey"])
            if entry_timeout is not None:
                entry["timeout"] = entry_timeout
            with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
                panels = self.ai_usage.fetch_one_remote(entry, default)
            self.assertEqual(panels[0]["state"], "missing", (default, entry_timeout))

    def test_every_alternate_ask_is_capped_by_what_is_left_of_the_budget(self):
        seen = []
        outputs = {"honey": self.PRIMARY_MISSING, "agent-claude@honey": self.PRIMARY_MISSING, "b@honey": self.PRIMARY_MISSING}

        def run(cmd, **kwargs):
            seen.append(kwargs.get("timeout"))
            target = next((c for c in cmd if c in outputs), None)
            return subprocess.CompletedProcess(cmd, 0, stdout=json.dumps(outputs.get(target, [])), stderr="")

        # entry timeout 10 -> filling budget 20 s.  The clock says 0 when it starts,
        # 15 s have gone when the first alternate is asked (5 s left), and 19.5 s
        # when the second would be (under a second left, so it is not asked at all).
        clock = iter([0.0, 15.0, 19.5, 19.5])
        with patch.object(self.ai_usage.subprocess, "run", side_effect=run), \
             patch.object(self.ai_usage.time, "monotonic", side_effect=lambda: next(clock)):
            self.ai_usage.fetch_one_remote(self.entry(timeout=10, also_ssh=["agent-claude@honey", "b@honey"]), 5.0)
        alternate_calls = seen[1:]
        self.assertEqual(len(alternate_calls), 1)
        self.assertLessEqual(alternate_calls[0], 5.0 + 2.0)

    def test_each_alternate_is_asked_once_however_many_panels_are_missing(self):
        calls = []
        outputs = {"honey": self.PRIMARY_MISSING * 2, "agent-claude@honey": self.PRIMARY_MISSING}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            self.ai_usage.fetch_one_remote(self.entry(also_ssh=["agent-claude@honey", "other@honey"]), 5.0)
        self.assertEqual(calls.count("agent-claude@honey"), 1)

    def test_an_ok_panel_is_never_replaced(self):
        calls = []
        outputs = {"honey": self.OTHER_OK, "agent-claude@honey": self.PRIMARY_MISSING}
        with patch.object(self.ai_usage.subprocess, "run", side_effect=self.fake_run(outputs, calls)):
            panels = self.ai_usage.fetch_one_remote(self.entry(also_ssh=["agent-claude@honey"]), 5.0)
        self.assertEqual(panels[0]["state"], "ok")
        self.assertNotIn("agent-claude@honey", calls)


if __name__ == "__main__":
    unittest.main()
