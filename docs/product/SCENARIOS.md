# Scenarios

## 1. Purpose

Этот документ описывает пользовательские сценарии Human Engine.

Цель:

- связать систему с реальным использованием
- показать, как формируется ценность
- зафиксировать ключевые user flows

---

## 2. Core scenario

### Daily training decision

Основной сценарий системы:

> пользователь хочет понять, в каком состоянии он находится сегодня и насколько день выглядит подходящим для нагрузки

### Flow

1. Пользователь открывает систему
2. Система анализирует последние данные
3. Рассчитывается readiness
4. Система возвращает status / score / probability и explanation
5. Пользователь принимает решение

### Output

Пользователь получает:

- текущий статус готовности
- readiness score
- good day probability
- краткое объяснение

Комментарий:

- readiness output уже реализован в backend
- recommendation / ride briefing layer пока остается planned

---

## 3. Scenario: After hard training block

### Context

- несколько дней высокой нагрузки
- накопленная усталость

### Expected system behavior

- снижение readiness
- снижение `good_day_probability`
- explanation через load + recovery breakdown

---

## 4. Scenario: After recovery

### Context

- период снижения нагрузки
- восстановление

### Expected system behavior

- рост readiness
- рост `good_day_probability`

---

## 5. Scenario: Stable training

### Context

- регулярные тренировки
- умеренная нагрузка

### Expected system behavior

- стабильный readiness
- стабильный readiness output без скрытой логики

---

## 6. Scenario: Load spike

### Context

- резкий рост нагрузки

### Expected system behavior

- корректировка readiness вниз
- корректировка probability вниз

---

## 7. Scenario: No recent data

### Context

- нет тренировок
- недостаточно данных

### Expected system behavior

- ограниченная уверенность
- fallback на доступные слои readiness

---

## 8. Scenario: Incomplete data

### Context

- отсутствуют некоторые метрики
- нет power / HR

### Expected system behavior

- использовать доступные данные
- не ломать модель
- явно ограничивать точность

---

## 9. Scenario: Long break

### Context

- длительный перерыв

### Expected system behavior

- формально возможен рост readiness за счет текущего baseline
- downstream decision layer должен учитывать это отдельно, когда будет реализован

---

## 10. System behavior expectations

Во всех сценариях система должна:

- быть предсказуемой
- быть объяснимой
- не давать противоречивые outputs между score, probability и status

---

## 11. Not in scope

Система пока не делает:

- долгосрочное планирование
- автоматическое построение тренировочных программ
- персонализированный coaching
- production-calibrated decision layer

---

## 12. Future scenarios

Планируется:

- адаптивные планы тренировок
- recommendation layer
- ride briefing layer
- прогнозирование результата
- интеграция с календарем

---

## 13. Usage

Этот документ используется для:

- проверки логики модели
- тестирования
- проектирования UI
- работы с AI

---

## 14. Validation

Сценарии должны:

- соответствовать реальному поведению системы
- использоваться в тестах
- обновляться при изменениях логики
