# Current Priorities

## 1. Strategic direction

Human Engine is currently in a phase of stabilization and simplification.

Key decision:
focus on a reliable deterministic core first, and treat AI as an external or experimental layer.

The goal is not to build "AI-first", but to build a correct system with optional AI augmentation.

---

## 2. Immediate priorities (now)

### 2.1 Simplify backend

- remove or disable AI endpoints from backend:
  - /ai/chat
  - /ai/task-from-idea
  - /ai/explain-metric
  - /ai/qna-docs (temporary)
- remove Ollama service from docker-compose
- keep backend focused on:
  - data ingestion
  - storage
  - deterministic services
  - API

---

### 2.2 Preserve deterministic logic

- ride briefing must remain deterministic
- readiness logic must remain explicit and inspectable
- no LLM inside core decision-making

---

### 2.3 Clean architecture boundaries

Separate clearly:

Human Engine core:
- backend
- postgres
- domain logic
- deterministic outputs

AI / RAG:
- separate tool or service
- not required for system to function

---

## 3. RAG direction (experimental)

RAG is currently treated as a developer tool, not a product feature.

### 3.1 Move RAG to local environment (Mac)

- build RAG outside of main backend
- run locally for fast iteration
- index:
  - docs
  - code
  - later GitHub issues

### 3.2 Goals for RAG v1

- answer questions about the system
- help navigate codebase
- surface relevant documents
- improve developer productivity

### 3.3 Non-goals

- do not integrate RAG deeply into backend yet
- do not rely on RAG for product decisions
- do not expose RAG as user-facing feature

---

## 4. Engineering workflow improvement

### 4.1 Introduce AI-assisted development (Codex)

- use Codex in VS Code as coding assistant
- agent works with repo context via:
  - AGENTS.md
  - docs/ai/*
- agent may:
  - read code
  - modify files
  - propose changes

### 4.2 Safety model

- no direct commits to main
- use branches / diffs / PRs
- human review required for all changes

---

## 5. Knowledge management

Move important knowledge from chats into repo:

- product context
- architecture decisions
- system map
- glossary
- open questions

Goal:
repository becomes the single source of truth.

---

## 6. Near-term technical improvements

### Backend

- keep services simple and explicit
- avoid unnecessary abstractions
- improve data models step by step
- maintain clear API contracts

### Data

- ensure clean ingestion pipelines
- store raw events reliably
- build toward reproducibility

---

## 7. What to avoid

- over-engineering infrastructure
- premature microservices
- embedding AI into every feature
- replacing logic with prompts
- building autonomous agents with write access too early

---

## 8. Next milestone

A stable system where:

- backend runs without AI dependencies
- core logic is deterministic and testable
- RAG exists as a separate working tool on Mac
- Codex is used for controlled code changes
- repository contains structured product knowledge

---

## 9. Longer-term direction (not now)

Later, reconsider:

- integrating RAG as a service
- controlled AI endpoints
- agent actions (issue creation, PR automation)
- hybrid model (local + external AI)

Only after core system is stable.