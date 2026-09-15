-- WoD-rpg V0.45+ - persistent state inside a played night and Chronicle time.
-- Apply after supabase/chronicle_schema.sql.

create table if not exists public.wod_character_night_state (
  game_id text not null,
  player_id text not null,
  character_id text not null,
  chapter integer not null check (chapter >= 1),
  segment integer not null check (segment >= 1),
  night_number integer not null check (night_number >= 1),
  phase text not null check (phase in ('event','free_actions')),
  event_id text not null check (char_length(event_id) between 1 and 160),
  remaining_actions integer not null default 0,
  max_actions integer not null default 2 check (max_actions between 1 and 5),
  log_json jsonb not null default '[]'::jsonb check (jsonb_typeof(log_json) = 'array'),
  updated_at timestamptz not null default now(),
  primary key (game_id, player_id),
  foreign key (game_id, player_id)
    references public.wod_player_characters(game_id, player_id)
    on delete cascade,
  check (remaining_actions between 0 and max_actions)
);

alter table public.wod_character_night_state enable row level security;
revoke all on table public.wod_character_night_state from public, anon, authenticated;
grant select, insert, update, delete on table public.wod_character_night_state to service_role;

create or replace function public.wod_ensure_night_cycle_state(
  p_game_id text,
  p_player_id text,
  p_character_id text,
  p_chapter integer,
  p_segment integer,
  p_night_number integer,
  p_event_id text,
  p_max_actions integer default 2
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_character public.wod_player_characters%rowtype;
  v_state public.wod_character_night_state%rowtype;
begin
  select * into v_character
  from public.wod_player_characters
  where game_id = p_game_id and player_id = p_player_id
  for update;

  if not found then
    raise exception 'unknown player character';
  end if;
  if v_character.character_id <> p_character_id
     or v_character.chapter <> p_chapter
     or v_character.segment <> p_segment
     or v_character.local_night <> p_night_number
     or v_character.ready_for_convergence then
    raise exception 'character is not at the requested playable night';
  end if;
  if char_length(trim(p_event_id)) < 1 or p_max_actions < 1 or p_max_actions > 5 then
    raise exception 'invalid night-cycle parameters';
  end if;

  select * into v_state
  from public.wod_character_night_state
  where game_id = p_game_id and player_id = p_player_id
  for update;

  if not found then
    insert into public.wod_character_night_state(
      game_id, player_id, character_id, chapter, segment, night_number,
      phase, event_id, remaining_actions, max_actions, log_json
    ) values (
      p_game_id, p_player_id, p_character_id, p_chapter, p_segment, p_night_number,
      'event', trim(p_event_id), 0, p_max_actions, '[]'::jsonb
    ) returning * into v_state;
  elsif v_state.character_id <> p_character_id
        or v_state.chapter <> p_chapter
        or v_state.segment <> p_segment
        or v_state.night_number <> p_night_number then
    update public.wod_character_night_state
    set character_id = p_character_id,
        chapter = p_chapter,
        segment = p_segment,
        night_number = p_night_number,
        phase = 'event',
        event_id = trim(p_event_id),
        remaining_actions = 0,
        max_actions = p_max_actions,
        log_json = '[]'::jsonb,
        updated_at = now()
    where game_id = p_game_id and player_id = p_player_id
    returning * into v_state;
  elsif v_state.phase = 'event'
        and jsonb_array_length(v_state.log_json) = 0
        and v_state.event_id <> trim(p_event_id) then
    update public.wod_character_night_state
    set event_id = trim(p_event_id),
        updated_at = now()
    where game_id = p_game_id and player_id = p_player_id
    returning * into v_state;
  end if;

  return to_jsonb(v_state);
end;
$$;

create or replace function public.wod_apply_night_cycle_step(
  p_game_id text,
  p_player_id text,
  p_expected_chapter integer,
  p_expected_segment integer,
  p_expected_night integer,
  p_expected_phase text,
  p_expected_log_count integer,
  p_phase text,
  p_event_id text,
  p_remaining_actions integer,
  p_max_actions integer,
  p_log jsonb,
  p_hunger integer,
  p_reputation integer,
  p_personal_influence double precision,
  p_sire_relation integer,
  p_goal_progress integer
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_character public.wod_player_characters%rowtype;
  v_state public.wod_character_night_state%rowtype;
begin
  select * into v_character
  from public.wod_player_characters
  where game_id = p_game_id and player_id = p_player_id
  for update;

  if not found then
    raise exception 'unknown player character';
  end if;
  if v_character.chapter <> p_expected_chapter
     or v_character.segment <> p_expected_segment
     or v_character.local_night <> p_expected_night
     or v_character.ready_for_convergence then
    raise exception 'character night changed before step submission';
  end if;

  select * into v_state
  from public.wod_character_night_state
  where game_id = p_game_id and player_id = p_player_id
  for update;

  if not found then
    raise exception 'night-cycle state is missing';
  end if;
  if v_state.character_id <> v_character.character_id
     or v_state.chapter <> p_expected_chapter
     or v_state.segment <> p_expected_segment
     or v_state.night_number <> p_expected_night
     or v_state.phase <> p_expected_phase
     or jsonb_array_length(v_state.log_json) <> p_expected_log_count then
    raise exception 'night-cycle state changed before step submission';
  end if;
  if p_phase not in ('event','free_actions')
     or p_remaining_actions < 0
     or p_remaining_actions > p_max_actions
     or p_max_actions < 1
     or p_max_actions > 5
     or jsonb_typeof(p_log) <> 'array'
     or jsonb_array_length(p_log) <> p_expected_log_count + 1 then
    raise exception 'invalid night-cycle update';
  end if;

  update public.wod_player_characters
  set hunger = p_hunger,
      reputation = p_reputation,
      personal_influence = p_personal_influence,
      sire_relation = p_sire_relation,
      goal_progress = p_goal_progress,
      updated_at = now()
  where game_id = p_game_id and player_id = p_player_id;

  update public.wod_character_night_state
  set phase = p_phase,
      event_id = p_event_id,
      remaining_actions = p_remaining_actions,
      max_actions = p_max_actions,
      log_json = p_log,
      updated_at = now()
  where game_id = p_game_id and player_id = p_player_id
  returning * into v_state;

  return to_jsonb(v_state);
end;
$$;

revoke all on function public.wod_ensure_night_cycle_state(text,text,text,integer,integer,integer,text,integer)
  from public, anon, authenticated;
revoke all on function public.wod_apply_night_cycle_step(text,text,integer,integer,integer,text,integer,text,text,integer,integer,jsonb,integer,integer,double precision,integer,integer)
  from public, anon, authenticated;
grant execute on function public.wod_ensure_night_cycle_state(text,text,text,integer,integer,integer,text,integer)
  to service_role;
grant execute on function public.wod_apply_night_cycle_step(text,text,integer,integer,integer,text,integer,text,text,integer,integer,jsonb,integer,integer,double precision,integer,integer)
  to service_role;

-- V0.46 - coarse calendar and narrative chapter closure.
-- Legacy segment/ellipse columns stay in place for backwards-compatible saves,
-- but production progression now goes through this temporal RPC.
create table if not exists public.wod_chronicle_time (
  game_id text primary key references public.wod_games(id) on delete cascade,
  month integer not null default 1 check (month between 1 and 12),
  minimum_cycles_per_chapter integer not null default 2
    check (minimum_cycles_per_chapter between 1 and 20),
  cycle_months integer not null default 1 check (cycle_months between 1 and 12),
  updated_at timestamptz not null default now()
);

alter table public.wod_chronicle_time enable row level security;
revoke all on table public.wod_chronicle_time from public, anon, authenticated;
grant select, insert, update, delete on table public.wod_chronicle_time to service_role;

create or replace function public.wod_resolve_temporal_convergence(
  p_game_id text,
  p_close_chapter boolean default false
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_progress public.wod_chronicle_progress%rowtype;
  v_time public.wod_chronicle_time%rowtype;
  v_total integer;
  v_not_ready integer;
  v_goal_ready integer;
  v_goal_strong integer;
  v_oldest_age integer;
  v_highest_status integer;
  v_old_chapter integer;
  v_old_segment integer;
  v_ellipse_months integer := 0;
  v_absolute_month integer;
  v_next_year integer;
  v_next_month integer;
  v_next_chapter integer;
  v_next_segment integer;
begin
  select * into v_progress
  from public.wod_chronicle_progress
  where game_id = p_game_id
  for update;

  if not found then
    raise exception 'chronicle progress missing';
  end if;

  insert into public.wod_chronicle_time(game_id)
  values(p_game_id)
  on conflict(game_id) do nothing;

  select * into v_time
  from public.wod_chronicle_time
  where game_id = p_game_id
  for update;

  v_old_chapter := v_progress.chapter;
  v_old_segment := v_progress.segment;

  select
    count(*),
    count(*) filter (where not ready_for_convergence),
    count(*) filter (where goal_progress >= 2),
    count(*) filter (where goal_progress >= 5),
    coalesce(max(greatest(0, v_progress.year - embraced_year)), 0),
    coalesce(max(status), 0)
  into
    v_total,
    v_not_ready,
    v_goal_ready,
    v_goal_strong,
    v_oldest_age,
    v_highest_status
  from public.wod_player_characters
  where game_id = p_game_id
    and is_active
    and chapter = v_progress.chapter
    and segment = v_progress.segment;

  if v_total = 0 or v_not_ready > 0 then
    raise exception 'all active characters must be ready for convergence';
  end if;

  if p_close_chapter and (
       v_progress.segment < v_time.minimum_cycles_per_chapter
       or v_goal_ready < v_total
       or v_goal_strong < 1
     ) then
    raise exception 'chapter cannot be closed at this convergence';
  end if;

  if p_close_chapter then
    if v_oldest_age >= 300 or v_progress.chapter >= 30 then
      v_ellipse_months := 120;
    elsif v_oldest_age >= 150 or v_progress.chapter >= 20 then
      v_ellipse_months := 60;
    elsif v_oldest_age >= 50 or v_progress.chapter >= 12 or v_highest_status >= 4 then
      v_ellipse_months := 24;
    elsif v_oldest_age >= 20 or v_progress.chapter >= 8 or v_highest_status >= 3 then
      v_ellipse_months := 12;
    elsif v_oldest_age >= 5 or v_progress.chapter >= 4 or v_highest_status >= 2 then
      v_ellipse_months := 3;
    else
      v_ellipse_months := 1;
    end if;
  end if;

  v_absolute_month :=
    v_progress.year * 12
    + (v_time.month - 1)
    + v_time.cycle_months
    + v_ellipse_months;
  v_next_year := v_absolute_month / 12;
  v_next_month := mod(v_absolute_month, 12) + 1;
  v_next_chapter := case when p_close_chapter then v_progress.chapter + 1 else v_progress.chapter end;
  v_next_segment := case when p_close_chapter then 1 else v_progress.segment + 1 end;

  update public.wod_chronicle_progress
  set year = v_next_year,
      chapter = v_next_chapter,
      segment = v_next_segment,
      updated_at = now()
  where game_id = p_game_id
  returning * into v_progress;

  update public.wod_chronicle_time
  set month = v_next_month,
      updated_at = now()
  where game_id = p_game_id
  returning * into v_time;

  update public.wod_player_characters
  set chronicle_year = v_next_year,
      chapter = v_next_chapter,
      segment = v_next_segment,
      local_night = 1,
      ready_for_convergence = false,
      experience = experience + case
        when p_close_chapter and goal_progress >= 5 then 2
        when p_close_chapter and goal_progress >= 2 then 1
        else 0 end,
      personal_influence = personal_influence + case
        when p_close_chapter and goal_progress >= 5 then 1.0
        when p_close_chapter and goal_progress >= 2 then 0.5
        else 0 end,
      reputation = least(3, reputation + case
        when p_close_chapter and goal_progress >= 5 then 1
        else 0 end),
      status = least(5, status + case
        when p_close_chapter and goal_progress >= 7 and status = 0 then 1
        else 0 end),
      goal_progress = case when p_close_chapter then 0 else goal_progress end,
      updated_at = now()
  where game_id = p_game_id
    and is_active
    and chapter = v_old_chapter
    and segment = v_old_segment;

  return jsonb_build_object(
    'progress', to_jsonb(v_progress),
    'time', to_jsonb(v_time),
    'chapter_closed', p_close_chapter,
    'ellipse_months', v_ellipse_months
  );
end;
$$;

revoke all on function public.wod_resolve_temporal_convergence(text,boolean)
  from public, anon, authenticated;
grant execute on function public.wod_resolve_temporal_convergence(text,boolean)
  to service_role;
