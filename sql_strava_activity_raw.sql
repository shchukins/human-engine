create table if not exists strava_activity_raw (
    id bigserial primary key,
    user_id text not null,
    strava_athlete_id bigint not null,
    strava_activity_id bigint not null,
    activity_type text,
    name text,
    start_date timestamptz,
    timezone text,
    distance_m double precision,
    moving_time_s integer,
    elapsed_time_s integer,
    total_elevation_gain_m double precision,
    average_speed_mps double precision,
    max_speed_mps double precision,
    average_heartrate double precision,
    max_heartrate double precision,
    average_watts double precision,
    max_watts double precision,
    weighted_average_watts double precision,
    kilojoules double precision,
    trainer boolean,
    commute boolean,
    manual boolean,
    raw_json jsonb not null,
    fetched_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    is_deleted boolean not null default false
);

create unique index if not exists uq_strava_activity_raw_activity_id
    on strava_activity_raw (strava_activity_id);

create index if not exists ix_strava_activity_raw_user_id_start_date
    on strava_activity_raw (user_id, start_date desc);

create index if not exists ix_strava_activity_raw_athlete_id_start_date
    on strava_activity_raw (strava_athlete_id, start_date desc);
