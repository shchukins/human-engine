# Architecture

## 1. Purpose

Этот документ описывает архитектуру системы Human Engine.

Цель:

- зафиксировать текущую структуру системы  
- определить границы компонентов  
- показать поток данных  
- обеспечить согласованность разработки  

---

## 2. System overview

Human Engine построен как pipeline:

> данные → состояние → решение

Высокоуровневый поток:
Data Sources
↓
Backend (Data Engine)
↓
PostgreSQL (Storage)
↓
Processing / Features (future)
↓
Modeling (future)
↓
Decision layer (future)

---

## 3. Deployment architecture
Internet
↓
VPS (Caddy reverse proxy)
↓
Tailscale VPN
↓
Home server
↓
Backend (FastAPI)
↓
PostgreSQL

Свойства:

- backend не доступен напрямую из интернета  
- доступ только через VPS + Tailscale  
- инфраструктура self-hosted  

---

## 4. Core components

### 4.1 Backend

FastAPI сервис.

Ответственность:

- прием webhook событий  
- управление ingestion pipeline  
- API для доступа к данным  
- оркестрация обработки  

Backend — это центр системы.

---

### 4.2 Database

PostgreSQL.

Хранит:

- webhook события  
- активности  
- raw данные  
- производные метрики (в будущем)  

Требование:

- данные должны быть воспроизводимыми  

---

### 4.3 Worker

Фоновый процесс.

Выполняет:

- загрузку активностей из Strava  
- загрузку streams  
- обновление данных  

---

## 5. Data pipeline

Текущий pipeline:

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
Worker
↓
Strava API
↓
strava_activity_raw

Свойства:

- события сохраняются  
- ingestion асинхронный  
- raw данные не изменяются  

---

## 6. Architectural layers

Система разделена на слои:

### 6.1 Data layer (implemented)

- ingestion  
- raw storage  

---

### 6.2 Processing layer (planned)

- feature extraction  
- базовые метрики  

---

### 6.3 Modeling layer (planned)

- physiology model  
- training load  
- fitness / fatigue  

---

### 6.4 Decision layer (planned)

- readiness  
- recommendation  
- ride briefing  

---

## 7. Core vs AI boundary

Критическое архитектурное разделение:

### Core (обязательная часть)

- backend  
- database  
- ingestion  
- domain logic  

Свойства:

- deterministic  
- воспроизводимый  
- проверяемый  

---

### AI (вспомогательный слой)

- RAG  
- LLM  
- генерация текста  

Свойства:

- не влияет на расчеты  
- не участвует в принятии решений  
- работает отдельно от core  

---

## 8. Architecture principles

Система строится по следующим принципам:

### Deterministic first
- логика должна быть явной  
- одинаковый вход → одинаковый результат  

---

### Simplicity over complexity
- простые решения предпочтительнее  
- избегать лишних абстракций  

---

### Reproducibility
- любой расчет можно повторить  
- raw данные сохраняются  

---

### Separation of concerns
- data / model / decision разделены  
- AI не смешивается с core  

---

## 9. Evolution path

Текущее состояние:

- ingestion pipeline  
- storage  
- базовая инфраструктура  

Следующие шаги:

- feature layer  
- расчет метрик (TSS, CTL, ATL)  
- physiology model  
- readiness  
- prediction  

---

## 10. Constraints

При изменении архитектуры:

Нельзя:

- внедрять AI в core  
- скрывать логику  
- усложнять систему без причины  

Можно:

- упрощать  
- делать логику явной  
- улучшать наблюдаемость  

---

## 11. Consistency with System Map

Любое изменение должно:

- вписываться в pipeline  
- не ломать слои  
- не смешивать уровни  

Если компонент не вписывается:

- либо он лишний  
- либо архитектура нарушена  