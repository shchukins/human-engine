create table if not exists user_strava_connection (
    id bigserial primary key,
    user_id text not null,
    strava_athlete_id bigint not null,
    access_token text not null,
    refresh_token text not null,
    expires_at timestamptz not null,
    scope text,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create unique index if not exists uq_user_strava_connection_user_id
    on user_strava_connection (user_id);

create unique index if not exists uq_user_strava_connection_strava_athlete_id
    on user_strava_connection (strava_athlete_id);
