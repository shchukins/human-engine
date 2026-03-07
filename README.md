# Human Engine

Human Engine — система сбора и анализа тренировочных данных для моделирования адаптации человека к физической нагрузке.

Первая экспериментальная платформа — велотренировки.

Проект собирает события из различных источников (Strava, HealthKit и др.), сохраняет их в базе данных и далее использует для анализа нагрузки, восстановления и прогнозирования формы.

---

# Architecture
Internet
│
│ https://api.shchlab.ru
▼
VPS (Beget)
Caddy reverse proxy
│
│ Tailscale tunnel
▼
Home server (mini PC)

Docker
├─ backend (FastAPI)
└─ postgres

Домашний сервер выступает общим application server.  
Human Engine — первый сервис, но инфраструктура остается нейтральной и может использоваться для других проектов.

---

# Stack

Backend

- FastAPI
- Python
- PostgreSQL
- Docker

Infrastructure

- Ubuntu Server 24.04
- Caddy
- Tailscale
- VPS (Beget)

Monitoring

- Telegram watchdog bot
- database backups

---

# API

Base URL

https://api.shchlab.ru

Health check

GET /healthz

Database check

GET /dbz

Create event

POST /events

Example

curl -X POST https://api.shchlab.ru/events \
-H "Content-Type: application/json" \
-d '{
  "source": "manual",
  "event_type": "test",
  "payload": { "message": "hello" }
}'

List events

GET /events

Strava webhook

GET /strava/webhook  
POST /strava/webhook

---

# Local development

Start services

docker compose up -d

Swagger docs

http://localhost:8000/docs

---

# Production

Public endpoint

https://api.shchlab.ru

Health check

curl https://api.shchlab.ru/healthz

---

# Monitoring

Server monitoring via Telegram watchdog bot.

Checks include:

- CPU load
- memory usage
- disk usage
- backend availability

Database backups are created daily using pg_dump.

---

# Project status

v0.1

Infrastructure deployed  
PostgreSQL storage working  
Event ingestion implemented  
Public API available  
HTTPS enabled via Let's Encrypt


