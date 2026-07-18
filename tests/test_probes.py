import time
import urllib.error
from datetime import timezone

import pytest

from llm_gate.probes import PROBE_PROMPT, ProbePolicy, ProbeRunner, openai_probe_transport


def ok_transport(calls):
    def transport(model_id, payload, timeout):
        calls.append((model_id, payload, timeout))
        return {
            "status_code": 200,
            "body": {
                "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                "usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": 1,
                    "total_tokens": 3,
                },
            },
        }

    return transport


def test_one_token_payload_and_usage_marks_ready():
    calls = []
    result = ProbeRunner(ProbePolicy(max_models_per_run=1)).run(
        ["runtime/model"], ok_transport(calls)
    )
    assert result[0].availability_state == "ready"
    assert result[0].usage_available is True
    assert result[0].completion_tokens == 1
    assert calls[0][1]["messages"][0]["content"] == PROBE_PROMPT
    assert calls[0][1]["max_tokens"] == 1
    assert calls[0][1]["tools"] == []


def test_bound_is_enforced_and_ids_remain_opaque():
    calls = []
    result = ProbeRunner(ProbePolicy(max_models_per_run=2)).run(
        ["catalog-id-1", "opaque/value.2", "third-runtime-id"],
        ok_transport(calls),
    )
    assert [item.model_id for item in result] == ["catalog-id-1", "opaque/value.2"]
    assert len(calls) == 2


def test_zero_usage_is_not_ready():
    def zero_usage(model_id, payload, timeout):
        return {
            "status_code": 200,
            "body": {
                "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_tokens": 0,
                },
            },
        }

    result = ProbeRunner().run(["runtime/model"], zero_usage)[0]

    assert result.availability_state == "degraded"
    assert result.usage_available is False


def test_empty_completion_is_not_ready():
    def empty_completion(model_id, payload, timeout):
        return {
            "status_code": 200,
            "body": {
                "choices": [{"message": {"role": "assistant", "content": ""}}],
                "usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": 1,
                    "total_tokens": 3,
                },
            },
        }

    result = ProbeRunner().run(["runtime/model"], empty_completion)[0]

    assert result.availability_state == "degraded"
    assert result.status == "completion_unavailable"


def test_quota_exhaustion_is_classified_separately():
    def quota_exhausted(model_id, payload, timeout):
        return {"status_code": 402, "body": {}}

    result = ProbeRunner().run(["runtime/model"], quota_exhausted)[0]

    assert result.availability_state == "degraded"
    assert result.error_class == "quota_exhausted"


def test_non_assistant_message_is_not_ready():
    def wrong_role(model_id, payload, timeout):
        return {
            "status_code": 200,
            "body": {
                "choices": [{"message": {"role": "user", "content": "OK"}}],
                "usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": 1,
                    "total_tokens": 3,
                },
            },
        }

    result = ProbeRunner().run(["runtime/model"], wrong_role)[0]

    assert result.availability_state == "degraded"
    assert result.status == "completion_unavailable"


def test_malformed_http_status_is_not_ready():
    def malformed_status(model_id, payload, timeout):
        return {
            "status_code": "200",
            "body": {
                "choices": [{"message": {"role": "assistant", "content": "OK"}}],
                "usage": {
                    "prompt_tokens": 2,
                    "completion_tokens": 1,
                    "total_tokens": 3,
                },
            },
        }

    result = ProbeRunner().run(["runtime/model"], malformed_status)[0]

    assert result.availability_state == "degraded"
    assert result.error_class == "malformed_response"


def test_openai_transport_preserves_http_error_classification():
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=None,
        )

    transport = openai_probe_transport("http://127.0.0.1:20128/v1", opener=opener)

    with pytest.raises(urllib.error.HTTPError):
        transport(
            "runtime/model",
            ProbePolicy().payload("runtime/model"),
            0.1,
        )


def test_runner_records_http_error_status_from_openai_transport():
    def opener(request, timeout):
        raise urllib.error.HTTPError(
            request.full_url,
            429,
            "Too Many Requests",
            hdrs=None,
            fp=None,
        )

    transport = openai_probe_transport("http://127.0.0.1:20128/v1", opener=opener)
    result = ProbeRunner().run(["runtime/model"], transport)[0]

    assert result.availability_state == "degraded"
    assert result.error_class == "rate_limited"
    assert result.http_status == 429


def test_cooldown_skips_without_transport():
    calls = []
    runner = ProbeRunner(ProbePolicy(cooldown_seconds=60))
    runner.run(["runtime/model"], ok_transport(calls))
    second = runner.run(["runtime/model"], ok_transport(calls))
    assert second[0].status == "skipped"
    assert second[0].error == "cooldown"
    assert len(calls) == 1


def test_repeated_failures_quarantine_and_redact():
    def failing(model_id, payload, timeout):
        raise RuntimeError("Bearer secret-value https://example.test/path?token=secret")

    runner = ProbeRunner(
        ProbePolicy(cooldown_seconds=0, failure_threshold=2, quarantine_seconds=60)
    )
    first = runner.run(["runtime/model"], failing)[0]
    second = runner.run(["runtime/model"], failing)[0]
    third = runner.run(["runtime/model"], failing)[0]
    assert first.availability_state == "degraded"
    assert second.availability_state == "denied"
    assert third.status == "skipped"
    assert "secret-value" not in (second.error or "")
    assert "token=secret" not in (second.error or "")
    assert "REDACTED" in (second.error or "")


def test_timeout_and_usage_unavailable_are_not_ready():
    def slow(model_id, payload, timeout):
        time.sleep(0.2)
        return {"status_code": 200, "body": {}}

    runner = ProbeRunner(ProbePolicy(timeout_seconds=0.03, cooldown_seconds=0))
    result = runner.run(["runtime/model"], slow)[0]
    assert result.status == "timeout"
    assert result.availability_state == "degraded"


def test_runtime_observation_mapping_is_structured():
    calls = []
    result = ProbeRunner().run(["runtime/model"], ok_transport(calls))[0]
    observation = result.as_runtime_observation()
    assert observation.source == "llm-gate:probe"
    assert observation.raw["usage_available"] is True
    assert observation.observed_at.tzinfo == timezone.utc


def test_injected_observation_time_controls_next_probe_time():
    from datetime import datetime

    observed_at = datetime(2025, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
    result = ProbeRunner(ProbePolicy(cooldown_seconds=30)).run(
        ["runtime/model"],
        ok_transport([]),
        now=observed_at,
    )[0]

    assert result.next_probe_at is not None
    assert (result.next_probe_at - observed_at).total_seconds() == 30
