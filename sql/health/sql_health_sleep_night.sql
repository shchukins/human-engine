create table if not exists health_sleep_night (
    id bigserial primary key,
    user_id text not null,
    wake_date date not null,
    sleep_start_at timestamptz not null,
    sleep_end_at timestamptz not null,
    total_sleep_minutes double precision not null,
    awake_minutes double precision not null,
    core_minutes double precision not null,
    rem_minutes double precision not null,
    deep_minutes double precision not null,
    in_bed_minutes double precision,
    source text not null default 'healthkit',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_health_sleep_night_user_wake_date
    on health_sleep_night(user_id, wake_date);

create index if not exists idx_health_sleep_night_user_wake_date
    on health_sleep_night(user_id, wake_date desc);