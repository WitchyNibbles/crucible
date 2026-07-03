#!/usr/bin/env python3
"""Validate a Hermes skill SKILL.md file against the authoring contract.

Usage:
    python3 validate_skill.py <path/to/SKILL.md>

Checks:
  - Frontmatter shape: starts with ---, closes with ---
  - Required keys: name, description, version, author, license, metadata
  - Limits: name <= 64 chars, description <= 1024 chars, file <= 100 000 chars
  - metadata.hermes.tags list and metadata.hermes.related_skills list present
  - Non-empty body after closing frontmatter fence

Exit codes:
  0 - all checks passed
  1 - validation failed
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_CONTENT_LENGTH = 100_000


def _die(msg: str) -> int:
    print(f"FAIL: {msg}", file=sys.stderr)
    return 1


def _ok(msg: str) -> None:
    print(f"OK: {msg}")


def _load_yaml_block(content: str) -> tuple[dict[str, object], int]:
    if not content.startswith("---"):
        raise ValueError("File does not start with '---'.")
    m = re.search(r"\n---\s*\n", content[3:])
    if not m:
        raise ValueError("Closing '---' fence not found.")
    block = content[3 : m.start() + 3]
    try:
        import yaml as _yaml

        return _yaml.safe_load(block) or {}, m.start() + 3 + 3
    except ImportError:
        return {}, m.start() + 3 + 3


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv[1:]
    if not argv:
        print("Usage: validate_skill.py <SKILL.md>", file=sys.stderr)
        return 1

    path = Path(argv[0]).resolve()
    if not path.exists():
        return _die(f"File not found: {path}")

    content = path.read_text(encoding="utf-8")

    if len(content) > MAX_CONTENT_LENGTH:
        return _die(f"File too large: {len(content)} chars (max {MAX_CONTENT_LENGTH}).")

    try:
        fm, after_fm = _load_yaml_block(content)
    except ValueError as exc:
        return _die(str(exc))

    if not isinstance(fm, dict):
        return _die("Frontmatter did not parse as a YAML mapping.")

    for key in ("name", "description", "version", "author", "license", "metadata"):
        if key not in fm:
            return _die(f"Missing required frontmatter key: '{key}'.")

    name = fm.get("name", "")
    if not isinstance(name, str) or not name:
        return _die("'name' must be a non-empty string.")
    if len(name) > MAX_NAME_LENGTH:
        return _die(f"'name' too long: {len(name)} chars (max {MAX_NAME_LENGTH}).")
    if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", name):
        return _die(
            f"'name' must be lowercase, hyphen-separated, alphanumeric (got: {name})."
        )

    description = fm.get("description", "")
    if not isinstance(description, str) or not description:
        return _die("'description' must be a non-empty string.")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return _die(
            f"'description' too long: {len(description)} chars (max {MAX_DESCRIPTION_LENGTH})."
        )

    metadata = fm.get("metadata")
    if not isinstance(metadata, dict):
        return _die("'metadata' must be a mapping.")
    hermes = metadata.get("hermes")
    if not isinstance(hermes, dict):
        return _die("'metadata.hermes' must be a mapping.")
    for key in ("tags", "related_skills"):
        if key not in hermes:
            return _die(f"Missing metadata.hermes.{key}.")
        val = hermes[key]
        if not isinstance(val, list):
            return _die(f"metadata.hermes.{key} must be a list.")

    body = content[after_fm:].lstrip("\n")
    if not body.strip():
        return _die("Skill body after frontmatter is empty.")

    _ok(f"name='{name}' description_len={len(description)} size={len(content)}")
    _ok("All checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
