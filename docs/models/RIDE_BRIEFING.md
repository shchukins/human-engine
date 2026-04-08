# Ride Briefing

## 1. Purpose

Этот документ описывает, как Human Engine формирует ride briefing.

Ride briefing — это пользовательский вывод системы перед тренировкой.

Цель:

- перевести состояние readiness в понятную рекомендацию
- сделать вывод стабильным и детерминированным
- обеспечить прозрачную связь между метриками и рекомендацией

---

## 2. Principles

Ride briefing должен быть:

- deterministic
- кратким
- понятным
- основанным на явных правилах

Нельзя:

- генерировать briefing свободным LLM-текстом
- использовать скрытую логику
- давать рекомендации, которые нельзя объяснить через входные метрики

---

## 3. Inputs

Ride briefing строится на основе:

- readiness zone
- readiness score
- good_day_probability
- freshness
- recovery signals
- recent training load
- consecutive training days

Минимально достаточный вход для MVP:

- `readiness_daily`
- `load_state_daily_v2`
- recovery summary из `health_recovery_daily`

---

## 4. Output structure

Ride briefing должен содержать:

### 4.1 Readiness status

Краткий статус состояния:

- low readiness
- moderate readiness
- high readiness

---

### 4.2 Load recommendation

Рекомендация по уровню нагрузки:

- rest
- easy
- moderate
- hard

---

### 4.3 Short explanation

Краткое объяснение причины рекомендации.

Примеры:

- высокая накопленная усталость при слабом recovery signal
- сбалансированное состояние load и recovery
- хорошее восстановление после снижения нагрузки

---

### 4.4 Optional constraints

Если нужно, briefing может содержать ограничения:

- избегать высокой интенсивности
- ограничить длительность
- не выполнять вторую тяжелую тренировку подряд

---

## 5. Mapping rules

### 5.1 Low readiness

Если readiness = low:

- recommendation = rest или easy
- explanation = сочетание freshness и recovery указывает на низкую готовность

---

### 5.2 Moderate readiness

Если readiness = moderate:

- recommendation = moderate
- explanation = load state и recovery state допускают обычную нагрузку

---

### 5.3 High readiness

Если readiness = high:

- recommendation = hard или key workout
- explanation = load state стабилен, recovery поддерживает высокую готовность

---

## 6. Rule-based adjustments

Итоговая рекомендация может быть понижена, если:

- был резкий всплеск нагрузки
- несколько дней подряд были тренировки
- recovery signals ухудшились
- наблюдается накопление `fatigue_total`

Итоговая рекомендация может быть повышена только в пределах заранее определенных правил.

---

## 7. Format requirement

Формат ride briefing должен быть стандартизирован.

Пример структуры:

- Status: Moderate readiness
- Recommendation: Moderate load
- Reason: Balanced load state with adequate recovery signal

Для пользовательского интерфейса могут существовать разные представления,
но логическая структура должна оставаться одинаковой.

---

## 8. Determinism requirement

При одинаковых входных данных ride briefing должен быть одинаковым.

Это означает:

- одинаковая категория readiness
- одинаковая рекомендация
- одинаковое объяснение по шаблону

Допускается только шаблонная вариативность, если она не меняет смысл и управляется явными правилами.

---

## 9. Not in scope

На текущем этапе ride briefing не включает:

- свободный coaching text
- психологическую мотивацию
- разговорный AI-стиль
- персонализированные длинные советы

Это может быть отдельным дополнительным слоем позже, но не частью core логики.

---

## 10. Future extensions

В будущем можно добавить:

- тип целевой тренировки
- рекомендуемую длительность
- ограничения по зонам мощности или пульса
- дополнительный explainability layer

Но только после стабилизации базовой модели.

---

## 11. Debugging

Если ride briefing кажется неверным, проверять:

1. readiness inputs
2. readiness zone
3. applied adjustments
4. final mapping rule

---

## 12. Design constraint

Ride briefing является частью deterministic core.

Любое изменение должно:

- сохранять объяснимость
- сохранять воспроизводимость
- не превращать вывод в black box
