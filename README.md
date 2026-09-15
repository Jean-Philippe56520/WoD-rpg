# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.8

Le MVP reste limité à **Brujah, Toreador et Ventrue**. Chaque joueur contrôle un clan mais incarne directement son **Primogène** ; les autres vampires du clan restent des acteurs politiques distincts.

### Fiche de vampire

Chaque personnage possède :

- **Humanité +/-** et **Traditions +/-** comme convictions idéologiques ;
- Physique, Social et Mental de **0 à 2** ;
- des **Expertises** donnant +1 lorsqu'elles sont pertinentes ;
- des **Disciplines** nommées de 0 à 2 ;
- un **Rang de Sang** : Nouveau-né, Ancilla ou Ancien ;
- des **Historiques** nommés de 0 à 2 ;
- une influence personnelle, une ambition et des relations politiques.

La base de résolution reste compacte :

```text
Caractéristique + Expertise éventuelle (+1) + meilleure Discipline OU meilleur Historique pertinent
```

Le Rang de Sang n'est pas un bonus universel.

## Deux coteries politiques par clan

Les quatre combinaisons idéologiques existent toujours, mais **ne sont plus quatre factions politiques**. Chaque clan possède seulement :

1. la **coterie du Primogène** ;
2. la **coterie d'opposition**.

Le Primogène dirige obligatoirement sa coterie. L'opposition possède un chef distinct dont la combinaison Humanité/Traditions ne peut pas être exactement identique à celle du Primogène. Un membre peut donc être idéologiquement proche du Primogène tout en appartenant politiquement à l'opposition.

L'influence d'une coterie est la somme de l'influence personnelle de ses membres.

### Relation au Primogène

Chaque membre possède une relation personnelle au Primogène de **0 à 2**. Le moteur calcule ensuite une relation effective :

| Compatibilité idéologique | Modificateur |
| --- | ---: |
| deux axes identiques | +1 |
| un axe identique | 0 |
| deux axes opposés | -1 |

```text
Relation effective = relation personnelle + modificateur idéologique
```

Le résultat peut donc aller de **-1 à 3**. La coterie n'est pas automatiquement déduite de cette relation : un opposant peut respecter le Primogène et un membre de sa coterie peut devenir politiquement fragile.

## Une action par vampire et par nuit

Une soumission V0.8 doit contenir **exactement une action pour chaque vampire actif du clan**. Un même vampire ne peut pas agir deux fois.

Le joueur choisit les missions, mais un membre de l'opposition n'est pas un pion : selon sa relation effective et la nature de la mission, il peut coopérer ou refuser. Un opposant qui refuse consacre actuellement sa nuit à renforcer ses propres réseaux.

Actions V0.8 :

- **Développer son influence** ;
- **Diplomatie** ;
- **Consolider une relation** avec un membre du clan ;
- **Recruter** un membre de l'autre coterie ;
- **Fragiliser** la relation d'un vampire étranger avec son Primogène ;
- **Débaucher** une cible politiquement fragile vers l'opposition de son propre clan ;
- **Enquêter** sur un autre clan.

### Opposition utile

L'idéologie de l'acteur compte dans les interactions politiques. Un membre de l'opposition peut être un meilleur diplomate que le Primogène face à un interlocuteur idéologiquement compatible. Le clan peut donc bénéficier de sa réussite tout en renforçant personnellement un rival intérieur.

La diplomatie peut créer des relations personnelles entre vampires en plus d'améliorer les rapports entre clans.

## Brouillard de guerre

Les Primogènes étrangers sont publics. Les autres membres, leurs coteries, leur relation réelle au Primogène et leur influence interne restent cachés tant qu'ils ne sont pas découverts.

L'action **Enquêter** produit progressivement du renseignement :

- niveau 1 : identité d'un membre étranger ;
- niveau 2 : coterie, relation effective et influence connues.

Cela permet ensuite de cibler les vampires vulnérables avec Fragiliser ou Débaucher.

