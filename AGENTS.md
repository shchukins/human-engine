# AGENTS.md

## 1. Purpose

This repository contains Human Engine — a system for analyzing training data and supporting workout decisions.

At the current stage:

> deterministic product core is the priority  
> AI is auxiliary  

---

## 2. Mental model (read first)

Human Engine is:

- a data pipeline  
- a physiology-driven model  
- a readiness evaluation system  
- a deterministic decision-support system  

It is NOT:

- an AI-driven system  
- a black-box model  
- a generative decision engine  

---

## 3. Absolute rules (do not violate)

The following rules have highest priority:

### 3.1 Do NOT replace deterministic logic with AI

Never:

- move calculations into LLM  
- replace formulas with generated text  
- introduce hidden probabilistic behavior  

---

### 3.2 Do NOT change domain meaning

Never:

- invent new physiology logic  
- silently change metric definitions  
- reinterpret readiness logic  

---

### 3.3 Do NOT break architecture boundaries

Core (protected):

- backend  
- database  
- domain logic  

AI (separate):

- explanation  
- text generation  
- documentation  

---

## 4. What AI is allowed to do

AI may:

- generate documentation  
- explain metrics  
- transform ideas into structured tasks  
- help navigate codebase  
- propose code changes  

---

## 5. What AI must NOT do

AI must not:

- implement core logic without explicit instructions  
- introduce new architecture patterns  
- add new services without justification  
- modify critical logic implicitly  

---

## 6. How to make changes

For non-trivial tasks:

1. read relevant files  
2. understand current behavior  
3. propose minimal change  
4. implement  
5. verify  
6. summarize  

---

## 7. Change strategy

Prefer:

- minimal changes  
- local impact  
- explicit logic  
- simple solutions  

Avoid:

- large refactoring without reason  
- renaming core structures  
- adding abstractions prematurely  

---

## 8. Verification

Before finishing:

- verify the change directly  
- check affected paths  
- avoid unrelated modifications  

If verification is not possible:

- state assumptions explicitly  

---

## 9. Safety constraints

Never:

- expose secrets  
- commit generated data  
- modify environment configs without reason  
- introduce unstable dependencies  

---

## 10. Context sources

When relevant, consult:

- docs/ai/PRODUCT_CONTEXT.md  
- docs/ai/CURRENT_PRIORITIES.md  
- docs/ai/GLOSSARY.md  
- architecture documents  

---

## 11. Conflict resolution

If rules conflict:

priority order:

1. deterministic correctness  
2. architecture boundaries  
3. simplicity  
4. developer convenience  

---

## 12. Definition of done

A task is complete when:

- change is implemented  
- architecture is preserved  
- behavior remains predictable  
- verification is performed  
- risks are stated  