"""crucible — audit-driven autonomous software development workflow.

Public API:
    from crucible import init, list_projects
    from crucible import add_discipline, set_layer_done, add_finding
    from crucible import complete_discipline, complete_project
    from crucible.engine import WorkflowEngine
    from crucible.runner import ArtifactWriter, AuditEngine, WorkflowRunner
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

__version__ = "0.1.0"

DEFAULT_STATE_DIR = Path.home() / ".crucible" / "state"
DEFAULT_LOG_DIR = Path.home() / ".crucible" / "log"
DEFAULT_REPO_ROOT = Path.home() / "projects"
DEFAULT_MAX_AUDIT_ROUNDS = 3


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs(state_dir: Path, log_dir: Path) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _state_path(slug: str, state_dir: Path) -> Path:
    return state_dir / f"{slug}.json"


def _load(slug: str, state_dir: Path) -> dict[str, Any]:
    p = _state_path(slug, state_dir)
    if not p.exists():
        _die(f"No project '{slug}' at {p}")
    with p.open() as f:
        return json.load(f)


def _save(slug: str, state: dict[str, Any], state_dir: Path) -> None:
    p = _state_path(slug, state_dir)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state, f, indent=2, default=str)
    tmp.replace(p)


def _log_event(slug: str, message: str, log_dir: Path) -> None:
    d = log_dir / slug
    d.mkdir(parents=True, exist_ok=True)
    log_file = d / "run.log"
    with log_file.open("a") as f:
        f.write(f"{_utcnow()} | {message}\n")


def _default_state(slug: str, name: str, repo_root: Path) -> dict[str, Any]:
    return {
        "slug": slug,
        "name": name,
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
        "status": "INTAKE",
        "requirements_path": None,
        "max_audit_rounds": DEFAULT_MAX_AUDIT_ROUNDS,
        "disciplines": {},
        "repo_path": str((repo_root / slug).resolve()),
        "history": [],
    }


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def init(
    slug: str,
    name: str,
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    """Create a new project and return initial state."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    repo_root = repo_root or DEFAULT_REPO_ROOT
    _ensure_dirs(state_dir, log_dir)
    p = _state_path(slug, state_dir)
    if p.exists():
        _die(f"Project '{slug}' already exists at {p}")
    state = _default_state(slug, name, repo_root)
    _save(slug, state, state_dir)
    _log_event(slug, f"INIT name={name}", log_dir)
    return state


def list_projects(
    *,
    state_dir: Path | None = None,
) -> list[dict[str, Any]]:
    """Return a summary list of all known projects."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    _ensure_dirs(state_dir, DEFAULT_LOG_DIR)
    files = sorted(state_dir.glob("*.json"))
    return [
        {
            "slug": json.loads(f.read_text())["slug"],
            "name": json.loads(f.read_text())["name"],
            "status": json.loads(f.read_text()).get("status", "UNKNOWN"),
        }
        for f in files
    ]


def load(
    slug: str,
    *,
    state_dir: Path | None = None,
) -> dict[str, Any]:
    """Load and return full project state."""
    return _load(slug, state_dir or DEFAULT_STATE_DIR)


def save(
    slug: str,
    state: dict[str, Any],
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
) -> None:
    """Persist updated project state."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    state["updated_at"] = _utcnow()
    _save(slug, state, state_dir)


