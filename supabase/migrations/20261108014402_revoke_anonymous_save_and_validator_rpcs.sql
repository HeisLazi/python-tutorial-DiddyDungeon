-- Keep security-definer save and validation helpers off the anonymous API.
-- The save RPC remains available to signed-in players; the validation
-- functions are implementation helpers called by that RPC.
revoke execute on function public.handle_new_quest_lab_user()
  from public, anon, authenticated;

revoke execute on function public.save_player_state(bigint, jsonb, uuid)
  from public, anon;
grant execute on function public.save_player_state(bigint, jsonb, uuid)
  to authenticated;

revoke execute on function public.validate_campaign_projection(jsonb)
  from public, anon, authenticated;
revoke execute on function public.validate_player_state_projection(jsonb)
  from public, anon, authenticated;
revoke execute on function public.validate_player_state_projection_base(jsonb)
  from public, anon, authenticated;
