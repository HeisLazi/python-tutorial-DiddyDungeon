-- Milestone D: private account-scoped character portraits.
-- The bucket is private; the object name is fixed to one path per account so
-- a browser client cannot use this surface as an arbitrary file store.

alter table public.profiles add column if not exists avatar_path text;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'profiles_avatar_path_safe'
      and conrelid = 'public.profiles'::regclass
  ) then
    alter table public.profiles
      add constraint profiles_avatar_path_safe check (
        avatar_path is null
        or (
          char_length(avatar_path) <= 120
          and avatar_path = (id::text || '/avatar.webp')
        )
      );
  end if;
end
$$;

insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values (
  'avatars',
  'avatars',
  false,
  1048576,
  array['image/webp']::text[]
)
on conflict (id) do update
set name = excluded.name,
    public = false,
    file_size_limit = excluded.file_size_limit,
    allowed_mime_types = excluded.allowed_mime_types;

drop policy if exists avatars_objects_select_own on storage.objects;
create policy avatars_objects_select_own
on storage.objects for select
to authenticated
using (
  bucket_id = 'avatars'
  and name = ((select auth.uid())::text || '/avatar.webp')
);

drop policy if exists avatars_objects_insert_own on storage.objects;
create policy avatars_objects_insert_own
on storage.objects for insert
to authenticated
with check (
  bucket_id = 'avatars'
  and name = ((select auth.uid())::text || '/avatar.webp')
);

drop policy if exists avatars_objects_update_own on storage.objects;
create policy avatars_objects_update_own
on storage.objects for update
to authenticated
using (
  bucket_id = 'avatars'
  and name = ((select auth.uid())::text || '/avatar.webp')
)
with check (
  bucket_id = 'avatars'
  and name = ((select auth.uid())::text || '/avatar.webp')
);

drop policy if exists avatars_objects_delete_own on storage.objects;
create policy avatars_objects_delete_own
on storage.objects for delete
to authenticated
using (
  bucket_id = 'avatars'
  and name = ((select auth.uid())::text || '/avatar.webp')
);
