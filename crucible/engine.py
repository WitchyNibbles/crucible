"""crucible engine — orchestration framework for the CTO dev team waterfall.

This module does NOT call delegate_task itself. It generates tier-specific prompts,
tracks workflow state, manages the audit loop, and exposes a clean API that the
primary CTO session uses to drive the full waterfall.

Typical CTO usage inside a Hermes session:

    engine = WorkflowEngine("myapp")
    engine.init_disciplines({
        "architect": ["data-model", "api-contract"],
        "engineering": ["backend", "frontend"],
        "qa": ["test-architecture", "test-automation"],
        "devops": ["ci", "deploy"],
    })

    # Drive each discipline through the waterfall
    for disc in engine.disciplines:
        result = engine.run_discipline(disc)
        if result["status"] == "FAIL":
            # escalate or retry
            ...

    engine.complete_project()
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from crucible import (
    add_discipline,
    add_finding,
    complete_project,
    init,
    load,
    set_layer_done,
)

DEFAULT_STATE_DIR = Path.home() / ".crucible" / "state"
DEFAULT_LOG_DIR = Path.home() / ".crucible" / "log"
MAX_AUDIT_ROUNDS = 3


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


class WorkflowEngine:
    """Orchestrates a project through the CTO dev team waterfall."""

    def __init__(
        self,
        slug: str,
        name: str | None = None,
        state_dir: Path | str | None = None,
        log_dir: Path | str | None = None,
    ) -> None:
        self.slug = slug
        self.state_dir = Path(state_dir) if state_dir else DEFAULT_STATE_DIR
        self.log_dir = Path(log_dir) if log_dir else DEFAULT_LOG_DIR
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Load or init
        state_path = self.state_dir / f"{slug}.json"
        if state_path.exists():
            self.state = load(slug, state_dir=self.state_dir)
            self.name = self.state.get("name", slug)
        else:
            if name is None:
                name = slug.replace("-", " ").replace("_", " ").title()
            self.state = init(slug, name, state_dir=self.state_dir, log_dir=self.log_dir)
            self.name = name

    # ------------------------------------------------------------------ #
    # Discipline management
    # ------------------------------------------------------------------ #

    def init_disciplines(self, spec: dict[str, list[str]]) -> dict[str, Any]:
        """Register disciplines and their layers.

        Args:
            spec: {discipline_name: [layer_names]}

        Returns:
            Updated project state
        """
        for disc, layers in spec.items():
            add_discipline(self.slug, disc, layers, state_dir=self.state_dir, log_dir=self.log_dir)
        return self.state

    # ------------------------------------------------------------------ #
    # Prompt generation
    # ------------------------------------------------------------------ #

    def discipline_lead_prompt(self, discipline: str, requirements: str) -> str:
        """Generate the prompt for a discipline lead agent."""
        layers = self._layers_for(discipline)
        return f"""You are the **{discipline} Lead** in a recursive software development waterfall.

PROJECT REQUIREMENTS:
{requirements}

YOUR DISCIPLINE: {discipline}
YOUR LAYERS: {', '.join(layers)}

YOUR TASK:
1. Break the requirements into layer-specific work packages.
2. For each layer, produce a detailed work package with:
   - Objective
   - Acceptance criteria
   - Deliverable format (file paths, schemas, configs, etc.)
3. Identify cross-cutting concerns within your discipline.
4. Produce an audit plan for each layer.

OUTPUT FORMAT (strict):
## {discipline} Work Packages
### Layer: <name>
- Objective: ...
- Criteria: ...
- Deliverables: ...
- Audit plan: ...
"""

    def layer_specialist_prompt(
        self, discipline: str, layer: str, work_package: str, languages: list[str]
    ) -> str:
        """Generate the prompt for a layer specialist."""
        return f"""You are the **{discipline} → {layer} Specialist** in a recursive software development waterfall.

WORK PACKAGE FROM YOUR DISCIPLINE LEAD:
{work_package}

SUPPORTED LANGUAGES: {', '.join(languages)}

YOUR TASK:
1. Break the work package into per-language implementation tasks.
2. For each language, produce:
   - Implementation plan (files, modules, interfaces)
   - Test plan (unit, integration, edge cases)
   - Acceptance criteria
3. Identify dependencies between language tasks.

OUTPUT FORMAT (strict):
## {discipline}/{layer} Implementation Plan
### Language: <name>
- Plan: ...
- Files: ...
- Tests: ...
- Acceptance criteria: ...
"""

    def language_specialist_prompt(
        self, discipline: str, layer: str, language: str, task: str
    ) -> str:
        """Generate the prompt for a language specialist (leaf agent)."""
        return f"""You are the **{discipline} → {layer} → {language} Specialist** — a leaf implementer in a recursive software development waterfall.

YOUR TASK FROM YOUR LAYER LEAD:
{task}

INSTRUCTIONS:
1. Write production-quality code.
2. Include tests.
3. Include docstrings / comments where non-obvious.
4. Include any config files, schemas, or manifests needed.
5. Follow the acceptance criteria exactly.

