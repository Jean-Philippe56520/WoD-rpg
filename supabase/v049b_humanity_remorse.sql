-- V0.49b - Humanité persistante à la clôture d'une Nuit significative.
-- La signature RPC reste inchangée : l'Humanité finale est transportée dans p_outcome
-- afin d'éviter de créer une surcharge PostgREST incompatible avec les anciens clients.

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
  v_humanity integer;
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

  v_humanity := coalesce((p_outcome ->> 'humanity')::integer, v_character.humanity);
  if v_humanity < 0 or v_humanity > 10 then
    raise exception 'humanity out of range';
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
      humanity = v_humanity,
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

revoke all on function public.wod_advance_personal_night(
  text,text,integer,integer,integer,text,jsonb,integer,integer,double precision,integer,integer,boolean,integer
) from public, anon, authenticated;

grant execute on function public.wod_advance_personal_night(
  text,text,integer,integer,integer,text,jsonb,integer,integer,double precision,integer,integer,boolean,integer
) to service_role;
