# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.9

Le MVP reste limité à **Brujah, Toreador et Ventrue**. Chaque joueur contrôle un clan mais incarne directement son **Primogène** ; les autres vampires restent des acteurs politiques distincts avec leurs propres intérêts.

### Fiche de vampire

Chaque personnage possède désormais des dimensions séparées :

- un **rapport aux mortels** : Humaniste ou Prédateur ;
- un **rapport à l'ordre** : Orthodoxe ou Réformateur ;
- une **Humanité réelle** de 0 à 10, distincte de l'idéologie politique ;
- Physique, Social et Mental de 0 à 2 ;
- des Expertises, Disciplines et Historiques ;
- un Rang de Sang ;
- une influence personnelle ;
- un **Statut** de 0 à 5 ;
- une **réputation** de -3 à +3 ;
- une ambition politique active ;
- des relations personnelles.

La résolution de base reste compacte :

```text
Caractéristique + Expertise éventuelle (+1) + meilleure Discipline OU meilleur Historique pertinent
```

Le Rang de Sang n'est pas un bonus universel.

## Factions internes du clan

Le terme **coterie** n'est plus utilisé pour les deux camps politiques internes. Une coterie, dans Vampire, reste un groupe de vampires potentiellement transclanique. Chaque clan possède donc actuellement :

1. la **faction du Primogène** ;
2. la **faction d'opposition**.

Le Primogène appartient obligatoirement à sa faction. L'opposition possède un chef distinct dont la combinaison politique ne peut pas être exactement identique à celle du Primogène.

L'influence d'une faction est la somme de l'influence personnelle de ses membres.

### Relation au Primogène

Chaque membre possède une relation personnelle au Primogène de **0 à 2**. Le moteur ajoute ensuite l'affinité politique :

| Compatibilité | Modificateur |
| --- | ---: |
| deux positions identiques | +1 |
| une position identique | 0 |
| deux positions opposées | -1 |

```text
Relation effective = relation personnelle + affinité politique
```

Le résultat peut aller de **-1 à 3**. Une faction n'est pas déduite automatiquement de cette valeur : un opposant peut respecter le Primogène et un loyaliste peut devenir politiquement fragile.

## Prestation

La V0.9 introduit une économie explicite de **faveurs** entre vampires.

Une faveur possède :

- un créancier ;
- un débiteur ;
- un niveau : mineure, majeure ou dette de vie ;
- une origine ;
- un statut : due, réclamée, honorée ou refusée ;
- un caractère public ou privé.

Honorer une faveur améliore la réputation. Refuser une faveur dégrade la réputation du débiteur et crée un grief politique proportionnel à la gravité de la dette.

Un vampire disposant d'une faveur due peut utiliser l'action **Réclamer une faveur**.

## Griefs, promesses et requêtes

La V0.9 ne repose pas sur une jauge opaque de « mécontentement ». Les tensions sont mémorisées sous forme de **griefs explicites** : auteur, cible, raison, gravité et nuit de création.

Chaque nuit, le moteur peut générer au plus une requête politique par clan à partir des ambitions et tensions existantes. Le Primogène peut :

- **accepter** ;
- **refuser** ;
- **négocier** ;
- **promettre**.

Accepter peut améliorer la relation et produire une contrepartie de Prestation. Refuser peut dégrader la relation et créer un grief. Négocier crée généralement une dette. Promettre crée une obligation persistante avec échéance ; une promesse non tenue crée un grief sérieux et abîme la réputation du Primogène.

## Autonomie politique des PNJ

Les réactions autonomes sont **déterministes et explicables**. Un membre ne change pas de faction au hasard.

Une défection vers l'opposition nécessite actuellement plusieurs conditions :

- relation effective très faible ;
- grief sérieux envers le Primogène ;
- opportunité politique ;
- compatibilité suffisante avec le chef d'opposition.

Le chef d'opposition peut également renforcer ses réseaux lorsque son ambition et le contexte politique le justifient.

Les actions autonomes sont résolues après les actions principales de la nuit et apparaissent dans les rapports lorsqu'elles sont connaissables par le clan.

## Une action par vampire et par nuit

