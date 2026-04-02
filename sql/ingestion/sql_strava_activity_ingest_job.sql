create table if not exists strava_activity_ingest_job (
    id bigserial primary key,
    webhook_event_id bigint references strava_webhook_event(id) on delete set null,
    user_id text not null,
    strava_athlete_id bigint not null,
    strava_activity_id bigint not null,
    reason text not null,
    status text not null default 'pending',
    attempt_count integer not null default 0,
    scheduled_at timestamptz not null default now(),
    started_at timestamptz,
    finished_at timestamptz,
    last_error text,
    created_at timestamptz not null default now()
);

create index if not exists ix_strava_activity_ingest_job_status_scheduled_at
    on strava_activity_ingest_job (status, scheduled_at);

create index if not exists ix_strava_activity_ingest_job_activity_id
    on strava_activity_ingest_job (strava_activity_id);

create unique index if not exists uq_strava_activity_ingest_job_active
    on strava_activity_ingest_job (strava_activity_id)
    where status in ('pending', 'running');
