-- Future ranked gear authority. Local campaign saves are never modified or
-- assumed to prove a verified grant. Only a trusted award service can write.
create table public.verified_hunter_gear (
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id text not null check (item_id ~ '^[a-z0-9][a-z0-9-]{0,127}$'),
  awarded_at timestamptz not null default now(),
  primary key (user_id, item_id)
);
create table private.hunter_gear_grants (
  event_id uuid primary key,
  user_id uuid not null references auth.users(id) on delete cascade,
  item_id text not null check (item_id ~ '^[a-z0-9][a-z0-9-]{0,127}$'),
  source_kind text not null check (source_kind in ('verified-campaign', 'verified-reward')),
  source_reference text not null check (char_length(source_reference) between 1 and 128 and source_reference !~ '[[:cntrl:]]'),
  awarded_at timestamptz not null default now()
);
revoke all on private.hunter_gear_grants from public, anon, authenticated;
alter table public.verified_hunter_gear enable row level security;
revoke all on public.verified_hunter_gear from public, anon, authenticated;
grant select on public.verified_hunter_gear to authenticated;
create policy verified_hunter_gear_owner_read on public.verified_hunter_gear for select to authenticated
  using (user_id = (select auth.uid()));

create function public.award_verified_hunter_gear(
  award_id uuid, target_user uuid, gear_id text, award_source text, reference_id text
) returns boolean language plpgsql security definer set search_path = '' as $$
declare existing private.hunter_gear_grants%rowtype;
begin
  if award_id is null or target_user is null or gear_id is null or gear_id !~ '^[a-z0-9][a-z0-9-]{0,127}$'
     or award_source is null or award_source not in ('verified-campaign', 'verified-reward')
     or reference_id is null or char_length(reference_id) not between 1 and 128 or reference_id ~ '[[:cntrl:]]' then
    raise exception 'Invalid verified gear award';
  end if;
  -- Serialize retrying the same receipt; clients cannot call this function.
  perform pg_advisory_xact_lock(hashtextextended(award_id::text, 0));
  select * into existing from private.hunter_gear_grants where event_id = award_id;
  if found then
    if existing.user_id <> target_user or existing.item_id <> gear_id
       or existing.source_kind <> award_source or existing.source_reference <> reference_id then
      raise exception 'Conflicting gear award';
    end if;
    return false;
  end if;
  insert into private.hunter_gear_grants(event_id, user_id, item_id, source_kind, source_reference)
    values (award_id, target_user, gear_id, award_source, reference_id);
  insert into public.verified_hunter_gear(user_id, item_id) values (target_user, gear_id) on conflict do nothing;
  return true;
end;
$$;
revoke all on function public.award_verified_hunter_gear(uuid,uuid,text,text,text) from public, anon, authenticated;
grant execute on function public.award_verified_hunter_gear(uuid,uuid,text,text,text) to service_role;
