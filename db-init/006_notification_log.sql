create table if not exists notification_log (
    id bigserial primary key,
    user_id text not null,
    notification_type text not null,
    notification_date date not null,
    payload_json jsonb,
    created_at timestamptz not null default now()
);

create unique index if not exists uq_notification_log_user_type_date
    on notification_log (user_id, notification_type, notification_date);

create index if not exists ix_notification_log_user_created_at
    on notification_log (user_id, created_at desc);
