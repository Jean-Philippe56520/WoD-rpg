# WoD RPG — Chronique vampirique persistante

Jeu de rôle vampirique solo et persistant, développé en Python + Streamlit, inspiré de Vampire et centré sur l'évolution d'un personnage dans une société caïnite autonome.

Application stable : https://wod-rpg.streamlit.app

## Direction actuelle

La production n'est plus un jeu où chaque joueur contrôle un clan ou incarne obligatoirement un Primogène.

**Un joueur contrôle un seul vampire.** Il commence comme un infant récemment Étreint, encore dépendant de son sire, puis évolue librement au fil des nuits, des années et des conséquences de ses choix.

Le personnage peut devenir influent, obtenir un Domaine, accumuler des faveurs, se faire des ennemis, participer aux intrigues de Cour et éventuellement atteindre une fonction politique comme représentant de clan, Primogène ou Prince. Aucune carrière n'est imposée.

Le cœur du jeu reste : **pouvoir, information, relations, Prestation, influence, territoire et conséquences persistantes**.

## Point de départ

La Chronique commence en **1435**.

Le personnage est un vampire jeune :

- récemment Étreint ;
- sous la responsabilité de son sire ;
- sans fonction politique ;
- avec un Statut et une influence faibles ;
- dépendant d'autrui pour son premier droit de chasse ;
- plongé dans une société vampirique qui existait avant lui et continue d'agir sans lui.

Les clans jouables initiaux restent :

- Brujah ;
- Toreador ;
- Ventrue.

Le clan détermine le Sang, les Disciplines, le Fléau et certains accès ou situations, mais le joueur ne contrôle pas les autres membres de son clan.

## Création du vampire

La création actuelle utilise notamment :

- clan ;
- origine mortelle ;
- Conviction ;
- Discipline dominante ;
- restriction de chasse Ventrue lorsque nécessaire ;
- sire déterminé à partir du profil de création.

Les personnages joueurs suivent actuellement **Via Humanitas**.

Le personnage démarre sans fonction politique. Les offices sont des positions du monde, pas des classes ou niveaux automatiques.

## Boucle de jeu

La Chronique est organisée en nuits personnelles, segments et chapitres.

```text
Situation de la nuit
        |
Décision du joueur
        |
Jet de dés / Faim / conséquences
        |
Modification du personnage et du monde
        |
Nuit suivante
        |
Fin du segment
        |
Convergence solo : le monde agit
        |
PNJ / Domaines / politique / événements
        |
Segment suivant
        |
Fin du chapitre
        |
Progression + éventuelle ellipse historique
```

Le joueur ne doit attendre aucun autre joueur pour faire avancer sa Chronique.

## V0.42 — Chronique personnelle

Chaque compte possède désormais sa propre instance de Chronique persistante.

L'identifiant de partie est dérivé de manière déterministe du compte sans exposer directement son identifiant. Cela isole :

- personnage ;
- chronologie ;
- historique des nuits ;
- simulation politique ;
- Domaines ;
- faveurs ;
- événements du monde.

Les anciennes sauvegardes V0.21–V0.41 stockées dans la Chronique partagée `chronicle_1435` sont migrées de manière non destructive vers une instance personnelle. L'ancienne sauvegarde reste intacte.

Lors de la migration, les références directes aux autres anciens PJ sont retirées, mais l'état persistant des PNJ, Domaines et institutions est conservé lorsque possible.

Aucune migration SQL structurelle n'est nécessaire pour V0.42 : les tables Chronicle utilisent déjà `game_id` comme frontière de persistance.

## Monde persistant

Le monde contient des vampires PNJ avec notamment :

- clan ;
- rôle ;
- ambition ;
- objectif court terme ;
- loyauté ;
- agressivité ;
- influence ;
- Statut ;
- attitude politique ;
- progression d'agenda ;
- relations persistantes.

Les PNJ agissent lors des convergences. Le joueur n'est pas le centre mécanique du monde : il est un acteur parmi d'autres.

## Sire et émancipation

Le sire est une relation structurante des premières nuits.

Il apporte :

- protection ;
- introductions ;
- accès initial à la chasse ;
- attentes et obligations ;
- responsabilité politique pour les actes de l'infant.

Lorsque le personnage devient suffisamment autonome, il peut demander sa libération. Une émancipation réussie retire notamment le droit implicite de chasser sous la responsabilité du sire.

## Faim et résolution

Les situations utilisent le profil Vampire du personnage, les compétences, les attributs et les dés de Faim.

Les résultats peuvent produire :

- succès ;
- succès critique ;
- critique bestial ;
- échec ;
- échec bestial ;
- progression ;
- réputation ;
- influence ;
- modification de relations ou de ressources.

La direction cible est de remplacer progressivement les effets génériques par des conséquences directement liées aux acteurs et ressources réels du monde.

## Domaines

Un Domaine est une ressource politique personnelle, jamais une simple case de conquête.

Chaque Domaine utilise :

