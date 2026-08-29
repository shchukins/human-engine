# Readiness Signal Composition Proposal

Status: accepted implementation baseline for issue #117, phase 1.

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

## Phase 1 composition

Phase 1 preserves the established readiness meaning and avoids double-counting
load:

- `load` exposes current load-state context but is not scored independently;
  `freshness` is the current readiness-bearing summary of that load state.
- `freshness` keeps a configured weight of `0.6`.
- `feeling` and `physiology` share the existing `0.4` recovery evidence budget.
- unavailable scored families are omitted and the available configured weights
  are normalized to `1.0`.
- `response` is present in the contract but remains unavailable until #118
  materializes versioned response metrics. Raw RPE alone is not treated as a
  readiness score because its meaning depends on objective session context.

The 1-5 morning feeling scale maps linearly to `0, 25, 50, 75, 100`. This makes
the mapping explicit and preserves the neutral midpoint at `50`.

Examples:

- freshness only: `1.0 * freshness`
- freshness + physiology: `0.6 * freshness + 0.4 * physiology`
- freshness + feeling: `0.6 * freshness + 0.4 * feeling`
- freshness + feeling + physiology:
  `0.6 * freshness + 0.2 * feeling + 0.2 * physiology`

Missing physiology is therefore unavailable, never zero and never a negative
recovery observation.

## Versioning and history

New rows use readiness version `v2_signal_composition`. Existing `v2` rows are
left untouched. Read paths explicitly select the current version; historical
legacy rows remain queryable in storage for calibration and comparison.

The explanation payload also includes model and formula metadata so exported
snapshots remain interpretable without relying only on the database version
column.

## Delivery phases

1. Add and persist the signal-family contract, morning feeling participation,
   current-version read paths, and availability-combination tests.
2. Implement response metrics and baselines in #118, then make `response`
   readiness-bearing through an explicit reviewed formula revision.
3. Build the web Today surface in #119 exclusively against backend-owned output.
4. Add the reproducible pilot report in #108 after the loop is operational.

## Explicit non-goals

- no ML or learned weights
- no inferred penalty for a missing optional signal
- no direct readiness score from raw RPE
- no rewriting of historical readiness rows
- no duplicated readiness logic in web or Telegram surfaces
