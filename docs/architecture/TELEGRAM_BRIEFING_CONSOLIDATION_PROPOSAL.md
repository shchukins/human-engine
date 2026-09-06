# Telegram Briefing Consolidation Proposal

## Scope

Unify the two Telegram notification paths behind the existing deterministic
decision layer. This is a delivery-layer change only: it does not alter
readiness composition, load metrics, thresholds, recommendation zones, or
database schema.

## Observed gap

`readiness_query` and the daily Telegram notification independently compose a
recommendation and briefing from the same persisted `readiness_daily` row.
The post-workout notification reads persisted state, but renders only a
partial readiness summary rather than the shared decision briefing.

Some notification helpers are legacy freshness-derived readiness and
trend/impact formatting. They must not remain reachable from Telegram
delivery, because they could reintroduce a synthetic readiness summary outside
the current versioned readiness contract.

## Minimal change

1. Add one decision-engine function that accepts a persisted readiness output
   (`readiness_score`, `status_text`, and `explanation_json`) and returns the
   existing deterministic recommendation, reason, and Russian briefing.
2. Make readiness API serialization, daily Telegram delivery, and supported
   post-workout delivery use that function.
3. Keep post-workout activity facts sourced from persisted `activity_metrics`
   and `load_state_daily_v2`; attach the shared briefing only when the
   current-version `readiness_daily` row for the activity date exists.
4. Remove legacy Telegram-path helpers that derive readiness, trends, or
   impact from freshness. Missing persisted state remains explicit; it is not
   synthesized.
5. Keep optional physiology display conditional on actual exact-date values;
   no `n/a` placeholders are emitted.

## Acceptance checks

- Daily and post-workout Telegram paths consume the same decision contract.
- No Telegram query references `daily_fitness_state`.
- A missing current-version readiness row does not produce a derived score or
  recommendation.
- Missing optional physiology creates no `n/a` or empty physiology rows.

## Non-goals

- No production operation, migration, model-version change, or readiness
  formula change.
- No new recommendation policy or training-planning behavior.
