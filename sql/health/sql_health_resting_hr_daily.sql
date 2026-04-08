create table if not exists health_resting_hr_daily (
    id bigserial primary key,
    user_id text not null,
    date date not null,
    bpm double precision not null,
    source text not null default 'healthkit',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_health_resting_hr_daily_user_date
    on health_resting_hr_daily(user_id, date);

create index if not exists idx_health_resting_hr_daily_user_date
    on health_resting_hr_daily(user_id, date desc);