-- Independent dated inputs: changing weight never copies or changes FTP.
create table if not exists user_profile_value (
    user_id text not null,
    metric text not null check (metric in ('ftp', 'weight')),
    effective_from date not null,
    value numeric not null,
    needs_recompute boolean not null default false,
    updated_at timestamptz not null default now(),
    primary key (user_id, metric, effective_from),
    check ((metric = 'ftp' and value between 1 and 1000)
        or (metric = 'weight' and value between 1 and 500))
);

-- Some empty installations have not provisioned the legacy profile table.
do $$ begin
    if to_regclass('user_training_profile') is not null then
        insert into user_profile_value (user_id, metric, effective_from, value)
        select user_id, 'ftp', effective_from, ftp_watts
        from user_training_profile where ftp_watts > 0 and ftp_watts <= 1000
        on conflict do nothing;
    end if;
end $$;
