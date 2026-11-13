-- Keep membership, cleanup, and ranked history lookups efficient as groups
-- accumulate matches. These indexes cover foreign keys that are not already
-- the leading columns of a primary key or existing index.
create index if not exists hunter_gear_grants_user_id_idx
  on private.hunter_gear_grants (user_id);
create index if not exists hunter_group_invites_group_id_idx
  on private.hunter_group_invites (group_id);
create index if not exists hunter_group_invites_created_by_idx
  on private.hunter_group_invites (created_by);
create index if not exists hunter_group_ratings_user_id_idx
  on public.hunter_group_ratings (user_id);
create index if not exists hunter_groups_owner_id_idx
  on public.hunter_groups (owner_id);
create index if not exists hunter_ranked_matches_player_one_idx
  on public.hunter_ranked_matches (player_one);
create index if not exists hunter_ranked_matches_player_two_idx
  on public.hunter_ranked_matches (player_two);
create index if not exists hunter_ranked_matches_winner_idx
  on public.hunter_ranked_matches (winner);
