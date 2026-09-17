-- Executable avatar bucket/RLS regression test.
begin;

insert into auth.users (id, email, raw_user_meta_data)
values
  ('00000000-0000-0000-0000-000000000201', 'avatar-a@example.test', '{"display_name":"Avatar A"}'::jsonb),
  ('00000000-0000-0000-0000-000000000202', 'avatar-b@example.test', '{"display_name":"Avatar B"}'::jsonb);

set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000201', true);

insert into storage.objects (bucket_id, name, owner_id, metadata)
values ('avatars', '00000000-0000-0000-0000-000000000201/avatar.webp', '00000000-0000-0000-0000-000000000201', '{"mimetype":"image/webp","size":12}'::jsonb);

do $assert_avatar_a$
declare
  visible_count integer;
  avatar_path text;
begin
  select count(*)::integer, max(name)
    into visible_count, avatar_path
  from storage.objects
  where bucket_id = 'avatars';
  if visible_count <> 1 or avatar_path <> '00000000-0000-0000-0000-000000000201/avatar.webp' then
    raise exception 'Avatar RLS failure: owner cannot see its own portrait';
  end if;

  begin
    insert into storage.objects (bucket_id, name, owner_id, metadata)
    values ('avatars', '00000000-0000-0000-0000-000000000202/avatar.webp', '00000000-0000-0000-0000-000000000201', '{}'::jsonb);
    raise exception 'Avatar RLS failure: User A inserted User B portrait';
  exception when others then
    if sqlstate <> '42501' then raise; end if;
  end;
end;
$assert_avatar_a$;

select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-000000000202', true);
do $assert_avatar_b$
declare
  visible_count integer;
begin
  select count(*)::integer into visible_count from storage.objects where bucket_id = 'avatars';
  if visible_count <> 0 then
    raise exception 'Avatar RLS failure: User B can read User A portrait';
  end if;
end;
$assert_avatar_b$;

select 'avatar_storage_rls: PASS' as result;
rollback;