Une soumission moderne contient **exactement une action pour chaque vampire actif du clan**. Un même vampire ne peut pas agir deux fois.

Actions disponibles :

- Développer son influence ;
- Diplomatie ;
- Consolider une relation ;
- Recruter dans sa faction ;
- Fragiliser un membre ;
- Débaucher vers l'opposition ;
- Enquêter ;
- Réclamer une faveur.

Un membre d'opposition peut refuser une mission lorsque sa relation avec le Primogène est trop faible. Une mission diplomatique compatible avec ses convictions peut au contraire être mieux acceptée et mieux exécutée.

## Brouillard de guerre

Les Primogènes étrangers sont publics. Les autres membres, leurs factions, relations, griefs, ambitions et ordres restent cachés tant qu'ils ne sont pas découverts.

L'action **Enquêter** produit progressivement du renseignement :

- niveau 1 : identité d'un membre étranger ;
- niveau 2 : faction, relation effective et influence connues.

## Praxis

Le vote des Primogènes est traité comme un **mécanisme local de reconnaissance de la Praxis**, pas comme une procédure universelle de la Camarilla.

- si l'opposition soutient son Primogène, 100 % de l'influence du clan suit son vote ;
- si elle refuse, l'influence d'opposition est divisée selon `opposition_transfer_ratio` ;
- par défaut, 50 % reste au Primogène et 50 % renforce le Primogène allié de l'opposition.

La règle reste configurable et testée.

## Cycle d'une nuit V0.9

```text
Requêtes internes / faveurs / promesses
        |
Décisions du Primogène
        |
Attribution des missions
        |
Validation des trois clans
        |
Résolution des actions
        |
Praxis / Étreintes si nécessaire
        |
Réactions autonomes motivées
        |
Conséquences : relations, griefs, réputation, factions
        |
Rapports privés
        |
Nuit suivante + nouvelles requêtes
```

## Compatibilité et persistance

Aucune migration SQL Supabase n'est nécessaire pour V0.9 : les nouveaux objets politiques sont intégrés au `state_json` existant.

La lecture est rétrocompatible :

- les sauvegardes V0.6/V0.7/V0.8 sont migrées à la lecture ;
- `Humanité +/-` devient le rapport aux mortels ;
- `Traditions +/-` devient le rapport à l'ordre ;
- les anciennes `coterie_memberships` deviennent `faction_memberships` ;
- la véritable Humanité, le Statut, la réputation et l'ambition active sont enrichis depuis la fiche canonique lorsqu'ils manquent ;
- les ordres V0.7 sans acteur restent résolubles ;
- les ordres V0.8 restent résolubles ;
- les nouveaux ordres V0.9 utilisent `version = 3` et incluent les décisions sur les requêtes internes.

Les données vivantes de la chronique ne sont jamais réinitialisées.

## Architecture

- `game/models.py` : modèles de domaine ;
- `game/character_rules.py` : résolution compacte des capacités ;
- `game/ideology.py` : compatibilité des anciens axes et affinités ;
- `game/factions.py` : factions internes, chef d'opposition, relation effective et influence ;
- `game/coteries.py` : couche de compatibilité V0.8 uniquement ;
- `game/social_politics.py` : Prestation, griefs, promesses et requêtes ;
- `game/autonomy.py` : réactions autonomes déterministes ;
- `game/politics.py` : reconnaissance de Praxis et transfert d'influence ;
- `game/actions.py` : actions individuelles ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : demandes d'Étreinte ;
- `game/resolution.py` : pipeline global d'une nuit ;
- `game/serialization.py` : sérialisation et migrations rétrocompatibles ;
- `game/multiplayer.py` : orchestration joueur/clan/nuit ;
- `game/persistence.py`, `game/supabase_repository.py` : persistance ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatisés et smoke test Streamlit.

## Tests

```bash
pytest -q
```

## Suite cible

1. vraies coteries transclaniques ;
2. domaines et droits de chasse comme sources de pouvoir politique ;
3. demandes d'Étreinte davantage reliées à la Prestation ;
4. rumeurs, secrets et information imparfaite ;
5. Prince comme acteur autonome ;
6. Mascarade, stabilité, institutions et factions PNJ.
