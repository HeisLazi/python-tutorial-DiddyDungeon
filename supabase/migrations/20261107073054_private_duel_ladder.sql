-- Private ranked leaderboard. A trusted match service is the sole writer;
-- user clients may only read rows belonging to their own groups.
create table public.hunter_group_ratings (
  group_id uuid not null references public.hunter_groups(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  rating integer not null default 1000 check (rating between 0 and 4000),
  wins integer not null default 0 check (wins >= 0),
  losses integer not null default 0 check (losses >= 0),
  draws integer not null default 0 check (draws >= 0),
  updated_at timestamptz not null default now(),
  primary key (group_id, user_id)
);
create table public.hunter_ranked_matches (
  id uuid primary key,
  group_id uuid not null references public.hunter_groups(id) on delete cascade,
  player_one uuid not null references auth.users(id) on delete cascade,
  player_two uuid not null references auth.users(id) on delete cascade,
  winner uuid references auth.users(id) on delete cascade,
  player_one_before integer not null,
  player_two_before integer not null,
  player_one_after integer not null,
  player_two_after integer not null,
  settled_at timestamptz not null default now(),
  check (player_one <> player_two),
  check (winner is null or winner in (player_one, player_two))
);
create index hunter_ranked_matches_group_time_idx on public.hunter_ranked_matches(group_id, settled_at desc);
alter table public.hunter_group_ratings enable row level security;
alter table public.hunter_ranked_matches enable row level security;
revoke all on public.hunter_group_ratings, public.hunter_ranked_matches from public, anon, authenticated;
grant select on public.hunter_group_ratings, public.hunter_ranked_matches to authenticated;
create policy hunter_group_ratings_member_read on public.hunter_group_ratings for select to authenticated
  using ((select private.is_hunter_group_member(group_id)));
create policy hunter_ranked_matches_member_read on public.hunter_ranked_matches for select to authenticated
  using ((select private.is_hunter_group_member(group_id)));

create function public.settle_hunter_ranked_match(
  match_id uuid, target_group uuid, first_player uuid, second_player uuid, winning_player uuid
) returns void language plpgsql security definer set search_path = '' as $$
declare existing public.hunter_ranked_matches%rowtype;
        first_rating integer; second_rating integer; delta integer;
        expected numeric; score numeric;
begin
  if match_id is null or target_group is null or first_player is null or second_player is null
     or first_player = second_player or (winning_player is not null and winning_player not in (first_player, second_player)) then
    raise exception 'Invalid ranked match';
  end if;
  -- Serializes retries, simultaneous settlements and membership checks for this group.
  perform 1 from public.hunter_groups where id = target_group for update;
  if not found then raise exception 'Group not found'; end if;
  select * into existing from public.hunter_ranked_matches where id = match_id;
  if found then
    if existing.group_id <> target_group or existing.player_one <> first_player or existing.player_two <> second_player
       or existing.winner is distinct from winning_player then
      raise exception 'Conflicting match settlement';
    end if;
    return;
  end if;
  if (select count(*) from public.hunter_group_members where group_id = target_group and user_id in (first_player, second_player)) <> 2 then
    raise exception 'Both hunters must belong to the group';
  end if;
  insert into public.hunter_group_ratings(group_id, user_id)
    values (target_group, first_player), (target_group, second_player) on conflict do nothing;
  -- The group lock above serializes all settlements in this group.
  select rating into first_rating from public.hunter_group_ratings where group_id = target_group and user_id = first_player for update;
  select rating into second_rating from public.hunter_group_ratings where group_id = target_group and user_id = second_player for update;
  expected := 1.0 / (1.0 + power(10.0::numeric, (second_rating - first_rating)::numeric / 400.0));
  score := case when winning_player is null then 0.5 when winning_player = first_player then 1.0 else 0.0 end;
  delta := round(24.0 * (score - expected));
  -- Keep the zero-sum change within both rating constraints.
  delta := greatest(-first_rating, least(4000 - first_rating, delta));
  delta := greatest(second_rating - 4000, least(second_rating, delta));
  update public.hunter_group_ratings set rating = first_rating + delta,
    wins = wins + case when winning_player = first_player then 1 else 0 end,
    losses = losses + case when winning_player = second_player then 1 else 0 end,
    draws = draws + case when winning_player is null then 1 else 0 end, updated_at = now()
    where group_id = target_group and user_id = first_player;
  update public.hunter_group_ratings set rating = second_rating - delta,
    wins = wins + case when winning_player = second_player then 1 else 0 end,
    losses = losses + case when winning_player = first_player then 1 else 0 end,
    draws = draws + case when winning_player is null then 1 else 0 end, updated_at = now()
    where group_id = target_group and user_id = second_player;
  insert into public.hunter_ranked_matches(id, group_id, player_one, player_two, winner,
    player_one_before, player_two_before, player_one_after, player_two_after)
    values (match_id, target_group, first_player, second_player, winning_player,
      first_rating, second_rating, first_rating + delta, second_rating - delta);
end;
$$;
revoke all on function public.settle_hunter_ranked_match(uuid, uuid, uuid, uuid, uuid) from public, anon, authenticated;
grant execute on function public.settle_hunter_ranked_match(uuid, uuid, uuid, uuid, uuid) to service_role;
