# WoD RPG — Chronique vampirique persistante

Jeu de rôle vampirique solo et persistant, développé en Python + Streamlit, inspiré de Vampire et centré sur l'évolution d'un personnage dans une société caïnite autonome.

Application stable : https://wod-rpg.streamlit.app

## Direction actuelle

La production n'est plus un jeu où chaque joueur contrôle un clan ou incarne obligatoirement un Primogène.

**Un joueur contrôle un seul vampire.** Il commence comme un infant récemment Étreint, encore dépendant de son sire, puis évolue librement au fil des nuits, des années et des conséquences de ses choix.

Le personnage peut devenir influent, obtenir un Domaine, accumuler des faveurs, se faire des ennemis, participer aux intrigues de Cour et éventuellement atteindre une fonction politique comme représentant de clan, Primogène ou Prince. Aucune carrière n'est imposée.

Le cœur du jeu reste : **pouvoir, information, relations, Prestation, influence, territoire et conséquences persistantes**.

## Point de départ : Paris, 1435

La Chronique commence à **Paris en 1435**.

Le personnage est :

- récemment Étreint ;
- sous la responsabilité de son sire ;
- sans fonction politique ;
- avec un Statut et une influence faibles ;
- dépendant d'autrui pour son premier droit de chasse ;
- plongé dans une société vampirique qui existait avant lui et continue d'agir sans lui.

Le Paris vampirique de départ est désormais ancré dans une continuité historique et caïnite documentée. Alexandre est le Prince de référence en 1435 ; les Toréador, les anciens Ventrue, les mouvements anarchs et la Cour des Miracles forment des rapports de force qui peuvent ensuite évoluer différemment selon la partie.

Les clans jouables initiaux restent : Brujah, Toréador et Ventrue. Le joueur contrôle uniquement son vampire, jamais son clan.

## Paris by Night comme source récurrente

Le wiki **Paris by Night** (`https://parisbynight.quelquesmots.fr/`) est enregistré comme source majeure et récurrente pour la continuité parisienne.

Il n'est pas recopié ni traité comme un canon aveugle. Chaque personnage ou événement important doit être recoupé entre fiche individuelle, lignée, chronologie, pages de règne et éventuelles sources officielles citées.

Le registre détaillé se trouve dans `docs/lore/PARIS_BY_NIGHT.md` et le catalogue machine dans `game/lore_sources.py`.

Les niveaux de provenance sont :

- **A** : source WoD officielle identifiée ou explicitement signalée ;
- **B** : continuité Paris by Night / Kaotic enrichie ;
- **C** : déduction WoD-rpg à partir de plusieurs sources ;
- **D** : création propre à WoD-rpg nécessaire à la simulation.

Une règle est impérative : **un statut moderne n'est jamais projeté automatiquement vers 1435**. François Villon est par exemple déjà un ancien Toréador en 1435, mais il n'est pas encore Prince de Paris.

## V0.43 — Paris vivant

V0.43 introduit le premier seed historique de Paris 1435 et la première couche de société caïnite réellement autonome.

Le roster initial audité comprend notamment :

- Alexandre ;
- Saviarre ;
- Béatrix ;
- François Villon ;
- Violetta ;
- Magnerius de Sens ;
- Henri le Preux ;
- Pierre Emmanuel de Pompignan.

Les données séparent :

1. l'identité durable d'un personnage ;
2. son état et sa localisation en 1435 ;
3. les interprétations mécaniques propres à WoD-rpg ;
4. les événements futurs de référence.

Henri le Preux est par exemple enregistré à Bourges en 1435 et n'agit donc pas comme s'il se trouvait physiquement à la Cour parisienne.

Les événements futurs connus ne sont pas forcés. La destruction d'Alexandre en 1481 ou l'ascension future d'autres figures sont stockées comme **pressions historiques potentielles** avec des conditions et des divergences possibles. La simulation peut converger vers le canon ou s'en éloigner fortement.

## Société autonome

Lors d'une convergence, les PNJ locaux peuvent désormais agir les uns sur les autres et produire des mutations persistantes concrètes :

- rapprochement et alliance ;
- rivalité ;
- modification de relation ;
- création d'une Prestation ;
- service politique ;
- droit de chasse temporaire lorsqu'un acteur contrôle réellement un Domaine ;
- progression d'agenda et influence ;
- pression des chasseurs mortels sur les Domaines.

Le monde ne se contente donc plus d'incrémenter un compteur abstrait. Le joueur arrive dans un réseau qui agit déjà sans lui.

## V0.44 — mémoire relationnelle persistante

Les PNJ peuvent maintenant conserver une mémoire structurée de leurs interactions avec le personnage joueur.

