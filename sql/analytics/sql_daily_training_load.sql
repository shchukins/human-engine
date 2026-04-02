create table if not exists daily_training_load (
    id bigserial primary key,

    user_id text not null,
    date date not null,

    activities_count integer,
    duration_s integer,
    distance_m double precision,
    elevation_gain_m double precision,

    work_kj double precision,
    tss double precision,

    computed_at timestamptz not null default now(),

    constraint uq_daily_training_load unique (user_id, date)
);

create index if not exists ix_daily_training_load_user_date
on daily_training_load(user_id, date desc);
