# Readiness Signal Composition Proposal

Status: implemented baseline for issue #117, including readiness-bearing
response metrics from issue #118.

## Goal

Make the daily readiness decision work without HealthKit while keeping every
input family explicit, deterministic, and independently observable.

The stable signal-family contract is:

- `load`
- `freshness`
- `response`
- `feeling`
- `physiology`

Each family exposes availability, whether it was used in the score, its score
when one exists, its effective weight, its readiness-point contribution, and
reason codes.

## Current composition

Phase 1 preserves the established readiness meaning and avoids double-counting
load:

- `load` exposes current load-state context but is not scored independently;
  `freshness` is the current readiness-bearing summary of that load state.
- `freshness` keeps a configured weight of `0.6`.
- `response` receives up to `0.2` from the existing `0.4` evidence budget.
- available `feeling` and `physiology` share the remaining evidence budget.
- unavailable scored families are omitted and the available configured weights
  are normalized to `1.0`.
- `response` reads versioned response metrics from #118 when a recent canonical
  activity exists. Only baseline-relative efficiency, drift, and normalized
  perceived-cost components are scored. Raw RPE and absolute load are excluded.
- without at least one usable component baseline, response stays available as
  context but has `used=false` and no score/contribution.

The 1-5 morning feeling scale maps linearly to `0, 25, 50, 75, 100`. This makes
the mapping explicit and preserves the neutral midpoint at `50`.

Examples:

- freshness only: `1.0 * freshness`
- freshness + physiology: `0.6 * freshness + 0.4 * physiology`
- freshness + feeling: `0.6 * freshness + 0.4 * feeling`
- freshness + feeling + physiology:
  `0.6 * freshness + 0.2 * feeling + 0.2 * physiology`
- freshness + fresh response + feeling + physiology:
  `0.6 * freshness + 0.2 * response + 0.1 * feeling + 0.1 * physiology`

Missing physiology is therefore unavailable, never zero and never a negative
recovery observation.

## Versioning and history

New rows use readiness version `v2_signal_composition_response_v1`. Existing
`v2` and `v2_signal_composition` rows are left untouched. Read paths explicitly
select the current version; historical rows remain queryable for calibration
and comparison.

The explanation payload also includes model and formula metadata so exported
snapshots remain interpretable without relying only on the database version
column.

## Delivery history

1. Add and persist the signal-family contract, morning feeling participation,
   current-version read paths, and availability-combination tests.
2. Implement response metrics and baselines in #118 and initially expose them
   as context-only.
3. Add the reviewed `signal_weighted_response_v1` formula with baseline-relative
   component scores, recency, and explicit weighting.
4. Build the web Today surface in #119 exclusively against backend-owned output.
5. Add the reproducible pilot report in #108 after the loop is operational.

## Explicit non-goals

- no ML or learned weights
- no inferred penalty for a missing optional signal
- no direct readiness score from raw RPE
- no rewriting of historical readiness rows
- no duplicated readiness logic in web or Telegram surfaces
