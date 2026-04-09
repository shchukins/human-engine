# Architecture

## 1. Purpose

Этот документ описывает текущую архитектуру Human Engine.

Цель:

- зафиксировать текущую структуру системы
- определить границы компонентов
- показать поток данных
- синхронизировать документацию с backend implementation

---

## 2. System overview

Human Engine построен как pipeline:

> данные -> состояние -> readiness -> решение

Высокоуровневый поток:

```text
Data Sources
↓
Backend (Data Engine)
↓
PostgreSQL (Storage)
↓
Raw / Normalized / Daily State
↓
LoadState + RecoveryState
↓
Readiness
↓
Insight / Decision layer
```

---

## 3. Deployment architecture

```text
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
```

Свойства:

- backend не доступен напрямую из интернета
- доступ идет через VPS + Tailscale
- инфраструктура self-hosted

---

## 4. Core components

### 4.1 Backend

FastAPI сервис.

Ответственность:

- прием webhook и sync payloads
- управление ingestion pipeline
- orchestration перерасчетов
- API для доступа к данным и derived state

Backend — центр deterministic core.

---

### 4.2 Database

PostgreSQL.

Хранит:

- raw события и payloads
- normalized tables
- derived daily state
- readiness outputs

Требование:

- расчеты должны быть воспроизводимыми

---

### 4.3 Worker / orchestration paths

Фоновый процесс и orchestration endpoints.

Выполняет:

- загрузку активностей из Strava
- обработку HealthKit sync payloads
- пересчет recovery и readiness

---

## 5. Current data pipelines

### 5.1 Strava pipeline

```text
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
↓
daily_training_load
```

Свойства:

- события сохраняются
- ingestion асинхронный
- raw данные не изменяются

---

### 5.2 HealthKit full-sync pipeline

```text
POST /api/v1/healthkit/full-sync/{user_id}
↓
healthkit_ingest_raw
↓
latest raw -> normalized health tables
↓
health_recovery_daily recompute
↓
readiness_daily recompute
```

Normalized health tables:

- `health_sleep_night`
- `health_resting_hr_daily`
- `health_hrv_sample`
- `health_weight_measurement`

---

## 6. Architectural layers

### 6.1 Data layer (implemented)

- Strava ingestion
- HealthKit ingestion
- raw storage

---

### 6.2 Normalization / processing layer (implemented)

- `daily_training_load`
- HealthKit normalized tables
- recovery aggregation

Этот слой больше не является только planned.

---

### 6.3 Modeling layer (implemented baseline)

Ключевые таблицы:

- `health_recovery_daily`
- `load_state_daily_v2`
- `readiness_daily`

Ключевые свойства:

- load и recovery разделены на независимые контуры
- `load_state_daily_v2` считает `fitness`, `fatigue_fast`, `fatigue_slow`, `fatigue_total`, `freshness`
- расчет идет по непрерывной календарной оси
- в дни без тренировок используется `tss = 0`
- `fatigue_total` является взвешенной смесью fast/slow fatigue
- readiness считается из load state и recovery state, а не только из freshness
- `good_day_probability` хранится как отдельный probability layer

---

### 6.4 Decision layer (partially implemented)

Сейчас реализованы базовые decision outputs:

- `readiness_score`
- `good_day_probability`
- `status_text`
- `explanation_json`

Следующий слой:

- daily readiness summary
- recommendation
- ride briefing

---

## 7. Core vs AI boundary

### Core

- backend
- database
- ingestion
- normalization
- domain logic
- readiness logic

Свойства:

- deterministic
- воспроизводимый
- проверяемый

---

### AI

- RAG
- LLM
- генерация текста

Свойства:

- не влияет на расчеты
- не участвует в принятии решений
- работает отдельно от core

---

## 8. Architecture principles

### Deterministic first

- логика должна быть явной
- одинаковый вход -> одинаковый результат

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

- source ingestion, normalization, model and decision разделены
- load и recovery не смешиваются в один неявный сигнал
- AI не смешивается с core

---

## 9. Current model v2 baseline

Текущая product-level схема:

```text
LoadState + RecoveryState -> Readiness -> GoodDayProbability
```

Где:

- `LoadState` описывает тренировочную нагрузку
- `RecoveryState` описывает восстановление организма
- `Readiness` является отдельным слоем, а не полем внутри load state

---

## 10. Evolution path

Текущее состояние:

- ingestion pipelines
- raw storage
- normalized health layer
- recovery layer
- load model v2 baseline
- readiness baseline

Следующие шаги:

- feature layer expansion
- readiness and probability calibration
- recommendation layer
- prediction

---

## 11. Constraints

Нельзя:

- внедрять AI в core
- скрывать логику
- подменять load/recovery контуры текстовой эвристикой
- менять доменный смысл без явной фиксации

Можно:

- упрощать
- делать логику явной
- улучшать наблюдаемость

---

## 12. Consistency rule

Любое изменение должно:

- вписываться в pipeline
- не ломать границы между слоями
- явно отделять implemented от planned

Если компонент не вписывается:

- либо он лишний
- либо архитектура нарушена
