# Wearable-independent Morning Loop pilot

## Purpose

This report measures the reliability and observed use of the deterministic
morning loop for GitHub issue #108. It reads stored backend state and does not
recompute readiness or change model parameters.

## Scope and command

The inclusive interval uses `WHATTE_TIMEZONE` unless a timezone is passed. The
unit for morning metrics is one local calendar day. The unit for post-workout
RPE is one canonical activity with a successfully stored RPE prompt delivery.

Run from `backend/`:

```bash
python -m scripts.pilot_report \
  --user-id sergey \
  --date-from 2026-09-01 \
  --date-to 2026-09-14
```

The command writes JSON to stdout and performs only `SELECT` queries.

## Metric definitions

| Metric | Numerator | Denominator | Stored source |
|---|---|---|---|
| Valid morning recommendation | Days with current-version readiness and a deterministic recommendation | All local days | `readiness_daily` |
| Valid recommendation without physiology | Valid days where physiology availability is false | Valid recommendation days | `readiness_daily.explanation_json.signal_families` |
| Morning recovery response | Eligible days with recovery feedback | Days after a stored training day | `daily_training_load`, `activity_subjective_feedback` |
| Post-workout RPE completion | Prompted canonical activities with RPE | Canonical activities with a successful RPE prompt | `activity_delivery_log`, `activity_subjective_feedback` |
| Signal-family distribution | Days where each family is available or used | Counts over the interval | `readiness_daily.explanation_json` |
| Stale/missing required training input | Days without a same-local-day training source snapshot | All local days | `readiness_daily.explanation_json.source_timestamps` |
| Recommendation change after check-in | Check-ins whose score or recommendation changed | Check-ins with before and after snapshots | `decision_context_snapshot` |
| Ingestion failures | Failed/error ingest jobs | Count | `strava_activity_ingest_job` |
| Delivery failures | Failed readiness deliveries and recovery prompts | Count | notification and prompt logs |

Every rate includes its numerator and denominator. A zero denominator produces
`null`, not zero percent.

## Historical decision snapshots (#78 production slice)

`decision_context_snapshot` stores append-only evidence after an accepted daily
readiness delivery and immediately before and after a recovery check-in. It
stores the computed decision, model version, explanation, source timestamps,
and signal availability. It does not participate in model calculations.
Identical retries are idempotent by a SHA-256 fingerprint of decision state.

Snapshots begin after migration `010_decision_context_snapshot.sql`. Earlier
before/after states cannot be reconstructed reliably because `readiness_daily`
and feedback upserts retain canonical current state.

## Explicit limitations

- Duplicate delivery attempts are not historically countable. Lifecycle tables
  keep canonical state instead of every attempt. The report returns
  `not_measurable` rather than an invented zero rate.
- API and Web share the backend readiness query, but historical rendered output
  is not recorded. Full presentation consistency is `not_measurable`.
- Processing, decision, and presentation failures lack a durable relational
  event store. Their report values are `null`; Loki remains operational evidence.
- Fourteen rows satisfy only interval length. Conclusions still require review
  of missing data and actual participation.