Pour chaque PNJ concerné, le moteur suit notamment :

- **disposition** : attitude générale envers le PJ ;
- **confiance** : capacité à croire sa parole ou à compter sur lui ;
- **respect** : poids accordé à ses décisions et à ses capacités ;
- **crainte** : peur inspirée par ses actes ou par la Bête ;
- **connaissance** : degré auquel le PNJ connaît réellement le personnage ;
- **griefs** : passif hostile durable ;
- **dernière interaction**.

Cette mémoire n'est pas décorative. Une relation particulièrement favorable peut réduire la difficulté d'un futur échange social ; un passif hostile ou plusieurs griefs peuvent l'augmenter.

Les actes visibles modifient la mémoire de l'interlocuteur réel : service au sire, négociation, refus, demande d'émancipation, prise de position politique, protection d'un intérêt, critique bestial ou échec bestial. Une chasse discrète n'est pas magiquement connue du détenteur d'un Domaine ; elle ne devient relationnelle que si elle laisse une trace suffisamment forte.

Le journal détaillé des relations n'est pas une seconde base de données. Les interactions sont marquées dans l'historique canonique des nuits puis reconstruites pour l'interface **Mes liens**. De même, les Prestations restent dérivées du registre canonique des faveurs et ne sont jamais dupliquées dans la mémoire relationnelle.

Les sauvegardes V0.43 restent compatibles : les dimensions relationnelles supplémentaires sont stockées dans les relations déjà sérialisées des PNJ. **Aucune migration de schéma Supabase n'est requise.** Le score historique `sire_relation` sert de baseline lorsque le sire ne dispose pas encore d'une mémoire détaillée.

## Canon divergent

L'histoire réelle et la continuité Vampire constituent des **conditions initiales et des pressions**, pas un scénario verrouillé.

Le moteur ne doit jamais faire :

```python
if year == 1481:
    kill_alexandre()
```

Il doit évaluer les rapports de force réellement produits par la partie : stabilité, relations, Prestations, rivalités, factions, Domaines, influence, secrets et interventions du PJ.

Le principe cible est : **plus la Chronique avance, plus son Paris devient l'histoire propre de cette sauvegarde**.

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

```text
Situation de la nuit
        |
Décision du joueur
        |
Jet de dés / Faim / conséquences
        |
Mémoire des acteurs réellement impliqués
        |
Modification du personnage et du monde
        |
Nuit suivante
        |
Fin du segment
        |
Convergence solo : le monde agit
        |
PNJ / relations / Prestations / Domaines / politique
        |
Segment suivant
        |
Fin du chapitre
        |
Progression + éventuelle ellipse historique
```

Le joueur ne doit attendre aucun autre joueur pour faire avancer sa Chronique.

## Chronique personnelle

Depuis V0.42, chaque compte possède sa propre instance de Chronique persistante.

L'identifiant de partie est dérivé de manière déterministe du compte sans exposer directement son identifiant. Cela isole personnage, chronologie, historique des nuits, simulation politique, Domaines, faveurs et événements.

Les anciennes sauvegardes V0.21–V0.41 stockées dans `chronicle_1435` sont migrées de manière non destructive vers une instance personnelle.

V0.43 ajoute le seed Paris de manière idempotente :

- l'ancien Prince fictif par défaut est remplacé par Alexandre ;
- une fonction politique déjà réellement modifiée par une partie n'est pas écrasée ;
- un ancien PNJ encore référencé par une dette, un droit ou une ressource persistante est conservé pour éviter les références cassées.

V0.44 enrichit ensuite les relations sans changer la structure de persistance : les souvenirs sont portés par le JSON de simulation déjà existant et l'historique détaillé reste celui des nuits personnelles.

## Sire et émancipation

Le sire structure les premières nuits par la protection, les introductions, l'accès initial à la chasse, les attentes et la responsabilité politique.

Lorsque le personnage devient suffisamment autonome, il peut chercher son émancipation. Une libération réussie modifie notamment son accès implicite à la chasse, sa position sociale et la mémoire que son sire conserve de cette confrontation.

## Domaines

Un Domaine est une ressource politique personnelle, jamais une simple case de conquête.

Chaque Domaine utilise :

- **Viandis** : richesse nourricière ;
- **Servage** : implantation dans les réseaux mortels ;
- **Rempart** : contrôle et sécurité ;
- pression ;
- risque pour la discrétion vampirique.

Détenir un Domaine et disposer du droit d'y chasser restent deux choses distinctes.

## Prestation

Les faveurs sont des obligations persistantes entre vampires. Les niveaux actuellement reconnus sont mineure, majeure et dette de vie.