## Praxis et opposition

Lors d'un vote de Praxis :

- si l'opposition soutient son Primogène, **100 % de l'influence du clan** suit son vote ;
- si elle refuse, la coterie du Primogène reste entièrement derrière lui ;
- l'influence de l'opposition est divisée selon `opposition_transfer_ratio` ;
- par défaut, **50 %** de l'influence d'opposition reste au Primogène et **50 %** renforce le Primogène allié choisi par l'opposition.

Cette règle reste configurable et testée.

## Identité et multijoueur asynchrone

- Supabase Auth fournit l'identité persistante du joueur ;
- un compte contrôle un seul clan dans la chronique ;
- un clan ne peut être occupé que par un seul compte ;
- les ordres sont persistés et peuvent être retirés tant que la nuit reste `OPEN` ;
- après validation des trois clans : `READY -> RESOLVING -> RESOLVED` ;
- la résolution globale reste unique et atomique ;
- chaque clan reçoit son propre rapport ;
- l'Elysium reste accessible pendant l'attente ;
- les demandes d'Étreinte restent portées par le Primogène au nom d'un membre précis du clan.

## Compatibilité des sauvegardes

Aucune migration SQL Supabase n'est nécessaire pour V0.8 : l'état politique et les ordres restent sérialisés dans les JSON existants.

La lecture est rétrocompatible :

- les sauvegardes V0.6/V0.7 sans coteries sont converties automatiquement ;
- la relation 0–2 est dérivée des anciennes données lorsqu'elle manque ;
- les anciennes soumissions V0.7 sans `actor_character_id` restent résolubles ;
- une même nuit peut donc contenir une soumission V0.7 déjà persistée et de nouvelles soumissions V0.8.

Les données vivantes de la chronique ne sont pas réinitialisées.

## Persistance et sécurité

`game/persistence.py` définit le contrat `GameRepository` et SQLite reste disponible pour le développement local et les tests. `game/supabase_repository.py` fournit la persistance distante PostgreSQL/Supabase.

En production, Streamlit utilise Supabase. Les transitions critiques de nuit sont effectuées côté serveur et atomiquement dans PostgreSQL. GitHub contient le code et les contenus statiques, jamais les sauvegardes vivantes.

Secrets Streamlit nécessaires :

```toml
SUPABASE_URL = "https://kxsutwksruraladbatti.supabase.co"
SUPABASE_SECRET_KEY = "<secret serveur Supabase>"
```

La clé publique Auth peut également être fournie :

```toml
SUPABASE_PUBLISHABLE_KEY = "<clé sb_publishable_...>"
```

`SUPABASE_SECRET_KEY` reste strictement serveur.

## Architecture

- `game/models.py` : modèles de domaine et fiche de personnage ;
- `game/character_rules.py` : résolution compacte des capacités ;
- `game/ideology.py` : convictions Humanité/Traditions et affinités ;
- `game/coteries.py` : deux coteries, chef d'opposition, relations effectives et influence ;
- `game/politics.py` : vote de Praxis et transfert d'influence d'opposition ;
- `game/actions.py` : actions individuelles ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : demandes d'Étreinte ;
- `game/resolution.py` : résolution globale d'une nuit ;
- `game/serialization.py` : sérialisation et migrations rétrocompatibles ;
- `game/multiplayer.py` : orchestration joueur/clan/nuit ;
- `game/persistence.py`, `game/supabase_repository.py` : persistance ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatisés, dont un smoke test Streamlit.

## Tests

```bash
pytest -q
```

## Suite cible

1. enrichir l'autonomie des membres : ambitions, demandes, refus contextualisés et initiatives propres ;
2. ajouter faveurs, dettes et contreparties aux missions ;
3. approfondir le brouillard de guerre et les informations partielles ;
4. développer le Prince comme acteur autonome et les contestations de Praxis ;
5. développer territoires, institutions, stabilité et Mascarade ;
6. enrichir Elysium, diplomatie et factions PNJ.
