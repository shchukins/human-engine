create table if not exists healthkit_ingest_raw (
    id bigserial primary key,
    user_id text not null,
    generated_at timestamptz not null,
    timezone text not null,
    payload_json jsonb not null,
    received_at timestamptz not null default now()
);

create index if not exists idx_healthkit_ingest_raw_user_id
    on healthkit_ingest_raw(user_id);

create index if not exists idx_healthkit_ingest_raw_received_at
    on healthkit_ingest_raw(received_at desc);