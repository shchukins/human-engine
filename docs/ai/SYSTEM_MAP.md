# System Map

## 1. Purpose

Human Engine — система, которая:

> преобразует тренировочные данные в решение о нагрузке

---

## 2. End-to-end flow
Data Sources
↓
Data Engine
↓
Data Storage
↓
Normalized / Daily Features
↓
Load Model + Recovery Model
↓
Readiness Engine
↓
Recommendation
↓
Workout Outcome
↓
Feedback
↓
Model update

---

## 3. Layer breakdown

### 3.1 Data layer

Отвечает за получение и хранение данных.

Включает:

- Strava webhook  
- ingestion pipeline  
- raw data storage  

Свойства:

- данные не теряются  
- данные не искажаются  

---

### 3.2 Processing layer

Преобразует данные в признаки.

- feature extraction  
- расчет базовых метрик  

---

### 3.3 Modeling layer

Оценивает состояние человека.

- load model v2
- recovery model
- fitness / fast fatigue / slow fatigue
- readiness score
- good day probability

---

### 3.4 Decision layer

Формирует вывод системы.

- readiness  
- recommendation  
- ride briefing  

---

### 3.5 Feedback loop

Система обучается на результате:

- фактическая тренировка  
- отклонение от прогноза  
- корректировка модели  

---

## 4. Key properties

Система должна быть:

### Deterministic
- одинаковый вход → одинаковый результат  

### Reproducible
- любой расчет можно повторить  

### Observable
- можно объяснить результат  

---

## 5. What is NOT part of the core flow

Не входит в основной pipeline:

- LLM  
- генеративные модели  
- AI-решения  

AI может работать только как:

- слой объяснения  
- инструмент навигации  
- developer assistant  

---

## 6. Mental model

Human Engine — это не один алгоритм.

Это цепочка:

> данные → состояние → решение

Если система дает неправильный результат:

ошибка всегда находится в одном из слоев:

- данные  
- признаки  
- модель  
- логика решения  

---

## 7. Current vs Future

### Сейчас:

- ingestion pipeline  
- raw data  
- базовая архитектура  

### Далее:

- normalized and daily feature layer
- load state v2
- recovery-aware readiness
- good day probability
- prediction  
- adaptive training  

---

## 8. Simplification rule

При развитии системы:

> каждый новый элемент должен вписываться в эту схему

Если не вписывается:

- либо он лишний  
- либо схема нарушена  
