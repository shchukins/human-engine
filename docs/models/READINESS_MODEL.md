# Readiness Model

## 1. Purpose

Этот документ описывает модель оценки готовности (readiness)
в системе Human Engine.

Цель:

- определить, насколько спортсмен готов к нагрузке  
- обеспечить детерминированное принятие решений  
- сделать модель прозрачной и объяснимой  

---

## 2. Principles

Модель должна быть:

- deterministic  
- простой  
- объяснимой  
- воспроизводимой  

Нельзя:

- использовать скрытую логику  
- использовать LLM  
- усложнять без необходимости  

---

## 3. Inputs

Модель использует следующие метрики:

- `freshness` из `load_state_daily_v2`  
- `recovery_score_simple` из `health_recovery_daily`  
- recent training load  

Дополнительно в расширенной версии могут использоваться:

- `sleep_score_simple`
- `hrv_dev`
- `rhr_dev`

---

## 4. Core logic

Основная идея:

> readiness определяется не только нагрузкой, а сочетанием load state и recovery state

Базовая формула v2:

```text
readiness_score_raw =
    w1 * freshness +
    w2 * recovery_score_simple
```

Где:

- `freshness = fitness - fatigue_total`
- `fatigue_total = fatigue_fast + fatigue_slow`

Расширенная формула v2+:

```text
readiness_score_raw =
    w1 * freshness
  + w2 * recovery_score
  + w3 * hrv_dev
  - w4 * rhr_dev
  + w5 * sleep_score
```

---

## 5. Readiness zones

Модель делит состояние на зоны на основе `readiness_score` и/или `good_day_probability`.

### 5.1 Low readiness

Условие:

- низкий `readiness_score`
- низкая `good_day_probability`

Интерпретация:

- высокая усталость  
- риск перегрузки  

Рекомендация:

- отдых или легкая тренировка  

---

### 5.2 Moderate readiness

Условие:

- средний `readiness_score`
- умеренная `good_day_probability`

Интерпретация:

- нормальное состояние  

Рекомендация:

- умеренная нагрузка  

---

### 5.3 High readiness

Условие:

- высокий `readiness_score`
- высокая `good_day_probability`

Интерпретация:

- хорошее восстановление  

Рекомендация:

- интенсивная тренировка  

---

## 6. Adjustments

Базовая модель уже включает recovery-контур и может быть расширена:

---

### 6.1 Recent load spike

Если:

- резкий рост нагрузки за последние 2–3 дня  

→ снижать readiness  

---

### 6.2 Consecutive training days

Если:

- несколько дней подряд без отдыха  

→ снижать readiness  

---

### 6.3 Recovery gap

Если:

- длительный отдых  

→ повышать readiness  

---

### 6.4 Recovery signals

Если:

- sleep ниже baseline
- HRV ниже baseline
- resting HR выше baseline

→ снижать readiness даже при приемлемом `freshness`

---

## 7. Output

Результат модели:

- `readiness_score`
- `good_day_probability`
- readiness zone
- вход для тренировочной рекомендации

---

## 8. Determinism requirement

При одинаковых входных данных:

- результат должен быть одинаковым  
- не допускается случайность  

---

## 9. Limitations

Текущая модель:

- использует простой recovery score как текущий recovery-контур
- пока не фиксирует окончательную калибровку весов и зон
- требует дальнейшей верификации на реальных данных

---

## 10. Future extensions

Планируется:

- калибровка весов `freshness` и `recovery_score_simple`
- явные `sleep_score_simple`, `hrv_dev`, `rhr_dev`
- уточнение зон и probability thresholds

Но:

- без потери прозрачности  

---

## 11. Debugging model

Если результат кажется неверным:

проверять:

1. входные данные  
2. расчет `load_state_daily_v2`
3. расчет `health_recovery_daily`
4. формирование `readiness_score_raw`
5. примененные правила маппинга в zone / probability

---

## 12. Design constraint

Любое усложнение модели должно:

- улучшать объяснимость  
- не нарушать deterministic поведение  
- быть обоснованным  

Иначе — не добавлять.
