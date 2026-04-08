# Human Engine

Human Engine — экспериментальная платформа анализа тренировок.

Проект предназначен для загрузки, хранения и анализа тренировочных данных
из Strava с использованием собственной инфраструктуры.

## Принципы проекта

Human Engine создается как инженерный эксперимент по построению
системы анализа тренировочных данных на собственной инфраструктуре.

Основные принципы проекта:

• простые и понятные модели вместо сложных ML без необходимости  
• прозрачные вычисления тренировочных метрик  
• минимальная зависимость от внешних сервисов  
• self-hosted инфраструктура  
• воспроизводимость расчетов  
• простая и наблюдаемая архитектура

## Архитектура

Текущая архитектура системы:

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

## Pipeline загрузки данных

Система уже реализует первый pipeline загрузки тренировок из Strava.

Текущий поток данных:

Strava  
↓  
Webhook event  
↓  
/webhook/strava  
↓  
strava_webhook_event  
↓  
strava_activity_ingest_job  
↓  
загрузка активности из Strava API  
↓  
strava_activity_raw

На текущий момент система:
- принимает webhook события Strava  
- сохраняет события в базе данных  
- создает jobs для загрузки активности  
- загружает сырые данные активности

В дальнейшем ingestion слой будет выделен в отдельный worker сервис.

## Технологический стек

Backend  
FastAPI  
PostgreSQL  
Python

Infrastructure  
Docker  
Docker Compose  
Caddy  
Tailscale

External integrations  
Strava API  
Strava Webhooks


## Структура проекта

backend/  
Основной код backend-сервиса на FastAPI и документация проекта.

backend/infra/  
Локальная инфраструктура для разработки (docker-compose для PostgreSQL).

db-init/  
SQL для инициализации базы данных.

compose.yaml  
docker compose стек для домашнего сервера.

sql_*.sql  
Черновые SQL-запросы для ingestion и аналитических метрик.


## Roadmap

Ближайшие этапы развития проекта:

- загрузка streams данных из Strava  
- нормализация recovery-данных  
- расчет тренировочных метрик и load state v2  
- readiness model v2 и probability layer  
- API для аналитики  
- мобильное приложение (iOS)

## AI Context

See:
- docs/ai/PRODUCT_CONTEXT.md
- docs/ai/CURRENT_PRIORITIES.md
- AGENTS.md

## Run locally

### Requirements

- Docker
- Docker Compose
- Python 3.11+

### 1. Clone repository

git clone https://github.com/shchukins/human-engine.git  
cd human-engine/backend

### 2. Create environment file

Copy example configuration:

cp infra/.env.example infra/.env

Edit values if necessary.

### 3. Start PostgreSQL

cd infra  
docker compose up -d

PostgreSQL will start on:

localhost:5433

Database:

human_engine

### 4. Install backend dependencies

cd ..

python -m venv .venv  
source .venv/bin/activate

pip install -r requirements.txt

### 5. Run backend

uvicorn backend.app:app --reload

API will be available at:

http://localhost:8000

Health check:

http://localhost:8000/healthz
