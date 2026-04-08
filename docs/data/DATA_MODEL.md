# Data Model

## 1. Purpose

Этот документ описывает модель данных системы Human Engine.

Цель:

- зафиксировать структуру хранения данных  
- обеспечить воспроизводимость расчетов  
- разделить raw и derived данные  

---

## 2. Principles

Модель данных должна:

- сохранять raw данные без изменений  
- позволять повторный расчет метрик  
- быть прозрачной  
- быть расширяемой  

---

## 3. Data layers

Система разделяет данные на уровни:

### 3.1 Raw data

Необработанные данные из внешних источников.

Свойства:

- не изменяются  
- сохраняются полностью  
- являются источником истины  

---

### 3.2 Ingestion data

Данные, связанные с процессом загрузки.

Содержат:

- события webhook  
- jobs  
- статусы обработки  

---

### 3.3 Derived data (future)

Производные данные:

- features  
- метрики  
- readiness  

Могут пересчитываться.

---

## 4. Core entities

---

### 4.1 strava_webhook_event

События от Strava.

Содержит:

- тип события  
- object_id  
- время  
- payload  

Назначение:

- триггер ingestion  

---

### 4.2 strava_activity_ingest_job

Задача на загрузку активности.

Содержит:

- ссылка на webhook_event  
- статус  
- попытки  
- ошибки  

Назначение:

- управление асинхронной загрузкой  

---

### 4.3 strava_activity_raw

Сырые данные активности.

Содержит:

- полный ответ Strava API  
- метаданные активности  

Назначение:

- источник для всех расчетов  

---

### 4.4 strava_activity_stream_raw (future)

Streams данных:

- power  
- heart rate  
- cadence  
- speed  

Назначение:

- детальный анализ  

---

## 5. Derived entities (planned)

---

### 5.1 activity_metrics

Метрики активности:

- NP  
- IF  
- TSS  

---

### 5.2 daily_training_load

Агрегированные данные:

- TSS за день  
- суммарная нагрузка  

---

### 5.3 daily_fitness_state

Legacy-состояние (V1 baseline):

- CTL  
- ATL  
- TSB  

---

### 5.4 health_recovery_daily

Дневная recovery-агрегация:

- sleep_minutes
- resting_hr_bpm
- hrv_daily_median_ms
- weight_kg
- recovery_score_simple

---

### 5.5 load_state_daily_v2

Load model v2:

- tss
- load_input_nonlinear
- fitness
- fatigue_fast
- fatigue_slow
- fatigue_total
- freshness

---

### 5.6 readiness_daily

Оценка готовности:

- freshness
- recovery_score
- readiness_score
- good_day_probability
- explanation_json

---

## 6. Relationships

Связи:

- webhook_event → ingest_job (1:N)  
- ingest_job → activity_raw (1:1)  
- activity_raw → activity_metrics (1:1)  
- activity_metrics → daily_training_load (N:1)  
- daily_training_load → load_state_daily_v2 (N:1)
- health_recovery_daily → readiness_daily (N:1)
- load_state_daily_v2 → readiness_daily (N:1)

---

## 7. Data flow

Webhook event
↓
Ingest job
↓
Raw activity
↓
Metrics
↓
Daily aggregates
↓
Load state + Recovery state
↓
Readiness

---

## 8. Reproducibility

Для обеспечения воспроизводимости:

- raw данные не изменяются  
- все derived данные можно пересчитать  
- формулы зафиксированы в METRICS.md  

---

## 9. Storage strategy

### Raw data

- хранить всегда  
- не удалять  

---

### Derived data

Возможные стратегии:

1. хранить полностью  
2. пересчитывать  
3. гибрид  

(решение пока открыто)

---

## 10. Versioning (future)

При изменении логики:

- версии метрик  
- версии моделей  

Исторические данные не должны ломаться.

---

## 11. Constraints

Нельзя:

- изменять raw данные  
- терять данные ingestion  
- хранить только агрегаты без исходных данных  

---

## 12. Open questions

- где хранить features  
- как делать пересчет  
- как организовать versioning  

(см. OPEN_DECISIONS.md)
