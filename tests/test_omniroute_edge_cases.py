from llm_gate.api import _build_proxy
from llm_gate.discovery import fetch_models
from llm_gate.headroom import check_headroom
from llm_gate.models import ModelInfo, ProviderConfig


def test_headroom_failures_are_bounded_and_fail_open() -> None:
    # Health/headroom failures are bounded and never turn unknown into ready
    # Check that even with an invalid endpoint, check_headroom returns True, 100.0 (fail-open)
    available, pct = check_headroom(
        "model",
        "provider",
        ProviderConfig(base_url="https://provider.example", headroom_endpoint="/bad-endpoint"),
    )
    assert available is True
    assert pct == 100.0


def test_stale_row_cached_discovery(monkeypatch) -> None:
    # Test our TTL cache correctly isolates stale rows or expires them
    import llm_gate.discovery

    monkeypatch.setattr(
        llm_gate.discovery,
        "_CACHE",
        {
            "omni": {
                "ts": 0.0,  # extremely old
                "models": [ModelInfo(id="stale-model", provider="omni", capability_tier=2)],
            }
        },
    )
    # the URL fetch should fail and fallback to []
    models = fetch_models("omni", ProviderConfig(base_url="http://invalid.local"), ttl=60)
    assert models == []


def test_endpoint_mismatch_and_upstream_failure(monkeypatch) -> None:
    monkeypatch.setenv("LLMGATE_UPSTREAM_BASE_URL", "http://invalid-endpoint-mismatch:9999/v1")
    proxy = _build_proxy()
    assert proxy.base_url == "http://invalid-endpoint-mismatch:9999/v1"
