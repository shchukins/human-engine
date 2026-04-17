# System Map

## 1. Purpose

Human Engine — система, которая:

> преобразует тренировочные и recovery-данные в readiness и downstream decision support

---

## 2. End-to-end flow

```text
Data Sources
↓
Ingestion / Raw Storage
↓
Normalized Data
↓
Daily State Layers
↓
LoadState + RecoveryState
↓
Readiness
↓
Notification
↓
Recommendation / Ride Briefing
↓
Workout Outcome
↓
Feedback
```

---

## 3. Layer breakdown

### 3.1 Data layer

Отвечает за получение и хранение данных.

Включает:

- Strava ingestion
- HealthKit ingestion
- raw data storage

Свойства:

- данные не теряются
- данные не искажаются

---

### 3.2 Normalization and processing layer

Преобразует raw payloads в прикладные таблицы и daily aggregates.

Текущие артефакты:

- `daily_training_load`
- `health_sleep_night`
- `health_resting_hr_daily`
- `health_hrv_sample`
- `health_weight_measurement`
- `health_recovery_daily`

---

### 3.3 Modeling layer

Оценивает состояние человека.

Текущие артефакты:

- `load_state_daily_v2`
- `health_recovery_daily`
- `readiness_daily`
- fitness / fast fatigue / slow fatigue / freshness
- recovery score + recovery breakdown
- readiness score
- good day probability

Цепочка:

- Data -> LoadState -> RecoveryState -> Readiness -> Notification

---

### 3.4 Decision layer

Формирует вывод системы.

Сейчас частично реализован через readiness outputs:

- readiness
- probability layer
- status text
- explanation payload
- Telegram daily notification

Следующий слой:

- recommendation
- ride briefing

---

### 3.5 Feedback loop

Система может развиваться на основе результата:

- фактическая тренировка
- отклонение от ожидаемого состояния
- корректировка модели

Этот слой пока не является основным реализованным контуром.

---

## 4. Key properties

Система должна быть:

### Deterministic

- одинаковый вход -> одинаковый результат

### Reproducible

- любой расчет можно повторить

### Observable

- можно объяснить результат по слоям

---

## 5. What is NOT part of the core flow

Не входит в основной pipeline:

- LLM
- генеративные модели
- AI-решения

AI может работать только как:

- слой объяснения
- инструмент навигации
- developer assistant

---

## 6. Mental model

Human Engine — это не один алгоритм.

Это цепочка:

> данные -> LoadState -> RecoveryState -> Readiness -> Notification / decision

Если система дает неправильный результат, ошибка находится в одном из слоев:

- данные
- нормализация
- модель нагрузки
- модель восстановления
- readiness logic
- notification formatting / interpretation
- decision mapping

---

## 7. Current vs Future

### Сейчас

- Strava ingestion pipeline
- HealthKit ingestion pipeline
- HealthKit full-sync orchestration
- raw data storage
- normalized health layer
- recovery daily layer
- baseline-aware recovery scoring
- load state v2
- readiness daily
- good day probability baseline

### Далее

- расширение feature layer
- readiness / probability calibration
- recommendation layer
- ride briefing layer
- prediction
- adaptive training

---

## 8. Simplification rule

При развитии системы:

> каждый новый элемент должен вписываться в схему  
> `source -> state -> readiness -> decision`

Если не вписывается:

- либо он лишний
- либо схема нарушена
