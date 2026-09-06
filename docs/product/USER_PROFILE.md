# Dated user profile

Implemented in the backend and Web Today at `/today/profile`.

The existing edge protection for `/today*` applies. The account is resolved from
`DAILY_READINESS_USER_ID`; this is a single-user surface, not an account system.

## Behavior

- FTP (watts) and weight (kg) have independent effective-date histories.
- Each value applies from its date until the next entry for the same metric.
- Saving the same metric/date corrects that entry; it does not append a duplicate.
- Future dates, non-finite values, FTP outside 1–1000 W and weight outside
  1–500 kg are rejected. Limits are input validation, not physiology thresholds.
- Historical FTP rows are initially copied from `user_training_profile`.
- Weight starts empty. Historical HealthKit weight remains separate; a manually
  entered profile weight is not a recovery observation and does not affect TSS
  or readiness.

## Calculations

Both ingestion and the debug metric endpoint resolve FTP on the activity's
calendar date in `WHATTE_TIMEZONE`. They do not use a later FTP for an earlier
activity. The resolved FTP is preserved in `activity_metrics.raw_json.ftp_watts`.
The TSS formula remains unchanged.

Legacy power/HR zone boundaries use their own dated training profile. Editing
FTP does not silently rescale these boundaries. If zone boundaries are absent,
zone times are unavailable (`null`). Zone editing is outside this first version.

Changing FTP persists `needs_recompute`. The page offers an explicit recalculation
from the earliest pending date. It rebuilds stored activity metrics, canonical
activity responses in chronological order, daily load, fitness and readiness
through today, including rest days. No Strava requests or Telegram messages are
sent. Existing notifications and decision snapshots are not rewritten.

Recalculation is synchronous. Per-user advisory locks serialize profile edits
and recalculations; another simultaneous submission receives HTTP 409. Existing
pipeline services commit in stages. A failure can therefore leave partially
updated derived data: pending flags are cleared only after all stages succeed,
and the page explicitly offers a retry. Missing stored streams must be restored
before a failed calculation can succeed. Ingestion is not locked by this form;
if it runs concurrently, repeat the calculation after ingestion completes.

## Deployment

Apply `db-init/011_user_profile.sql` to the existing database before starting the
updated backend and worker. Merely restarting Docker does not apply db-init SQL
to an existing volume. The migration is additive and rerunnable; it preserves
existing profile entries. Deploy the same code to both backend and worker.

After deployment, enter FTP **222 W effective 2026-07-25** on the profile page,
then run its recalculation action. Enter weight only when supplied by the user;
no weight is inferred. Check the resulting TSS and pending status before treating
the historical correction as complete.

Production migration and the user's values are not applied by a code deployment
alone. The original Telegram layout changes remain a separate task.
