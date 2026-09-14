# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.6

Le MVP reste limité à **Brujah, Toreador et Ventrue**.

### Identité et lobby

- l'application utilise **Supabase Auth** avec email + mot de passe ;
- l'identité persistante d'un joueur est l'UUID de son compte Supabase Auth ;
- l'identifiant joueur n'est plus transmis dans l'URL ;
- un compte ne peut contrôler qu'un seul clan dans la chronique ;
- un clan ne peut être contrôlé que par un seul compte ;
- après reconnexion avec le même compte, le joueur retrouve automatiquement son clan ;
- le lobby n'affiche que les clans disponibles/occupés et le nom public de leur contrôleur.

### Partie multijoueur asynchrone

- un joueur contrôle un seul clan et incarne son **Primogène actuel** ;
- sa session expose son clan en détail, plus les informations publiques de la ville ;
- les membres, courants, loyautés et ordres internes des autres clans restent privés ;
- chaque joueur prépare puis valide ses ordres de nuit ;
- les ordres validés sont persistés dans Supabase et restent consultables par leur auteur ;
- tant que la nuit est encore `OPEN`, un joueur peut **annuler sa validation** et reprendre ses ordres ;
- dès que les trois clans ont validé, la nuit passe par `READY -> RESOLVING -> RESOLVED` et ne peut plus être modifiée ;
- la résolution globale est unique et atomique ;
- chaque clan reçoit son propre rapport selon les informations qu'il peut connaître ;
- l'Elysium reste accessible pendant l'attente ;
- une demande d'Étreinte est portée officiellement par le Primogène au nom d'un membre précis du clan.

Le moteur conserve Praxis, incompatibilité Prince/Primogène, successions, axes Humanisme/Tradition, quatre courants idéologiques possibles, dissidence 50/50 courant par courant, affinité idéologique et capital politique du Prince.

## Persistance et sécurité

`game/persistence.py` définit le contrat `GameRepository` et conserve SQLite pour le développement local et les tests.

`game/supabase_repository.py` fournit la persistance distante PostgreSQL/Supabase. `game/editable_repository.py` ajoute la consultation et la reprise des ordres de nuit sans mélanger cette logique avec le moteur politique. Le schéma reproductible se trouve dans `supabase/schema.sql`.

Le projet Supabase dédié est `WoD-rpg` (`eu-west-3`). En production, Streamlit utilise Supabase comme source persistante de la chronique. Les tables de jeu ne sont jamais utilisées directement par le navigateur : `anon` et `authenticated` n'ont aucun accès direct à l'état complet, aux ordres ou aux rapports. Les transitions critiques de nuit sont effectuées côté serveur et atomiquement dans PostgreSQL.

Supabase Auth sert uniquement à établir l'identité réelle du joueur. Le serveur Streamlit valide la session auprès de Supabase Auth avant d'utiliser l'UUID du compte comme `player_id`.

Secrets Streamlit nécessaires :

```toml
SUPABASE_URL = "https://kxsutwksruraladbatti.supabase.co"
SUPABASE_SECRET_KEY = "<secret serveur Supabase>"
```

La clé publique Auth peut également être fournie explicitement :

```toml
SUPABASE_PUBLISHABLE_KEY = "<clé sb_publishable_...>"
```

`SUPABASE_SECRET_KEY` est strictement serveur et ne doit **jamais** être commité, envoyé au navigateur ou partagé. GitHub contient le code, la configuration reproductible et les contenus statiques, jamais les sauvegardes vivantes d'une chronique.

## Architecture

- `game/models.py` : modèles de domaine ;
- `game/ideology.py` : axes et courants dynamiques ;
- `game/politics.py` : dissidences et vote de Praxis ;
- `game/actions.py` : actions politiques ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : demandes d'Étreinte ;
- `game/resolution.py` : résolution globale d'une nuit ;
- `game/serialization.py` : sérialisation JSON stable ;
- `game/auth.py` : authentification Supabase et validation des sessions joueur ;
- `game/persistence.py` : contrat de stockage + SQLite local ;
- `game/supabase_repository.py` : stockage distant Supabase via Data API ;
- `game/editable_repository.py` : extension des dépôts pour consultation/retrait d'ordres ;
- `game/repository_factory.py` : sélection du backend de persistance ;
- `game/multiplayer.py` : orchestration joueur/clan/nuit ;
- `supabase/schema.sql` : schéma PostgreSQL et fonctions atomiques ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatisés.

## Cycle d'une nuit

```text
Nuit N ouverte
   |
   +-- Ventrue prépare / valide
   +-- Toreador prépare / valide
   +-- Brujah prépare / valide
   |
   |  tant que la nuit est OPEN : validation annulable
   |
   +-- trois validations
          |
          v
        READY
          |
          v
      RESOLVING
          |
          v
       RESOLVED
          |
          +-- rapports privés par clan
          +-- état persistant mis à jour
          +-- Nuit N+1 ouverte
```

## Tests

```bash
pytest -q
```

## Suite cible

1. approfondir la **politique interne autonome** : demandes, ambitions, pressions et réactions des membres et courants ;
2. enrichir les rapports de nuit et le **brouillard de guerre** : informations partielles, découvertes et attribution incertaine ;
3. développer le **Prince comme acteur politique autonome** et approfondir les contestations de Praxis ;
4. ajouter relations personnelles, faveurs et dettes ;
5. développer territoires, institutions, stabilité et Mascarade ;
6. enrichir ensuite Elysium, diplomatie et factions PNJ.
