# Human Engine

Human Engine — экспериментальная платформа анализа тренировок.

Проект предназначен для загрузки, хранения и анализа тренировочных данных
из Strava с использованием собственной инфраструктуры.

Технологический стек:

• FastAPI  
• PostgreSQL  
• Docker  
• Strava API  
• Tailscale + VPS reverse proxy

## Текущее состояние проекта

Сейчас реализовано:

• прием webhook событий Strava  
• очередь ingestion jobs  
• загрузка сырых данных активностей  
• backend API на FastAPI  
• PostgreSQL база данных  
• деплой через Docker  
• публичный API через VPS reverse proxy

---
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

## Что уже реализовано

Сейчас в системе работает базовый pipeline загрузки тренировок из Strava.

Strava отправляет webhook события при создании или обновлении активности.

Эти события принимаются backend-сервисом и сохраняются в базу данных. Далее создается job, которая загружает сырые данные активности через API Strava.


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
• принимает webhook события Strava  
• сохраняет события в базе данных  
• создает jobs для загрузки активности  
• загружает сырые данные активности

В дальнейшем ingestion слой будет выделен в отдельный worker сервис.

---


## Инфраструктура

Система развернута на двух серверах.

VPS  
Используется как публичная точка входа.

Функции VPS:

• HTTPS termination  
• reverse proxy  
• публичный API endpoint

Home server  
На домашнем сервере работают:

• backend  
• postgres  
• worker

Связь между VPS и домашним сервером осуществляется через Tailscale (WireGuard VPN).

Это позволяет не открывать домашний сервер напрямую в интернет.

---

## Домен

API доступен по адресу

https://api.shchlab.ru

Health check

https://api.shchlab.ru/healthz

---

## Цель проекта

Human Engine исследует идею персональной модели адаптации спортсмена.

Планируется реализовать:

• расчет тренировочной нагрузки  
• моделирование адаптации  
• прогноз формы  
• выявление аномалий тренировок  
• интеграцию с HealthKit  
• визуализацию данных

Проект находится на ранней стадии разработки.


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
