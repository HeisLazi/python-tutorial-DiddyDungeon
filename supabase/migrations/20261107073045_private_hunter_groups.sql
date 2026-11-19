-- Private hunter groups. This migration does not touch campaign or save data.
-- All writes happen through authenticated functions; invitation secrets are
-- stored only as SHA-256 hashes and can be redeemed once.
create schema if not exists private;
create extension if not exists pgcrypto with schema extensions;
revoke all on schema private from public, anon;
grant usage on schema private to authenticated;

create table public.hunter_groups (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete cascade,
  name text not null check (char_length(trim(name)) between 1 and 40 and name !~ '[[:cntrl:]]'),
  created_at timestamptz not null default now()
);
create table public.hunter_group_members (
  group_id uuid not null references public.hunter_groups(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  joined_at timestamptz not null default now(),
  primary key (group_id, user_id)
);
create index hunter_group_members_user_idx on public.hunter_group_members(user_id);
create table private.hunter_group_invites (
  token_hash bytea primary key,
  group_id uuid not null references public.hunter_groups(id) on delete cascade,
  created_by uuid not null references auth.users(id) on delete cascade,
  expires_at timestamptz not null,
  redeemed_at timestamptz
);
revoke all on private.hunter_group_invites from public, anon, authenticated;

create function private.is_hunter_group_member(group_to_check uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select auth.uid() is not null and exists (
    select 1 from public.hunter_group_members m
    where m.group_id = group_to_check and m.user_id = auth.uid()
  );
$$;
revoke all on function private.is_hunter_group_member(uuid) from public, anon;
grant execute on function private.is_hunter_group_member(uuid) to authenticated;

alter table public.hunter_groups enable row level security;
alter table public.hunter_group_members enable row level security;
revoke all on public.hunter_groups, public.hunter_group_members from public, anon, authenticated;
grant select on public.hunter_groups, public.hunter_group_members to authenticated;
create policy hunter_groups_member_read on public.hunter_groups for select to authenticated
  using ((select private.is_hunter_group_member(id)));
create policy hunter_group_members_member_read on public.hunter_group_members for select to authenticated
  using ((select private.is_hunter_group_member(group_id)));

create function public.create_hunter_group(group_name text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare created_group uuid; caller uuid := auth.uid();
begin
  if caller is null then raise exception 'Sign in first'; end if;
  if group_name is null or char_length(trim(group_name)) not between 1 and 40 or group_name ~ '[[:cntrl:]]' then
    raise exception 'Group name must be 1–40 characters';
  end if;
  insert into public.hunter_groups(owner_id, name) values (caller, trim(group_name)) returning id into created_group;
  insert into public.hunter_group_members(group_id, user_id) values (created_group, caller);
  return created_group;
end;
$$;

create function public.create_hunter_group_invite(target_group uuid)
returns text language plpgsql security definer set search_path = '' as $$
declare raw_token text; caller uuid := auth.uid();
begin
  if caller is null then raise exception 'Sign in first'; end if;
  perform 1 from public.hunter_groups where id = target_group and owner_id = caller for update;
  if not found then raise exception 'Only the group owner can invite'; end if;
  if (select count(*) from public.hunter_group_members where group_id = target_group) >= 4 then
    raise exception 'This group is full';
  end if;
  -- One active invitation at a time prevents accumulating unlimited open links.
  delete from private.hunter_group_invites where group_id = target_group and redeemed_at is null;
  raw_token := encode(extensions.gen_random_bytes(24), 'hex');
  insert into private.hunter_group_invites(token_hash, group_id, created_by, expires_at)
    values (extensions.digest(raw_token, 'sha256'), target_group, caller, now() + interval '24 hours');
  return raw_token;
end;
$$;

create function public.join_hunter_group(invitation text)
returns uuid language plpgsql security definer set search_path = '' as $$
declare invite private.hunter_group_invites%rowtype; caller uuid := auth.uid();
begin
  if caller is null then raise exception 'Sign in first'; end if;
  if invitation is null or invitation !~ '^[0-9a-f]{48}$' then raise exception 'Invalid invitation'; end if;
  select * into invite from private.hunter_group_invites
    where token_hash = extensions.digest(invitation, 'sha256');
  if not found or invite.redeemed_at is not null or invite.expires_at <= now() then
    raise exception 'Invitation is invalid or expired';
  end if;
  perform 1 from public.hunter_groups where id = invite.group_id for update;
  -- Lock group before invitation, matching the invitation-creation order.
  select * into invite from private.hunter_group_invites
    where token_hash = extensions.digest(invitation, 'sha256') for update;
  if not found or invite.redeemed_at is not null or invite.expires_at <= now() then
    raise exception 'Invitation is invalid or expired';
  end if;
  if exists (select 1 from public.hunter_group_members where group_id = invite.group_id and user_id = caller) then
    raise exception 'You are already in this group';
  end if;
  if (select count(*) from public.hunter_group_members where group_id = invite.group_id) >= 4 then
    raise exception 'This group is full';
  end if;
  insert into public.hunter_group_members(group_id, user_id) values (invite.group_id, caller);
  update private.hunter_group_invites set redeemed_at = now() where token_hash = invite.token_hash;
  return invite.group_id;
end;
$$;

create function public.leave_hunter_group(target_group uuid)
returns void language plpgsql security definer set search_path = '' as $$
declare caller uuid := auth.uid();
begin
  if caller is null then raise exception 'Sign in first'; end if;
  if exists (select 1 from public.hunter_groups where id = target_group and owner_id = caller) then
    raise exception 'The group owner cannot leave without transferring ownership';
  end if;
  delete from public.hunter_group_members where group_id = target_group and user_id = caller;
end;
$$;

-- Profiles are private by default. Group members can request only the names
-- and IDs of hunters in their own group, with no emails or account metadata.
create function public.hunter_group_roster(target_group uuid)
returns table(user_id uuid, display_name text) language plpgsql stable security definer set search_path = '' as $$
begin
  if not private.is_hunter_group_member(target_group) then raise exception 'Group not found'; end if;
  return query select m.user_id, coalesce(nullif(trim(p.display_name), ''), 'Hunter')
    from public.hunter_group_members m left join public.profiles p on p.id = m.user_id
    where m.group_id = target_group order by m.joined_at, m.user_id;
end;
$$;

revoke all on function public.create_hunter_group(text), public.create_hunter_group_invite(uuid), public.join_hunter_group(text), public.leave_hunter_group(uuid), public.hunter_group_roster(uuid) from public, anon;
grant execute on function public.create_hunter_group(text), public.create_hunter_group_invite(uuid), public.join_hunter_group(text), public.leave_hunter_group(uuid), public.hunter_group_roster(uuid) to authenticated;

-- This policy controls only the scoped private Realtime topic, never save data.
-- The deployment must also disable public Realtime channel access.
create policy hunter_group_realtime_read on realtime.messages for select to authenticated
using (extension in ('presence', 'broadcast') and exists (
  select 1 from public.hunter_group_members m
  where m.user_id = (select auth.uid()) and (select realtime.topic()) = 'hunter-group:' || m.group_id::text
));
create policy hunter_group_realtime_write on realtime.messages for insert to authenticated
with check (extension in ('presence', 'broadcast') and exists (
  select 1 from public.hunter_group_members m
  where m.user_id = (select auth.uid()) and (select realtime.topic()) = 'hunter-group:' || m.group_id::text
));