def add_discipline(
    slug: str,
    discipline: str,
    layers: list[str],
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Register a discipline and its layers."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    state = _load(slug, state_dir)

    disc = state["disciplines"].get(discipline)
    if disc is not None:
        _die(f"Discipline '{discipline}' already exists.")
    assert disc is None  # tell type checker we only reach here if missing

    state["disciplines"][discipline] = {
        "layers": {l: {"status": "PENDING"} for l in layers},
        "findings": [],
        "sign_off": None,
    }
    save(slug, state, state_dir=state_dir, log_dir=log_dir)
    _log_event(slug, f"ADD_DISCIPLINE name={discipline} layers={layers}", log_dir)
    return state


def set_layer_done(
    slug: str,
    discipline: str,
    layer: str,
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Mark a layer as completed."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    state = _load(slug, state_dir)

    disc = state["disciplines"].get(discipline)
    if disc is None:
        _die(f"Discipline '{discipline}' not found.")
    assert disc is not None

    if layer not in disc["layers"]:
        _die(f"Layer '{layer}' not found in '{discipline}'.")
    disc["layers"][layer]["status"] = "DONE"
    disc["layers"][layer]["completed_at"] = _utcnow()
    save(slug, state, state_dir=state_dir, log_dir=log_dir)
    _log_event(slug, f"LAYER_DONE discipline={discipline} layer={layer}", log_dir)
    return state


def add_finding(
    slug: str,
    discipline: str,
    text: str,
    status: str = "FAIL",
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Add an audit finding (FAIL or FIXED)."""
    if status not in ("FAIL", "FIXED"):
        _die("Status must be FAIL or FIXED")

    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    state = _load(slug, state_dir)

    disc = state["disciplines"].get(discipline)
    if disc is None:
        _die(f"Discipline '{discipline}' not found.")
    assert disc is not None

    # If an identical finding already exists and toggling its status, update it
    # instead of creating a duplicate. This supports the common pattern:
    #   add_finding(..., "Missing auth", FAIL)
    #   add_finding(..., "Missing auth", FIXED)
    existing = next(
        (i for i, f in enumerate(disc["findings"]) if f["text"] == text),
        None,
    )
    if existing is not None and disc["findings"][existing]["status"] != status:
        disc["findings"][existing]["status"] = status
        disc["findings"][existing]["at"] = _utcnow()
    else:
        disc["findings"].append({
            "text": text,
            "status": status,
            "at": _utcnow(),
        })
    save(slug, state, state_dir=state_dir, log_dir=log_dir)
    return state


def complete_discipline(
    slug: str,
    discipline: str,
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Sign off a discipline (requires zero open FAIL findings)."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    state = _load(slug, state_dir)

    disc = state["disciplines"].get(discipline)
    if disc is None:
        _die(f"Discipline '{discipline}' not found.")
    assert disc is not None

    open_findings = [f for f in disc["findings"] if f["status"] == "FAIL"]
    if open_findings:
        _die(
            f"Cannot sign off '{discipline}': "
            f"{len(open_findings)} open FAIL findings."
        )
    disc["sign_off"] = _utcnow()
    save(slug, state, state_dir=state_dir, log_dir=log_dir)
    _log_event(slug, f"DISCIPLINE_SIGN_OFF name={discipline}", log_dir)
    return state


def complete_project(
    slug: str,
    *,
    state_dir: Path | None = None,
    log_dir: Path | None = None,
) -> dict[str, Any]:
    """Mark project COMPLETED (all disciplines signed off, no open findings)."""
    state_dir = state_dir or DEFAULT_STATE_DIR
    log_dir = log_dir or DEFAULT_LOG_DIR
    state = _load(slug, state_dir)

    unsigned = [n for n, d in state["disciplines"].items() if not d.get("sign_off")]
    if unsigned:
        _die(f"Cannot complete project: unsigned disciplines: {unsigned}")

    open_findings = [
        f for d in state["disciplines"].values()
        for f in d["findings"]
        if f["status"] == "FAIL"
    ]
    if open_findings:
        _die(f"Cannot complete project: {len(open_findings)} open FAIL findings.")

    state["status"] = "COMPLETED"
    state["completed_at"] = _utcnow()
    save(slug, state, state_dir=state_dir, log_dir=log_dir)
    _log_event(slug, "PROJECT_COMPLETED", log_dir)
    return state


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="crucible",
        description="crucible — audit-driven autonomous development workflow",
    )
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Create a new project")
    p_init.add_argument("slug")
    p_init.add_argument("name")

    sub.add_parser("list", help="List all projects")

    p_status = sub.add_parser("status", help="Show project state")
    p_status.add_argument("slug")

    p_disc = sub.add_parser("add_discipline", help="Register a discipline")
    p_disc.add_argument("slug")
    p_disc.add_argument("discipline")
    p_disc.add_argument("layers", help="Comma-separated layer names")

    p_ld = sub.add_parser("set_layer_done", help="Mark a layer complete")
    p_ld.add_argument("slug")
    p_ld.add_argument("discipline")
    p_ld.add_argument("layer")

    p_find = sub.add_parser("add_finding", help="Record an audit finding")
    p_find.add_argument("slug")
    p_find.add_argument("discipline")
    p_find.add_argument("text")
    p_find.add_argument("status", nargs="?", default="FAIL")

    p_sig = sub.add_parser("complete_discipline", help="Sign off a discipline")
    p_sig.add_argument("slug")
    p_sig.add_argument("discipline")

    p_cmp = sub.add_parser("complete_project", help="Final project sign-off")
    p_cmp.add_argument("slug")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "init":
        state = init(args.slug, args.name)
        print(f"Initialized '{state['name']}' [{state['slug']}] at {_state_path(args.slug, DEFAULT_STATE_DIR)}")

    elif args.command == "list":
        projects = list_projects()
        if not projects:
            print("No projects.")
        for p in projects:
            print(f"  {p['slug']:20s}  {p['status']:15s}  {p['name']}")

    elif args.command == "status":
        state = load(args.slug)
        print(json.dumps(state, indent=2, default=str))

    elif args.command == "add_discipline":
        layers = [l.strip() for l in args.layers.split(",") if l.strip()]
        state = add_discipline(args.slug, args.discipline, layers)
        print(f"Added discipline '{args.discipline}' with layers: {', '.join(layers)}")

    elif args.command == "set_layer_done":
        state = set_layer_done(args.slug, args.discipline, args.layer)
        print(f"Layer '{args.layer}' in '{args.discipline}' marked DONE.")

    elif args.command == "add_finding":
        state = add_finding(args.slug, args.discipline, args.text, args.status)
        print(f"Added finding to '{args.discipline}': [{args.status.upper()}] {args.text}")

    elif args.command == "complete_discipline":
        state = complete_discipline(args.slug, args.discipline)
        print(f"Discipline '{args.discipline}' signed off.")

    elif args.command == "complete_project":
        state = complete_project(args.slug)
        print(f"Project '{state['name']}' marked COMPLETED.")
        print(f"Repo: {state['repo_path']}")


if __name__ == "__main__":
    main()



