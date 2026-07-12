"""Unit tests for the Gate routing engine."""
import pytest
from unittest.mock import patch, MagicMock
from llm_gate.gate import Gate, TIER_MAP
from llm_gate.models import ProviderConfig, RoutingDecision, ModelInfo


class TestTierMap:
    def test_critical_is_zero(self):
        assert TIER_MAP["critical"] == 0

    def test_high_is_one(self):
        assert TIER_MAP["high"] == 1

    def test_medium_is_two(self):
        assert TIER_MAP["medium"] == 2

    def test_low_is_three(self):
        assert TIER_MAP["low"] == 3


class TestGateInit:
    def test_default_primary_model(self):
        gate = Gate()
        assert gate.primary_model == "anthropic/claude-3-opus-20240229"

    def test_custom_primary_model(self):
        gate = Gate(primary_model="openai/gpt-4")
        assert gate.primary_model == "openai/gpt-4"

    def test_empty_providers(self):
        gate = Gate()
        assert gate.providers == {}

    def test_custom_providers(self):
        providers = {"groq": ProviderConfig(base_url="https://api.groq.com/openai/v1")}
        gate = Gate(providers=providers)
        assert "groq" in gate.providers

    def test_log_path_default(self):
        gate = Gate()
        assert gate.log_path == "llm-gate-decisions.jsonl"


class TestGateRouting:
    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    def test_critical_never_offloads(self, mock_log, mock_scan):
        gate = Gate(primary_model="anthropic/claude-3-opus-20240229")
        dec = gate.route("deploy to production", criticality="critical")
        assert dec.model == "anthropic/claude-3-opus-20240229"
        assert dec.provider == "primary"
        assert dec.tier == 0
        assert "critical" in dec.reason

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    def test_low_criticality_falls_back_without_providers(self, mock_log, mock_scan):
        gate = Gate(primary_model="anthropic/claude-3-opus-20240229")
        dec = gate.route("format this json", criticality="low")
        assert dec.model == "anthropic/claude-3-opus-20240229"
        assert "fallback" in dec.reason

    @patch("llm_gate.gate.scan", return_value=(0, "keyword: deploy"))
    @patch("llm_gate.gate.log_decision")
    def test_escalation_bumps_to_critical(self, mock_log, mock_scan):
        gate = Gate(primary_model="anthropic/claude-3-opus-20240229")
        dec = gate.route("deploy the database migration", criticality="low")
        assert dec.tier == 0
        assert dec.escalated is True

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    def test_latency_is_recorded(self, mock_log, mock_scan):
        gate = Gate()
        dec = gate.route("test task")
        assert dec.latency_ms > 0

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    def test_logged_flag_set(self, mock_log, mock_scan):
        gate = Gate(log_path="test.jsonl")
        dec = gate.route("test")
        assert dec.logged is True

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    def test_logged_flag_false_when_no_path(self, mock_log, mock_scan):
        gate = Gate(log_path="")
        dec = gate.route("test")
        assert dec.logged is False


class TestGateWithProviders:
    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    @patch("llm_gate.gate.fetch_models")
    @patch("llm_gate.gate.select_best_model")
    def test_routes_to_provider_when_available(self, mock_select, mock_fetch, mock_log, mock_scan):
        mock_model = MagicMock()
        mock_model.id = "groq/llama-3"
        mock_model.tier = 3
        mock_fetch.return_value = [mock_model]
        mock_select.return_value = ("groq", mock_model)

        providers = {"groq": ProviderConfig(base_url="https://api.groq.com/openai/v1")}
        gate = Gate(providers=providers)
        dec = gate.route("simple formatting task", criticality="low")
        assert dec.model == "groq/llama-3"
        assert dec.provider == "groq"

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    @patch("llm_gate.gate.fetch_models")
    @patch("llm_gate.gate.select_best_model")
    def test_falls_back_when_no_candidate_matches(self, mock_select, mock_fetch, mock_log, mock_scan):
        mock_fetch.return_value = []
        mock_select.return_value = (None, None)

        providers = {"groq": ProviderConfig(base_url="https://api.groq.com/openai/v1")}
        gate = Gate(primary_model="anthropic/claude-3-opus-20240229", providers=providers)
        dec = gate.route("complex task", criticality="medium")
        assert dec.model == "anthropic/claude-3-opus-20240229"
        assert "fallback" in dec.reason

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    @patch("urllib.request.urlopen")
    def test_fallback_on_429_http_error(self, mock_urlopen, mock_log, mock_scan):
        from urllib.error import HTTPError
        import llm_gate.discovery
        llm_gate.discovery._CACHE.clear()
        
        mock_urlopen.side_effect = HTTPError("http://fake.api", 429, "Too Many Requests", {}, None)
        
        providers = {"openrouter": ProviderConfig(base_url="https://fake.api/v1")}
        gate = Gate(primary_model="anthropic/claude-3-opus-20240229", providers=providers)
        
        dec = gate.route("do something", criticality="low")
        
        assert dec.model == "anthropic/claude-3-opus-20240229"
        assert dec.provider == "primary"
        assert "fallback" in dec.reason

    @patch("llm_gate.gate.scan", return_value=(None, ""))
    @patch("llm_gate.gate.log_decision")
    @patch("urllib.request.urlopen")
    def test_fallback_on_529_http_error(self, mock_urlopen, mock_log, mock_scan):
        from urllib.error import HTTPError
        import llm_gate.discovery
        llm_gate.discovery._CACHE.clear()
        
        mock_urlopen.side_effect = HTTPError("http://fake.api", 529, "Overloaded", {}, None)
        
        providers = {"openrouter": ProviderConfig(base_url="https://fake.api/v1")}
        gate = Gate(primary_model="anthropic/claude-3-opus-20240229", providers=providers)
        
        dec = gate.route("do something", criticality="low")
        
        assert dec.model == "anthropic/claude-3-opus-20240229"
        assert dec.provider == "primary"
        assert "fallback" in dec.reason
