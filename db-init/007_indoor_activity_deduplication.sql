alter table if exists strava_activity_raw
    add column if not exists duplicate_of_activity_id bigint,
    add column if not exists is_excluded boolean not null default false,
    add column if not exists exclusion_reason text,
    add column if not exists duplicate_confidence double precision,
    add column if not exists duplicate_reason jsonb,
    add column if not exists duplicate_detected_at timestamptz,
    add column if not exists duplicate_detection_version text,
    add column if not exists deduplication_manual_override text,
    add column if not exists duplicate_candidate_activity_id bigint;

do $$
begin
    if to_regclass('public.strava_activity_raw') is not null and not exists (
        select 1
        from pg_constraint
        where conname = 'chk_strava_activity_raw_not_self_duplicate'
    ) then
        alter table strava_activity_raw
            add constraint chk_strava_activity_raw_not_self_duplicate
            check (
                duplicate_of_activity_id is null
                or duplicate_of_activity_id <> strava_activity_id
            );
    end if;

    if to_regclass('public.strava_activity_raw') is not null and not exists (
        select 1
        from pg_constraint
        where conname = 'chk_strava_activity_raw_duplicate_confidence'
    ) then
        alter table strava_activity_raw
            add constraint chk_strava_activity_raw_duplicate_confidence
            check (
                duplicate_confidence is null
                or duplicate_confidence between 0.0 and 1.0
            );
    end if;

    if to_regclass('public.strava_activity_raw') is not null and not exists (
        select 1
        from pg_constraint
        where conname = 'chk_strava_activity_raw_manual_override'
    ) then
        alter table strava_activity_raw
            add constraint chk_strava_activity_raw_manual_override
            check (
                deduplication_manual_override is null
                or deduplication_manual_override in ('exclude', 'separate')
            );
    end if;

    if to_regclass('public.strava_activity_raw') is not null then
        execute 'create index if not exists ix_strava_activity_raw_user_dedup_candidates
            on strava_activity_raw (user_id, start_date)
            where is_deleted = false';
        execute 'create index if not exists ix_strava_activity_raw_duplicate_of
            on strava_activity_raw (duplicate_of_activity_id)
            where duplicate_of_activity_id is not null';
        execute 'create index if not exists ix_strava_activity_raw_excluded
            on strava_activity_raw (user_id, is_excluded, start_date)';
    end if;
end
$$;

create table if not exists activity_delivery_log (
    id bigserial primary key,
    user_id text not null,
    activity_id bigint not null,
    delivery_type text not null,
    delivery_status text not null,
    telegram_message_id bigint,
    payload_json jsonb,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    constraint chk_activity_delivery_log_type
        check (delivery_type in ('training_processed', 'post_ride_rpe')),
    constraint chk_activity_delivery_log_status
        check (delivery_status in ('claimed', 'sent', 'failed'))
);

create unique index if not exists uq_activity_delivery_log_activity_type
    on activity_delivery_log (activity_id, delivery_type);

create index if not exists ix_activity_delivery_log_user_created_at
    on activity_delivery_log (user_id, created_at desc);

alter table if exists activity_subjective_feedback
    add column if not exists canonical_activity_id bigint;

update activity_subjective_feedback
set canonical_activity_id = strava_activity_id
where canonical_activity_id is null
  and strava_activity_id is not null;

create unique index if not exists uq_activity_subjective_feedback_canonical_type
    on activity_subjective_feedback (canonical_activity_id, feedback_type)
    where canonical_activity_id is not null;

create index if not exists ix_activity_subjective_feedback_canonical_activity_id
    on activity_subjective_feedback (canonical_activity_id)
    where canonical_activity_id is not null;
