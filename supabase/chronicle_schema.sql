-- WoD-rpg - schema declaratif de la chronique personnage (V0.21 -> V0.39).
-- A executer APRES supabase/schema.sql sur une base vierge.
-- GitHub documente ici l'etat reproductible attendu ; les changements de production
-- restent appliques par migrations Supabase explicites.
-- Toutes les tables de chronique restent server-only : aucun acces direct anon/authenticated.

create table if not exists public.wod_chronicle_progress (
  game_id text primary key references public.wod_games(id) on delete cascade,
  year integer not null default 1435 check (year >= 1),
  chapter integer not null default 1 check (chapter >= 1),
  segment integer not null default 1 check (segment >= 1),
  nights_per_segment integer not null default 3 check (nights_per_segment between 1 and 20),
  segments_per_chapter integer not null default 3 check (segments_per_chapter between 1 and 20),
  ellipse_years integer not null default 2 check (ellipse_years between 0 and 200),
  updated_at timestamptz not null default now()
);

create table if not exists public.wod_player_characters (
  game_id text not null references public.wod_games(id) on delete cascade,
  player_id text not null,
  player_name text not null check (char_length(player_name) between 1 and 80),
  character_id text not null,
  name text not null check (char_length(name) between 1 and 120),
  clan_id text not null check (clan_id in ('ventrue','toreador','brujah')),
  concept text not null,
  sire_id text not null,
  sire_name text not null,
  embraced_year integer not null,
  chronicle_year integer not null,
  chapter integer not null check (chapter >= 1),
  segment integer not null check (segment >= 1),
  local_night integer not null check (local_night >= 1),
  hunger integer not null check (hunger between 0 and 5),
  humanity integer not null check (humanity between 0 and 10),
  status integer not null check (status between 0 and 5),
  reputation integer not null check (reputation between -3 and 3),
  personal_influence double precision not null default 0 check (personal_influence >= 0),
  sire_relation integer not null check (sire_relation between 0 and 3),
  goal_progress integer not null default 0 check (goal_progress >= 0),
  long_term_goal text not null,
  chapter_goal text not null,
  starting_discipline text not null,
  mortal_stance text not null check (mortal_stance in ('humanist','predatory')),
  order_stance text not null check (order_stance in ('orthodox','reformist')),
  ready_for_convergence boolean not null default false,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  experience integer not null default 0 check (experience >= 0),
  office text not null default 'none'
    check (office in ('none','domain_holder','clan_envoy','primogen','prince')),
  lineage_parent_id text,
  primary key (game_id, player_id),
  unique (game_id, character_id)
);

create index if not exists wod_player_characters_lineage_idx
  on public.wod_player_characters(game_id, lineage_parent_id)
  where lineage_parent_id is not null;

create table if not exists public.wod_character_night_history (
  game_id text not null,
  character_id text not null,
  chapter integer not null,
  segment integer not null,
  night_number integer not null,
  action text not null,
  outcome_json jsonb not null,
  created_at timestamptz not null default now(),
  primary key (game_id, character_id, chapter, segment, night_number),
  foreign key (game_id, character_id)
    references public.wod_player_characters(game_id, character_id)
    on delete cascade
);

create table if not exists public.wod_character_scenes (
  id text primary key,
  game_id text not null references public.wod_games(id) on delete cascade,
  from_character_id text not null,
  to_character_id text not null,
  chapter integer not null,
  segment integer not null,
  night_number integer not null,
  title text not null check (char_length(title) between 1 and 160),
  opening_text text not null check (char_length(opening_text) between 1 and 2000),
  response_text text,
  status text not null default 'open' check (status in ('open','responded','closed')),
  created_at timestamptz not null default now(),
  responded_at timestamptz,
  foreign key (game_id, from_character_id)
    references public.wod_player_characters(game_id, character_id)
    on delete cascade,
  foreign key (game_id, to_character_id)
    references public.wod_player_characters(game_id, character_id)
    on delete cascade,
  check (from_character_id <> to_character_id)
);

create index if not exists wod_character_scenes_incoming_idx
  on public.wod_character_scenes(game_id, to_character_id, status, created_at desc);
create index if not exists wod_character_scenes_outgoing_idx
  on public.wod_character_scenes(game_id, from_character_id, created_at desc);

create table if not exists public.wod_chronicle_world_events (
  id text primary key,
  game_id text not null references public.wod_games(id) on delete cascade,
  year integer not null,
  chapter integer not null,
  segment integer not null,
  actor_id text not null,
  actor_name text not null,
  category text not null,
  public_text text not null,
  hidden_intent text not null,
  created_at timestamptz not null default now()
);

