# Human Engine Architecture

Этот документ описывает архитектуру системы Human Engine.

---

## Общая схема

Internet
↓
VPS
↓
HTTPS / Caddy
↓
Tailscale VPN
↓
Home server
↓
FastAPI backend
↓
PostgreSQL

---

## Компоненты системы

### VPS

Публичная точка входа.

Функции:

• HTTPS termination  
• reverse proxy  
• routing к backend  

Используется Caddy.

---

### Backend

FastAPI приложение.

Функции:

• прием webhook событий  
• управление ingestion pipeline  
• API для работы с данными  

---

### Database

PostgreSQL используется для хранения:

• webhook событий  
• активностей  
• сырых данных активности  
• расчетных метрик

---

### Worker

Фоновый процесс выполняет jobs:

• загрузка активности из Strava  
• загрузка streams данных  
• обновление данных

---

## Pipeline загрузки активности

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
worker  
↓  
Strava API  
↓  
strava_activity_raw

---

## Безопасность

Backend не доступен напрямую из интернета.

Доступ осуществляется через:

VPS → reverse proxy → Tailscale → backend

Таким образом backend остается внутри защищенной сети.

---

## Будущие компоненты

Планируется добавить:

Data Engineering layer  
агрегации и расчет фичей

Modeling layer  
модели адаптации спортсмена

Visualization layer  
дашборды и графики

Mobile client  
интеграция с HealthKit