OUTPUT FORMAT:
- File paths and their contents (use ```language blocks)
- Test commands
- Any setup/install steps
"""

    def audit_prompt(self, tier: str, work: str, spec: str) -> str:
        """Generate the audit prompt for any tier."""
        return f"""You are auditing **{tier}** output against its assigned delivery spec.

WORK PRODUCT:
{work}

DELIVERY SPEC:
{spec}

AUDIT CHECKLIST (must check ALL):
- Functional completeness: nothing missing from the spec
- Correctness: code compiles/runs, tests pass
- Consistency: aligns with architecture and upper-tier agreements
- Completeness: docs, types, error handling, edge cases, configs
- Hygiene: no placeholders, no broken imports, no TODO stubs

OUTPUT FORMAT (strict):
## Audit Result: [PASS] or [FAIL]
- Missing: ...
- Defects: ...
- Inconsistencies: ...
- Hygiene issues: ...
- Remediation: ...
"""

    def escalation_prompt(self, tier: str, failure_summary: str) -> str:
        """Generate escalation prompt when an agent is stuck."""
        return f"""The **{tier}** agent is stuck after {MAX_AUDIT_ROUNDS} audit cycles.

FAILURE SUMMARY:
{failure_summary}

ACTION REQUIRED:
1. Analyze what went wrong.
2. Propose a corrective approach.
3. Spawn a fresh replacement agent with the corrective approach.
4. Do NOT repeat the same strategy that failed.
"""

    # ------------------------------------------------------------------ #
    # Audit helpers
    # ------------------------------------------------------------------ #

    def record_finding(
        self,
        discipline: str,
        layer: str,
        text: str,
        status: str = "FAIL",
    ) -> dict[str, Any]:
        """Record an audit finding in project state."""
        return add_finding(
            self.slug,
            discipline,
            text,
            status,
            state_dir=self.state_dir,
            log_dir=self.log_dir,
        )

    def mark_layer_done(self, discipline: str, layer: str) -> dict[str, Any]:
        """Mark a layer as completed."""
        return set_layer_done(
            self.slug, discipline, layer, state_dir=self.state_dir, log_dir=self.log_dir
        )

    # ------------------------------------------------------------------ #
    # State helpers
    # ------------------------------------------------------------------ #

    def _layers_for(self, discipline: str) -> list[str]:
        state = load(self.slug, state_dir=self.state_dir)
        disc = state.get("disciplines", {}).get(discipline, {})
        return list(disc.get("layers", {}).keys())

    def status(self) -> dict[str, Any]:
        """Return full project state."""
        return load(self.slug, state_dir=self.state_dir)

    def complete_project(self) -> dict[str, Any]:
        """Final project sign-off."""
        return complete_project(self.slug, state_dir=self.state_dir, log_dir=self.log_dir)

    # ------------------------------------------------------------------ #
    # Workflow runner
    # ------------------------------------------------------------------ #

    def run_discipline(self, discipline: str, requirements: str) -> dict[str, Any]:
        """Drive one discipline through the full waterfall.

        This is the method the CTO calls for each discipline. It returns
        the final state — including all findings, sign-offs, and any
        remaining issues.
        """
        layers = self._layers_for(discipline)
        result: dict[str, Any] = {
            "discipline": discipline,
            "layers": {},
            "findings_count": 0,
            "status": "PENDING",
        }

        # Phase 1: Discipline lead decomposes into layer tasks
        disc_lead_prompt = self.discipline_lead_prompt(discipline, requirements)

        # The CTO session calls delegate_task here with disc_lead_prompt
        # disc_lead_output = delegate_task(goal=disc_lead_prompt, ...)
        # For now, we store the prompt and let the CTO session execute it.
        result["discipline_lead_prompt"] = disc_lead_prompt
        result["layer_prompts"] = {}

        for layer in layers:
            # Phase 2: Layer specialist prompt
            wp_ref = f"Work package from {discipline} lead (see their output)"
            layer_prompt = self.layer_specialist_prompt(
                discipline, layer, wp_ref, ["python", "typescript"]  # default languages
            )
            result["layer_prompts"][layer] = layer_prompt

            # Phase 3: Language specialist prompts (per language)
            result["layer_prompts"][layer + "_languages"] = {}
            for lang in ["python", "typescript"]:
                lang_prompt = self.language_specialist_prompt(
                    discipline, layer, lang, f"Implementation task for {layer} in {lang}"
                )
                result["layer_prompts"][layer + "_languages"][lang] = lang_prompt

            # Audit prompts
            result["layer_prompts"][layer + "_audit"] = self.audit_prompt(
                f"{discipline}/{layer}", "<work output>", "<layer spec>"
            )

        result["status"] = "READY"
        return result

    def to_json(self) -> str:
        """Serialize the workflow plan for the CTO session."""
        plan = {
            "slug": self.slug,
            "name": self.name,
            "state": self.status(),
            "disciplines": {},
        }
        for disc in self.status().get("disciplines", {}):
            plan["disciplines"][disc] = self.run_discipline(disc, "<requirements>")
        return json.dumps(plan, indent=2)
