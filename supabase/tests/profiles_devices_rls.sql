-- Executable RLS regression test. It intentionally uses plain SQL/DO
-- assertions so it can run through `supabase db query --linked` without
-- requiring the optional pgTAP extension.
begin;

insert into auth.users (id, email, raw_user_meta_data)
values
  ('00000000-0000-4000-8000-000000000001', 'quest-a@example.test', '{"display_name":"Quest A"}'::jsonb),
  ('00000000-0000-4000-8000-000000000002', 'quest-b@example.test', '{"display_name":"Quest B"}'::jsonb);

insert into public.devices (id, user_id, display_name)
values
  ('00000000-0000-4000-8000-000000000011', '00000000-0000-4000-8000-000000000001', 'Papasmurff Desktop'),
  ('00000000-0000-4000-8000-000000000012', '00000000-0000-4000-8000-000000000002', 'TUF Laptop');

set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000001', true);

do $assert_user_a$
declare
  profile_count integer;
  profile_name text;
  device_count integer;
  device_name text;
begin
  select count(*)::integer, max(display_name) into profile_count, profile_name from public.profiles;
  if profile_count <> 1 or profile_name <> 'Quest A' then
    raise exception 'RLS failure: User A profile visibility is incorrect';
  end if;

  select count(*)::integer, max(display_name) into device_count, device_name from public.devices;
  if device_count <> 1 or device_name <> 'Papasmurff Desktop' then
    raise exception 'RLS failure: User A device visibility is incorrect';
  end if;

  begin
    insert into public.profiles (id, display_name)
      values ('00000000-0000-4000-8000-000000000002', 'A hacked B');
    raise exception 'RLS failure: User A inserted User B profile';
  exception when others then
    if sqlstate <> '42501' then raise; end if;
  end;

  begin
    insert into public.devices (id, user_id, display_name)
      values ('00000000-0000-4000-8000-000000000013', '00000000-0000-4000-8000-000000000002', 'A hacked device');
    raise exception 'RLS failure: User A inserted User B device';
  exception when others then
    if sqlstate <> '42501' then raise; end if;
  end;

  -- An ON CONFLICT clause must not turn a hidden User B row into an update
  -- primitive for User A. Depending on the Postgres planner, the rejected
  -- path is either an RLS violation or a uniqueness violation; both fail
  -- closed and leave the protected row unchanged.
  declare
    upsert_rejected boolean := false;
  begin
    begin
      insert into public.devices (id, user_id, display_name)
        values ('00000000-0000-4000-8000-000000000012', '00000000-0000-4000-8000-000000000001', 'A upsert hijack')
        on conflict (id) do update set display_name = 'A upsert hijack';
    exception when others then
      if sqlstate in ('42501', '23505') then
        upsert_rejected := true;
      else
        raise;
      end if;
    end;
    if not upsert_rejected then
      raise exception 'RLS failure: User A upserted User B device';
    end if;
  end;
end;
$assert_user_a$;

-- UPDATE is filtered by USING, so these cross-owner targets affect zero rows.
update public.profiles set display_name = 'A hacked B' where id = '00000000-0000-4000-8000-000000000002';
update public.devices set display_name = 'A hacked device' where id = '00000000-0000-4000-8000-000000000012';

reset role;
do $assert_unchanged$
declare
  profile_name text;
  device_name text;
begin
  select display_name into profile_name from public.profiles where id = '00000000-0000-4000-8000-000000000002';
  select display_name into device_name from public.devices where id = '00000000-0000-4000-8000-000000000012';
  if profile_name <> 'Quest B' then
    raise exception 'RLS failure: User B profile changed from User A update';
  end if;
  if device_name <> 'TUF Laptop' then
    raise exception 'RLS failure: User B device changed from User A update';
  end if;
end;
$assert_unchanged$;

set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000002', true);
do $assert_user_b$
declare
  profile_count integer;
  device_count integer;
begin
  select count(*)::integer into profile_count from public.profiles;
  select count(*)::integer into device_count from public.devices;
  if profile_count <> 1 or device_count <> 1 then
    raise exception 'RLS failure: User B can see another users private rows';
  end if;
end;
$assert_user_b$;

select 'profiles_devices_rls: PASS' as result;
rollback;
