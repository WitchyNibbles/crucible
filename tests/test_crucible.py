import json
import os
import tempfile

import pytest

from crucible import (
    add_discipline,
    add_finding,
    complete_discipline,
    complete_project,
    init,
    list_projects,
    load,
    set_layer_done,
)


@pytest.fixture()
def tmp_dirs(tmp_path):
    state_dir = tmp_path / "state"
    log_dir = tmp_path / "log"
    state_dir.mkdir()
    log_dir.mkdir()
    return state_dir, log_dir


def test_init_create_project(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    state = init("demo", "Demo App", state_dir=state_dir, log_dir=log_dir)
    assert state["slug"] == "demo"
    assert state["name"] == "Demo App"
    assert state["status"] == "INTAKE"
    assert (state_dir / "demo.json").exists()


def test_init_duplicate_rejects(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("demo", "Demo App", state_dir=state_dir, log_dir=log_dir)
    with pytest.raises(SystemExit):
        init("demo", "Duplicate", state_dir=state_dir, log_dir=log_dir)


def test_list_projects_empty(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    result = list_projects(state_dir=state_dir)
    assert result == []


def test_list_projects_populated(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("a", "A", state_dir=state_dir, log_dir=log_dir)
    init("b", "B", state_dir=state_dir, log_dir=log_dir)
    result = list_projects(state_dir=state_dir)
    assert len(result) == 2
    assert result[0]["slug"] == "a"


def test_add_discipline(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    state = add_discipline("x", "architect", ["data-model", "api"], state_dir=state_dir, log_dir=log_dir)
    assert "architect" in state["disciplines"]
    assert set(state["disciplines"]["architect"]["layers"].keys()) == {"data-model", "api"}


def test_add_discipline_duplicate(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "qa", ["tests"], state_dir=state_dir, log_dir=log_dir)
    with pytest.raises(SystemExit):
        add_discipline("x", "qa", ["tests-again"], state_dir=state_dir, log_dir=log_dir)


def test_set_layer_done(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "arch", ["schema"], state_dir=state_dir, log_dir=log_dir)
    state = set_layer_done("x", "arch", "schema", state_dir=state_dir, log_dir=log_dir)
    assert state["disciplines"]["arch"]["layers"]["schema"]["status"] == "DONE"
    assert "completed_at" in state["disciplines"]["arch"]["layers"]["schema"]


def test_add_finding(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "eng", ["api"], state_dir=state_dir, log_dir=log_dir)
    state = add_finding("x", "eng", "Missing error handling", "FAIL", state_dir=state_dir, log_dir=log_dir)
    findings = state["disciplines"]["eng"]["findings"]
    assert len(findings) == 1
    assert findings[0]["status"] == "FAIL"
    assert findings[0]["text"] == "Missing error handling"


def test_complete_discipline_fails_on_open_findings(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "eng", ["api"], state_dir=state_dir, log_dir=log_dir)
    add_finding("x", "eng", "Bug", "FAIL", state_dir=state_dir, log_dir=log_dir)
    with pytest.raises(SystemExit):
        complete_discipline("x", "eng", state_dir=state_dir, log_dir=log_dir)


def test_complete_discipline_succeeds_when_all_fixed(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "eng", ["api"], state_dir=state_dir, log_dir=log_dir)
    add_finding("x", "eng", "Bug", "FAIL", state_dir=state_dir, log_dir=log_dir)
    # Resolve by re-adding the same text with FIXED status
    add_finding("x", "eng", "Bug", "FIXED", state_dir=state_dir, log_dir=log_dir)
    state = complete_discipline("x", "eng", state_dir=state_dir, log_dir=log_dir)
    assert state["disciplines"]["eng"]["sign_off"] is not None


def test_complete_project_fails_on_unsigned_disciplines(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "arch", ["schema"], state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "eng", ["api"], state_dir=state_dir, log_dir=log_dir)
    complete_discipline("x", "arch", state_dir=state_dir, log_dir=log_dir)
    with pytest.raises(SystemExit):
        complete_project("x", state_dir=state_dir, log_dir=log_dir)


def test_complete_project_success(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    init("x", "X", state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "arch", ["schema"], state_dir=state_dir, log_dir=log_dir)
    add_discipline("x", "eng", ["api"], state_dir=state_dir, log_dir=log_dir)
    complete_discipline("x", "arch", state_dir=state_dir, log_dir=log_dir)
    complete_discipline("x", "eng", state_dir=state_dir, log_dir=log_dir)
    state = complete_project("x", state_dir=state_dir, log_dir=log_dir)
    assert state["status"] == "COMPLETED"
    assert "completed_at" in state


def test_load_missing_raises(tmp_dirs):
    state_dir, log_dir = tmp_dirs
    with pytest.raises(SystemExit):
        load("nope", state_dir=state_dir)
