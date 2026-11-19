do $$
begin
  if has_function_privilege('anon', 'public.handle_new_quest_lab_user()'::regprocedure, 'execute') then
    raise exception 'anonymous role can invoke the auth signup trigger';
  end if;
  if has_function_privilege('authenticated', 'public.handle_new_quest_lab_user()'::regprocedure, 'execute') then
    raise exception 'authenticated role can invoke the auth signup trigger directly';
  end if;

  if has_function_privilege('anon', 'public.save_player_state(bigint,jsonb,uuid)'::regprocedure, 'execute') then
    raise exception 'anonymous role can invoke the player-state save RPC';
  end if;
  if not has_function_privilege('authenticated', 'public.save_player_state(bigint,jsonb,uuid)'::regprocedure, 'execute') then
    raise exception 'authenticated role cannot invoke the player-state save RPC';
  end if;

  if has_function_privilege('anon', 'public.validate_campaign_projection(jsonb)'::regprocedure, 'execute')
    or has_function_privilege('authenticated', 'public.validate_campaign_projection(jsonb)'::regprocedure, 'execute')
    or has_function_privilege('anon', 'public.validate_player_state_projection(jsonb)'::regprocedure, 'execute')
    or has_function_privilege('authenticated', 'public.validate_player_state_projection(jsonb)'::regprocedure, 'execute')
    or has_function_privilege('anon', 'public.validate_player_state_projection_base(jsonb)'::regprocedure, 'execute')
    or has_function_privilege('authenticated', 'public.validate_player_state_projection_base(jsonb)'::regprocedure, 'execute') then
    raise exception 'a player-state validation helper is exposed to API roles';
  end if;

  if has_function_privilege('anon', 'public.create_hunter_group(text)'::regprocedure, 'execute') then
    raise exception 'anonymous role can create private hunter groups';
  end if;
  if not has_function_privilege('authenticated', 'public.create_hunter_group(text)'::regprocedure, 'execute') then
    raise exception 'authenticated group creation was unexpectedly disabled';
  end if;
end
$$;
