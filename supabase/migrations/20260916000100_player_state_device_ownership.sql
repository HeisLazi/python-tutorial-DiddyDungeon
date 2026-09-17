-- Bind player-state provenance to an account-owned device row.
-- The browser supplies the device UUID, but the security-definer RPC must not
-- trust that value as provenance unless it belongs to auth.uid().

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
  if not exists (
    select 1
    from public.devices
    where id = source_device_id
      and user_id = auth.uid()
  ) then
    raise exception 'source_device_id does not belong to the authenticated account' using errcode = '42501';
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
