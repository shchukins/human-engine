alter table if exists notification_log
    add column if not exists recovery_date date,
    add column if not exists freshness_status text,
    add column if not exists delivery_status text,
    add column if not exists telegram_chat_id text,
    add column if not exists telegram_message_id bigint,
    add column if not exists sent_at timestamptz,
    add column if not exists updated_at timestamptz not null default now(),
    add column if not exists content_fingerprint text;

update notification_log
set recovery_date = coalesce(
        recovery_date,
        nullif(payload_json->'data_freshness'->>'recovery_date', '')::date
    ),
    freshness_status = coalesce(
        freshness_status,
        payload_json->'data_freshness'->>'state',
        'missing'
    ),
    delivery_status = coalesce(
        delivery_status,
        payload_json->>'delivery_state',
        'sent'
    ),
    sent_at = case
        when coalesce(payload_json->>'delivery_state', 'sent') = 'sent'
            then coalesce(sent_at, created_at)
        else sent_at
    end,
    updated_at = coalesce(updated_at, created_at)
where notification_type = 'daily_readiness';

do $$
begin
    if to_regclass('public.notification_log') is not null and not exists (
        select 1 from pg_constraint
        where conname = 'chk_notification_log_daily_freshness'
    ) then
        alter table notification_log
            add constraint chk_notification_log_daily_freshness
            check (
                notification_type <> 'daily_readiness'
                or freshness_status in ('fresh', 'stale', 'missing')
            );
    end if;

    if to_regclass('public.notification_log') is not null and not exists (
        select 1 from pg_constraint
        where conname = 'chk_notification_log_daily_delivery_status'
    ) then
        alter table notification_log
            add constraint chk_notification_log_daily_delivery_status
            check (
                notification_type <> 'daily_readiness'
                or delivery_status in (
                    'claimed', 'sent', 'updating', 'updated', 'superseded', 'failed'
                )
            );
    end if;
end
$$;
