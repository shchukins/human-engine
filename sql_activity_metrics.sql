create table if not exists activity_metrics (
    id bigserial primary key,
    user_id text not null,
    strava_activity_id bigint not null,
    computed_at timestamptz not null default now(),
    version text not null default 'v1',

    duration_s integer,
    moving_time_s integer,
    distance_m double precision,
    elevation_gain_m double precision,

    avg_speed_mps double precision,
    max_speed_mps double precision,

    avg_heartrate double precision,
    max_heartrate double precision,

    avg_power double precision,
    max_power double precision,
    weighted_avg_power double precision,

    normalized_power double precision,
    intensity_factor double precision,
    variability_index double precision,

    work_kj double precision,
    trimp double precision,
    tss double precision,
    hr_drift_pct double precision,

    time_in_power_z1_s integer,
    time_in_power_z2_s integer,
    time_in_power_z3_s integer,
    time_in_power_z4_s integer,
    time_in_power_z5_s integer,
    time_in_power_z6_s integer,
    time_in_power_z7_s integer,

    time_in_hr_z1_s integer,
    time_in_hr_z2_s integer,
    time_in_hr_z3_s integer,
    time_in_hr_z4_s integer,
    time_in_hr_z5_s integer,

    raw_json jsonb,

    constraint uq_activity_metrics unique (strava_activity_id, version)
);

create index if not exists ix_activity_metrics_user_id
    on activity_metrics (user_id);

create index if not exists ix_activity_metrics_activity_id
    on activity_metrics (strava_activity_id);
