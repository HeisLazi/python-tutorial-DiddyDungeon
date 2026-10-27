-- Run against a disposable database after applying the Home projection migration.
do $home_room_projection$
declare
  valid jsonb := '{"player":{"level":1,"xp":0,"xp_next":100},"homestead":{"owned_cosmetics":[],"equipped":{},"room_levels":{"great_hall":3,"library":0,"armory":3,"pantry":8,"gallery":9,"war_room":0,"den":1},"upgrade_tokens":86,"room_upgrades":["reinforced-hearth"],"upgrade_effects":{"max_hp_delta":10},"market_purchases":[]}}'::jsonb;
  bad jsonb;
begin
  perform public.validate_player_state_projection(valid);
  perform public.validate_player_state_projection('{"player":{"level":1,"xp":0,"xp_next":100}}'::jsonb);
  foreach bad in array array[
    jsonb_set(valid, '{homestead,room_levels,den}', '10'::jsonb),
    jsonb_set(valid, '{homestead,room_levels,pantry}', '9'::jsonb),
    jsonb_set(valid, '{homestead,room_levels,den}', 'true'::jsonb),
    jsonb_set(valid, '{homestead,room_levels}', '{}'::jsonb),
    jsonb_set(valid, '{homestead,upgrade_tokens}', '-1'::jsonb),
    jsonb_set(valid, '{homestead,upgrade_effects}', '{"unknown":1}'::jsonb),
    jsonb_set(valid, '{player,level}', '-1'::jsonb)
  ] loop
    begin
      perform public.validate_player_state_projection(bad);
      raise exception 'invalid Home projection was accepted';
    exception when sqlstate '22023' then null;
    end;
  end loop;
end;
$home_room_projection$;
