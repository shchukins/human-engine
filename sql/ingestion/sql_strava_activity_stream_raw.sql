create table if not exists strava_activity_stream_raw (
    id bigserial primary key,
    strava_activity_id bigint not null,
    stream_type text not null,
    series_type text,
    resolution text,
    original_size integer,
    data_json jsonb not null,
    fetched_at timestamptz not null default now(),

    constraint uq_strava_activity_stream_raw unique (strava_activity_id, stream_type)
);

create index if not exists ix_strava_activity_stream_raw_activity_id
    on strava_activity_stream_raw (strava_activity_id);
