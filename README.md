# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.5

Le MVP reste limité à **Brujah, Toreador et Ventrue**.

### Partie multijoueur asynchrone

- un joueur contrôle un seul clan et incarne son Primogène ;
- chaque joueur prépare puis verrouille ses ordres de nuit ;
- les actions ne sont résolues qu'une fois les trois clans prêts ;
- le verrou `READY -> RESOLVING -> RESOLVED` empêche une double résolution ;
- chaque clan reçoit son propre rapport selon les informations qu'il peut connaître ;
- l'Elysium reste disponible pendant l'attente ;
- une demande d'Étreinte est portée par le Primogène au nom d'un membre précis du clan.

Le moteur conserve Praxis, Prince/Primogène incompatibles, successions, axes Humanisme/Tradition, quatre courants idéologiques possibles, dissidence 50/50 courant par courant, affinité idéologique et capital politique du Prince.

## Persistance

`game/persistence.py` définit le contrat `GameRepository` et conserve `SQLiteGameRepository` pour le développement local et les tests.

`game/supabase_repository.py` fournit la persistance distante PostgreSQL/Supabase. Le schéma reproductible se trouve dans `supabase/schema.sql`.

Le projet Supabase dédié est `WoD-rpg` (`eu-west-3`). Les tables de jeu sont accessibles uniquement au rôle serveur ; `anon` et `authenticated` n'ont aucun accès direct à l'état complet, aux ordres ou aux rapports. Les transitions critiques de nuit sont atomiques dans PostgreSQL.

Pour activer Supabase sur Streamlit Cloud, les secrets serveur doivent être configurés hors Git :

```toml
SUPABASE_URL = "https://kxsutwksruraladbatti.supabase.co"
SUPABASE_SECRET_KEY = "<secret serveur Supabase>"
```

Le secret serveur ne doit jamais être commité. Tant que ces secrets ne sont pas présents dans l'application Streamlit, le backend SQLite actuel reste utilisé.

## Architecture

- `game/models.py` : modèles de domaine ;
- `game/ideology.py` : axes et courants dynamiques ;
- `game/politics.py` : dissidences et vote de Praxis ;
- `game/actions.py` : actions politiques ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : demandes d'Étreinte ;
- `game/resolution.py` : résolution globale d'une nuit ;
- `game/serialization.py` : sérialisation JSON stable ;
- `game/persistence.py` : contrat de stockage + SQLite local ;
- `game/supabase_repository.py` : stockage distant Supabase ;
- `game/multiplayer.py` : orchestration joueur/clan/nuit ;
- `supabase/schema.sql` : schéma PostgreSQL et fonctions atomiques ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatisés.

## Tests

```bash
pytest -q
```

## Suite cible

1. ajouter le secret serveur dans Streamlit Cloud et valider une écriture réelle depuis l'application ;
2. ajouter une authentification réelle des joueurs ;
3. approfondir les mécaniques politiques internes : demandes autonomes des membres, candidatures, pressions et négociations ;
4. affiner le brouillard de guerre et les informations ;
5. relations, faveurs et dettes ;
6. territoires, institutions et Mascarade avancée.
