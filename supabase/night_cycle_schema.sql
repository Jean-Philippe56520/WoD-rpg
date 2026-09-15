-- WoD-rpg V0.45 - persistent state inside a played night.
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
