create table if not exists daily_fitness_state (
    id bigserial primary key,

    user_id text not null,
    date date not null,

    daily_tss double precision not null default 0,
    fitness_signal double precision not null default 0,
    fatigue_signal double precision not null default 0,
    freshness_signal double precision not null default 0,

    model_version text not null default 'v1',
    computed_at timestamptz not null default now(),

    constraint uq_daily_fitness_state unique (user_id, date, model_version)
);

create index if not exists ix_daily_fitness_state_user_date
    on daily_fitness_state (user_id, date desc);
