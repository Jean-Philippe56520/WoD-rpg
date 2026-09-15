# V0.47 — Intrigues émergentes

## Intention

Une Nuit ne doit plus principalement provenir d'une petite bibliothèque de situations génériques. Le moteur doit faire remonter vers le joueur les conséquences du Paris propre à sa sauvegarde.

La boucle V0.47b est :

```text
Convergence
  ↓
les PNJ poursuivent leurs agendas
  ↓
relations / Prestations / patronages / droits / pression changent réellement
  ↓
SimulationBeat persistant dans wod_chronicle_world_events
  ↓
Cycle suivant
  ↓
le joueur reçoit un écho imparfait de certains changements
  ↓
source + fiabilité, sans intention cachée ni score omniscient
  ↓
situation jouable
  ↓
le choix du PJ modifie à son tour relations, influence, mémoire et ressources
```

## Source de vérité

V0.47b n'ajoute pas une seconde mémoire narrative.

- `NpcState.agenda_progress` reste le compteur persistant d'avancement des plans PNJ ;
- `wod_chronicle_world_events` reste l'historique persistant des changements produits à la Convergence ;
- les rumeurs et hooks sont des **vues dérivées** de ces faits persistants ;
- aucune nouvelle table Supabase n'est requise.

## Agendas multi-étapes

Les agendas autonomes utilisent quatre stades :

1. `probe` — repérage : tester les relations, observer les résistances ;
2. `recruit` — recrutement : rapprochements, services et premières dettes ;
3. `commit` — engagement : rivalités assumées, Prestations, patronages ;
4. `consolidate` — consolidation : stabiliser les alliances et convertir les services en pouvoir durable.

Le stade découle du `agenda_progress` déjà sérialisé. Une ancienne sauvegarde peut donc entrer dans ce système sans migration.

## Information imparfaite

Un événement du monde possède deux niveaux distincts :

- **état canonique interne** : action réelle, relation modifiée, Prestation créée, agenda du PNJ ;
- **information du joueur** : texte public de l'événement, type de source et fiabilité estimée.

L'interface ne doit jamais afficher :

- `hidden_intent` ;
- les scores numériques de relation entre PNJ ;
- un booléen vrai/faux de rumeur ;
- l'objectif interne complet d'un acteur ;
- une conséquence qu'aucune source du PJ ne permet de connaître.

Le joueur voit à la place des formulations comme :

- rumeur fragile ;
- source plausible ;
- information recoupée.

Même un événement réellement arrivé peut donc parvenir sous une forme partielle ou orientée.

## Temporalité des hooks

Les conséquences d'une Convergence servent d'amorces au **Cycle immédiatement suivant**.

Chaque événement persistant est attribué de manière déterministe à une seule Nuit significative du Cycle suivant. Cette règle évite qu'une même rivalité réapparaisse mécaniquement à chacune des trois Nuits sans ajouter un état de consommation en base.

Lorsqu'un chapitre vient d'être clos, seuls les événements du dernier Cycle du chapitre précédent alimentent directement le premier Cycle du nouveau chapitre.

## Priorités de Nuit

L'ordre de priorité reste :

1. demande d'émancipation lorsqu'elle devient disponible ;
2. obligation/relation particulièrement forte avec le sire ;
3. conséquence émergente du monde ;
4. situation générique de repli.

La Faim ne transforme jamais automatiquement la chasse en événement imposé. La chasse reste une action du joueur.

## Domaines et Prestations

Les ressources politiques existantes deviennent des générateurs narratifs :

- une Prestation créée par un PNJ peut susciter une rumeur et une enquête ;
- un patronage politique crée une dépendance observable ;
- un droit de chasse temporaire peut déplacer des alliances ;
- la pression des chasseurs sur un Domaine peut déclencher une crise de discrétion et d'accès.

Ainsi le Domaine, le droit de chasse et la Prestation ne sont pas des compteurs abstraits : leurs changements deviennent des situations.

## Limites actuelles et suite

V0.47b est la première boucle complète, mais plusieurs extensions restent nécessaires :

- produire de vraies informations fausses ou manipulées à partir d'acteurs intéressés, pas uniquement des fragments partiels d'événements réels ;
- faire persister certaines enquêtes sur plusieurs Cycles ;
- permettre aux PNJ de réagir explicitement à l'intervention du PJ dans une intrigue ;
- relier plusieurs hooks à un même agenda long au lieu de les traiter uniquement comme conséquences successives ;
- faire émerger les crises de Praxis depuis l'affaiblissement réel du Prince, les alliances, les Prestations, les Domaines et un candidat crédible ;
- enrichir le roster 1435 à mesure que le corpus Paris by Night est audité.

Le principe reste : **les règles génèrent une histoire propre à la sauvegarde ; elles ne remplacent pas cette histoire par une suite de scripts prédéfinis.**
