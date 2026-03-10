create table if not exists strava_webhook_event (
    id bigserial primary key,
    subscription_id bigint,
    owner_id bigint not null,
    object_type text not null,
    object_id bigint not null,
    aspect_type text not null,
    event_time timestamptz not null,
    updates jsonb,
    payload jsonb not null,
    received_at timestamptz not null default now(),
    status text not null default 'new',
    dedupe_key text,
    error_text text
);

create index if not exists ix_strava_webhook_event_received_at
    on strava_webhook_event (received_at desc);

create index if not exists ix_strava_webhook_event_owner_id
    on strava_webhook_event (owner_id);

create index if not exists ix_strava_webhook_event_object_id
    on strava_webhook_event (object_id);

create unique index if not exists uq_strava_webhook_event_dedupe_key
    on strava_webhook_event (dedupe_key)
    where dedupe_key is not null;
