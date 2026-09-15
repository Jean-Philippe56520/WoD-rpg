# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## Périmètre du MVP

Le MVP reste limité à **Brujah, Toreador et Ventrue**. Chaque joueur contrôle un clan mais incarne directement son **Primogène**. Les autres vampires du clan sont des acteurs politiques distincts avec leurs propres ambitions, relations, Humanité, Statut, réputation, faveurs, griefs, coteries et intérêts territoriaux.

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

Une **faction** est un camp politique interne au clan. Chaque clan possède actuellement :

1. la **Faction du Primogène** ;
2. la **Faction d'opposition**.

Le Primogène représente officiellement le clan mais ne commande pas automatiquement tous ses membres. L'opposition possède son propre chef et ses propres intérêts.

La relation effective au Primogène combine la relation personnelle 0–2 et l'affinité politique :

- deux positions identiques : +1 ;
- une position identique : 0 ;
- deux positions opposées : -1.

## Coteries transclaniques — V0.11

Une **coterie** est désormais un véritable petit groupe de vampires et reste totalement distincte d'une faction interne. Elle peut unir des membres de plusieurs clans dont les intérêts institutionnels divergent.

Trois coteries structurent le MVP initial :

- **La Concorde des Trois** — Camille Vernier, Helene Beaumont, Ines Le Floch ;
- **Les Cendres Libres** — Claire Beaumont, Lucien Marceau, Sarah Morel ;
- **Le Pacte de Fer** — Victor de Keravel, Gabriel Sorel, Yann Kergoat.

Chaque coterie possède un chef, un objectif et une cohésion de base. La cohésion effective n'est pas une nouvelle jauge opaque : elle est calculée à partir des **relations personnelles** et des **griefs persistants** de ses membres.

Les coteries créent des loyautés croisées :

- un compagnon étranger est connu au niveau identité sans révéler sa faction interne ou ses griefs ;
- **Diplomatie** et **Enquête** bénéficient d'un accès supplémentaire entre compagnons ;
- **Fragiliser**, **Débaucher**, **Infiltrer** ou **Braconner** contre un compagnon crée un conflit de loyauté ;
- un PNJ peu lié à son Primogène peut refuser une mission hostile envers un compagnon d'une coterie soudée ;
- un membre très fidèle au Primogène peut obéir malgré tout, mais avec un malus d'exécution ;
- une trahison détectée dégrade les relations concernées et peut affaiblir durablement la cohésion de la coterie.

Les refus sont déterministes : ils dépendent de la cohésion, des relations, des griefs et de la relation effective au Primogène, jamais d'un tirage aléatoire opaque.

## Prestation, griefs et promesses

Les faveurs sont des obligations persistantes : mineure, majeure ou dette de vie. Elles possèdent un créancier, un débiteur, une origine et un statut. Honorer une faveur améliore la réputation ; la refuser peut créer un grief et dégrader fortement la crédibilité du débiteur.

Les tensions politiques ne reposent pas sur une jauge opaque. Elles sont enregistrées comme **griefs explicites** avec auteur, cible, cause et gravité.

Les PNJ peuvent adresser des requêtes au Primogène. Celui-ci peut accepter, refuser, négocier ou promettre. Les promesses ont une échéance et peuvent être **honorées explicitement avant les missions de nuit**.

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

Un membre de l'opposition conserve son autonomie : une action territoriale ordonnée par le joueur peut encore être refusée si elle ne sert pas suffisamment ses intérêts. Depuis la V0.11, une loyauté de coterie peut également entrer en conflit avec cet ordre.

## Politique territoriale et requêtes

L'ambition **Obtenir un Domaine** produit une demande concrète de droit de chasse lorsqu'un Domaine du Primogène est disponible.

Le Primogène peut :

- accepter et concéder l'accès ;
- négocier l'accès contre une faveur ;
- refuser et créer potentiellement un grief ;
- promettre l'accès pour une nuit ultérieure.

Une promesse territoriale honorée crée effectivement le droit de chasse avant les missions de la nuit.

## Brouillard de guerre

Le nom d'un Domaine et son détenteur officiel sont publics.

Restent privés ou soumis au renseignement :

- Viandis, Servage et Rempart des Domaines étrangers ;
- pression réelle ;
- droits privés ;
- certains litiges ;
- intrusions non détectées ;
- factions internes, ambitions, griefs et relation au Primogène des vampires étrangers.

Une coterie révèle naturellement l'identité de ses compagnons étrangers au clan concerné, mais pas leurs informations politiques privées. Le renseignement territorial reste séparé du renseignement sur les personnages.

## Praxis

Le vote des Primogènes reste un **mécanisme local de reconnaissance de la Praxis**, pas une procédure universelle de la Camarilla.

Si l'opposition refuse de suivre son Primogène, son influence est divisée selon `opposition_transfer_ratio`, configurable et fixé à 50 % par défaut.

## Cycle d'une nuit V0.11

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
Conflits de loyauté faction / Primogène / coterie
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

Aucune migration SQL Supabase n'est requise pour V0.11. Les coteries initiales sont du contenu statique ; leur évolution utilise les relations et griefs déjà stockés dans le `state_json`.

La lecture reste rétrocompatible :

- sauvegardes V0.6/V0.7/V0.8/V0.9/V0.10 conservées ;
- anciennes `coterie_memberships` converties en `faction_memberships` — ce nom legacy ne désigne pas les coteries V0.11 ;
- sauvegardes V0.9 sans Domaines enrichies automatiquement avec les six Domaines initiaux ;
- les liens initiaux de coterie sont reconstruits sans écraser une relation déjà dégradée ;
- ordres V0.7, V0.8, V0.9 et V0.10 toujours lisibles et résolubles ;
- les ordres actuels restent en `version = 4` car V0.11 n'ajoute aucun nouveau type d'ordre ;
- la nuit de production déjà soumise au format legacy reste explicitement couverte par les tests.

GitHub contient le code et les contenus statiques, jamais les sauvegardes vivantes.

## Architecture

- `game/models.py` : modèles de domaine ;
- `game/factions.py` : politique interne aux clans ;
- `game/coteries.py` : coteries transclaniques, cohésion et conflits de loyauté ;
- `game/coterie_ui.py` : vue Streamlit des coteries ;
- `game/social_politics.py` : Prestation, griefs, promesses et requêtes ;
- `game/domains.py` : Domaines, droits de chasse, Viandis, Servage, Rempart, pression et litiges ;
- `game/actions.py` : actions individuelles et effets des loyautés croisées ;
- `game/autonomy.py` : réactions autonomes déterministes ;
- `game/politics.py` : reconnaissance de Praxis ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : Étreintes ;
- `game/resolution.py` : pipeline global d'une nuit ;
- `game/serialization.py` : sérialisation et migrations rétrocompatibles ;
- `game/multiplayer.py` : orchestration asynchrone ;
- `game/persistence.py`, `game/supabase_repository.py` : persistance ;
- `game/runtime.py` : séparation Chronique / Atelier et initialisation runtime ;
- `app.py`, `game_ui.py` : interface Streamlit ;
- `tests/` : tests automatisés et smoke tests Streamlit.

## Tests

```bash
pytest -q
```

## Suite cible

1. Prince comme acteur politique autonome ;
2. résolution et arbitrage avancés des litiges territoriaux ;
3. rumeurs, secrets et information imparfaite ;
4. Étreintes davantage reliées à la Prestation, aux coteries et aux Domaines ;
5. institutions, stabilité, Mascarade et factions PNJ ;
6. approfondissement des coteries : engagements communs, secrets et ressources partagées.
