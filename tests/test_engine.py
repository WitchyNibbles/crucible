"""Tests for crucible.engine.WorkflowEngine."""

from crucible.engine import WorkflowEngine


def test_engine_init_creates_state(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "engine-demo",
        name="Engine Demo",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    assert engine.name == "Engine Demo"
    assert engine.slug == "engine-demo"
    assert (state_dir / "engine-demo.json").exists()


def test_engine_init_loads_existing(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine1 = WorkflowEngine(
        "reuse-me",
        name="First",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    engine2 = WorkflowEngine(
        "reuse-me",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    assert engine2.state["name"] == "First"
    assert engine2.status()["slug"] == "reuse-me"


def test_engine_init_disciplines(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "disc-test",
        name="Discipline Test",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    engine.init_disciplines({
        "architect": ["data-model", "api"],
        "engineering": ["backend"],
    })
    state = engine.status()
    assert "architect" in state["disciplines"]
    assert "engineering" in state["disciplines"]
    assert set(state["disciplines"]["architect"]["layers"].keys()) == {
        "data-model",
        "api",
    }


def test_discipline_lead_prompt_contains_discipline_and_layers(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "prompt-test",
        name="Prompt Test",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    engine.init_disciplines({"architect": ["schema"]},)
    prompt = engine.discipline_lead_prompt(
        "architect", "Build a todo API with auth"
    )
    assert "architect" in prompt
    assert "schema" in prompt
    assert "Build a todo API with auth" in prompt


def test_layer_specialist_prompt_contains_language(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "layer-prompt",
        name="Layer Prompt",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    prompt = engine.layer_specialist_prompt(
        "engineering", "backend", "Implement CRUD", ["python", "go"]
    )
    assert "engineering" in prompt
    assert "backend" in prompt
    assert "python" in prompt
    assert "go" in prompt


def test_audit_prompt_contains_pas_fail(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "audit-prompt",
        name="Audit Prompt",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    prompt = engine.audit_prompt("architect/schema", "<work>", "<spec>")
    assert "[PASS]" in prompt
    assert "[FAIL]" in prompt
    assert "<work>" in prompt


def test_record_finding_updates_state(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "findings",
        name="Findings",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    engine.init_disciplines({"qa": ["tests"]})
    engine.record_finding("qa", "tests", "Missing edge cases", "FAIL")
    state = engine.status()
    findings = state["disciplines"]["qa"]["findings"]
    assert len(findings) == 1
    assert findings[0]["status"] == "FAIL"


def test_run_discipline_returns_ready_status(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    engine = WorkflowEngine(
        "run-test",
        name="Run Test",
        state_dir=state_dir,
        log_dir=log_dir,
    )
    engine.init_disciplines({"devops": ["ci", "deploy"]})
    result = engine.run_discipline("devops", "Deploy to AWS")
    assert result["status"] == "READY"
    assert "discipline_lead_prompt" in result
    assert "ci" in result["layer_prompts"]
    assert "deploy" in result["layer_prompts"]
