# Ride Briefing

## 1. Purpose

Этот документ описывает, как Human Engine должен формировать ride briefing поверх текущей readiness layer.

Ride briefing — это пользовательский вывод системы перед тренировкой.

Цель:

- перевести readiness state в понятную рекомендацию
- сохранить детерминированность
- опираться на уже реализованные backend layers

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
- выдавать рекомендации, которые нельзя объяснить через readiness inputs

---

## 3. Current backend basis

На текущем этапе ride briefing должен опираться на уже реализованные слои:

- `health_recovery_daily`
- `load_state_daily_v2`
- `readiness_daily`

Это важно, потому что:

- readiness больше не равен freshness
- briefing должен учитывать двухконтурную модель `load + recovery`
- вероятность хорошего тренировочного дня уже выделена в отдельный слой

---

## 4. Inputs

Практический вход для ride briefing:

- `readiness_score`
- `good_day_probability`
- `status_text`
- `freshness`
- `recovery_score_simple`
- `explanation_json`

Дополнительные rule-based inputs могут использоваться позже, но их нужно отделять от уже реализованного backend baseline.

---

## 5. Output structure

Ride briefing должен содержать:

### 5.1 Readiness status

Краткий статус состояния, основанный на `status_text`.

---

### 5.2 Load recommendation

Рекомендация по уровню нагрузки:

- rest
- easy
- moderate
- hard

---

### 5.3 Short explanation

Краткое объяснение, связывающее вывод с двумя контурами:

- load contour
- recovery contour

Примеры формулировок:

- высокая усталость по load contour при слабом recovery signal
- нормальная готовность: load и recovery не конфликтуют
- хорошая готовность: recovery поддерживает благоприятный load state

---

### 5.4 Optional constraints

Если нужно, briefing может содержать ограничения:

- избегать высокой интенсивности
- ограничить длительность
- не делать второй тяжелый день подряд

Эти ограничения должны появляться только как явные rule-based additions.

---

## 6. Mapping rules

Текущее требование к mapping:

- опираться на `readiness_score` и `good_day_probability`
- не сводить решение только к `freshness`
- сохранять объяснимую связь с recovery layer

Пример минимального baseline mapping:

- низкий readiness -> `rest` или `easy`
- средний readiness -> `moderate`
- высокий readiness -> `hard`

Точный mapping еще требует продуктовой фиксации.

---

## 7. Format requirement

Формат ride briefing должен быть стандартизирован.

Пример структуры:

- Status: `Нормальная готовность`
- Recommendation: `Moderate load`
- Reason: `Load contour stable, recovery score supports normal training`

Для UI могут существовать разные представления, но логическая структура должна оставаться одинаковой.

---

## 8. Determinism requirement

При одинаковых входных данных ride briefing должен быть одинаковым.

Это означает:

- одинаковый статус
- одинаковая категория нагрузки
- одинаковое объяснение по шаблону

Допускается только шаблонная вариативность без изменения логики.

---

## 9. Not in scope

На текущем этапе ride briefing не включает:

- свободный coaching text
- разговорный AI-стиль
- скрытые эвристики вне readiness layer
- длинные персонализированные советы

---

## 10. Future extensions

В будущем можно добавить:

- тип целевой тренировки
- рекомендуемую длительность
- ограничения по зонам мощности или пульса
- дополнительный explainability layer

Но только после фиксации decision mapping поверх текущего readiness baseline.

---

## 11. Debugging

Если ride briefing кажется неверным, проверять:

1. `health_recovery_daily`
2. `load_state_daily_v2`
3. `readiness_daily`
4. mapping rule from readiness to recommendation

---

## 12. Design constraint

Ride briefing должен оставаться частью deterministic decision layer.

Любое изменение должно:

- сохранять объяснимость
- сохранять воспроизводимость
- опираться на уже реализованные backend layers
