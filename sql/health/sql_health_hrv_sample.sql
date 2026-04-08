create table if not exists health_hrv_sample (
    id bigserial primary key,
    user_id text not null,
    sample_start_at timestamptz not null,
    value_ms double precision not null,
    source text not null default 'healthkit',
    created_at timestamptz not null default now()
);

create unique index if not exists uq_health_hrv_sample_user_start_at
    on health_hrv_sample(user_id, sample_start_at);

create index if not exists idx_health_hrv_sample_user_start_at
    on health_hrv_sample(user_id, sample_start_at desc);