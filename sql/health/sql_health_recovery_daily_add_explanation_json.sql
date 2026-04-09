alter table health_recovery_daily
add column if not exists recovery_explanation_json jsonb;