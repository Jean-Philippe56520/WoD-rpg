# Paris 1435 — état initial de la Chronique

Ce document décrit la **photographie de départ** utilisée par le moteur. Il ne remplace ni `PARIS_BY_NIGHT.md` ni `PARIS_CORPUS.md` : il fixe uniquement les éléments suffisamment solides pour influencer l'état initial du jeu.

## Principe

Paris 1435 n'est pas une Cour stable dans laquelle un Prince incontesté gouverne normalement.

Le moteur distingue désormais :

- **titre** : Alexandre reste le Prince reconnu dans la continuité retenue ;
- **pouvoir effectif** : son autorité est fortement affaiblie ;
- **pressions collectives** : occupation mortelle et Cour des Miracles ne sont pas transformées en faux PNJ ;
- **succession** : aucune chute d'Alexandre n'est scriptée ;
- **joueur** : un infant nouvellement Étreint n'est évidemment pas un prétendant crédible à la Praxis.

## Contexte mortel

La référence historique indépendante enregistrée sous `bnf_hundred_years_war` confirme :

- paix entre le duc de Bourgogne et Charles VII en 1435 ;
- Paris reste cependant hors du contrôle de Charles VII pendant cette année ;
- les Anglais abandonnent Paris et sa région en 1436.

Cette donnée historique réelle est séparée des niveaux de provenance A/B/C/D du lore Vampire.

## Contexte vampirique

### Alexandre

Paris by Night décrit, après l'offensive anglaise de 1415 et les manœuvres de Mithras, un Alexandre privé de l'essentiel de son pouvoir effectif mais refusant d'abandonner Paris.

WoD-rpg conserve donc :

- `office.prince = npc_alexandre` ;
- son statut d'Ancien et sa légitimité historique ;
- une **Praxis contestée** à l'ouverture de la Chronique.

Le jeu ne traduit pas « contestée » par « condamné ». Alexandre peut consolider son autorité, perdre Paris, survivre à la crise, être remplacé, ou conduire la partie vers une histoire très différente de la référence de 1481.

### Cour des Miracles

Paris by Night décrit dans la crise une Cour parallèle réunissant :

- Brujah ;
- Malkaviens ;
- Gangrels ;
- Nosferatus.

Elle exerce une influence supérieure à la Cour officielle dans le Paris chaotique de cette période. Comme aucun dirigeant individuel fiable n'est encore établi pour 1435, le moteur représente cette force sous forme de **pression politique collective**, pas sous forme de personnage inventé.

### Fidèles d'Alexandre

Le roster actuel conserve notamment Alexandre, Saviarre, Magnerius et Pompignan comme noyau de la Cour fidèle, avec Béatrix et les réseaux toréador comme partenaires politiques plus autonomes.

Ces relations sont des points de départ, pas un verrou : les agendas autonomes peuvent transformer les alliances, rivalités et Prestations dès les premiers Cycles.

## Pressions politiques de départ

`game/paris_1435_context.py` fournit deux pressions actives uniquement pour l'année 1435 :

1. occupation anglaise et recomposition des appuis bourguignons ;
2. contre-pouvoir de la Cour des Miracles.

Ces pressions :

- augmentent la fragilité de la Praxis ;
- n'imposent aucune issue ;
- ne donnent aucun score brut au joueur ;
- ne créent aucun dirigeant fictif ;
- disparaissent du **contexte historique automatique** après 1435.

Si leurs conséquences doivent continuer en 1436 et au-delà, elles doivent alors avoir été transformées par la simulation en relations, événements, Domaines, Prestations, crises ou nouvelles pressions propres à cette sauvegarde.

## Effet en jeu

À l'ouverture :

- Alexandre est Prince ;
- sa Praxis est **contestée mais pas critique** ;
- plusieurs PNJ anciens peuvent objectivement constituer des prétendants crédibles ;
- le PJ initial ne le peut pas ;
- le joueur ne reçoit ni le score interne de Praxis ni la liste secrète des prétendants ;
- les tensions remontent par rumeurs, conversations, événements de Convergence et situations émergentes.

Le cœur politique de la Chronique commence donc immédiatement, sans faire du personnage joueur le centre artificiel du monde.
