# Audit Loop — Enforcement Mechanism

This is the hard quality gate. Every agent in the waterfall runs this before passing
work up. "Works for this task" is not acceptable.

---

## The Contract

There are exactly two outcomes of an audit:

1. **`[PASS]`** — every assigned artifact is present, correct, and complete.
2. **`[FAIL]` with findings** — a list of blocking issues, each with:
   - Severity: `CRITICAL` (blocks sign-off) or `RECOMMENDED` (improvements)
   - File path + relevant line or region
   - What is wrong
   - How to fix it (when possible)

An audit report with even one `CRITICAL` finding is a hard FAIL. Pass upward only
when findings is truly empty.

---

## Audit Checklist (all tiers)

### Completeness
- [ ] Every file listed in the task brief is present
- [ ] No placeholder comments, stubs, or `TODO` without an issue tracker reference
- [ ] Every requirement mapped to at least one artifact (traceability)

### Correctness
- [ ] Code compiles / lints / type-checks on the target runtime
- [ ] All tests in the suite run and pass (verified by actually running them)
- [ ] Imports and dependencies resolve
- [ ] Schemas match the contract established by upstream tiers

### Consistency
- [ ] Naming aligns with architecture decisions in the requirements doc
- [ ] Cross-layer boundaries honor the interfaces agreed between layers
- [ ] Error handling paths match the error model in the requirements doc
- [ ] Auth/authz calls are present where required and not present where not

### Hygiene
- [ ] No hardcoded secrets, API keys, or environment-specific configs
- [ ] README present for every deliverable component
- [ ] Deployment-relevant env vars and secrets are documented as required inputs
- [ ] Shell scripts are executable, have shebangs, and contain `set -e`

---

## Loop Mechanics

```
Round 1:
  Child produces artifacts.
  Supervisor audits: if pass → sign off. if fail → return findings to child.

Round N (N > 1, N ≤ max_rounds):
  Child receives previous failure findings + any new failing context.
  Child fixes and resubmits.
  Supervisor re-audits.

Round = max_rounds + 1:
  Escalate to parent's supervisor with:
  - full history
  - the persistent failure reason
  - recommendation: re-task with simpler scope, replace agent, or escalate to CTO
```

**max_rounds** defaults to 3. This is configurable but never higher than 5.

---

## Supervisor Interventions

An agent may need to:

- **Replace a stuck subagent.** If a child hits max_audit_rounds, kill, spawn fresh.
  The fresh agent gets the original task brief + the full failure history + explicit
  instructions not to repeat the prior failure pattern.

- **Re-scope a task.** If a task cannot be completed within the max-round budget, the
  layer lead (or discipline lead) may split the task into smaller sub-tasks and re-spawn.
  The new scope must be tighter — shrinking the surface of the failing component.

- **Escalate to CTO.** When re-scoping is impossible and re-spawning failed, escalate
  with the failure history and recommend whether this is a spec gap, a modeling issue,
  or a hard implementation dead-end.

- **Escalate for requirement ambiguities.** If the audit surfaces a direct conflict
  between the artifact and the requirements doc, do NOT patch over it. Report to CTO
  immediately; only the CTO can update the requirements doc.

---

## Audit Report Template

````abcd
[AUDIT REPORT]
Discipline: <name> | Layer: <name> | Round: <N> | Status: <PASS | FAIL>

## Traceability
| Req ID | Artifact | Status |
|---------|----------|--------|
| REQ-001 | backend/api/users.py | MET |
| REQ-001 | tests/test_users_api.py | MET |
| REQ-002 | backend/services/auth.py | NOT_FOUND |

## Findings
CRITICAL:
- [F01] backend/models/user.py missing `email` field required by REQ-003.
  File: ~/projects/foo/backend/models/user.py, line 14.
  Fix: add `email: str` field with validation.

RECOMMENDED:
- [R01] Logging is missing in the retry handler in backend/services/payment.py.

## Tests Run
- pytest tests/ — PASS (14/14)
- mypy backend/ — FAIL (2 errors, see above)

## Verdict
FAIL. Blocking: F01. Resubmit after fixing F01.
````

---

## Anti-patterns (immediate FAIL on the audit itself, not just flagged)

- An audit report that classifies a failing artifact as `[PASS]`.
- An audit report with vague findings ("code quality issues" without specifics).
- An audit that skipped running the test suite.
- An audit run but the agent never read the actual files (hallucinated status).
- Correction passes with no explanation of what changed or why.

If any audit is found to be fraudulent (i.e., claiming pass when artifacts were clearly
broken), the supervising agent must restart the current phase with the original task brief
plus a stricter correction history.
