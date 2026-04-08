# Metrics

## 1. Purpose

Этот документ описывает базовые метрики Human Engine.

Цель:

- зафиксировать формулы  
- обеспечить воспроизводимость  
- сделать логику прозрачной  

---

## 2. Principles

Все метрики должны быть:

- deterministic  
- объяснимыми  
- воспроизводимыми  

Нельзя:

- использовать скрытые формулы  
- менять определения без фиксации  

---

## 3. Activity-level metrics

Метрики, рассчитываемые для одной тренировки.

---

### 3.1 Duration

Время тренировки.

---

### 3.2 Average Power

Средняя мощность.

---

### 3.3 Normalized Power (NP)

Оценка "эффективной" мощности с учетом вариативности нагрузки.

---

### 3.4 Intensity Factor (IF)

IF = NP / FTP

---

### 3.5 Training Stress Score (TSS)

TSS = (Duration × NP × IF) / (FTP × 3600) × 100

---

## 4. Daily metrics

Агрегируются на уровне дня.

---

### 4.1 Daily Training Load

Сумма TSS за день.

---

### 4.2 Nonlinear Load Input

Для model v2 дневная нагрузка подается в load model через нелинейную функцию.

Формула:

```text
load_input = A * (1 - exp(-B * TSS))
```

---

### 4.3 Fitness

Долгосрочная адаптационная компонента.

Экспоненциальное скользящее среднее:

- `tau_fitness ≈ 40`

---

### 4.4 Fatigue Fast

Короткая компонента усталости.

- `tau_fatigue_fast ≈ 2`

---

### 4.5 Fatigue Slow

Средняя по длительности компонента усталости.

- `tau_fatigue_slow ≈ 7`

---

### 4.6 Fatigue Total

```text
fatigue_total = fatigue_fast + fatigue_slow
```

---

### 4.7 Freshness

```text
freshness = fitness - fatigue_total
```

---

## 5. Derived metrics

---

### 5.1 Fatigue

В model v2 представлена как:

- `fatigue_fast`
- `fatigue_slow`
- `fatigue_total`

---

### 5.2 Fitness

`fitness` остается отдельной сглаженной компонентой load state.

---

### 5.3 Form

В качестве основной прикладной метрики model v2 использует `freshness`.

Legacy-метрики `CTL / ATL / TSB` могут использоваться только как reference baseline или для обратной совместимости.

---

## 6. Readiness (model v2)

Readiness — ключевая метрика системы.

В model v2 readiness:

- не равна `freshness`
- рассчитывается из `load_state + recovery_state`
- может сопровождаться `good_day_probability`

Базовая формула:

```text
readiness_score_raw =
    w1 * freshness +
    w2 * recovery_score_simple
```

Probability layer:

```text
good_day_probability = sigmoid(readiness_score_raw)
```

---

## 7. Constraints

Метрики должны:

- быть пересчитываемыми  
- использовать raw данные  
- не зависеть от AI  

---

## 8. Future extensions

Планируется добавить:

- `sleep_score_simple`
- `hrv_dev`
- `rhr_dev`
- уточненную калибровку probability / readiness zones

Но:

- только без потери прозрачности и versioning

---

## 9. Versioning

При изменении формул:

- фиксировать версию  
- не менять исторические расчеты  
