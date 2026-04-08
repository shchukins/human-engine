create table if not exists health_recovery_daily (
    id bigserial primary key,
    user_id text not null,
    date date not null,
    sleep_minutes double precision,
    awake_minutes double precision,
    rem_minutes double precision,
    deep_minutes double precision,
    resting_hr_bpm double precision,
    hrv_daily_median_ms double precision,
    weight_kg double precision,
    recovery_score_simple double precision,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_health_recovery_daily_user_date
    on health_recovery_daily(user_id, date);

create index if not exists idx_health_recovery_daily_user_date
    on health_recovery_daily(user_id, date desc);