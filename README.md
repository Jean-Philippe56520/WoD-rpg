# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## Périmètre du MVP

Le MVP reste limité à **Brujah, Toreador et Ventrue**. Chaque joueur contrôle un clan mais incarne directement son **Primogène**. Les autres vampires du clan sont des acteurs politiques distincts avec leurs propres ambitions, relations, Humanité, Statut, réputation, faveurs, griefs et intérêts territoriaux.

Le cœur du jeu reste : **pouvoir, influence, information, relations, Prestation et conséquences persistantes**. Les Domaines ne transforment pas le jeu en jeu de conquête.

## Modèle politique

Chaque vampire possède notamment :

- un rapport aux mortels : **Humaniste / Prédateur** ;
- un rapport à l'ordre : **Orthodoxe / Réformateur** ;
- une Humanité réelle de 0 à 10 ;
- Physique, Social et Mental de 0 à 2 ;
- Expertises, Disciplines et Historiques ;
- un Rang de Sang ;
- une influence personnelle ;
- un Statut de 0 à 5 ;
- une réputation de -3 à +3 ;
- une ambition politique active ;
- des relations personnelles.

La résolution de base reste compacte :

```text
Caractéristique + Expertise éventuelle (+1) + meilleure Discipline OU meilleur Historique pertinent
```

## Factions internes

Le terme **coterie** est réservé aux futures vraies coteries vampiriques, potentiellement transclaniques. Chaque clan possède actuellement :

1. la **Faction du Primogène** ;
2. la **Faction d'opposition**.

Le Primogène représente officiellement le clan mais ne commande pas automatiquement tous ses membres. L'opposition possède son propre chef et ses propres intérêts.

La relation effective au Primogène combine la relation personnelle 0–2 et l'affinité politique :

- deux positions identiques : +1 ;
- une position identique : 0 ;
- deux positions opposées : -1.

## Prestation, griefs et promesses

Les faveurs sont des obligations persistantes : mineure, majeure ou dette de vie. Elles possèdent un créancier, un débiteur, une origine et un statut. Honorer une faveur améliore la réputation ; la refuser peut créer un grief et dégrader fortement la crédibilité du débiteur.

Les tensions politiques ne reposent pas sur une jauge opaque. Elles sont enregistrées comme **griefs explicites** avec auteur, cible, cause et gravité.

Les PNJ peuvent adresser des requêtes au Primogène. Celui-ci peut accepter, refuser, négocier ou promettre. Les promesses ont une échéance et peuvent désormais être **honorées explicitement avant les missions de nuit**.

## Domaines — V0.10

Un Domaine est une ressource politique personnelle, pas une case appartenant automatiquement au clan ou au Primogène.

Chaque Domaine possède trois caractéristiques de 0 à 3 :

- **Viandis** : richesse et capacité nourricière du Domaine ;
- **Servage** : implantation et emprise sur les mortels et réseaux locaux ;
- **Rempart** : contrôle, sécurité et capacité à détecter les intrusions.

Il possède également une pression territoriale et un risque de Mascarade.

### Six Domaines initiaux

La ville commence volontairement avec six Domaines asymétriques :

- Quartier des Affaires — Adrien de Keravel ;
- Vieux-Centre — Claire Beaumont ;
- Quartier des Arts — Elise Valmont ;
- Campus et Hôpital — Camille Vernier ;
- Les Docks — Marcus Le Guen ;
- Les Faubourgs — Sarah Morel.

Des membres de l'opposition détiennent donc déjà des Domaines. La Primogéniture et la propriété territoriale sont volontairement séparées.

## Droits de chasse

Détenir un Domaine et disposer du droit d'y chasser sont deux choses différentes.

Un droit de chasse possède :

- un Domaine ;
- un bénéficiaire ;
- un accordeur ;
- une durée précise en nuits ;
- des conditions ;
- éventuellement une faveur de Prestation associée ;
- un statut actif, révoqué, expiré ou contesté.

Le détenteur peut accorder ou retirer des droits sur son Domaine. Le **Prince reconnu** peut également arbitrer les droits et dispose côté moteur de la prérogative de réattribuer ou retirer un Domaine personnel. Une réattribution contestée peut devenir un litige public.

Une succession de Primogène ne transfère jamais automatiquement les Domaines personnels du titulaire sortant.

## Pression territoriale

Le Viandis n'est pas une production abstraite de points. Il limite politiquement la quantité d'exploitation supportable.

