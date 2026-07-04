
from __future__ import annotations

from crucible.runner import (
    AgentResult,
    FakeAgentBridge,
    HermesSubagentBridge,
    validate_result,
)


def test_validate_result_fake_allows_empty_artifacts():
    result = AgentResult(
        output="ignored",
        artifacts={},
        metadata={},
    )
    findings = validate_result(result, mode="fake")
    assert findings == []


def test_validate_result_default_requires_artifacts():
    findings = validate_result(
        AgentResult(
            output="ignored",
            artifacts={},
            metadata={},
        ),
        mode="default",
    )
    assert any(f["status"] == "FAIL" and "artifacts must not be empty" in f["text"] for f in findings)


def test_validate_result_default_rejects_empty_artifact_values():
    findings = validate_result(
        AgentResult(
            output="ignored",
            artifacts={"a.py": ""},
            metadata={},
        ),
        mode="default",
    )
    assert any(f["status"] == "FAIL" and "empty artifact value" in f["text"] for f in findings)


def test_validate_result_real_requires_real_flag():
    findings = validate_result(
        AgentResult(
            output="ignored",
            artifacts={"a.py": "x = 1"},
            metadata={"real": False},
        ),
        mode="real",
    )
    assert any(f["status"] == "FAIL" and "real" in f["text"].lower() for f in findings)


def test_validate_result_real_passes_with_real_flag():
    findings = validate_result(
        AgentResult(
            output="ignored",
            artifacts={"a.py": "x = 1"},
            metadata={"real": True},
        ),
        mode="real",
    )
    assert findings == []


def test_validate_result_default_passes_with_all_required_fields():
    findings = validate_result(
        AgentResult(
            output="ignored",
            artifacts={"a.py": "x = 1"},
            metadata={},
        ),
        mode="default",
    )
    assert findings == []


def test_validate_result_unknown_mode_returns_fail():
    findings = validate_result(
        AgentResult(output="ignored", artifacts={}, metadata={}),
        mode="mystery",
    )
    assert any(f["status"] == "FAIL" for f in findings)


def test_fake_agent_bridge_returns_non_real_metadata():
    bridge = FakeAgentBridge(fixtures={})
    result = bridge.run_language_task("task", "python", {})
    assert result.metadata.get("real") is False
    assert result.metadata.get("bridge") == "FakeAgentBridge"


def test_fake_agent_bridge_uses_fixture_artifacts():
    fixture = {"main.py": "print('hi')"}
    bridge = FakeAgentBridge(fixtures={"python": fixture})
    result = bridge.run_language_task("task", "python", {})
    assert result.artifacts == fixture


def test_fake_agent_bridge_returns_empty_artifacts_for_missing_language():
    bridge = FakeAgentBridge(fixtures={})
    result = bridge.run_language_task("task", "rust", {})
    assert result.artifacts == {}


def test_hermes_subagent_bridge_delegates_to_callable():
    calls = []

    def delegate_fn(task, language, context):
        calls.append((task, language, context))
        return AgentResult(
            output="delegated",
            artifacts={"out.txt": "done"},
            metadata={"real": True, "bridge": "HermesSubagentBridge"},
        )

    bridge = HermesSubagentBridge(delegate_fn=delegate_fn)
    result = bridge.run_language_task("do x", "python", {"repo_root": "/tmp"})
    assert len(calls) == 1
    assert calls[0] == ("do x", "python", {"repo_root": "/tmp"})
    assert result.output == "delegated"
    assert result.artifacts == {"out.txt": "done"}
    assert result.real is True


def test_hermes_subagent_bridge_requires_delegate_fn():
    import pytest

    with pytest.raises(ValueError):
        HermesSubagentBridge()


def test_hermes_subagent_bridge_default_passes_validation():
    bridge = HermesSubagentBridge(
        delegate_fn=lambda t, l, c: AgentResult(
            output="ok",
            artifacts={"a.py": "x=1"},
            metadata={"real": True},
        )
    )
    result = bridge.run_language_task("t", "python", {})
    findings = validate_result(result, mode="real")
    assert findings == []
