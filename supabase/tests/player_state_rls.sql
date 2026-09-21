-- Executable player-state RLS and compare-and-swap regression test.
begin;

insert into auth.users (id, email, raw_user_meta_data)
values
  ('00000000-0000-4000-8000-000000000101', 'player-state-a@example.test', '{"display_name":"State A"}'::jsonb),
  ('00000000-0000-4000-8000-000000000102', 'player-state-b@example.test', '{"display_name":"State B"}'::jsonb);

insert into public.devices (id, user_id, display_name)
values
  ('00000000-0000-0000-0000-000000000111', '00000000-0000-4000-8000-000000000101', 'State A device'),
  ('00000000-0000-0000-0000-000000000112', '00000000-0000-4000-8000-000000000102', 'State B device');

insert into public.player_state (user_id, state, revision, device_id)
values
  ('00000000-0000-4000-8000-000000000101', '{"player":{"level":1,"xp":0,"xp_next":100},"homestead":{"owned_cosmetics":["cursor-basic"],"equipped":{"cursor":"cursor-basic"}}}'::jsonb, 0, '00000000-0000-4000-8000-000000000111'),
  ('00000000-0000-4000-8000-000000000102', '{"player":{"level":4,"xp":20,"xp_next":100}}'::jsonb, 0, '00000000-0000-4000-8000-000000000112');

set local role authenticated;
select set_config('request.jwt.claim.sub', '00000000-0000-4000-8000-000000000101', true);

do $assert_visibility_and_cas$
declare
  visible_count integer;
  saved_revision bigint;
  stale_rejected boolean := false;
begin
  select count(*)::integer into visible_count from public.player_state;
  if visible_count <> 1 then
    raise exception 'RLS failure: User A can see another users player state';
  end if;

  begin
    insert into public.player_state (user_id, state, device_id)
      values ('00000000-0000-4000-8000-000000000101', '{}'::jsonb, '00000000-0000-4000-8000-000000000111');
    raise exception 'RLS failure: direct player-state insert was accepted';
  exception when others then
    if sqlstate <> '42501' then raise; end if;
  end;

  begin
    update public.player_state set state = '{}'::jsonb where user_id = '00000000-0000-4000-8000-000000000101';
    raise exception 'RLS failure: direct player-state update was accepted';
  exception when others then
    if sqlstate <> '42501' then raise; end if;
  end;

  begin
    perform public.save_player_state(
      0,
      '{"player":{"level":2,"xp":5,"xp_next":100}}'::jsonb,
      '00000000-0000-0000-0000-000000000112'
    );
    raise exception 'Provenance failure: User A used User B device';
  exception when others then
    if sqlstate <> '42501' then raise; end if;
  end;

  select revision into saved_revision
  from public.save_player_state(
    0,
    '{"player":{"level":2,"xp":5,"xp_next":100,"coins":10}}'::jsonb,
    '00000000-0000-4000-8000-000000000111'
  );
  if saved_revision <> 1 then
    raise exception 'CAS failure: expected revision 1, got %', saved_revision;
  end if;

  begin
    perform public.save_player_state(
      0,
      '{"player":{"level":3,"xp":9,"xp_next":100}}'::jsonb,
      '00000000-0000-4000-8000-000000000111'
    );
  exception when others then
    if sqlstate = '40001' then stale_rejected := true; else raise; end if;
  end;
  if not stale_rejected then
    raise exception 'CAS failure: stale revision was accepted';
  end if;
end;
$assert_visibility_and_cas$;

reset role;
do $assert_unchanged$
declare
  level_value integer;
  revision_value bigint;
begin
  select (state->'player'->>'level')::integer, revision
    into level_value, revision_value
  from public.player_state
  where user_id = '00000000-0000-4000-8000-000000000101';
  if level_value <> 2 or revision_value <> 1 then
    raise exception 'CAS failure: accepted state was not retained';
  end if;
end;
$assert_unchanged$;

select 'player_state_rls: PASS' as result;
rollback;
