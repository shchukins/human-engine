# Web Today Surface Proposal

Status: accepted implementation baseline for issue #119.

## Goal

Provide the minimum wearable-independent Whatte daily loop from a phone browser:

1. read the current backend-owned readiness and recommendation;
2. submit or edit today's one-tap recovery feeling;
3. submit or edit one-tap RPE for the latest eligible activity.

The web surface is a delivery and interaction layer. It does not calculate
readiness, interpret missing physiology, or duplicate recommendation rules.

## Surface and ownership

- Add a dedicated FastAPI SSR route at `/today`.
- Keep `/dashboard` operational and read-only.
- Use the configured `DAILY_READINESS_USER_ID` for the current single-user
  deployment; do not accept an arbitrary user id from the browser.
- Protect `/today` at the Caddy edge with the same Basic Auth policy as the
  internal dashboard.
- Use native HTML forms and mobile-first CSS. No SPA, frontend build step, or
  JavaScript state is required for the primary flow.

## Read model

The server builds one Today view from existing backend state:

- latest current-version `readiness_daily` response, including deterministic
  recommendation, briefing, signal families, data quality, and freshness;
- today's date-level `next_day_recovery` feedback when present;
- the most recent canonical, non-deleted, non-excluded activity missing
  `post_ride_rpe`;
- when no activity is missing RPE, the latest eligible activity and its current
  RPE remain available for editing.

Missing physiology is rendered from the existing signal-family availability
contract as unavailable. It is not converted into a score or an error.

## Write paths

Morning recovery reuses `upsert_next_day_recovery_feedback`. Its existing
idempotent natural key updates the date-level row, then the service recomputes
readiness for the same date.

Post-workout RPE reuses `upsert_activity_subjective_feedback`. Its canonical
activity key updates the existing row instead of inserting a duplicate.

Both paths use the documented `web` feedback source, validate the 1-5 score on
the backend, reject cross-site form submissions, and use POST/redirect/GET.

## Failure and empty states

- missing readiness: show that a recommendation is not available yet;
- stale readiness: show the backend freshness state and calculation evidence;
- missing physiology: show unavailable, not failed;
- no eligible activity: show a completed/empty RPE state;
- section read failure: preserve the rest of the page and show a bounded error;
- write failure: do not claim success and do not manufacture local state.

## Tests

- Today aggregation for full, partial, missing, and stale data;
- missing physiology rendering;
- latest missing-RPE selection and editable existing values;
- recovery/RPE insert and update through existing idempotent services;
- readiness refresh after recovery feedback;
- 1-5 validation, user/activity ownership, cross-site rejection, and PRG;
- responsive HTML semantics and regression coverage for `/dashboard`.

## Explicit non-goals

- no readiness or recommendation formula changes;
- no direct readiness contribution from raw RPE before #118;
- no additional sleep, stress, motivation, or fatigue questions;
- no trend chart, planner, OAuth, multi-user account model, or new frontend
  framework;
- no production deployment as part of the repository change.
