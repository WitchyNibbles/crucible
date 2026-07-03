---
name: cto-dev-team
description: >
  Use when the user wants a full autonomous dev team to build a complete software project
  from intake to review-ready repo. Provides role discipline simulation via Hermes delegate_task,
  recursive reverse-prompt intake, multi-layer audit loops (CTO → discipline lead → layer lead →
  language specialist), persistent per-project state, and zero human intervention between intake
  approval and final delivery.
version: 1.0.0
author: Samantha
license: MIT
metadata:
  hermes:
    tags: [autonomous, multi-agent, development, waterfall, audit, intake]
    related_skills: [hermes-agent, hermes-agent-skill-authoring, plan, requesting-code-review]
---

# CTO Dev Team — Autonomous Recursive Software Factory

## Overview

This skill implements a fully autonomous software development workflow: one human approval gate
at intake, one at delivery, zero intervention in between. The agent (you, acting as CTO)
spawns a recursive team of Hermes subagents structured in three execution layers:

```
CTO (primary session / you)
 └── Discipline Leads (discipline agents - team leads)
      └── Layer Specialists (senior agents - per discipline layer)
           └── Language Specialists (code agents - per layer, per language)
```

Communication flows top-down at dispatch time; findings, audits, corrections, and escalation flow
both directions during the audit loop. Every level audits its direct reports before passing work
up. Audits are mandatory and exhaustive — "works well enough" is not a pass condition.

Output: a git-ready repo under `~/projects/<slugified-name>/` with design docs, code, tests,
CI/CD config, and deployment manifests. Deliverable is considered ready when every non-leaf
agent signs off on every artifact.

**Persistent state** lives at `~/.hermes/cto-state/<project-slug>.json`. The state file is the
project's memory across sessions.

## When to Use

- User asks you to "build X" as a complete, production-ready project
- User wants zero input loops during actual development
- User wants audit-driven quality gates, not "hope it works"
- User wants a deployable repo — not snippets, not a blog post, actual repo they can push to GitHub

Don't use for:
- One-off shell commands or file edits
- Trivial changes to existing repos (use normal Hermes workflow)
- Exploratory research without a build intent

---

## Workflow (end-to-end)

1. **Intake (reverse prompting).** Load `protocol.md` and enter the refinement loop.
   Engage the user with research-backed clarifying questions until every ambiguity is resolved.
   Produce a formal Requirements & Architecture doc.
2. **User approves the Requirements doc.** Pause here and wait for user approval.
   Do NOT proceed until the user explicitly approves.
3. **CTO decomposes.** Break the approved spec into discipline-level work packages.
   Initialize project state via `scripts/state.py init <slug> "<name>"`.
4. **Discipline dispatch.** Spawn discipline lead subagents via `delegate_task` for each domain.
   Each discipline receives the full requirements. They decompose into layer tasks themselves.
5. **Layer dispatch.** Each discipline lead spawns layer specialists for its layers (backend,
   frontend, database, test, ops, etc.).
6. **Language dispatch.** Each layer specialist spawns language specialists for the required
   languages/frameworks. Leaf nodes do the actual code-writing.
7. **Audit loop.** Every agent audits its direct reports before passing work upward.
   Audits are exhaustive. Any finding — functional defect, missing doc, schema inconsistency,
   untested code path, missing manifest — is a blocking issue. The child agent is prompted
   with specific corrections. Loop terminates only on zero blocking findings.
8. **CTO final review.** After all disciplines sign off, the CTO (you) does a final cross-cutting
   review for integration issues, consistency gaps, and project-level requirements alignment.
   Fix any issues found and re-run the full review loop until clean.
9. **Delivery.** Present the finished repo. Tell the user: "Repo is at `~/projects/<slug>/`.
   Review it. If it doesn't match what you asked for, say the word and we'll iterate on intake."

### Adaptation layer

Maximum delegation depth is **2** (`discipline → layer → language`) to avoid context bloat.
If a task is small enough that discipline + layer covers it, skip the language tier and have the
layer specialist write the code directly.

---

## Intake Protocol (reverse prompting)

**Load this every time the user asks you to start a new project.**

1. Read `protocol.md` entirely before asking the first question.
2. Do research on existing prior work, industry patterns, libraries, and best practices relevant
   to the project.
3. Ask focused, specific questions that eliminate ambiguity — not generic "tell me more."
4. Present the draft Requirements & Architecture doc for user review.
5. Iterate until the user approves.
6. **STOP. Wait for explicit approval.** Do not proceed until approved.

### Key intake questions (non-exhaustive - reference protocol.md for the full list)

Function & non-functional requirements, target stack, scaling assumptions, auth/authz model,
data model, failover/backup, deployment target, CI/CD platform, observability requirements,
licensing constraints, known integrations/algorithms, failure tolerance.

Full protocol with example questions, research guidance, and doc template lives in
`references/protocol.md`.

---

## Role System

Detailed specifications for every tier live in `references/role-specs.md`. In brief:

### Discipline Leads
**Role:** Engineering manager equivalents. Receive full requirements. Decompose into
layer-level work packages. Audit layer output. Escalate integration and cross-cutting
issues to CTO.

Disciplines (default set, extend as needed):
- **architect** — System design, data model, API contracts, technical decisions
- **engineering** — Implementation (backend, frontend, infrastructure, data)
- **qa** — Test strategy, test suites, coverage analysis, acceptance criteria
- **devops** — CI/CD, deployment manifests, infrastructure as code, monitoring

