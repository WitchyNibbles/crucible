#!/usr/bin/env python3
"""CTO Dev Team — project state manager (standalone wrapper).

For Python usage, import from `crucible` directly:
    from crucible import init, list_projects, add_discipline

Usage:
    python3 state.py init <slug> "<name>"
    python3 state.py list
    python3 state.py status <slug>
    python3 state.py set_requirements <slug> <path>
    python3 state.py add_discipline <slug> <name> <layer1,layer2,...>
    python3 state.py set_layer_done <slug> <discipline> <layer>
    python3 state.py add_finding <slug> <discipline> "<text>" [FAIL|FIXED]
    python3 state.py complete_discipline <slug> <discipline>
    python3 state.py complete_project <slug>

State lives at ~/.crucible/state/<slug>.json.
Logs live at   ~/.crucible/log/<slug>/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STATE_DIR = Path.home() / ".crucible" / "state"
LOG_DIR = Path.home() / ".crucible" / "log"


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_dirs() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)


def _die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _state_path(slug: str) -> Path:
    return STATE_DIR / f"{slug}.json"


def _load(slug: str) -> dict[str, Any]:
    p = _state_path(slug)
    if not p.exists():
        _die(f"No project '{slug}' at {p}")
    with p.open() as f:
        return json.load(f)


def _save(slug: str, state: dict[str, Any]) -> None:
    p = _state_path(slug)
    tmp = p.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(state, f, indent=2, default=str)
    tmp.replace(p)


def _log_event(slug: str, message: str) -> None:
    d = LOG_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    log_file = d / "run.log"
    with log_file.open("a") as f:
        f.write(f"{_utcnow()} | {message}\n")


def _default_state(slug: str, name: str) -> dict[str, Any]:
    return {
        "slug": slug,
        "name": name,
        "created_at": _utcnow(),
        "updated_at": _utcnow(),
        "status": "INTAKE",
        "requirements_path": None,
        "max_audit_rounds": 3,
        "disciplines": {},
        "repo_path": str((Path.home() / "projects" / slug).resolve()),
        "history": [],
    }


def cmd_init(args: argparse.Namespace) -> None:
    _ensure_dirs()
    p = _state_path(args.slug)
    if p.exists():
        _die(f"Project '{args.slug}' already exists at {p}")
    state = _default_state(args.slug, args.name)
    _save(args.slug, state)
    _log_event(args.slug, f"INIT name={args.name}")
    print(f" Initialized '{args.name}' [{args.slug}] at {p}")


def cmd_list(_: argparse.Namespace) -> None:
    _ensure_dirs()
    files = sorted(STATE_DIR.glob("*.json"))
    if not files:
        print("No projects.")
        return
    for f in files:
        st = json.loads(f.read_text())
        print(f"  {st['slug']:20s}  {st.get('status','?'):15s}  {st.get('name','?')}")


def cmd_status(args: argparse.Namespace) -> None:
    st = _load(args.slug)
    print(json.dumps(st, indent=2, default=str))


def cmd_set_requirements(args: argparse.Namespace) -> None:
    p = Path(args.path)
    if not p.exists():
        _die(f"Requirements file not found: {args.path}")
    st = _load(args.slug)
    st["requirements_path"] = str(p.resolve())
    st["updated_at"] = _utcnow()
    _save(args.slug, st)
    _log_event(args.slug, f"SET_REQUIREMENTS path={p}")
    print(f" Requirements set: {p}")


def cmd_add_discipline(args: argparse.Namespace) -> None:
    layers = [l.strip() for l in args.layers.split(",") if l.strip()]
    st = _load(args.slug)
    if args.discipline in st["disciplines"]:
        _die(f"Discipline '{args.discipline}' already exists.")
    st["disciplines"][args.discipline] = {
        "layers": {l: {"status": "PENDING"} for l in layers},
        "findings": [],
        "sign_off": None,
    }
    st["updated_at"] = _utcnow()
    _save(args.slug, st)
    _log_event(args.slug, f"ADD_DISCIPLINE name={args.discipline} layers={layers}")
    print(f" Added discipline '{args.discipline}' with layers: {', '.join(layers)}")


def cmd_set_layer_done(args: argparse.Namespace) -> None:
    st = _load(args.slug)
    disc = st["disciplines"].get(args.discipline)
    if disc is None:
        _die(f"Discipline '{args.discipline}' not found.")
    assert disc is not None
    if args.layer not in disc["layers"]:
        _die(f"Layer '{args.layer}' not found in '{args.discipline}'.")
    disc["layers"][args.layer]["status"] = "DONE"
    disc["layers"][args.layer]["completed_at"] = _utcnow()
    st["updated_at"] = _utcnow()
    _save(args.slug, st)
    _log_event(args.slug, f"LAYER_DONE discipline={args.discipline} layer={args.layer}")
    print(f" Layer '{args.layer}' in '{args.discipline}' marked DONE.")


def cmd_add_finding(args: argparse.Namespace) -> None:
    status = (args.status or "FAIL").upper()
    if status not in ("FAIL", "FIXED"):
        _die("Status must be FAIL or FIXED")
    st = _load(args.slug)
    disc = st["disciplines"].get(args.discipline)
    if disc is None:
        _die(f"Discipline '{args.discipline}' not found.")
    assert disc is not None
    disc["findings"].append({
        "text": args.text,
        "status": status,
        "at": _utcnow(),
    })
    st["updated_at"] = _utcnow()
    _save(args.slug, st)
    print(f" Added finding to '{args.discipline}': [{status}] {args.text}")


def cmd_complete_discipline(args: argparse.Namespace) -> None:
    st = _load(args.slug)
    disc = st["disciplines"].get(args.discipline)
    if disc is None:
        _die(f"Discipline '{args.discipline}' not found.")
    assert disc is not None
    open_findings = [f for f in disc["findings"] if f["status"] == "FAIL"]
    if open_findings:
        _die(
            f"Cannot sign off '{args.discipline}': "
            f"{len(open_findings)} open FAIL findings."
        )
    disc["sign_off"] = _utcnow()
    st["updated_at"] = _utcnow()
    _save(args.slug, st)
    _log_event(args.slug, f"DISCIPLINE_SIGN_OFF name={args.discipline}")
    print(f" Discipline '{args.discipline}' signed off.")


def cmd_complete_project(args: argparse.Namespace) -> None:
    st = _load(args.slug)
    unsigned = [n for n, d in st["disciplines"].items() if not d.get("sign_off")]
    if unsigned:
        _die(f"Cannot complete project: unsigned disciplines: {unsigned}")
    open_findings = [
        f for d in st["disciplines"].values()
        for f in d["findings"]
        if f["status"] == "FAIL"
    ]
    if open_findings:
        _die(f"Cannot complete project: {len(open_findings)} open FAIL findings.")
    st["status"] = "COMPLETED"
    st["completed_at"] = _utcnow()
    st["updated_at"] = _utcnow()
    _save(args.slug, st)
    _log_event(args.slug, "PROJECT_COMPLETED")
    print(f" Project '{st['name']}' marked COMPLETED.")
    print(f" Repo: {st['repo_path']}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="crucible-state",
        description="crucible — project state manager",
    )
    sub = parser.add_subparsers(dest="command")

    p_init = sub.add_parser("init", help="Create a new project")
    p_init.add_argument("slug")
    p_init.add_argument("name")

    sub.add_parser("list", help="List all projects")

    p_status = sub.add_parser("status", help="Show project state")
    p_status.add_argument("slug")

    p_reqs = sub.add_parser("set_requirements", help="Link requirements doc")
    p_reqs.add_argument("slug")
    p_reqs.add_argument("path")

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

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "init": cmd_init,
        "list": cmd_list,
        "status": cmd_status,
        "set_requirements": cmd_set_requirements,
        "add_discipline": cmd_add_discipline,
        "set_layer_done": cmd_set_layer_done,
        "add_finding": cmd_add_finding,
        "complete_discipline": cmd_complete_discipline,
        "complete_project": cmd_complete_project,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
