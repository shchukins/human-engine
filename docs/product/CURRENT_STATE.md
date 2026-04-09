# Human Engine — CURRENT STATE

Last updated: 2026-04-09

---

## 1. Общий статус

Human Engine перешел от прототипа load-based модели к рабочей архитектуре Model V2.

Система теперь представляет собой end-to-end pipeline:

HealthKit / Strava → Data Engine → Load + Recovery → Readiness → API → iOS

Это первая версия, где:
- данные реально поступают из внешних источников
- модель считает состояние пользователя
- результат возвращается в клиент

---

## 2. Архитектура (актуальная)

### 2.1 Контуры модели

Система разделена на два независимых контура:

#### Load contour
Источник:
- Strava

Pipeline:
- strava_activity_raw
- daily_training_load
- load_state_daily_v2

Содержит:
- fitness
- fatigue_fast
- fatigue_slow
- fatigue_total
- freshness

---

#### Recovery contour
Источник:
- HealthKit

Pipeline:
- healthkit_ingest_raw
- normalized tables:
  - health_sleep_night
  - health_resting_hr_daily
  - health_hrv_sample
  - health_weight_measurement
- health_recovery_daily

Содержит:
- sleep
- HRV
- resting HR
- weight
- recovery_score_simple

---

#### Readiness layer

Pipeline:
- load_state_daily_v2 + health_recovery_daily → readiness_daily

Содержит:
- readiness_score
- good_day_probability
- status_text
- explanation_json

---

## 3. Data pipeline

### HealthKit full sync

Endpoint:
POST /api/v1/healthkit/full-sync/{user_id}

Flow:
1. raw ingest
2. latest raw → normalized tables
3. recompute health_recovery_daily
4. recompute readiness_daily

---

### Load model v2 recompute

Endpoint:
POST /api/v1/model/load-state-v2/{user_id}

Особенности:
- непрерывная календарная ось
- tss = 0 в дни без тренировок
- fast + slow fatigue

---

### Readiness recompute

Endpoint:
POST /api/v1/model/readiness-daily/{user_id}/{date}

---

## 4. Модель (Model V2)

### Load model

Параметры:

- tau_fitness = 40
- tau_fatigue_fast = 4
- tau_fatigue_slow = 9

Расчеты:

fitness(t)
fatigue_fast(t)
fatigue_slow(t)

fatigue_total = w_fast * fatigue_fast + w_slow * fatigue_slow  
freshness = fitness - fatigue_total

---

### Recovery model (v1)

Агрегаты:

- sleep_minutes
- hrv_daily_median_ms
- resting_hr_bpm
- weight_kg

Текущий скоринг:

recovery_score_simple = heuristic (v1)

⚠️ baseline и deviation пока не реализованы

---

### Readiness model

Текущая формула:

readiness_score_raw =
    0.6 * freshness_norm +
    0.4 * recovery_score_simple

good_day_probability = sigmoid(readiness_score)

---

## 5. Что уже работает end-to-end

- iOS приложение отправляет HealthKit payload
- backend принимает full-sync
- данные попадают в raw таблицу
- нормализуются
- агрегируются в recovery
- считается readiness
- результат возвращается в iOS

---

## 6. Основные ограничения текущей версии

1. Recovery модель упрощенная
- нет baseline HRV
- нет HRV deviation
- нет RHR deviation
- sleep используется без нормализации

2. Load model
- nonlinear TSS пока не включен
- параметры не калиброваны

3. Readiness
- веса фиксированы
- нет персонализации

4. Нет decision layer
- нет явной рекомендации тренировки

---

## 7. Ключевые архитектурные решения

- Load и Recovery разделены
- Readiness не равен freshness
- Recovery влияет на readiness, но не переписывает fatigue
- используется daily aggregation
- используется probability layer (good_day_probability)

---

## 8. Текущие источники данных

### Реальные
- Strava
- HealthKit

### Планируемые
- Garmin (опционально)
- дополнительные recovery сигналы

---

## 9. Следующие шаги (приоритет)

### P1 — Recovery model улучшение
- HRV baseline
- HRV deviation
- RHR deviation
- sleep score нормализация

---

### P2 — Decision layer
- recommendation на основе good_day_probability

---

### P3 — UX (iOS)
- экран "Today readiness"
- отображение:
  - recovery
  - freshness
  - readiness
  - probability

---

### P4 — Model improvements
- nonlinear load
- калибровка параметров
- персонализация

---

## 10. Definition of Done (для текущей стадии)

Система считается рабочей, если:

- данные приходят из HealthKit
- данные приходят из Strava
- считается load_state_daily_v2
- считается health_recovery_daily
- считается readiness_daily
- iOS получает результат

---

## 11. Ключевой инсайт

Human Engine теперь:

не просто считает нагрузку,

а моделирует состояние человека как результат взаимодействия:

нагрузки и восстановления