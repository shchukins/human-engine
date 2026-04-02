create table if not exists user_training_profile (
    id bigserial primary key,
    user_id text not null,
    effective_from date not null,
    ftp_watts double precision,
    hr_max integer,
    hr_rest integer,
    hr_threshold integer,

    power_z1_upper double precision,
    power_z2_upper double precision,
    power_z3_upper double precision,
    power_z4_upper double precision,
    power_z5_upper double precision,
    power_z6_upper double precision,

    hr_z1_upper integer,
    hr_z2_upper integer,
    hr_z3_upper integer,
    hr_z4_upper integer,

    source text,
    created_at timestamptz not null default now(),

    constraint uq_user_training_profile unique (user_id, effective_from)
);

create index if not exists ix_user_training_profile_user_id_effective_from
    on user_training_profile (user_id, effective_from desc);
