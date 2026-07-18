"""Contract compatibility and fixture tests for issue #21."""

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from llm_gate.contracts import (
    ContractValidationError,
    RoutingDecisionContract,
    RuntimeCandidate,
    TaskSpec,
    contract_from_dict,
)

FIXTURE_DIR = Path(__file__).parent / "fixtures"
SCHEMA = json.loads((Path(__file__).parents[1] / "schemas" / "contracts.v1.json").read_text())


def test_fixture_is_valid_against_versioned_schema() -> None:
    payload = json.loads((FIXTURE_DIR / "contract-v1.json").read_text())
    errors = list(Draft202012Validator(SCHEMA).iter_errors(payload))
    assert errors == []


def test_all_contracts_round_trip_fixture() -> None:
    payload = json.loads((FIXTURE_DIR / "contract-v1.json").read_text())
    for name, value in payload.items():
        restored = contract_from_dict(name, value)
        assert restored.to_dict() == value


def test_unknown_fields_are_rejected() -> None:
    payload = {"objective": "ship", "task_type": "coding", "compatibility": {"future": True}}
    with pytest.raises(ContractValidationError, match="unknown field"):
        TaskSpec.from_dict(payload)


def test_secret_bearing_fields_are_rejected() -> None:
    with pytest.raises(ContractValidationError, match="secret-bearing"):
        TaskSpec.from_dict({"objective": "ship", "context": {"api_key": "do-not-store"}})


def test_schema_version_defaults_to_v1_when_omitted() -> None:
    task = TaskSpec.from_dict({"objective": "ship", "task_type": "coding"})

    assert task.schema_version == "1"


def test_schema_version_mismatch_is_rejected() -> None:
    with pytest.raises(ContractValidationError, match=r"schema_version must be '1', got '2'"):
        TaskSpec.from_dict({"objective": "ship", "task_type": "coding", "schema_version": "2"})


def test_fixture_contracts_all_declare_schema_version_v1() -> None:
    payload = json.loads((FIXTURE_DIR / "contract-v1.json").read_text())

    for name, value in payload.items():
        assert value["schema_version"] == "1", name


def test_catalog_presence_is_distinct_from_live_eligibility() -> None:
    candidate = RuntimeCandidate.from_dict(
        {
            "runtime_id": "ollama/llama3",
            "catalog_present": True,
            "live_eligible": False,
            "availability": "unknown",
            "signals": {"catalog": {"source": "catalog", "freshness_seconds": 30}},
        }
    )
    assert candidate.catalog_present is True
    assert candidate.live_eligible is False
    assert candidate.signals["catalog"]["source"] == "catalog"


def test_existing_routing_decision_remains_importable() -> None:
    decision = RoutingDecisionContract.from_dict(
        {"selected_route": {"runtime_id": "x"}, "policy_floor": "protected"}
    )
    assert decision.selected_route["runtime_id"] == "x"


def test_invalid_fixture_is_rejected_by_python_contract() -> None:
    payload = json.loads((FIXTURE_DIR / "invalid-unknown-field.json").read_text())
    with pytest.raises(ContractValidationError):
        TaskSpec.from_dict(payload)


def test_invalid_schema_version_fixture_is_rejected_by_schema_and_python_contract() -> None:
    payload = json.loads((FIXTURE_DIR / "invalid-schema-version.json").read_text())

    errors = list(Draft202012Validator(SCHEMA).iter_errors({"task_spec": payload}))
    assert any(error.json_path == "$.task_spec.schema_version" for error in errors)

    with pytest.raises(ContractValidationError, match=r"schema_version must be '1', got '2'"):
        TaskSpec.from_dict(payload)
