-- Corrective migration for PostgreSQL operators used by the initial player
-- state RPC. Validation is expressed with JSON-key loops so `->` and `-`
-- precedence cannot reinterpret a domain name as JSON.

create or replace function public.validate_player_state_projection(next_state jsonb)
returns void
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  domain_key text;
  field_key text;
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
    end loop;
  end if;
  if next_state ? 'equipment' then
    allowed_fields := array['armor','trinket','title'];
    for field_key in select jsonb_object_keys(next_state -> 'equipment') loop
      if not (field_key = any(allowed_fields)) then
        raise exception 'equipment projection contains unsupported fields' using errcode = '22023';
      end if;
    end loop;
  end if;
  if next_state ? 'companion' then
    allowed_fields := array['name','form','level','bond','next_form','next_form_requirement'];
    for field_key in select jsonb_object_keys(next_state -> 'companion') loop
      if not (field_key = any(allowed_fields)) then
        raise exception 'companion projection contains unsupported fields' using errcode = '22023';
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
    if (next_state -> 'homestead') ? 'owned_cosmetics' then
      if jsonb_typeof((next_state -> 'homestead') -> 'owned_cosmetics') <> 'array' then
        raise exception 'owned_cosmetics must be an array' using errcode = '22023';
      end if;
      if jsonb_array_length((next_state -> 'homestead') -> 'owned_cosmetics') > 100 then
        raise exception 'owned_cosmetics must be bounded' using errcode = '22023';
      end if;
    end if;
    if (next_state -> 'homestead') ? 'equipped' then
      if jsonb_typeof((next_state -> 'homestead') -> 'equipped') <> 'object' then
        raise exception 'equipped projection must be an object' using errcode = '22023';
      end if;
      allowed_fields := array['theme','cursor','hud','terminal'];
      for field_key in select jsonb_object_keys((next_state -> 'homestead') -> 'equipped') loop
        if not (field_key = any(allowed_fields)) then
          raise exception 'equipped projection contains unsupported fields' using errcode = '22023';
        end if;
      end loop;
    end if;
  end if;
end;
$$;

revoke all on function public.validate_player_state_projection(jsonb) from public;

create or replace function public.save_player_state(
  expected_revision bigint,
  next_state jsonb,
  source_device_id uuid
)
returns public.player_state
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  current_row public.player_state;
  saved_row public.player_state;
begin
  if auth.uid() is null then
    raise exception 'Authentication is required' using errcode = '42501';
  end if;
  if expected_revision is null or expected_revision < 0 then
    raise exception 'expected_revision must be non-negative' using errcode = '22023';
  end if;
  if source_device_id is null then
    raise exception 'source_device_id is required' using errcode = '22023';
  end if;
  perform public.validate_player_state_projection(next_state);

  select * into current_row
  from public.player_state
  where user_id = auth.uid()
  for update;

  if current_row is null then
    if expected_revision <> 0 then
      raise exception 'Cloud player state revision conflict' using errcode = '40001';
    end if;
    insert into public.player_state (user_id, state, revision, device_id)
    values (auth.uid(), next_state, 1, source_device_id)
    on conflict (user_id) do nothing
    returning * into saved_row;
    if saved_row is null then
      raise exception 'Cloud player state revision conflict' using errcode = '40001';
    end if;
    return saved_row;
  end if;

  if current_row.revision <> expected_revision then
    raise exception 'Cloud player state revision conflict' using errcode = '40001';
  end if;

  update public.player_state
  set state = next_state,
      revision = current_row.revision + 1,
      device_id = source_device_id,
      updated_at = timezone('utc', now())
  where user_id = auth.uid()
    and revision = expected_revision
  returning * into saved_row;
  if saved_row is null then
    raise exception 'Cloud player state revision conflict' using errcode = '40001';
  end if;
  return saved_row;
end;
$$;

revoke all on function public.save_player_state(bigint, jsonb, uuid) from public;
grant execute on function public.save_player_state(bigint, jsonb, uuid) to authenticated;
