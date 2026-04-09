# Readiness Model

## 1. Purpose

Этот документ описывает текущую readiness model в Human Engine.

Цель:

- определить, насколько спортсмен готов к нагрузке
- зафиксировать текущую baseline-логику backend
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
- подменять readiness только load-only proxy

---

## 3. Inputs

Текущая model v2 использует:

- `freshness` из `load_state_daily_v2`
- `recovery_score_simple` из `health_recovery_daily`

Важно:

- readiness больше не равен freshness
- recovery contour не заменяет fatigue, а дополняет load contour

Дополнительные сигналы, такие как `sleep_score_simple`, `hrv_dev`, `rhr_dev`, пока не являются отдельными входами readiness formula.

---

## 4. Core logic

Основная идея:

> readiness определяется сочетанием load state и recovery state

### 4.1 Load contour

Load contour формируется в `load_state_daily_v2`:

- `fitness`
- `fatigue_fast`
- `fatigue_slow`
- `fatigue_total`
- `freshness`

Где:

- `fatigue_total = 0.65 * fatigue_fast + 0.35 * fatigue_slow`
- `freshness = fitness - fatigue_total`

### 4.2 Recovery contour

Recovery contour формируется в `health_recovery_daily` из:

- сна
- HRV
- resting HR
- веса

Текущий прикладной выход этого слоя:

- `recovery_score_simple`

### 4.3 Baseline formula v2

Сначала `freshness` нормализуется:

```text
freshness_norm = clamp(50 + freshness, 0, 100)
```

Затем readiness считается так:

```text
readiness_score_raw = 0.6 * freshness_norm + 0.4 * recovery_score_simple
```

Fallback behavior:

- если нет recovery score, используется `freshness_norm`
- если нет load score, используется `recovery_score_simple`

### 4.4 Final outputs

```text
readiness_score = clamp(round(readiness_score_raw, 1), 0, 100)
good_day_probability = readiness_score / 100
```

`good_day_probability` пока является baseline probability-like mapping, а не откалиброванной статистической вероятностью.

---

## 5. Status zones

Текущие статусные зоны backend:

### 5.1 Высокая усталость

- `readiness_score <= 24`

### 5.2 Нагрузка

- `25 <= readiness_score <= 44`

### 5.3 Нормальная готовность

- `45 <= readiness_score <= 64`

### 5.4 Хорошая готовность

- `65 <= readiness_score <= 84`

### 5.5 Очень свежий

- `readiness_score >= 85`

---

## 6. Output

Результат текущей модели:

- `readiness_score_raw`
- `readiness_score`
- `good_day_probability`
- `status_text`
- `explanation_json`

`readiness_daily` является отдельным storage layer для этих outputs.

---

## 7. Explanation payload

Текущий `explanation_json` хранит:

- `freshness`
- `freshness_norm`
- `recovery_score_simple`
- веса формулы
- строку формулы

Это нужно для explainability и отладки.

---

## 8. Limitations

Текущая модель:

- использует простой recovery score как baseline recovery contour
- пока не использует индивидуальные baseline deviations
- пока не имеет отдельной probability calibration
- требует дальнейшей верификации на реальных данных

---

## 9. Planned extensions

Планируется:

- калибровка весов `freshness_norm` и `recovery_score_simple`
- явные `sleep_score_simple`, `hrv_dev`, `rhr_dev`
- уточнение interpretation layer для `good_day_probability`
- уточнение decision mapping

Но:

- без потери прозрачности
- с явным versioning

---

## 10. Debugging model

Если результат кажется неверным, проверять:

1. входные данные HealthKit и training load
2. расчет `health_recovery_daily`
3. расчет `load_state_daily_v2`
4. нормализацию `freshness`
5. формирование `readiness_score_raw`
6. status mapping и probability mapping

---

## 11. Design constraint

Любое усложнение модели должно:

- улучшать объяснимость
- не нарушать deterministic поведение
- быть отделено от planned layers

Иначе его не нужно добавлять.
