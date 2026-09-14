-- WoD-rpg V0.5 - schema preparatoire PostgreSQL/Supabase.
-- A appliquer uniquement sur un projet Supabase dedie a WoD-rpg.

create table if not exists public.wod_games (
    id text primary key,
    name text not null,
    current_night integer not null,
    state_json jsonb not null,
    required_clans_json jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.wod_game_players (
    game_id text not null references public.wod_games(id) on delete cascade,
    player_id text not null,
    player_name text not null,
    clan_id text not null,
    claimed_at timestamptz not null default now(),
    primary key (game_id, player_id),
    unique (game_id, clan_id)
);

create table if not exists public.wod_nights (
    game_id text not null references public.wod_games(id) on delete cascade,
    night_number integer not null,
    status text not null check (status in ('open','ready','resolving','resolved')),
    state_before_json jsonb not null,
    state_after_json jsonb,
    created_at timestamptz not null default now(),
    resolved_at timestamptz,
    primary key (game_id, night_number)
);

create table if not exists public.wod_night_submissions (
    game_id text not null,
    night_number integer not null,
    clan_id text not null,
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
    clan_id text not null,
    report_json jsonb not null,
    primary key (game_id, night_number, clan_id),
    foreign key (game_id, night_number)
        references public.wod_nights(game_id, night_number) on delete cascade
);

create table if not exists public.wod_elysium_messages (
    id bigint generated always as identity primary key,
    game_id text not null references public.wod_games(id) on delete cascade,
    player_id text not null,
    clan_id text not null,
    body text not null check (char_length(body) between 1 and 2000),
    created_at timestamptz not null default now()
);

alter table public.wod_games enable row level security;
alter table public.wod_game_players enable row level security;
alter table public.wod_nights enable row level security;
alter table public.wod_night_submissions enable row level security;
alter table public.wod_night_reports enable row level security;
alter table public.wod_elysium_messages enable row level security;

revoke all on table public.wod_games from anon, authenticated;
revoke all on table public.wod_game_players from anon, authenticated;
revoke all on table public.wod_nights from anon, authenticated;
revoke all on table public.wod_night_submissions from anon, authenticated;
revoke all on table public.wod_night_reports from anon, authenticated;
revoke all on table public.wod_elysium_messages from anon, authenticated;
