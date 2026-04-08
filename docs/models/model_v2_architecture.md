# Human Engine — Model V2 Architecture

## Контекст

Текущая модель (V1) основана на load-only логике:

TSS → fitness / fatigue → freshness → readiness

На практике выявлены ограничения:

- readiness слишком инертен
- отсутствует учет восстановления
- модель плохо отражает реальные ощущения после сна / recovery
- используется только один канал fatigue

## Цель Model V2

Перейти к двухконтурной модели:

LoadState + RecoveryState → Readiness → GoodDayProbability

---

# 1. Архитектурные принципы

## 1.1 Load и Recovery — независимые контуры

Load:
- отражает тренировочную нагрузку
- формируется из TSS / NP

Recovery:
- отражает восстановление организма
- формируется из:
  - sleep
  - HRV
  - resting HR

❗ Важно:
Recovery не заменяет fatigue, а корректирует итоговую readiness.

---

## 1.2 Readiness ≠ Freshness

В Model V1:
readiness ≈ freshness

В Model V2:
readiness = f(load_state, recovery_state)

---

## 1.3 Fast / Slow fatigue

Вместо одного fatigue:

- fatigue_fast (τ ≈ 2 дня)
- fatigue_slow (τ ≈ 7 дней)

Итого:

fatigue_total = fatigue_fast + fatigue_slow  
freshness = fitness - fatigue_total

Это дает:
- быстрый отклик после восстановления
- накопление усталости при серии тренировок

---

## 1.4 Нелинейность нагрузки

Вход нагрузки должен быть нелинейным:

load_input = A * (1 - exp(-B * TSS))

Смысл:
- 200 TSS ≠ 2 × 100 TSS
- предотвращает «раздувание» модели

---

## 1.5 Probability вместо только score

Model V2 вводит:

- readiness_score
- good_day_probability

good_day_probability = sigmoid(readiness_score_raw)

Это позволяет:
- убрать жесткие пороги
- сделать рекомендации более гибкими

---

# 2. Архитектура слоев

## 2.1 Ingestion layer

Источники:
- Strava
- HealthKit

---

## 2.2 Normalized layer

Таблицы:

Load:
- activity_metrics
- daily_training_load

Recovery:
- health_sleep_night
- health_resting_hr_daily
- health_hrv_sample
- health_weight_measurement

---

## 2.3 Daily feature layer

- daily_training_load
- daily_fitness_state (V1, legacy)
- health_recovery_daily

---

## 2.4 Model layer (V2)

Новые таблицы:

- load_state_daily_v2
- readiness_daily

---

## 2.5 User insight layer

Использует Model V2:

- daily readiness summary
- ride briefing
- training feedback
- recommendations

---

# 3. Load Model V2

## 3.1 Параметры

- tau_fitness ≈ 40
- tau_fatigue_fast ≈ 2
- tau_fatigue_slow ≈ 7

## 3.2 Формулы

fitness[d] =
    fitness[d-1] + (load_input[d] - fitness[d-1]) / tau_fitness

fatigue_fast[d] =
    fatigue_fast[d-1] + (load_input[d] - fatigue_fast[d-1]) / tau_fatigue_fast

fatigue_slow[d] =
    fatigue_slow[d-1] + (load_input[d] - fatigue_slow[d-1]) / tau_fatigue_slow

fatigue_total[d] = fatigue_fast[d] + fatigue_slow[d]

freshness[d] = fitness[d] - fatigue_total[d]

---

# 4. Recovery Model

Источник: HealthKit

Данные:

- sleep
- HRV
- resting HR
- weight

## 4.1 Текущая реализация (V1)

health_recovery_daily:

- sleep_minutes
- resting_hr_bpm
- hrv_daily_median_ms
- weight_kg
- recovery_score_simple

## 4.2 План расширения

Добавить:

- sleep_score_simple
- hrv_dev (относительно baseline)
- rhr_dev

---

# 5. Readiness Model V2

## 5.1 Базовая формула (V1)

readiness_score_raw =
    w1 * freshness +
    w2 * recovery_score_simple

## 5.2 Расширенная формула (V2+)

readiness_score_raw =
    w1 * freshness
  + w2 * recovery_score
  + w3 * hrv_dev
  - w4 * rhr_dev
  + w5 * sleep_score

---

# 6. Probability Layer

good_day_probability = sigmoid(readiness_score_raw)

Назначение:
- оценка вероятности успешной тренировки
- основа для рекомендаций

---

# 7. Таблицы Model V2

## 7.1 load_state_daily_v2

- tss
- load_input_nonlinear
- fitness
- fatigue_fast
- fatigue_slow
- fatigue_total
- freshness

## 7.2 readiness_daily

- freshness
- recovery_score
- readiness_score
- good_day_probability
- explanation_json

---

# 8. Roadmap

## Phase 1
- load_state_daily_v2
- fast / slow fatigue

## Phase 2
- расширение health_recovery_daily
- readiness_daily (freshness + recovery)

## Phase 3
- probability layer
- интеграция в user layer

## Phase 4
- baseline (HRV_dev, RHR_dev)
- улучшение модели

---

# 9. Что сознательно НЕ делаем сейчас

- ML модели
- ARIMA / forecasting
- сложные нелинейные системы
- personalization через обучение

Причина:
приоритет — прозрачность и интерпретируемость

---

# 10. Ключевой принцип

Model V2:

Сначала объясняет нагрузку  
Потом корректируется сигналами восстановления  

Это базовая архитектура Human Engine.