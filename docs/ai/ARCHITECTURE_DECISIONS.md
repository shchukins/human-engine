# Architecture Decisions

## AI boundaries

Decision:
LLM must not replace deterministic product logic.

Reason:
The system must remain inspectable and controllable.

## Ride briefing

Decision:
Ride briefing is deterministic.

Reason:
The output must be stable, predictable, and free from hallucinations.

## RAG

Decision:
RAG is a knowledge layer for documentation and code understanding.

Reason:
It is useful for developer productivity, but should remain separated from core product decision-making.

## Service philosophy

Decision:
Prefer smaller, explicit services and minimal architecture over premature complexity.

Reason:
Human Engine is still evolving and benefits from simplicity.