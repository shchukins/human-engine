# Human Engine — CURRENT STATE

Last updated: 2026-04-09

---

## 1. Общий статус

Human Engine перешел от load-only readiness к рабочей baseline-архитектуре Model V2.

Текущая схема:

```text
LoadState + RecoveryState -> Readiness -> GoodDayProbability
```

Система уже работает как end-to-end pipeline:

```text
iOS -> public API -> backend -> raw -> normalized -> recovery -> readiness -> response
```

Это уже не только модельная заготовка. В backend реализованы ingestion, materialized daily layers и response path.

---

## 2. Архитектура (актуальная)

### 2.1 Load contour

Источник:

- Strava

Pipeline:

- `strava_activity_raw`
- `daily_training_load`
- `load_state_daily_v2`

Содержит:

- `tss`
- `load_input_nonlinear`
- `fitness`
- `fatigue_fast`
- `fatigue_slow`
- `fatigue_total`
- `freshness`
- `version`

### 2.2 Recovery contour

Источник:

- HealthKit

Pipeline:

- `healthkit_ingest_raw`
- normalized tables:
  - `health_sleep_night`
  - `health_resting_hr_daily`
  - `health_hrv_sample`
  - `health_weight_measurement`
- `health_recovery_daily`

Содержит:

- `sleep_minutes`
- `awake_minutes`
- `rem_minutes`
- `deep_minutes`
- `resting_hr_bpm`
- `hrv_daily_median_ms`
- `weight_kg`
- `recovery_score_simple`
- `recovery_explanation_json`

Важно:

- таблица `health_recovery_daily` уже реализована
- поле `recovery_score_simple` исторически сохраняет старое имя
- по смыслу текущий recovery layer уже baseline-aware, а не purely heuristic-only placeholder
- breakdown recovery baseline сохраняется в `recovery_explanation_json`

### 2.3 Readiness layer

Pipeline:

- `load_state_daily_v2 + health_recovery_daily -> readiness_daily`

Содержит:

- `freshness`
- `recovery_score_simple`
- `readiness_score_raw`
- `readiness_score`
- `good_day_probability`
- `status_text`
- `explanation_json`
- `version`

Важно:

- readiness хранится как отдельный daily storage layer
- readiness не равен `freshness`
- readiness объединяет load contour и recovery contour
- `readiness_daily.explanation_json` теперь включает recovery breakdown из `health_recovery_daily.recovery_explanation_json`

---

## 3. Data pipeline

### 3.1 HealthKit full sync

Endpoint:

`POST /api/v1/healthkit/full-sync/{user_id}`

Flow:

1. raw ingest в `healthkit_ingest_raw`
2. latest raw -> normalized health tables
3. сбор affected dates
4. recompute `health_recovery_daily`
5. recompute `readiness_daily`
6. response обратно в клиент

### 3.2 Load model v2 recompute

Endpoint:

`POST /api/v1/model/load-state-v2/{user_id}`

Особенности:

- непрерывная календарная ось
- `tss = 0` в дни без тренировок
- fast + slow fatigue
- `fatigue_total` как weighted mixture

### 3.3 Readiness recompute

Endpoint:

`POST /api/v1/model/readiness-daily/{user_id}/{date}`

---

## 4. Реализованная baseline model

### 4.1 Load model v2

Параметры:

- `tau_fitness = 40`
- `tau_fatigue_fast = 4`
- `tau_fatigue_slow = 9`
- `weight_fatigue_fast = 0.65`
- `weight_fatigue_slow = 0.35`

Расчеты:

```text
load_input_nonlinear = TSS
fatigue_total = 0.65 * fatigue_fast + 0.35 * fatigue_slow
freshness = fitness - fatigue_total
```

Важно:

- поле называется `load_input_nonlinear`
- в текущем backend это все еще линейный input по TSS

### 4.2 Recovery baseline

Текущий recovery scoring:

- использует `sleep_minutes`
- использует `hrv_today` и `rhr_today`
- использует `hrv_baseline` и `rhr_baseline`
- считает `hrv_dev` и `rhr_dev`
- считает `sleep_score`, `hrv_score`, `rhr_score`
- сохраняет breakdown в `recovery_explanation_json`

Базовая формула:

```text
recovery_score_simple = 0.4 * hrv_score + 0.3 * rhr_score + 0.3 * sleep_score
```

Если baseline для компонента недоступен, используется нейтральное значение.

### 4.3 Readiness baseline

Текущая формула:

```text
freshness_norm = clamp(50 + freshness, 0, 100)
readiness_score_raw = 0.6 * freshness_norm + 0.4 * recovery_score_simple
readiness_score = clamp(round(readiness_score_raw, 1), 0, 100)
good_day_probability = readiness_score / 100
```

Важно:

- `good_day_probability` уже реализован
- это baseline probability-like mapping
- это не статистически откалиброванная вероятность
- readiness formula не менялась; расширен только explanation payload

---

## 5. Что уже работает end-to-end

- iOS приложение отправляет HealthKit payload
- backend принимает `full-sync`
- данные попадают в raw таблицу
- latest raw раскладывается в normalized health tables
- пересчитывается `health_recovery_daily`
- пересчитывается `readiness_daily`
- результат возвращается в iOS через public API

Публичный API уже проксируется через VPS / Caddy по пути `/api/*`.

---

## 6. Основные ограничения текущей версии

1. Recovery baseline уже реализован, но еще не откалиброван на популяционных или персональных outcome данных.
2. `load_input_nonlinear` пока фактически линейный.
3. `good_day_probability` пока является простым mapping от readiness score.
4. Decision layer и recommendation layer еще не реализованы как отдельный production layer.
5. Персонализация и calibration остаются следующим этапом.

---

## 7. Ключевые архитектурные решения

- Load и Recovery разделены
- Readiness не равен freshness
- Readiness хранится отдельно в `readiness_daily`
- Recovery влияет на readiness, но не переписывает load model
- используется daily aggregation
- используется probability layer (`good_day_probability`)
- deterministic core остается приоритетом

---

## 8. Текущие источники данных

### Реальные

- Strava
- HealthKit

### Planned

- Garmin
- дополнительные recovery signals
- decision / recommendation outputs

---

## 9. Следующие шаги (приоритет)

### P1 — Calibration

- readiness / probability calibration
- проверка recovery baseline на реальных данных
- уточнение readiness zones

### P2 — Decision layer

- recommendation layer поверх readiness
- rule-based decision mapping

### P3 — UX / Product integration

- user-facing readiness screen в iOS
- объяснения на основе уже существующих breakdown payloads

### P4 — Model improvements

- nonlinear load transform
- personalization
- расширение feature layer

---

## 10. Definition of Done для текущей стадии

Система считается рабочей на текущем этапе, если:

- данные приходят из HealthKit и Strava
- считается `load_state_daily_v2`
- считается `health_recovery_daily`
- считается `readiness_daily`
- `good_day_probability` доступен как отдельный output
- документация соответствует реальному backend baseline
