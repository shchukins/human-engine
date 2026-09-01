# Training Response Metrics

## 1. Purpose

`activity_response_metrics` is the deterministic activity-level layer that
describes how much a completed workout cost the athlete. It combines existing
objective activity metrics with optional post-ride RPE without requiring
HealthKit.

The layer is versioned, persisted, recomputable from source data, and separate
from readiness scoring.

## 2. Inputs

- canonical, non-deleted, non-excluded `strava_activity_raw` row
- `activity_metrics` version `v1`
- `time`, `watts`, and `heartrate` raw streams when present
- canonical `post_ride_rpe` feedback when present

Missing inputs remain unavailable. They are never converted to zero.

## 3. Version 1 metrics

Version `v1` persists:

- average and normalized power
- average heart rate
- average-power / HR and normalized-power / HR ratios
- aerobic decoupling for eligible steady workouts
- RPE on the existing 1-5 Whatte scale
- session-RPE load: `duration_minutes * RPE`
- RPE / intensity factor
- session-RPE load / TSS
- per-metric availability and reason codes

### 3.1 Aerobic decoupling

An activity is eligible only when:

- duration is at least 30 minutes
- variability index is available and `<= 1.10`
- aligned positive power and HR cover at least 80% of stream duration

For eligible activities, time-weighted power / HR is calculated independently
for the first and second halves:

```text
decoupling_pct = (first_half_power_hr / second_half_power_hr - 1) * 100
```

A positive value means power / HR deteriorated in the second half. Pauses,
missing samples, non-positive power, and non-positive HR do not contribute.

### 3.2 Intensity bands

Comparable groups use activity type plus the following intensity-factor band:

- `< 0.55`: `recovery`
- `0.55 .. < 0.75`: `endurance`
- `0.75 .. < 0.90`: `tempo`
- `0.90 .. < 1.05`: `threshold`
- `>= 1.05`: `high_intensity`

Without intensity factor, the response row remains valid but no intensity-band
baseline is claimed.

## 4. Personal baseline

Each response row stores a baseline snapshot from up to 20 earlier canonical
activities with the same user, activity type, intensity band, and response
version. The current activity is excluded.

For every metric independently:

- at least 3 non-null historical values are required
- the baseline is their median
- deviation is `(current / baseline - 1) * 100`

The snapshot stores sample counts and explicit insufficient-sample reasons. No
synthetic aggregate `response_score` is created in version 1.

## 5. Lifecycle

The row is upserted:

- after activity metrics and canonical deduplication in the Strava pipeline
- after post-ride RPE is inserted or edited through Telegram or Web Today

An RPE update also recomputes existing readiness rows in the activity's
seven-day response window so stored readiness explanations receive the current
response context.

## 6. Readiness boundary

The latest response row from the preceding seven days is exposed in the stable
`response` signal family:

- `availability = available`
- `used = false`
- `score = null`
- `effective_weight = 0`
- `contribution = 0`
- reason code `response_context_only_phase_1`

Making response readiness-bearing requires a separately reviewed formula and a
new formula/version contract. Version 1 does not silently alter readiness.
