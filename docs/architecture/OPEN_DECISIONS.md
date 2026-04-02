# Open Decisions

Этот документ фиксирует архитектурные и продуктовые вопросы,
которые на данный момент не имеют окончательного решения.

Цель:

- сохранить контекст размышлений  
- избежать потери важных вопросов  
- поддерживать осознанное развитие системы  

---

## OD-001: Readiness model definition

### Context

Readiness — ключевая метрика системы.

Но не определено:

- точная формула  
- набор входных параметров  
- баланс между простотой и точностью  

---

### Options

1. Простая модель (CTL / ATL / TSB аналог)
2. Расширенная модель (учет HR, HRV, сна)
3. Гибридная модель

---

### Open questions

- какой минимальный набор данных нужен  
- насколько модель должна быть объяснимой  
- допустима ли аппроксимация  

---

### Status

open  

---

## OD-002: Feature layer design

### Context

Feature layer пока не реализован.

Нужно решить:

- где он живет  
- как хранится  
- как пересчитывается  

---

### Options

1. SQL-based (materialized views)
2. Python pipeline
3. гибрид  

---

### Open questions

- как обеспечить воспроизводимость  
- как делать перерасчет  
- как хранить версии  

---

### Status

open  

---

## OD-003: Prediction model

### Context

Система предполагает прогноз:

- как тренировка повлияет на состояние  

Но пока нет модели.

---

### Options

1. Простая эвристика  
2. Физиологическая модель  
3. ML-подход  

---

### Open questions

- нужен ли ML вообще  
- как валидировать прогноз  
- какие метрики использовать  

---

### Status

open  

---

## OD-004: Data sources expansion

### Context

Сейчас используется Strava.

В будущем возможны:

- Garmin  
- HealthKit  
- HRV  
- сон  

---

### Options

1. Strava-only (MVP)
2. Multi-source aggregation
3. Приоритет Apple Health  

---

### Open questions

- как синхронизировать источники  
- что считать источником истины  
- как решать конфликты данных  

---

### Status

open  

---

## OD-005: Ride briefing format

### Context

Ride briefing — ключевой output системы.

Но не определено:

- формат  
- уровень детализации  
- структура  

---

### Options

1. Короткий текст  
2. Структурированный блок  
3. Полноценный план тренировки  

---

### Open questions

- насколько детализирован должен быть вывод  
- нужен ли адаптивный формат  
- как сохранять детерминированность  

---

### Status

open  

---

## OD-006: UI / Visualization layer

### Context

Визуализация пока отсутствует.

---

### Options

1. Web dashboard  
2. Mobile-first (iOS)  
3. Минималистичный интерфейс  

---

### Open questions

- что показывать в первую очередь  
- какие метрики критичны  
- как не превратить систему в "dashboard без смысла"  

---

### Status

open  

---

## OD-007: Storage strategy for derived data

### Context

Появятся производные данные:

- features  
- метрики  
- readiness  

---

### Options

1. хранить все  
2. пересчитывать на лету  
3. гибрид  

---

### Open questions

- баланс storage vs compute  
- как обеспечивать консистентность  
- как делать versioning  

---

### Status

open  

---

## OD-008: AI reintroduction strategy

### Context

AI временно удален из core.

В будущем возможен возврат.

---

### Options

1. только RAG  
2. AI как explainability слой  
3. ограниченные AI endpoints  

---

### Open questions

- где проходит граница допустимого  
- как не нарушить deterministic core  
- какие use-cases действительно полезны  

---

### Status

deferred  

---

## How to use this document

- добавлять новые вопросы по мере появления  
- не удалять старые, а переводить в ARCHITECTURE_DECISIONS  
- регулярно пересматривать  

---

## Lifecycle

open → decision → ADR  

После принятия решения:

- перенос в ARCHITECTURE_DECISIONS.md  
- обновление архитектуры при необходимости  