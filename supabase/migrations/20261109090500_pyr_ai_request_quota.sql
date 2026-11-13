-- Keep the shared PYR provider key usable only by authenticated players in a
-- private Hunter group, with a persistent per-account request budget.
create schema if not exists private;
revoke all on schema private from public, anon;

create table private.pyr_ai_usage (
  user_id uuid primary key references auth.users(id) on delete cascade,
  minute_started_at timestamptz not null default now(),
  minute_requests integer not null default 0 check (minute_requests >= 0),
  usage_day date not null default ((now() at time zone 'utc')::date),
  daily_requests integer not null default 0 check (daily_requests >= 0)
);
alter table private.pyr_ai_usage enable row level security;
revoke all on private.pyr_ai_usage from public, anon, authenticated;

create function public.consume_pyr_ai_request()
returns boolean
language plpgsql
security definer
set search_path = ''
as $$
declare
  caller uuid := auth.uid();
  usage_row private.pyr_ai_usage%rowtype;
  current_time_utc timestamptz := now();
  current_day_utc date := (now() at time zone 'utc')::date;
begin
  if caller is null then
    raise exception 'Sign in first';
  end if;

  insert into private.pyr_ai_usage(user_id, minute_started_at, usage_day)
    values (caller, current_time_utc, current_day_utc)
    on conflict (user_id) do nothing;
  select * into usage_row from private.pyr_ai_usage where user_id = caller for update;

  if usage_row.usage_day <> current_day_utc then
    usage_row.usage_day := current_day_utc;
    usage_row.daily_requests := 0;
  end if;
  if current_time_utc - usage_row.minute_started_at >= interval '1 minute' then
    usage_row.minute_started_at := current_time_utc;
    usage_row.minute_requests := 0;
  end if;

  if usage_row.daily_requests >= 100 or usage_row.minute_requests >= 12 then
    update private.pyr_ai_usage
      set usage_day = usage_row.usage_day,
          daily_requests = usage_row.daily_requests,
          minute_started_at = usage_row.minute_started_at,
          minute_requests = usage_row.minute_requests
      where user_id = caller;
    return false;
  end if;

  update private.pyr_ai_usage
    set usage_day = usage_row.usage_day,
        daily_requests = usage_row.daily_requests + 1,
        minute_started_at = usage_row.minute_started_at,
        minute_requests = usage_row.minute_requests + 1
    where user_id = caller;
  return true;
end;
$$;

revoke all on function public.consume_pyr_ai_request() from public, anon;
grant execute on function public.consume_pyr_ai_request() to authenticated;
