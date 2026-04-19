# Human Engine

<p align="center">
  <img src="https://img.shields.io/badge/status-experimental-blue" />
  <img src="https://img.shields.io/badge/license-MIT-yellow" />
  <img src="https://img.shields.io/badge/core-deterministic-green" />
  <img src="https://img.shields.io/badge/backend-FastAPI-009688" />
  <img src="https://img.shields.io/badge/database-PostgreSQL-336791" />
  <img src="https://img.shields.io/badge/iOS-HealthKit-black" />
  <img src="https://img.shields.io/badge/integration-Strava-FC4C02" />
</p>

<p align="center">
  A system for analyzing training load, recovery, readiness, and decision support.
</p>

<p align="center">
  <code>signal → load state + recovery state → readiness → decision</code>
</p>

## Core Idea

**The right training on the right day.**

Human Engine is not a training log and not an AI coach.  
It is an engineering system designed to support decisions through explicit, reproducible, and deterministic logic.

## What Human Engine Does

- Collects training and recovery data
- Stores raw source payloads for reproducibility
- Builds daily load and recovery state
- Calculates readiness and good-day probability
- Provides deterministic outputs for downstream decision support

## What the System Is

- A training data processing system
- A physiology-driven load and recovery model
- A readiness evaluation engine
- A deterministic foundation for training decisions

## What the System Is Not

- Not just a dashboard
- Not black-box AI
- Not a generative coach
- Not a system where an LLM makes product decisions

See: [docs/ai/PRODUCT_CONTEXT.md](docs/ai/PRODUCT_CONTEXT.md)

## Current State

The current backend already includes:

- FastAPI backend
- PostgreSQL
- Strava ingestion pipeline
- HealthKit raw ingestion and full-sync orchestration
- Raw data storage for Strava and HealthKit payloads
- HealthKit normalized tables
- Recovery layer via `health_recovery_daily`
- Load model v2 via `load_state_daily_v2`
- Readiness layer via `readiness_daily`
- Probability layer via `good_day_probability`
- Docker deployment
- Public API exposed through a VPS

Implemented model baseline:

- `LoadState + RecoveryState -> Readiness -> GoodDayProbability`
- HealthKit full-sync endpoint `POST /api/v1/healthkit/full-sync/{user_id}`
- baseline-aware recovery scoring stored in `health_recovery_daily`
- explanation payloads for recovery and readiness
- deterministic storage-backed daily layers for load, recovery, and readiness

### Current Focus

- Deterministic core
- Transparent logic
- Reproducible results
- Stabilization of model v2 baseline and downstream decision outputs

See: [docs/ai/CURRENT_PRIORITIES.md](docs/ai/CURRENT_PRIORITIES.md)

## System Overview

### Data Flow

```text
Strava ---------------------------> daily_training_load ----------+
                                                                 |
HealthKit -> raw ingest -> normalized health tables -> recovery -+-> readiness
                                                                 |
                                                                 v
                                                     load_state_daily_v2
```

### Current End-to-End Pipeline

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
Raw / Normalized / Daily State
        |
        v
LoadState + RecoveryState
        |
        v
Readiness + GoodDayProbability
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

## Observability

Human Engine includes a minimal observability layer for backend logs:

- structured JSON logging in the FastAPI backend
- Promtail pipeline with docker log parsing and JSON extraction
- Loki for log storage
- Grafana dashboard for API requests, HealthKit sync, readiness recompute, errors, and pipeline trace

See: [docs/architecture/OBSERVABILITY.md](docs/architecture/OBSERVABILITY.md)

## Architecture Principles

- Simplicity over complexity
- Deterministic logic over AI
- Calculations remain transparent
- Data and outputs remain reproducible
- Load and recovery remain separate physiological contours
- AI is an auxiliary layer, not the product core

## Repository Structure

```text
backend/        main service
backend/infra/  local infrastructure
db-init/        database initialization
compose.yaml    deployment
docs/           system documentation
```

## Documentation

### Core Docs

- [backend/README.md](backend/README.md)
- [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- [docs/architecture/OBSERVABILITY.md](docs/architecture/OBSERVABILITY.md)
- [backend/ROADMAP.md](backend/ROADMAP.md)
- [docs/models/model_v2_architecture.md](docs/models/model_v2_architecture.md)
- [docs/product/CURRENT_STATE.md](docs/product/CURRENT_STATE.md)

### Product and AI Context

- [docs/ai/PRODUCT_CONTEXT.md](docs/ai/PRODUCT_CONTEXT.md)
- [docs/ai/CURRENT_PRIORITIES.md](docs/ai/CURRENT_PRIORITIES.md)
- [docs/ai/GLOSSARY.md](docs/ai/GLOSSARY.md)
- [AGENTS.md](AGENTS.md)

## Current Model V2 Baseline

- Load contour: `daily_training_load -> load_state_daily_v2`
- Recovery contour: HealthKit normalized tables -> `health_recovery_daily`
- Readiness contour: `load_state_daily_v2 + health_recovery_daily -> readiness_daily`
- `freshness = fitness - fatigue_total`
- `fatigue_total` is a weighted mixture of `fatigue_fast` and `fatigue_slow`
- `recovery_score_simple` is currently produced by a baseline-aware recovery scoring layer
- Readiness is not equal to freshness
- `good_day_probability` is stored as a separate probability-like output
- `good_day_probability` is currently `readiness_score / 100`, not a statistically calibrated probability

## Short Roadmap

Already implemented:

- HealthKit ingestion and normalization
- HealthKit full-sync orchestration
- Recovery daily aggregation
- Recovery explanation payload
- Load model v2
- Readiness model v2 baseline
- Good day probability baseline

Next:

- activity streams ingestion
- feature extraction expansion
- readiness / probability calibration
- decision layer / recommendation layer
- prediction engine
- iOS client integration polish

## Documentation Map

- `docs/ai/` — AI context and system language
- `docs/architecture/` — architecture and decisions
- `docs/data/` — data model
- `docs/models/` — features, metrics, readiness and ride briefing
- `docs/dev/` — workflow and testing strategy
- `docs/product/` — user scenarios

## Status

Experimental engineering project with a deterministic product core and an implemented Model V2 baseline in backend.
