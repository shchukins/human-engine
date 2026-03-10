# Human Engine

Human Engine — экспериментальная платформа для анализа тренировочных данных и моделирования адаптации человека к нагрузке.

## Что уже реализовано

- backend на FastAPI
- PostgreSQL
- webhook интеграция со Strava
- ingestion pipeline для загрузки сырых данных активностей
- публичный API через VPS + Caddy + Tailscale

## Архитектура

Strava
↓
Webhook
↓
FastAPI backend
↓
PostgreSQL

Деплой:

Internet
↓
VPS (Caddy reverse proxy)
↓
Tailscale
↓
Home server
↓
FastAPI + PostgreSQL

## Технологический стек

- Python
- FastAPI
- PostgreSQL
- Docker
- Caddy
- Tailscale
- Strava API

## Документация

- [Backend README](backend/README.md)
- [Architecture](backend/ARCHITECTURE.md)
- [Roadmap](backend/ROADMAP.md)
