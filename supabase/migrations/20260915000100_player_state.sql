-- Bounded player-state transport for Sync Engine v1.
-- The browser may read its own row, but all writes go through the
-- security-definer compare-and-swap RPC below.

create table if not exists public.player_state (
  user_id uuid primary key references auth.users (id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  revision bigint not null default 0,
  device_id uuid not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint player_state_state_object check (jsonb_typeof(state) = 'object'),
  constraint player_state_state_domains check ((state - array['player', 'equipment', 'companion', 'homestead']) = '{}'::jsonb),
  constraint player_state_state_size check (octet_length(state::text) <= 24000),
  constraint player_state_revision_nonnegative check (revision >= 0)
);

alter table public.player_state enable row level security;

revoke all on public.player_state from anon;
revoke all on public.player_state from authenticated;
grant select on public.player_state to authenticated;

drop policy if exists player_state_select_own on public.player_state;
create policy player_state_select_own
on public.player_state for select
to authenticated
using ((select auth.uid()) = user_id);

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
  state_domains text[] := array['player', 'equipment', 'companion', 'homestead'];
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
  if next_state is null or jsonb_typeof(next_state) <> 'object' then
    raise exception 'next_state must be a JSON object' using errcode = '22023';
  end if;
  if (next_state - state_domains) <> '{}'::jsonb then
    raise exception 'next_state contains unsupported domains' using errcode = '22023';
  end if;
  if octet_length(next_state::text) > 24000 then
    raise exception 'next_state is too large' using errcode = '22023';
  end if;

  if next_state ? 'player' then
    if jsonb_typeof(next_state -> 'player') <> 'object' or
       ((next_state -> 'player') - array['name','title','rank','level','xp','xp_next','lifetime_xp','hp','max_hp','coins','potions']) <> '{}'::jsonb then
      raise exception 'player projection contains unsupported fields' using errcode = '22023';
    end if;
  end if;
  if next_state ? 'equipment' then
    if jsonb_typeof(next_state -> 'equipment') <> 'object' or
       ((next_state -> 'equipment') - array['armor','trinket','title']) <> '{}'::jsonb then
      raise exception 'equipment projection contains unsupported fields' using errcode = '22023';
    end if;
  end if;
  if next_state ? 'companion' then
    if jsonb_typeof(next_state -> 'companion') <> 'object' or
       ((next_state -> 'companion') - array['name','form','level','bond','next_form','next_form_requirement']) <> '{}'::jsonb then
      raise exception 'companion projection contains unsupported fields' using errcode = '22023';
    end if;
  end if;
  if next_state ? 'homestead' then
    if jsonb_typeof(next_state -> 'homestead') <> 'object' or
       ((next_state -> 'homestead') - array['name','owned_cosmetics','equipped']) <> '{}'::jsonb then
      raise exception 'homestead projection contains unsupported fields' using errcode = '22023';
    end if;
    if (next_state -> 'homestead') ? 'owned_cosmetics' and
       (jsonb_typeof((next_state -> 'homestead') -> 'owned_cosmetics') <> 'array' or
        jsonb_array_length((next_state -> 'homestead') -> 'owned_cosmetics') > 100) then
      raise exception 'owned_cosmetics must be a bounded array' using errcode = '22023';
    end if;
    if (next_state -> 'homestead') ? 'equipped' and
       (jsonb_typeof((next_state -> 'homestead') -> 'equipped') <> 'object' or
        (((next_state -> 'homestead') -> 'equipped') - array['theme','cursor','hud','terminal']) <> '{}'::jsonb) then
      raise exception 'equipped projection contains unsupported fields' using errcode = '22023';
    end if;
  end if;

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