- **Viandis** : richesse nourricière ;
- **Servage** : implantation dans les réseaux mortels ;
- **Rempart** : contrôle et sécurité ;
- pression ;
- risque pour la discrétion vampirique.

Détenir un Domaine et disposer du droit d'y chasser restent deux choses distinctes.

Un personnage peut devenir politiquement important sans posséder de Domaine.

## Prestation

Les faveurs sont des obligations persistantes entre vampires.

Les niveaux actuellement reconnus sont :

- mineure ;
- majeure ;
- dette de vie.

Elles possèdent un créancier, un débiteur, une origine, un statut et peuvent être publiques ou privées.

À terme, la Prestation doit être un des principaux moteurs de progression politique plutôt qu'une simple monnaie abstraite.

## Politique et offices

Le monde politique est stocké dans un état canonique commun aux PJ et PNJ.

Les fonctions actuellement modélisées comprennent notamment :

- détenteur de Domaine ;
- représentant du clan ;
- Primogène ;
- Prince.

Prince et Primogène sont deux fonctions distinctes et ne peuvent pas être détenues simultanément par le même vampire.

Les fonctions dépendent aussi de l'époque : le moteur ne suppose pas qu'une institution moderne existe déjà en 1435.

Le joueur pourra accéder à ces fonctions uniquement si son parcours, le contexte et les rapports de force le permettent.

## Chronologie historique

Le moteur est sensible à l'époque.

Les chapitres peuvent produire des ellipses de plusieurs années et traverser des étapes historiques qui modifient progressivement :

- institutions ;
- rapports de pouvoir ;
- Révolte Anarch ;
- coalition proto-Camarilla ;
- Camarilla institutionnelle ;
- pression des chasseurs ;
- fonctions politiques disponibles.

L'histoire fournit un cadre, mais le monde local et le personnage conservent leurs conséquences propres.

## Brouillard de guerre

Le moteur possède déjà la notion d'intention cachée pour les actions autonomes du monde.

La prochaine étape est d'en faire un véritable système d'information imparfaite : le personnage ne doit pas connaître automatiquement les ambitions, relations, dettes et projets secrets des PNJ.

## Atelier legacy

L'application conserve un **Mode Atelier legacy (test/dev)** isolé de la Chronique de production.

Il contient l'ancien moteur politique centré sur Brujah, Toreador et Ventrue et permet de basculer entre les clans sans authentification.

Cet Atelier sert de banc de test et de réservoir de mécaniques historiques. Il ne définit plus la boucle principale du jeu et ne doit jamais écrire dans une Chronique personnelle de production.

## Persistance

GitHub contient :

- code ;
- configuration ;
- contenus statiques ;
- tests ;
- schémas reproductibles.

GitHub n'est jamais utilisé comme sauvegarde dynamique des parties.

La persistance de production utilise Supabase. SQLite reste utilisé pour les tests et l'exécution locale.

## Architecture principale

- `game/chronicle.py` : personnage, progression et actions personnelles historiques ;
- `game/chronicle_instance.py` : isolation d'une Chronique personnelle par compte et migration legacy ;
- `game/chronicle_store.py` : persistance du personnage, nuits et progression ;
- `game/chronicle_simulation.py` : PNJ, Domaines, faveurs, droits de chasse et simulation ;
- `game/chronicle_simulation_store.py` : persistance de la simulation ;
- `game/chronicle_politics.py` : état politique canonique PJ/PNJ ;
- `game/chronicle_offices.py` : éligibilité aux fonctions ;
- `game/chronicle_service.py` : convergence et progression du monde ;
- `game/chronicle_world_store.py` : historique des événements du monde ;
- `game/situations.py` : situations jouables et résolutions ;
- `game/vampire_profile.py` : fiche Vampire ;
- `game/vampire_profile_store.py` : persistance de la fiche ;
- `game/era.py` : règles et institutions selon l'époque ;
- `game/chronicle_ui.py` : interface de la Chronique ;
- `app.py` : launcher, authentification et séparation Chronique / Atelier ;
- `game/` historique : moteur politique legacy conservé pour l'Atelier ;
- `supabase/chronicle_schema.sql` : schéma reproductible de la Chronique ;
- `tests/` : tests automatisés.

## Tests

```bash
pytest -q
```

La CI GitHub exécute la suite complète sur chaque pull request et chaque push vers `main`.

## Priorités après V0.42

1. enrichir les PNJ en véritable société vampirique autonome ;
2. mémoire relationnelle persistante entre le PJ et les PNJ ;
3. situations générées par l'état réel du monde ;
4. rumeurs, secrets et information imparfaite ;
5. progression sociale fondée sur des relations et ressources concrètes ;
6. approfondissement Domaines et droits de chasse ;
7. accès organique aux fonctions politiques ;
8. boucle longue sur plusieurs décennies et évolution historique.

Le principe directeur reste : **le personnage commence petit, le monde existe sans lui, et son importance éventuelle doit être gagnée par le jeu**.
