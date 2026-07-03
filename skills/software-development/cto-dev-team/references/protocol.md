# Intake Protocol — Reverse Prompting & Requirements Capture

## Purpose

Eliminate ambiguity before a single line of code is written. The intake phase produces a
formal **Requirements & Architecture Document** that is the single source of truth for every
subagent in the waterfall. Nothing is built until the user approves this document.

---

## Process

1. **Preliminary research** — before asking anything, do web research on:
   - The problem domain (existing solutions, established patterns)
   - Relevant libraries / frameworks / tools for the inferred stack
   - Common failure modes and gotchas for projects of this type
   - Any industry standards, protocols, or specifications that apply

   Cite concrete sources. Research-backed questions are far more productive than
   generic prompts.

2. **Clarifying question round** — ask targeted questions. One question at a time OR
   grouped by topic area (no open-ended "tell me everything" prompts).

3. **Draft Requirements & Architecture doc** — write to the project's state directory
   when it exists, otherwise draft inline.

4. **User review + iterate** — show the doc, wait for feedback, patch, repeat.

5. **Explicit approval gate** — ask for explicit approval. Proceed only on:
   - "Approved"
   - "Go ahead"
   - "LGTM"
   - Any unambiguous positive signal

---

## Document Template

```markdown
# Requirements & Architecture: <Project Name>

## 1. Problem Statement
[Elevator-pitch description. What pain does this solve?]

## 2. Functional Requirements
### 2.1 Core capabilities
- [REQ-001] ...
- [REQ-002] ...

### 2.2 User stories
- As a <role>, I want <action> so that <value>

### 2.3 Workflows
[Sequence or flowchart description of key flows]

## 3. Non-Functional Requirements
- Performance: ...
- Reliability: ...
- Scalability assumptions: ...
- Security/auth model: ...
- Data retention: ...
- Observability: ...

## 4. Architecture
### 4.1 High-level design
[ASCII architecture diagram or description]

### 4.2 Data model
[Entity-relationship description, schemas]

### 4.3 API contracts
[OpenAPI-style: endpoints, request/response shapes]

### 4.4 Technology stack
| Component | Choice | Rationale |
|-----------|--------|-----------|
| Language  | ...    | ...       |
| Framework | ...    | ...       |

## 5. Delivery Criteria
What does "done" look like? List every output expected:
- [ ] Repo scaffolded with README
- [ ] Test suite with coverage >= X%
- [ ] CI/CD pipeline
- [ ] Deployment manifests
- [ ] Documentation

## 6. Out of Scope
Explicit boundaries so subagents don't drift:
- NOT building: ...
- NOT supporting: ...

## 7. Assumptions & Open Items
[Anything still assumed but not yet validated]
```

---

## Question Bank (reference, don't dump as wall-of-text)

Pick 3-5 per round. Group by topic.

### Functional
- What problem does this solve, and who experiences that problem?
- What does the success path look like end-to-end?
- What are the material failure modes?
- What integrations are required (databases, APIs, file systems, queues)?
- What data comes in, what data goes out, what data is stored indefinitely?
- Is there concurrency / multi-user / multi-tenant?

### Non-functional
- What is the expected load (requests/sec, data volume, concurrent users)?
- What is the uptime / durability target?
- What auth/authz model is required?
- What are the compliance constraints (GDPR, SOC2, licensing)?

### Architecture / Stack
- Is there a mandated language, framework, or runtime?
- Is there an existing codebase to conform to, or is this greenfield?
- What is the deployment target (K8s, serverless, VPS, bare metal)?
- What CI/CD tooling is already in use or mandated?
- Are there constraints on external services / vendor lock-in concerns?

### Delivery
- What does "launch" mean? (preview, MVP, production at scale?)
- Who are the operators after handoff?
- What skill level should the codebase leave behind? (self-documenting, lavishly commented?)

---

## Rules

- **Never proceed without approval.** This is a hard gate.
- **No "I'll figure it out later."** If something is unclear, ask. If the user says "I don't
  know yet," document that explicitly in Assumptions & Open Items and move on — but note
  that later changes trigger a new intake.
- **One doc, one source of truth.** Don't scatter requirements across multiple messages.
- **Keep it readable.** Headings, numbered sections, tables. Subagents will read this.
