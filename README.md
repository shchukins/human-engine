# Human Engine

> A system for analyzing training load, estimating athlete state, and supporting training decisions.
>
> `signal -> load/recovery state -> readiness -> decision`

## Core Idea

**The right training on the right day.**

Human Engine is not just a training log and not an AI coach.  
It is an engineering system designed to support decisions through explicit, reproducible, and deterministic logic.

## What Human Engine Does

- Collects training data
- Estimates load and recovery state
- Calculates readiness and good-day probability
- Supports training load decisions

## What the System Is

- A training data processing system
- A load adaptation model
- A readiness evaluation engine
- A foundation for training decisions

## What the System Is Not

- Not just a dashboard
- Not black-box AI
- Not a generative coach
- Not a system where an LLM makes product decisions

See: [docs/ai/PRODUCT_CONTEXT.md](docs/ai/PRODUCT_CONTEXT.md)

## Current State

The system is currently in a stabilization phase. The current setup includes:

- Backend built with FastAPI
- PostgreSQL
- Strava ingestion pipeline
- Health recovery ingestion and normalization
- Raw data storage
- Daily load and recovery feature layer
- Model V2 architecture for readiness
- Docker deployment
- Public API exposed through a VPS

### Current Focus

- Deterministic core
- Transparent logic
- Reproducible results

See: [docs/ai/CURRENT_PRIORITIES.md](docs/ai/CURRENT_PRIORITIES.md)

## System Overview

### Data Flow

```text
Strava + HealthKit
        |
        v
     Backend
        |
        v
   PostgreSQL
        |
        v
Normalized / Daily Features
        |
        v
Model V2
        |
        v
Readiness / Insights
```

### Infrastructure

```text
Internet
   |
   v
VPS (Caddy)
   |
   v
Tailscale
   |
   v
Home server
   |
   v
Backend + DB
```

## Architecture Principles

- Simplicity over complexity
- Deterministic logic over AI
- Calculations should remain transparent
- Data and outputs should remain reproducible
- AI is an auxiliary layer, not the product core

## Repository Structure

```text
backend/        main service
backend/infra/  local infrastructure
db-init/        database initialization
compose.yaml    deployment
sql_*.sql       analytics and ingestion scripts
docs/           system documentation
```

## Documentation

### Core Docs

- [backend/README.md](backend/README.md)
- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- [backend/ROADMAP.md](backend/ROADMAP.md)
- [docs/models/model_v2_architecture.md](docs/models/model_v2_architecture.md)

### Product and AI Context

- [docs/ai/PRODUCT_CONTEXT.md](docs/ai/PRODUCT_CONTEXT.md)
- [docs/ai/CURRENT_PRIORITIES.md](docs/ai/CURRENT_PRIORITIES.md)
- [docs/ai/GLOSSARY.md](docs/ai/GLOSSARY.md)
- [AGENTS.md](AGENTS.md)

## Short Roadmap

- Streams ingestion
- Recovery data normalization
- Load model v2: nonlinear load, fitness, fast/slow fatigue
- Readiness model v2
- Good day probability
- Prediction engine
- iOS client

## Documentation

Repository knowledge is organized as follows:

- `docs/ai/` — AI context and system language
- `docs/architecture/` — architecture and decisions
- `docs/data/` — data model
- `docs/models/` — features, metrics, readiness and ride briefing
- `docs/dev/` — workflow and testing strategy
- `docs/product/` — user scenarios

## Status

Experimental engineering project with a strong focus on a deterministic product core.
