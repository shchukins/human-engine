# Human Engine

Human Engine — экспериментальная платформа для загрузки, хранения и анализа тренировочных данных.

Проект исследует возможность построения собственной системы анализа тренировочной нагрузки и адаптации человека на основе данных из Strava.

Основная идея проекта — создать прозрачный и воспроизводимый pipeline обработки тренировочных данных, начиная от получения событий Strava и заканчивая расчетом тренировочных метрик и моделей адаптации.

---

## Текущее состояние проекта

На данный момент реализованы:

- backend сервис на FastAPI
- PostgreSQL база данных
- webhook интеграция со Strava
- ingestion pipeline для загрузки активностей
- хранение сырых данных активностей
- деплой через Docker
- публичный API через VPS reverse proxy

---

## Архитектура

Поток данных:

Strava  
↓  
Webhook event  
↓  
FastAPI backend  
↓  
PostgreSQL  

Инфраструктура деплоя:

Internet  
↓  
VPS (Caddy reverse proxy)  
↓  
Tailscale  
↓  
Home server  
↓  
FastAPI + PostgreSQL  

---

## Технологический стек

Backend

- Python
- FastAPI
- PostgreSQL

Infrastructure

- Docker
- Docker Compose
- Caddy
- Tailscale

External integrations

- Strava API
- Strava Webhooks

---

## Структура проекта

backend/
основной backend код и документация

backend/infra/
docker compose и инфраструктура для разработки

db-init/
инициализация базы данных

compose.yaml
docker compose стек для домашнего сервера

sql_*.sql
черновые SQL-запросы для ingestion и аналитики

---

## Документация

Подробная документация находится в каталоге backend:

- backend/README.md — детали backend сервиса
- backend/ARCHITECTURE.md — архитектура системы
- backend/ROADMAP.md — план развития проекта

---

## Roadmap

Ближайшие направления развития:

- загрузка streams данных из Strava
- расчет тренировочных метрик (TSS, CTL, ATL)
- модель тренировочной адаптации
- API для аналитики
- мобильное приложение

---

## Статус проекта

Проект находится в стадии активного прототипирования.
