-- Quest Lab identity foundation. Game-state tables are intentionally deferred
-- until the Sync Engine milestone; these tables contain account/device identity
-- only and are private to the authenticated owner.

create table if not exists public.profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text not null default 'Quest Lab player',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  constraint profiles_display_name_length check (char_length(trim(display_name)) between 1 and 80),
  constraint profiles_display_name_no_control_chars check (display_name !~ '[[:cntrl:]]')
);

create table if not exists public.devices (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  display_name text not null default 'Quest Lab device',
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  last_seen_at timestamptz not null default timezone('utc', now()),
  constraint devices_display_name_length check (char_length(trim(display_name)) between 1 and 80),
  constraint devices_display_name_safe check (
    display_name !~ '[[:cntrl:]]'
    and position('/' in display_name) = 0
    and position(chr(92) in display_name) = 0
    and position(':' in display_name) = 0
  )
);

create index if not exists devices_user_id_idx on public.devices (user_id);

create or replace function public.set_identity_updated_at()
returns trigger
language plpgsql
set search_path = public
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

drop trigger if exists profiles_set_updated_at on public.profiles;
create trigger profiles_set_updated_at
before update on public.profiles
for each row execute function public.set_identity_updated_at();

drop trigger if exists devices_set_updated_at on public.devices;
create trigger devices_set_updated_at
before update on public.devices
for each row execute function public.set_identity_updated_at();

create or replace function public.handle_new_quest_lab_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  metadata_name text;
  email_name text;
begin
  metadata_name := nullif(trim(new.raw_user_meta_data ->> 'display_name'), '');
  email_name := nullif(trim(split_part(coalesce(new.email, ''), '@', 1)), '');

  insert into public.profiles (id, display_name)
  values (new.id, left(coalesce(metadata_name, email_name, 'Quest Lab player'), 80))
  on conflict (id) do nothing;
  return new;
end;
$$;

revoke all on function public.handle_new_quest_lab_user() from public;
drop trigger if exists on_auth_user_created_quest_lab on auth.users;
create trigger on_auth_user_created_quest_lab
after insert on auth.users
for each row execute function public.handle_new_quest_lab_user();

alter table public.profiles enable row level security;
alter table public.devices enable row level security;

revoke all on public.profiles from anon;
revoke all on public.devices from anon;
grant select, insert, update on public.profiles to authenticated;
grant select, insert, update, delete on public.devices to authenticated;

drop policy if exists profiles_select_own on public.profiles;
create policy profiles_select_own
on public.profiles for select
to authenticated
using ((select auth.uid()) = id);

drop policy if exists profiles_insert_own on public.profiles;
create policy profiles_insert_own
on public.profiles for insert
to authenticated
with check ((select auth.uid()) = id);

drop policy if exists profiles_update_own on public.profiles;
create policy profiles_update_own
on public.profiles for update
to authenticated
using ((select auth.uid()) = id)
with check ((select auth.uid()) = id);

drop policy if exists devices_select_own on public.devices;
create policy devices_select_own
on public.devices for select
to authenticated
using ((select auth.uid()) = user_id);

drop policy if exists devices_insert_own on public.devices;
create policy devices_insert_own
on public.devices for insert
to authenticated
with check ((select auth.uid()) = user_id);

drop policy if exists devices_update_own on public.devices;
create policy devices_update_own
on public.devices for update
to authenticated
using ((select auth.uid()) = user_id)
with check ((select auth.uid()) = user_id);

drop policy if exists devices_delete_own on public.devices;
create policy devices_delete_own
on public.devices for delete
to authenticated
using ((select auth.uid()) = user_id);
