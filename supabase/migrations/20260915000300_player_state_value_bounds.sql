-- Keep the public RPC projection compatible with the local state gateway's
-- primitive bounds as well as its domain/field allowlist.

create or replace function public.validate_player_state_projection(next_state jsonb)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  domain_key text;
  field_key text;
  item_value jsonb;
  field_value text;
  allowed_domains text[] := array['player', 'equipment', 'companion', 'homestead'];
  allowed_fields text[];
begin
  if next_state is null or jsonb_typeof(next_state) <> 'object' then
    raise exception 'next_state must be a JSON object' using errcode = '22023';
  end if;
  if octet_length(next_state::text) > 24000 then
    raise exception 'next_state is too large' using errcode = '22023';
  end if;

  for domain_key in select jsonb_object_keys(next_state) loop
    if not (domain_key = any(allowed_domains)) then
      raise exception 'next_state contains unsupported domains' using errcode = '22023';
    end if;
    if jsonb_typeof(next_state -> domain_key) <> 'object' then
      raise exception '% projection must be an object', domain_key using errcode = '22023';
    end if;
  end loop;

  if next_state ? 'player' then
    allowed_fields := array['name','title','rank','level','xp','xp_next','lifetime_xp','hp','max_hp','coins','potions'];
    for field_key in select jsonb_object_keys(next_state -> 'player') loop
      if not (field_key = any(allowed_fields)) then
        raise exception 'player projection contains unsupported fields' using errcode = '22023';
      end if;
      field_value := next_state -> 'player' ->> field_key;
      if field_key in ('name','title','rank') then
        if jsonb_typeof(next_state -> 'player' -> field_key) <> 'string' or char_length(trim(field_value)) not between 1 and 120 or field_value ~ '[[:cntrl:]]' or field_value ~ '[/\\:]' then
          raise exception 'player text fields must be bounded and safe' using errcode = '22023';
        end if;
      else
        if jsonb_typeof(next_state -> 'player' -> field_key) <> 'number' then
          raise exception 'player counters must be numbers' using errcode = '22023';
        end if;
        if (field_value::numeric < 0) or (field_key in ('level','max_hp','xp_next') and field_value::numeric < 1) or (field_value::numeric > 1000000000) or (field_key = 'level' and field_value::numeric > 1000) then
          raise exception 'player counters are outside their bounds' using errcode = '22023';
        end if;
      end if;
    end loop;
    if (next_state -> 'player') ? 'xp' and (next_state -> 'player') ? 'xp_next' and
       ((next_state -> 'player' ->> 'xp')::numeric >= (next_state -> 'player' ->> 'xp_next')::numeric) then
      raise exception 'player.xp must be below player.xp_next' using errcode = '22023';
    end if;
    if (next_state -> 'player') ? 'hp' and (next_state -> 'player') ? 'max_hp' and
       ((next_state -> 'player' ->> 'hp')::numeric > (next_state -> 'player' ->> 'max_hp')::numeric) then
      raise exception 'player.hp must not exceed player.max_hp' using errcode = '22023';
    end if;
  end if;

  if next_state ? 'equipment' then
    allowed_fields := array['armor','trinket','title'];
    for field_key in select jsonb_object_keys(next_state -> 'equipment') loop
      if not (field_key = any(allowed_fields)) or jsonb_typeof(next_state -> 'equipment' -> field_key) <> 'string' then
        raise exception 'equipment projection contains invalid fields' using errcode = '22023';
      end if;
      field_value := next_state -> 'equipment' ->> field_key;
      if char_length(trim(field_value)) not between 1 and 120 or field_value ~ '[[:cntrl:]]' or field_value ~ '[/\\:]' then
        raise exception 'equipment values must be bounded and safe' using errcode = '22023';
      end if;
    end loop;
  end if;

  if next_state ? 'companion' then
    allowed_fields := array['name','form','level','bond','next_form','next_form_requirement'];
    for field_key in select jsonb_object_keys(next_state -> 'companion') loop
      if not (field_key = any(allowed_fields)) then
        raise exception 'companion projection contains unsupported fields' using errcode = '22023';
      end if;
      if field_key in ('name','form','next_form','next_form_requirement') then
        if jsonb_typeof(next_state -> 'companion' -> field_key) <> 'string' then
          raise exception 'companion text fields must be strings' using errcode = '22023';
        end if;
        field_value := next_state -> 'companion' ->> field_key;
        if char_length(trim(field_value)) not between 1 and 120 or field_value ~ '[[:cntrl:]]' or field_value ~ '[/\\:]' then
          raise exception 'companion text fields must be bounded and safe' using errcode = '22023';
        end if;
      else
        if jsonb_typeof(next_state -> 'companion' -> field_key) <> 'number' or (next_state -> 'companion' ->> field_key)::numeric not between 0 and 1000 then
          raise exception 'companion counters are outside their bounds' using errcode = '22023';
        end if;
      end if;
    end loop;
  end if;

  if next_state ? 'homestead' then
    allowed_fields := array['name','owned_cosmetics','equipped'];
    for field_key in select jsonb_object_keys(next_state -> 'homestead') loop
      if not (field_key = any(allowed_fields)) then
        raise exception 'homestead projection contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
    if (next_state -> 'homestead') ? 'name' then
      if jsonb_typeof(next_state -> 'homestead' -> 'name') <> 'string' then
        raise exception 'homestead name must be a string' using errcode = '22023';
      end if;
      field_value := next_state -> 'homestead' ->> 'name';
      if char_length(trim(field_value)) not between 1 and 120 or field_value ~ '[[:cntrl:]]' or field_value ~ '[/\\:]' then
        raise exception 'homestead name must be bounded and safe' using errcode = '22023';
      end if;
    end if;
    if (next_state -> 'homestead') ? 'owned_cosmetics' then
      if jsonb_typeof(next_state -> 'homestead' -> 'owned_cosmetics') <> 'array' or jsonb_array_length(next_state -> 'homestead' -> 'owned_cosmetics') > 100 then
        raise exception 'owned_cosmetics must be a bounded array' using errcode = '22023';
      end if;
      for item_value in select jsonb_array_elements(next_state -> 'homestead' -> 'owned_cosmetics') loop
        if jsonb_typeof(item_value) <> 'string' then
          raise exception 'owned_cosmetics entries must be strings' using errcode = '22023';
        end if;
        field_value := item_value #>> '{}';
        if char_length(field_value) not between 1 and 120 or field_value !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
          raise exception 'owned_cosmetics entries must be safe identifiers' using errcode = '22023';
        end if;
      end loop;
    end if;
    if (next_state -> 'homestead') ? 'equipped' then
      if jsonb_typeof(next_state -> 'homestead' -> 'equipped') <> 'object' then
        raise exception 'equipped projection must be an object' using errcode = '22023';
      end if;
      allowed_fields := array['theme','cursor','hud','terminal'];
      for field_key in select jsonb_object_keys(next_state -> 'homestead' -> 'equipped') loop
        if not (field_key = any(allowed_fields)) or jsonb_typeof((next_state -> 'homestead' -> 'equipped') -> field_key) <> 'string' then
          raise exception 'equipped projection contains invalid fields' using errcode = '22023';
        end if;
        field_value := (next_state -> 'homestead' -> 'equipped') ->> field_key;
        if field_value !~ '^[A-Za-z0-9][A-Za-z0-9._-]{0,119}$' then
          raise exception 'equipped values must be safe identifiers' using errcode = '22023';
        end if;
      end loop;
    end if;
  end if;
end;
$$;

revoke all on function public.validate_player_state_projection(jsonb) from public;
