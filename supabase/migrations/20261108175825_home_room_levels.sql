-- Validate the compact Home ladder projection without weakening existing domain checks.
create or replace function public.validate_player_state_projection(next_state jsonb)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  base_state jsonb;
  field_name text;
  item jsonb;
begin
  if next_state is null or jsonb_typeof(next_state) <> 'object' then
    raise exception 'next_state must be a JSON object' using errcode = '22023';
  end if;
  if octet_length(next_state::text) > 24000 then
    raise exception 'next_state is too large' using errcode = '22023';
  end if;
  if next_state ? 'campaign' then
    perform public.validate_campaign_projection(next_state -> 'campaign');
    base_state := next_state - 'campaign';
  else
    base_state := next_state;
  end if;

  -- Campaign gear inventories are bounded identifiers owned by the state
  -- service. The older primitive validator only knew the three equipped text
  -- fields, so validate the new lists here and strip them before delegation.
  if base_state ? 'equipment' and jsonb_typeof(base_state -> 'equipment') = 'object' then
    for field_name in select jsonb_object_keys(base_state -> 'equipment') loop
      if field_name in ('owned_armor', 'owned_trinkets') then
        if jsonb_typeof((base_state -> 'equipment') -> field_name) <> 'array'
           or jsonb_array_length((base_state -> 'equipment') -> field_name) > 24 then
          raise exception 'equipment inventory must be a bounded array' using errcode = '22023';
        end if;
        for item in select jsonb_array_elements((base_state -> 'equipment') -> field_name) loop
          if jsonb_typeof(item) <> 'string' or (item #>> '{}') !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
            raise exception 'equipment inventory entries must be safe identifiers' using errcode = '22023';
          end if;
        end loop;
      end if;
    end loop;
    base_state := jsonb_set(
      base_state,
      '{equipment}',
      (base_state -> 'equipment') - array['owned_armor', 'owned_trinkets']
    );
  end if;
  -- The new Home ladder and the older Home purchases share the same
  -- revision/CAS state. Validate every added field before the legacy validator.
  if base_state ? 'homestead' and jsonb_typeof(base_state -> 'homestead') = 'object' then
    if (base_state -> 'homestead') ? 'room_levels' then
      if jsonb_typeof(base_state -> 'homestead' -> 'room_levels') <> 'object' then
        raise exception 'room_levels must be an object' using errcode = '22023';
      end if;
      if (select count(*) from jsonb_object_keys(base_state -> 'homestead' -> 'room_levels')) <> 7 then
        raise exception 'room_levels must contain seven rooms' using errcode = '22023';
      end if;
      for field_name in select jsonb_object_keys(base_state -> 'homestead' -> 'room_levels') loop
        if not (field_name = any(array['great_hall','library','armory','pantry','gallery','war_room','den'])) then
          raise exception 'room_levels contains an unknown room' using errcode = '22023';
        end if;
        item := (base_state -> 'homestead' -> 'room_levels') -> field_name;
        if jsonb_typeof(item) <> 'number' or (item #>> '{}') !~ '^(0|[1-9][0-9]*)$' then
          raise exception 'room level must be a nonnegative integer' using errcode = '22023';
        end if;
        if (item #>> '{}')::numeric > (case when field_name = 'pantry' then 8 else 9 end) then
          raise exception 'room level exceeds its ladder' using errcode = '22023';
        end if;
      end loop;
    end if;
    if (base_state -> 'homestead') ? 'upgrade_tokens' then
      item := base_state -> 'homestead' -> 'upgrade_tokens';
      if jsonb_typeof(item) <> 'number' or (item #>> '{}') !~ '^(0|[1-9][0-9]*)$' then
        raise exception 'upgrade_tokens must be a nonnegative integer' using errcode = '22023';
      end if;
      if (item #>> '{}')::numeric > 1000000000 then
        raise exception 'upgrade_tokens exceeds the limit' using errcode = '22023';
      end if;
    end if;
    for field_name in select unnest(array['room_upgrades','market_purchases']) loop
      if (base_state -> 'homestead') ? field_name then
        item := (base_state -> 'homestead') -> field_name;
        if jsonb_typeof(item) <> 'array' then
          raise exception '% must be an array', field_name using errcode = '22023';
        end if;
        if jsonb_array_length(item) > (case when field_name = 'room_upgrades' then 5 else 11 end) then
          raise exception '% contains too many entries', field_name using errcode = '22023';
        end if;
        for item in select jsonb_array_elements((base_state -> 'homestead') -> field_name) loop
          if jsonb_typeof(item) <> 'string' or (item #>> '{}') !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
            raise exception '% contains an invalid identifier', field_name using errcode = '22023';
          end if;
          if field_name = 'room_upgrades' and not ((item #>> '{}') = any(array['reinforced-hearth','warding-loom','breaker-workbench','siphon-basin','field-kitchen'])) then
            raise exception 'room_upgrades contains an unknown upgrade' using errcode = '22023';
          end if;
          if field_name = 'market_purchases' and not ((item #>> '{}') = any(array['field-bandage','ember-tonic','camp-meal','debugger-plate','ledgerguard-coat','emberweave-mantle','syntax-ward','loop-lens','guard-bell','scimitar-of-momentum','vision-scroll'])) then
            raise exception 'market_purchases contains an unknown item' using errcode = '22023';
          end if;
        end loop;
      end if;
    end loop;
    if (base_state -> 'homestead') ? 'upgrade_effects' then
      if jsonb_typeof(base_state -> 'homestead' -> 'upgrade_effects') <> 'object' then
        raise exception 'upgrade_effects must be an object' using errcode = '22023';
      end if;
      for field_name in select jsonb_object_keys(base_state -> 'homestead' -> 'upgrade_effects') loop
        if not (field_name = any(array['max_hp_delta','failure_damage_reduction','resolve_impact_delta','guard_break_heal','meal_heal_delta'])) then
          raise exception 'upgrade_effects contains an unknown field' using errcode = '22023';
        end if;
        item := (base_state -> 'homestead' -> 'upgrade_effects') -> field_name;
        if jsonb_typeof(item) <> 'number' or (item #>> '{}') !~ '^(0|[1-9][0-9]*)$' then
          raise exception 'upgrade effect must be a nonnegative integer' using errcode = '22023';
        end if;
        if (item #>> '{}')::numeric > 1000000000 then
          raise exception 'upgrade effect exceeds the limit' using errcode = '22023';
        end if;
      end loop;
    end if;
    base_state := jsonb_set(base_state, '{homestead}',
      (base_state -> 'homestead') - array['room_levels','upgrade_tokens','room_upgrades','upgrade_effects','market_purchases']);
  end if;
  perform public.validate_player_state_projection_base(base_state);
end;
$$;

revoke all on function public.validate_player_state_projection(jsonb) from public;
