-- WoD-rpg V0.5 - persistence distante Supabase/PostgreSQL.
-- Le moteur Python reste cote serveur. Aucun secret Supabase ne doit etre commite.
-- V0.5 conserve un player_id opaque ; Supabase Auth sera ajoute dans une etape separee.

create table if not exists public.wod_games (
  id text primary key,
  name text not null,
  current_night integer not null default 1 check (current_night >= 1),
  status text not null default 'active' check (status in ('active','archived')),
  required_clans text[] not null default array['ventrue','toreador','brujah']::text[],
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.wod_game_states (
  game_id text primary key references public.wod_games(id) on delete cascade,
  state_json jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists public.wod_game_players (
  game_id text not null references public.wod_games(id) on delete cascade,
  player_id text not null,
  player_name text not null check (char_length(player_name) between 1 and 80),
  clan_id text not null check (clan_id in ('ventrue','toreador','brujah')),
  claimed_at timestamptz not null default now(),
  primary key (game_id, player_id),
  unique (game_id, clan_id)
);

create table if not exists public.wod_nights (
  game_id text not null references public.wod_games(id) on delete cascade,
  night_number integer not null check (night_number >= 1),
  status text not null check (status in ('open','ready','resolving','resolved')),
  created_at timestamptz not null default now(),
  resolved_at timestamptz,
  primary key (game_id, night_number)
);

create table if not exists public.wod_night_submissions (
  game_id text not null,
  night_number integer not null,
  clan_id text not null check (clan_id in ('ventrue','toreador','brujah')),
  player_id text not null,
  orders_json jsonb not null,
  submitted_at timestamptz not null default now(),
  primary key (game_id, night_number, clan_id),
  foreign key (game_id, night_number)
    references public.wod_nights(game_id, night_number) on delete cascade
);

create table if not exists public.wod_night_reports (
  game_id text not null,
  night_number integer not null,
  clan_id text not null check (clan_id in ('ventrue','toreador','brujah')),
  report_json jsonb not null,
  created_at timestamptz not null default now(),
  primary key (game_id, night_number, clan_id),
  foreign key (game_id, night_number)
    references public.wod_nights(game_id, night_number) on delete cascade
);

create table if not exists public.wod_elysium_messages (
  id bigint generated always as identity primary key,
  game_id text not null references public.wod_games(id) on delete cascade,
  player_id text not null,
  clan_id text not null check (clan_id in ('ventrue','toreador','brujah')),
  body text not null check (char_length(body) between 1 and 2000),
  created_at timestamptz not null default now()
);

create index if not exists wod_game_players_player_idx
  on public.wod_game_players(player_id, game_id);
create index if not exists wod_nights_game_status_idx
  on public.wod_nights(game_id, status, night_number);
create index if not exists wod_submissions_player_idx
  on public.wod_night_submissions(player_id, game_id, night_number);
create index if not exists wod_reports_clan_idx
  on public.wod_night_reports(game_id, clan_id, night_number desc);
create index if not exists wod_elysium_game_created_idx
  on public.wod_elysium_messages(game_id, created_at desc);
create index if not exists wod_elysium_player_idx
  on public.wod_elysium_messages(player_id, game_id, created_at desc);

alter table public.wod_games enable row level security;
alter table public.wod_game_states enable row level security;
alter table public.wod_game_players enable row level security;
alter table public.wod_nights enable row level security;
alter table public.wod_night_submissions enable row level security;
alter table public.wod_night_reports enable row level security;
alter table public.wod_elysium_messages enable row level security;

revoke all on table public.wod_games from public, anon, authenticated;
revoke all on table public.wod_game_states from public, anon, authenticated;
revoke all on table public.wod_game_players from public, anon, authenticated;
revoke all on table public.wod_nights from public, anon, authenticated;
revoke all on table public.wod_night_submissions from public, anon, authenticated;
revoke all on table public.wod_night_reports from public, anon, authenticated;
revoke all on table public.wod_elysium_messages from public, anon, authenticated;
revoke all on sequence public.wod_elysium_messages_id_seq from public, anon, authenticated;

grant select, insert, update, delete on table public.wod_games to service_role;
grant select, insert, update, delete on table public.wod_game_states to service_role;
grant select, insert, update, delete on table public.wod_game_players to service_role;
grant select, insert, update, delete on table public.wod_nights to service_role;
grant select, insert, update, delete on table public.wod_night_submissions to service_role;
grant select, insert, update, delete on table public.wod_night_reports to service_role;
grant select, insert, update, delete on table public.wod_elysium_messages to service_role;
grant usage, select on sequence public.wod_elysium_messages_id_seq to service_role;

create or replace function public.wod_ensure_game(
  p_game_id text,
  p_name text,
  p_current_night integer,
  p_required_clans text[],
  p_state_json jsonb
)
returns void
language plpgsql
security definer
set search_path = ''
as $$
begin
  insert into public.wod_games(id,name,current_night,status,required_clans)
  values (p_game_id,p_name,p_current_night,'active',p_required_clans)
  on conflict (id) do nothing;
  insert into public.wod_game_states(game_id,state_json)
  values (p_game_id,p_state_json) on conflict (game_id) do nothing;
  insert into public.wod_nights(game_id,night_number,status)
  values (p_game_id,p_current_night,'open') on conflict (game_id,night_number) do nothing;
end;
$$;

create or replace function public.wod_submit_orders(p_game_id text,p_player_id text,p_clan_id text,p_orders_json jsonb)
returns text language plpgsql security definer set search_path = '' as $$
declare v_night integer; v_status text; v_required text[]; v_count integer; v_assigned text;
begin
  select g.current_night,g.required_clans into v_night,v_required from public.wod_games g where g.id=p_game_id for update;
  if v_night is null then raise exception 'Unknown game'; end if;
  select gp.clan_id into v_assigned from public.wod_game_players gp where gp.game_id=p_game_id and gp.player_id=p_player_id;
  if v_assigned is null or v_assigned<>p_clan_id then raise exception 'Player is not assigned to this clan'; end if;
  select n.status into v_status from public.wod_nights n where n.game_id=p_game_id and n.night_number=v_night for update;
  if v_status<>'open' then raise exception 'This night no longer accepts orders'; end if;
  insert into public.wod_night_submissions(game_id,night_number,clan_id,player_id,orders_json)
  values(p_game_id,v_night,p_clan_id,p_player_id,p_orders_json);
  select count(*) into v_count from public.wod_night_submissions s where s.game_id=p_game_id and s.night_number=v_night and s.clan_id=any(v_required);
  if v_count>=cardinality(v_required) then
    update public.wod_nights set status='ready' where game_id=p_game_id and night_number=v_night;
    return 'ready';
  end if;
  return 'open';
end;
$$;

create or replace function public.wod_try_begin_resolution(p_game_id text)
returns jsonb language plpgsql security definer set search_path = '' as $$
declare v_night integer; v_state jsonb; v_orders jsonb; v_rows integer;
begin
  select g.current_night into v_night from public.wod_games g where g.id=p_game_id for update;
  if v_night is null then raise exception 'Unknown game'; end if;
  update public.wod_nights set status='resolving' where game_id=p_game_id and night_number=v_night and status='ready';
  get diagnostics v_rows=row_count;
  if v_rows=0 then return null; end if;
  select gs.state_json into v_state from public.wod_game_states gs where gs.game_id=p_game_id;
  select coalesce(jsonb_object_agg(s.clan_id,s.orders_json),'{}'::jsonb) into v_orders from public.wod_night_submissions s where s.game_id=p_game_id and s.night_number=v_night;
  return jsonb_build_object('game_id',p_game_id,'night',v_night,'state_json',v_state,'orders_by_clan',v_orders);
end;
$$;

create or replace function public.wod_abort_resolution(p_game_id text,p_night integer)
returns void language plpgsql security definer set search_path = '' as $$
begin
  update public.wod_nights set status='ready' where game_id=p_game_id and night_number=p_night and status='resolving';
end;
$$;

create or replace function public.wod_finalize_resolution(p_game_id text,p_night integer,p_next_night integer,p_state_json jsonb,p_reports jsonb)
returns void language plpgsql security definer set search_path = '' as $$
declare v_status text; r record;
begin
  select n.status into v_status from public.wod_nights n where n.game_id=p_game_id and n.night_number=p_night for update;
  if v_status<>'resolving' then raise exception 'Night is not locked for resolution'; end if;
  update public.wod_nights set status='resolved',resolved_at=now() where game_id=p_game_id and night_number=p_night;
  for r in select key as clan_id,value as report_json from jsonb_each(p_reports) loop
    insert into public.wod_night_reports(game_id,night_number,clan_id,report_json)
    values(p_game_id,p_night,r.clan_id,r.report_json)
    on conflict(game_id,night_number,clan_id) do update set report_json=excluded.report_json;
  end loop;
  insert into public.wod_game_states(game_id,state_json,updated_at) values(p_game_id,p_state_json,now())
  on conflict(game_id) do update set state_json=excluded.state_json,updated_at=excluded.updated_at;
  update public.wod_games set current_night=p_next_night,updated_at=now() where id=p_game_id;
  insert into public.wod_nights(game_id,night_number,status) values(p_game_id,p_next_night,'open') on conflict(game_id,night_number) do nothing;
end;
$$;

revoke all on function public.wod_ensure_game(text,text,integer,text[],jsonb) from public,anon,authenticated;
revoke all on function public.wod_submit_orders(text,text,text,jsonb) from public,anon,authenticated;
revoke all on function public.wod_try_begin_resolution(text) from public,anon,authenticated;
revoke all on function public.wod_abort_resolution(text,integer) from public,anon,authenticated;
revoke all on function public.wod_finalize_resolution(text,integer,integer,jsonb,jsonb) from public,anon,authenticated;
grant execute on function public.wod_ensure_game(text,text,integer,text[],jsonb) to service_role;
grant execute on function public.wod_submit_orders(text,text,text,jsonb) to service_role;
grant execute on function public.wod_try_begin_resolution(text) to service_role;
grant execute on function public.wod_abort_resolution(text,integer) to service_role;
grant execute on function public.wod_finalize_resolution(text,integer,integer,jsonb,jsonb) to service_role;
