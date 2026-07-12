import re

with open("tests/test_gate_unit.py", "r") as f:
    content = f.read()

new_tests = """
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
"""
content = content + new_tests

with open("tests/test_gate_unit.py", "w") as f:
    f.write(content)