- trop de droits de chasse actifs par rapport au Viandis augmentent la pression ;
- le braconnage augmente également la pression ;
- le détenteur peut utiliser l'action **Administrer son Domaine** et son Servage pour réduire cette pression ;
- une pression excessive peut provoquer un incident local et endommager la Mascarade.

## Intrusion, Rempart et braconnage

Actions territoriales V0.10 :

- **Administrer son Domaine** ;
- **Infiltrer un Domaine** ;
- **Braconner sur un Domaine**.

Le Rempart s'oppose aux intrusions. Une infiltration réussie peut améliorer le renseignement territorial. Une intrusion ou un braconnage détecté peut produire :

- grief personnel ;
- litige territorial ;
- information dans les rapports concernés ;
- pression supplémentaire ;
- conséquences ultérieures sur la Mascarade.

Un membre de l'opposition conserve son autonomie : une action territoriale ordonnée par le joueur peut encore être refusée si elle ne sert pas suffisamment ses intérêts.

## Politique territoriale et requêtes

L'ambition **Obtenir un Domaine** produit désormais une demande concrète de droit de chasse lorsqu'un Domaine du Primogène est disponible.

Le Primogène peut :

- accepter et concéder l'accès ;
- négocier l'accès contre une faveur ;
- refuser et créer potentiellement un grief ;
- promettre l'accès pour une nuit ultérieure.

Une promesse territoriale honorée crée effectivement le droit de chasse avant les missions de la nuit.

## Brouillard de guerre territorial

Le nom d'un Domaine et son détenteur officiel sont publics.

Restent privés ou soumis au renseignement :

- Viandis, Servage et Rempart des Domaines étrangers ;
- pression réelle ;
- droits privés ;
- certains litiges ;
- intrusions non détectées.

Le renseignement territorial possède deux niveaux et est séparé du renseignement sur les personnages.

## Praxis

Le vote des Primogènes reste un **mécanisme local de reconnaissance de la Praxis**, pas une procédure universelle de la Camarilla.

Si l'opposition refuse de suivre son Primogène, son influence est divisée selon `opposition_transfer_ratio`, configurable et fixé à 50 % par défaut.

## Cycle d'une nuit V0.10

```text
Requêtes / promesses / Prestation
        |
Décisions du Primogène
        |
Promesses honorées
        |
Concessions ou révocations territoriales
        |
Une mission par vampire
        |
Validation des trois clans
        |
Résolution simultanée
        |
Praxis / Étreintes
        |
Réactions autonomes
        |
Pression territoriale / Mascarade
        |
Rapports privés
        |
Nuit suivante
```

## Compatibilité et persistance

Aucune migration SQL Supabase n'est requise pour V0.10. Les Domaines, droits, litiges et renseignements territoriaux sont intégrés au `state_json` existant.

La lecture reste rétrocompatible :

- sauvegardes V0.6/V0.7/V0.8/V0.9 migrées à la lecture ;
- anciennes `coterie_memberships` converties en `faction_memberships` ;
- sauvegardes V0.9 sans Domaines enrichies automatiquement avec les six Domaines initiaux ;
- ordres V0.7, V0.8 et V0.9 toujours lisibles et résolubles ;
- ordres V0.10 utilisent `version = 4` ;
- la nuit de production déjà soumise au format legacy reste explicitement couverte par les tests.

GitHub contient le code et les contenus statiques, jamais les sauvegardes vivantes.

## Architecture

- `game/models.py` : modèles de domaine ;
- `game/factions.py` : politique interne ;
- `game/social_politics.py` : Prestation, griefs, promesses et requêtes ;
- `game/domains.py` : Domaines, droits de chasse, Viandis, Servage, Rempart, pression et litiges ;
- `game/actions.py` : actions individuelles ;
- `game/autonomy.py` : réactions autonomes déterministes ;
- `game/politics.py` : reconnaissance de Praxis ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : Étreintes ;
- `game/resolution.py` : pipeline global d'une nuit ;
- `game/serialization.py` : sérialisation et migrations rétrocompatibles ;
- `game/multiplayer.py` : orchestration asynchrone ;
- `game/persistence.py`, `game/supabase_repository.py` : persistance ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatisés et smoke test Streamlit.

## Tests

```bash
pytest -q
```

## Suite cible

1. vraies coteries transclaniques ;
2. Prince comme acteur politique autonome ;
3. résolution et arbitrage avancés des litiges territoriaux ;
4. rumeurs, secrets et information imparfaite ;
5. Étreintes davantage reliées à la Prestation et aux Domaines ;
6. institutions, stabilité, Mascarade et factions PNJ.
