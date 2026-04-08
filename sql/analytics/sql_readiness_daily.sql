create table if not exists readiness_daily (
    id bigserial primary key,
    user_id text not null,
    date date not null,
    freshness double precision,
    recovery_score_simple double precision,
    readiness_score_raw double precision,
    readiness_score double precision,
    good_day_probability double precision,
    status_text text,
    explanation_json jsonb,
    version text not null default 'v2',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_readiness_daily_user_date_version
    on readiness_daily(user_id, date, version);

create index if not exists idx_readiness_daily_user_date
    on readiness_daily(user_id, date desc);