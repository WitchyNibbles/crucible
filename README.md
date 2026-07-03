# crucible

Audit-driven autonomous software development workflow.

One intake gate. Zero intervention during development. One delivery gate.

```text
CTO
 └── Discipline Leads (architect, engineering, qa, devops)
      └── Layer Specialists (api, services, ui, test-automation, ci, ...)
           └── Language Specialists (Python, TypeScript, Go, ...)
```

Every tier audits its direct reports before passing work up. FAIL findings are blocking. "Works for this task" is not a pass condition.

## Install

```bash
git clone https://github.com/<you>/crucible.git
cd crucible
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Quick Start

```bash
# Initialize a project
crucible init myapp "My Application"

# Register disciplines and layers
crucible add_discipline myapp architect "data-model,api-contract"
crucible add_discipline myapp engineering "backend,frontend"

# Mark layers complete
crucible set_layer_done myapp architect data-model

# Record audit findings
crucible add_finding myapp architect "Missing auth on API" FAIL
crucible add_finding myapp architect "Auth implemented" FIXED

# Sign off discipline (requires zero open FAIL findings)
crucible complete_discipline myapp architect

# Final project completion (requires all disciplines signed off)
crucible complete_project myapp
```

## Python API

```python
from crucible import init, list_projects, load, save
from crucible import add_discipline, set_layer_done, add_finding
from crucible import complete_discipline, complete_project

# Create project
state = init("myapp", "My Application")

# Register a discipline
add_discipline("myapp", "architect", ["data-model", "api-contract"])

# Mark layer done
set_layer_done("myapp", "architect", "data-model")

# Add finding
add_finding("myapp", "architect", "Missing auth", "FAIL")
add_finding("myapp", "architect", "Auth fixed", "FIXED")

# Sign off and complete
complete_discipline("myapp", "architect")
complete_project("myapp")
```

## Project Structure

```
/home/<user>/projects/<slug>/          # Generated project repo
~/.crucible/state/<slug>.json         # Project state (across sessions)
~/.crucible/log/<slug>/run.log        # Append-only audit trail
```

## State Fields

- `slug`, `name`, `created_at`, `updated_at`
- `status`: `INTAKE` → `EXECUTING` → `COMPLETED`
- `requirements_path`: path to the approved Requirements & Architecture doc
- `max_audit_rounds`: default 3
- `disciplines`: dict of discipline → {layers, findings, sign_off}
- `repo_path`: where the generated repo lives
- `history`: append-only event log

## Hermes Skill

The repo includes a Hermes Agent skill at:

```
skills/software-development/cto-dev-team/
  SKILL.md                    # Main contract + workflow triggers
  references/protocol.md      # Intake protocol (reverse prompting)
  references/role-specs.md    # Tier-specific behavioral contracts
  references/audit-loop.md    # Quality gate enforcement
  scripts/state.py            # CLI shim (thin wrapper around crucible API)
  scripts/validate_skill.py   # Skill validator
```

Load it in Hermes with `/skill cto-dev-team`.

## Long-running Projects

Because subagents are not durable across sessions, use one of:

- **Single session** (recommended for <6h): block until done
- **Cron heartbeat**: re-invoke every N hours, pick up from state
- **Background loop**: run until `crucible status <slug>` shows COMPLETED

## License

MIT
