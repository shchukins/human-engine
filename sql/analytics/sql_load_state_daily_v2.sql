create table if not exists load_state_daily_v2 (
    id bigserial primary key,
    user_id text not null,
    date date not null,
    tss double precision not null default 0,
    load_input_nonlinear double precision,
    fitness double precision,
    fatigue_fast double precision,
    fatigue_slow double precision,
    fatigue_total double precision,
    freshness double precision,
    version text not null default 'v2',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_load_state_daily_v2_user_date_version
    on load_state_daily_v2(user_id, date, version);

create index if not exists idx_load_state_daily_v2_user_date
    on load_state_daily_v2(user_id, date desc);