create index if not exists wod_chronicle_world_events_game_idx
  on public.wod_chronicle_world_events(game_id, created_at desc);

create table if not exists public.wod_character_profiles (
  game_id text not null,
  character_id text not null,
  profile_json jsonb not null,
  updated_at timestamptz not null default now(),
  primary key (game_id, character_id),
  foreign key (game_id, character_id)
    references public.wod_player_characters(game_id, character_id)
    on delete cascade
);

create table if not exists public.wod_chronicle_simulations (
  game_id text primary key references public.wod_games(id) on delete cascade,
  state_json jsonb not null,
  updated_at timestamptz not null default now()
);

alter table public.wod_chronicle_progress enable row level security;
alter table public.wod_player_characters enable row level security;
alter table public.wod_character_night_history enable row level security;
alter table public.wod_character_scenes enable row level security;
alter table public.wod_chronicle_world_events enable row level security;
alter table public.wod_character_profiles enable row level security;
alter table public.wod_chronicle_simulations enable row level security;

revoke all on table public.wod_chronicle_progress from public, anon, authenticated;
revoke all on table public.wod_player_characters from public, anon, authenticated;
revoke all on table public.wod_character_night_history from public, anon, authenticated;
revoke all on table public.wod_character_scenes from public, anon, authenticated;
revoke all on table public.wod_chronicle_world_events from public, anon, authenticated;
revoke all on table public.wod_character_profiles from public, anon, authenticated;
revoke all on table public.wod_chronicle_simulations from public, anon, authenticated;

grant select, insert, update, delete on table public.wod_chronicle_progress to service_role;
grant select, insert, update, delete on table public.wod_player_characters to service_role;
grant select, insert, update, delete on table public.wod_character_night_history to service_role;
grant select, insert, update, delete on table public.wod_character_scenes to service_role;
grant select, insert, update, delete on table public.wod_chronicle_world_events to service_role;
grant select, insert, update, delete on table public.wod_character_profiles to service_role;
grant select, insert, update, delete on table public.wod_chronicle_simulations to service_role;

