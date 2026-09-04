create table if not exists decision_context_snapshot (
    id bigserial primary key,
    user_id text not null,
    snapshot_date date not null,
    event_type text not null,
    reference_key text not null,
    model_version text not null,
    readiness_score double precision,
    good_day_probability double precision,
    recommendation text,
    status_text text,
    snapshot_json jsonb not null,
    content_fingerprint text not null,
    captured_at timestamptz not null default now(),
    constraint chk_decision_context_snapshot_event_type
        check (event_type in (
            'daily_readiness_delivery',
            'recovery_checkin_before',
            'recovery_checkin_after'
        ))
);

create unique index if not exists uq_decision_context_snapshot_event_state
    on decision_context_snapshot (
        user_id,
        snapshot_date,
        event_type,
        reference_key,
        content_fingerprint
    );

create index if not exists ix_decision_context_snapshot_user_date
    on decision_context_snapshot (user_id, snapshot_date, captured_at);