Elles possèdent un créancier, un débiteur, une origine, un statut et peuvent être publiques ou privées. V0.43 permet au monde autonome d'en créer entre PNJ ; V0.44 peut afficher leur poids dans une relation sans les recopier dans la mémoire du PNJ.

## Politique et offices

Le monde politique est stocké dans un état canonique commun aux PJ et PNJ.

Les fonctions modélisées comprennent notamment détenteur de Domaine, représentant du clan, Primogène et Prince.

Prince et Primogène sont distincts et ne peuvent pas être détenus simultanément par le même vampire. Les fonctions disponibles dépendent de l'époque ; le moteur ne suppose pas qu'une institution moderne existe déjà en 1435.

Les situations politiques utilisent désormais le détenteur réel de l'office de Prince dans la sauvegarde, et non un identifiant historique figé.

## Chronologie historique

Le moteur est sensible à l'époque et peut traverser Révolte Anarch, coalition proto-Camarilla, Camarilla institutionnelle, changements de pouvoirs mortels et pression accrue des chasseurs.

La direction actuelle est de remplacer les jalons déterministes par des transitions conditionnelles lorsque le monde local peut raisonnablement diverger.

## Brouillard de guerre

La mémoire relationnelle V0.44 décrit ce que les PNJ pensent du PJ ; elle ne doit pas devenir une fenêtre omnisciente sur leur esprit.

Le moteur possède déjà une notion d'intention cachée pour les actions autonomes. La cible suivante reste un véritable système d'information imparfaite : rumeurs, sources, soupçons, secrets, ancienneté d'une information et degré de certitude.

## Atelier legacy

L'application conserve un **Mode Atelier legacy (test/dev)** isolé de la Chronique de production.

Il contient l'ancien moteur politique centré sur Brujah, Toréador et Ventrue. Il sert de banc de test et de réservoir de mécaniques historiques et ne doit jamais écrire dans une Chronique personnelle de production.

## Persistance

GitHub contient code, configuration, contenus statiques, lore structuré, tests et schémas reproductibles. GitHub n'est jamais utilisé comme sauvegarde dynamique des parties.

La persistance de production utilise Supabase. SQLite reste utilisé pour les tests et l'exécution locale.

## Architecture principale

- `game/chronicle.py` : personnage, progression et actions personnelles ;
- `game/chronicle_instance.py` : Chronique personnelle et migration legacy ;
- `game/chronicle_store.py` : personnage, nuits et progression ;
- `game/chronicle_simulation.py` : primitives génériques de PNJ, Domaines, Prestation et droits ;
- `game/paris_lore.py` : seed historique Paris 1435, factions et futurs de référence ;
- `game/lore_sources.py` : registre machine des sources et provenance ;
- `game/paris_simulation.py` : adaptation Paris, migration idempotente et actions autonomes ;
- `game/relationship_memory.py` : mémoire persistante PNJ → PJ et effets relationnels ;
- `game/relationship_ui.py` : lecture non omnisciente des liens connus du PJ ;
- `game/chronicle_simulation_store.py` : persistance de la simulation ;
- `game/chronicle_politics.py` : état politique canonique PJ/PNJ ;
- `game/chronicle_offices.py` : éligibilité aux fonctions ;
- `game/chronicle_service.py` : convergence et progression du monde ;
- `game/chronicle_world_store.py` : historique des événements ;
- `game/situations.py` : situations jouables, résolutions et conséquences relationnelles ;
- `game/vampire_profile.py` : fiche Vampire ;
- `game/era.py` : règles et institutions selon l'époque ;
- `game/chronicle_ui.py` : interface de la Chronique ;
- `docs/lore/PARIS_BY_NIGHT.md` : protocole et audit permanent de Paris by Night ;
- `app.py` : launcher, authentification et séparation Chronique / Atelier ;
- `tests/` : tests automatisés.

## Tests

```bash
pytest -q
```

La CI GitHub exécute la suite complète sur chaque pull request et chaque push vers `main`.

## Priorités après V0.44

1. situations générées par l'état réel de la société et des relations ;
2. enrichissement progressif du roster Paris by Night, sans invention présentée comme canon ;
3. rumeurs, secrets et information imparfaite ;
4. factions autonomes, dont la Cour des Miracles, avec vrais membres et agendas ;
5. progression sociale fondée sur des relations et ressources concrètes ;
6. approfondissement Domaines et droits de chasse ;
7. offices politiques émergents et Praxis ;
8. boucle longue où les grandes dates deviennent des pressions conditionnelles.

Le principe directeur reste : **le personnage commence petit, le monde existe sans lui, et son importance éventuelle doit être gagnée par le jeu**.