create or replace function public.wod_advance_personal_night(
  p_game_id text,
  p_player_id text,
  p_expected_chapter integer,
  p_expected_segment integer,
  p_expected_night integer,
  p_action text,
  p_outcome jsonb,
  p_hunger integer,
  p_reputation integer,
  p_personal_influence double precision,
  p_sire_relation integer,
  p_goal_progress integer,
  p_ready boolean,
  p_next_night integer
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_character public.wod_player_characters%rowtype;
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
    raise exception 'character night changed before submission';
  end if;

  insert into public.wod_character_night_history(
    game_id, character_id, chapter, segment, night_number, action, outcome_json
  ) values (
    p_game_id, v_character.character_id, p_expected_chapter, p_expected_segment,
    p_expected_night, p_action, p_outcome
  );

  update public.wod_player_characters
  set local_night = p_next_night,
      hunger = p_hunger,
      reputation = p_reputation,
      personal_influence = p_personal_influence,
      sire_relation = p_sire_relation,
      goal_progress = p_goal_progress,
      ready_for_convergence = p_ready,
      updated_at = now()
  where game_id = p_game_id and player_id = p_player_id
  returning * into v_character;

  return to_jsonb(v_character);
end;
$$;

create or replace function public.wod_resolve_convergence(p_game_id text)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_progress public.wod_chronicle_progress%rowtype;
  v_total integer;
  v_not_ready integer;
  v_next_year integer;
  v_next_chapter integer;
  v_next_segment integer;
  v_reset_goal boolean := false;
begin
  select * into v_progress
  from public.wod_chronicle_progress
  where game_id = p_game_id
  for update;

  if not found then
    raise exception 'chronicle progress missing';
  end if;

  select count(*), count(*) filter (where not ready_for_convergence)
  into v_total, v_not_ready
  from public.wod_player_characters
  where game_id = p_game_id
    and is_active
    and chapter = v_progress.chapter
    and segment = v_progress.segment;

  if v_total = 0 or v_not_ready > 0 then
    raise exception 'all active characters must be ready for convergence';
  end if;

  if v_progress.segment >= v_progress.segments_per_chapter then
    v_next_year := v_progress.year + v_progress.ellipse_years;
    v_next_chapter := v_progress.chapter + 1;
    v_next_segment := 1;
    v_reset_goal := true;
  else
    v_next_year := v_progress.year;
    v_next_chapter := v_progress.chapter;
    v_next_segment := v_progress.segment + 1;
  end if;

  update public.wod_chronicle_progress
  set year = v_next_year,
      chapter = v_next_chapter,
      segment = v_next_segment,
      updated_at = now()
  where game_id = p_game_id
  returning * into v_progress;

  update public.wod_player_characters
  set chronicle_year = v_next_year,
      chapter = v_next_chapter,
      segment = v_next_segment,
      local_night = 1,
      ready_for_convergence = false,
      experience = experience + case
        when v_reset_goal and goal_progress >= 5 then 2
        when v_reset_goal and goal_progress >= 2 then 1
        else 0 end,
      personal_influence = personal_influence + case
        when v_reset_goal and goal_progress >= 5 then 1.0
        when v_reset_goal and goal_progress >= 2 then 0.5
        else 0 end,
      reputation = least(3, reputation + case
        when v_reset_goal and goal_progress >= 5 then 1
        else 0 end),
      status = least(5, status + case
        when v_reset_goal and goal_progress >= 7 and status = 0 then 1
        else 0 end),
      goal_progress = case when v_reset_goal then 0 else goal_progress end,
      updated_at = now()
  where game_id = p_game_id and is_active;

  return to_jsonb(v_progress);
end;
$$;

create or replace function public.wod_respond_character_scene(
  p_game_id text,
  p_scene_id text,
  p_character_id text,
  p_response text
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_scene public.wod_character_scenes%rowtype;
begin
  select * into v_scene
  from public.wod_character_scenes
  where id = p_scene_id and game_id = p_game_id
  for update;

  if not found then
    raise exception 'unknown scene';
  end if;
  if v_scene.to_character_id <> p_character_id then
    raise exception 'only the targeted character may respond';
  end if;
  if v_scene.status <> 'open' then
    raise exception 'scene is no longer open';
  end if;
  if char_length(trim(p_response)) < 1 or char_length(p_response) > 2000 then
    raise exception 'response length invalid';
  end if;

  update public.wod_character_scenes
  set response_text = trim(p_response),
      status = 'responded',
      responded_at = now()
  where id = p_scene_id and game_id = p_game_id
  returning * into v_scene;

  return to_jsonb(v_scene);
end;
$$;

create or replace function public.wod_upsert_character_profile(
  p_game_id text,
  p_character_id text,
  p_profile jsonb
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_profile jsonb;
begin
  if p_profile is null or jsonb_typeof(p_profile) <> 'object' then
    raise exception 'Character profile must be a JSON object';
  end if;

  insert into public.wod_character_profiles(game_id, character_id, profile_json, updated_at)
  values(p_game_id, p_character_id, p_profile, now())
  on conflict(game_id, character_id)
  do update set profile_json = excluded.profile_json, updated_at = excluded.updated_at
  returning profile_json into v_profile;

  return v_profile;
end;
$$;

create or replace function public.wod_upsert_chronicle_simulation(
  p_game_id text,
  p_state jsonb
)
returns jsonb
language plpgsql
security invoker
set search_path = ''
as $$
declare
  v_state jsonb;
begin
  if p_state is null or jsonb_typeof(p_state) <> 'object' then
    raise exception 'Chronicle simulation must be a JSON object';
  end if;

  insert into public.wod_chronicle_simulations(game_id, state_json, updated_at)
  values(p_game_id, p_state, now())
  on conflict(game_id)
  do update set state_json = excluded.state_json, updated_at = excluded.updated_at
  returning state_json into v_state;

  return v_state;
end;
$$;

revoke all on function public.wod_advance_personal_night(text,text,integer,integer,integer,text,jsonb,integer,integer,double precision,integer,integer,boolean,integer) from public, anon, authenticated;
revoke all on function public.wod_resolve_convergence(text) from public, anon, authenticated;
revoke all on function public.wod_respond_character_scene(text,text,text,text) from public, anon, authenticated;
revoke all on function public.wod_upsert_character_profile(text,text,jsonb) from public, anon, authenticated;
revoke all on function public.wod_upsert_chronicle_simulation(text,jsonb) from public, anon, authenticated;

grant execute on function public.wod_advance_personal_night(text,text,integer,integer,integer,text,jsonb,integer,integer,double precision,integer,integer,boolean,integer) to service_role;
grant execute on function public.wod_resolve_convergence(text) to service_role;
grant execute on function public.wod_respond_character_scene(text,text,text,text) to service_role;
grant execute on function public.wod_upsert_character_profile(text,text,jsonb) to service_role;
grant execute on function public.wod_upsert_chronicle_simulation(text,jsonb) to service_role;