### Layer Specialists
**Role:** Seniors who translate discipline directives into executable plans for each
technical layer. Write or coordinate language specialists. Audit language output before
passing to their discipline lead.

Common layers (per-domain):
- Backend: `api`, `services`, `data`
- Frontend: `ui`, `state-management`, `routing`
- QA: `test-architecture`, `test-automation`, `test-manual`
- DevOps: `ci`, `deploy`, `observability`

### Language Specialists
**Role:** Grass-roots implementers. Write tests and code, produce module-level docs.
Direct supervised by their layer specialist. They do NOT audit — they produce.

---

## Audit Loop (every level)

**This is non-negotiable.** Every agent in the chain runs an audit before passing work upward:

1. Pull the work product and the assigned delivery spec.
2. Run exhaustive review:
   - Functional completeness — nothing missing from the spec
   - Correctness — code compiles/runs, tests pass
   - Consistency — aligns with architecture, naming, interfaces agreed in upper tiers
   - Completeness — docs, types, error handling, edge cases, configs
   - Hygiene — no placeholder comments, no broken imports, no TODO stubs
3. Produce an explicit finding list: `[PASS]` or `[FAIL]` with specific remediation.
4. **Only pass upward on 100% pass.** Any finding means prompt the child agent with
   precise corrections and re-run.
5. Timeout/retry: if an agent gets stuck in a loop (>2 re-audit cycles with no progress),
   kill it, spawn a fresh agent with the same task + accumulated failure context, and reset
   the cycle counter.

Full audit checklist and loop mechanics in `references/audit-loop.md`.

---

## Project State

State is managed by `scripts/state.py` and persisted to
`~/.hermes/cto-state/<project-slug>.json`.

State tracks:
- Project metadata (name, slug, started, status)
- Requirements document
- Disciplines: per-discipline tasks, layer breakdown, completion status
- Audit state: per-level findings count, current audit round, stuck loops
- Deliverable manifest: files generated, paths, sizes
- History log (append-only audit trail)

### State operations (Python one-liners)

```bash
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py init <slug> "<name>"
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py list
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py status <slug>
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py set_requirements <slug> <path>
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py add_discipline <slug> <name> <layer1,layer2,...>
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py add_finding <slug> <discipline> "<text>" [FAIL|FIXED]
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py set_layer_done <slug> <discipline> <layer>
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py complete_discipline <slug> <discipline>
python3 ~/projects/crucible/skills/software-development/cto-dev-team/scripts/state.py complete_project <slug>
```

### Streaming output

Coordinate subagents to write progress directly to:
`~/.hermes/cto-log/<project-slug>/correspondence/<discipline>/<layer>/`

Use `file read/write` to deliver artifact content between tiers. Each agent reads the
spec for its tier, produces output into its assigned file path, and notifies its supervisor.

---

## Chaining: Long-Running Projects

Because subprocess-spawned subagents are **not durable**, long-running projects need
one session to orchestrate everything through the full waterfall.

OPTION A — Single blocking session (recommended for projects under ~6 hours wall time):
- User stays around. CTO orchestrates through the entire cascade.
- Use `delegate_task` + blocking wait for each discipline phase.

OPTION B — Cron-shell session bridge (for multi-day builds):
- Use `cronjob` to re-invoke Hermes every N hours with a continuation prompt that reads
  project state, picks up where execution stopped, and keeps moving.
- State survives arbitrarily long gaps. On each cron tick, the CTO session loads state,
  audits progress, dispatches next pending discipline, continues the waterfall.

OPTION C — Periodic retry until done:
- Use `terminal(background=true, notify_on_complete=true)` to run a script that loops
  through execution cycles, sleeping between them. Terminates when `state.py status` shows
  `status: COMPLETED`.

Your call which pattern; state persistence covers all three.

---

## Safety & Boundaries

- **Skills scope**: this skill encodes the workflow. The actual execution still goes through
  Hermes tools. The skill cannot enforce quality — only the CTO session running it can.
- **No silent execution**: the user must approve requirements. No exception.
- **No ambiguity-forwarding**: if a subagent passes an incomplete artifact, the auditing
  agent must explicitly say so and demand a fix. Pass-through of broken work is a system failure.
- **Cost awareness**: delegate_task on the same free model keeps token cost at zero, but
  wall-clock cost is real. Prefer skill save/load to avoid re-doing research.
- **Failure recovery**: every killing event is logged in the project's state history with
  reason. After a kill, spawn a fresh worker with explicit context that the previous worker failed.

---

## Verification

Run these checks before declaring any authored skill done:

```
scripts/validate_skill.py skills/<category>/<name>/SKILL.md
find skills/<category>/<name>/ -type f | sort
```

The bundled `scripts/validate_skill.py` checks frontmatter shape, required keys, limits,
and body presence inline without requiring the validator. A script causes fewer skipped
checks than inline snippets because it is re-runnable after each edit, catching frontmatter
or size-limit failures before commit/session reload.

## Verification Checklist

- [ ] Intake: requirements doc produced, user approved
- [ ] Project state initialized with correct slug and name
- [ ] Each discipline has at least one layer listed in state
- [ ] Each layer has an assigned language (or skip-reason for leaf agents)
- [ ] Every non-leaf agent produced a written audit (findings list) for its direct reports
- [ ] All findings are either FIXED or documented as accepted risk with user approval
- [ ] Project repo contains README, tests, and runnable build pipeline
- [ ] CTO cross-cutting review completed with zero findings
- [ ] Final state shows `status: COMPLETED`
- [ ] User has been told the repo path and invited to review
