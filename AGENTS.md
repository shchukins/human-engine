# Human Engine - AGENTS.md

## 1. Purpose of this repository

Human Engine is a system for analyzing training data, estimating athlete state, evaluating readiness, and supporting workout decisions.

At the current stage, the deterministic product core is the priority.
AI-related features are experimental unless explicitly marked as production-ready.

## 2. Product boundaries

The agent must respect the following architectural boundary:

### AI / LLM may do
- generate text
- explain metrics
- transform rough ideas into structured tasks
- answer grounded questions using indexed documentation
- help with documentation and developer productivity

### AI / LLM must not do
- invent physiology formulas
- replace readiness logic
- replace deterministic product logic
- introduce hidden decision-making into training recommendations
- silently change domain meaning

## 3. Current architecture principles

- Human Engine core should remain deterministic where possible.
- Ride briefing is deterministic and should not be re-implemented as free-form LLM generation.
- RAG is currently an auxiliary knowledge layer, not the product core.
- Product logic, scoring, readiness, and metrics should remain explicit and inspectable.
- Prefer simple architecture over clever architecture.

## 4. Repo working rules

When making changes:
- read relevant files before editing
- prefer minimal and local changes
- preserve existing API compatibility unless the task explicitly allows breaking changes
- do not rename files, modules, endpoints, or tables without clear reason
- do not add new infrastructure services unless necessary
- do not add new dependencies unless justified

## 5. Code organization expectations

Prefer these directions:
- business logic in services
- request/response schema clarity
- deterministic formatting where the output must be stable
- AI integration behind clearly named service boundaries
- avoid mixing AI prompt logic with deterministic product logic when they should stay separate

## 6. Work style

For non-trivial tasks:
1. inspect the existing implementation
2. explain the intended change briefly
3. make the change
4. run the narrowest useful verification
5. summarize what changed and any follow-up risks

If the task is ambiguous, ask targeted questions only when truly necessary.
If the request is clear enough, make the best grounded change directly.

## 7. Testing and verification

Before finishing:
- run the narrowest relevant checks
- prefer targeted verification over unrelated broad changes
- if tests are not available, state what was verified manually

Do not claim success without verification.

## 8. Constraints and do-not rules

Do not:
- leak secrets from .env, dumps, or private files
- commit local backups or generated data dumps
- commit experimental data unless explicitly requested
- rewrite large parts of the system when a smaller change is sufficient
- replace deterministic behavior with probabilistic behavior without explicit instruction

## 9. Context files to read when relevant

Before making product or architecture changes, consult:
- docs/ai/PRODUCT_CONTEXT.md
- docs/ai/SYSTEM_MAP.md
- docs/ai/ARCHITECTURE_DECISIONS.md
- docs/ai/CURRENT_PRIORITIES.md
- docs/ai/OPEN_DECISIONS.md
- docs/ai/GLOSSARY.md

## 10. Definition of done

A task is done when:
- the requested change is implemented
- the change fits the existing architecture
- verification was run
- outputs remain stable where stability matters
- important assumptions and risks are clearly stated
