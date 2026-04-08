create table if not exists health_weight_measurement (
    id bigserial primary key,
    user_id text not null,
    measured_at timestamptz not null,
    kilograms double precision not null,
    source text not null default 'healthkit',
    created_at timestamptz not null default now()
);

create unique index if not exists uq_health_weight_measurement_user_measured_at
    on health_weight_measurement(user_id, measured_at);

create index if not exists idx_health_weight_measurement_user_measured_at
    on health_weight_measurement(user_id, measured_at desc);