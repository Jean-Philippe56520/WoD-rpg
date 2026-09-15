# V0.48b — Résolution V5 simplifiée

Cette passe consolide le système de résolution de la Chronique solo autour du noyau déjà présent dans le moteur.

## Règle centrale

Une action utilise un pool fondé sur la fiche du vampire :

- Attribut + Compétence ;
- bonus de personnage déjà prévus par le moteur ;
- dés de Faim inclus dans le pool selon la Faim actuelle.

Le moteur compare les succès à une difficulté exacte qui reste interne.

## Difficulté cachée

Le joueur ne voit jamais le nombre de succès requis.

Échelle interne :

- 1 : facile ;
- 2–3 : standard ;
- 4–5 : difficile ;
- 6+ : extrême.

L'interface affiche uniquement :

- l'approche utilisée (Attribut + Compétence) ;
- une catégorie de risque ;
- un indice narratif.

Le résultat final peut afficher le nombre de succès obtenu, mais pas le seuil exact.

## Capacité et contexte restent séparés

Ce qui améliore le vampire modifie son pool.

Ce qui améliore ou dégrade la situation modifie la difficulté : relation acquise, passif, pression du Domaine, risque de Mascarade, etc.

Exemple : une bonne relation avec un interlocuteur peut faire passer une difficulté interne de 4 à 3. Le personnage n'a pas gagné un point de Politique : la situation est simplement devenue plus favorable.

## V5 conservé

Le moteur utilise déjà :

- D10 ;
- succès sur 6+ ;
- dés de Faim ;
- critiques ;
- critiques bestiaux ;
- échecs bestiaux ;
- Rouse Check déterministe ;
- conséquences persistantes liées au résultat.

Les jets sont déterministes à seed identique pour garantir l'idempotence des résolutions asynchrones et des retries.

## Conséquences

La réussite ou l'échec ne constitue pas à lui seul toute la résolution. Le moteur peut modifier selon la situation :

- Faim ;
- réputation ;
- influence ;
- relation au sire ;
- mémoire relationnelle des PNJ ;
- Prestations ;
- pression ou risque de Domaine ;
- temps restant dans la nuit.

Cette architecture doit rester le socle des futures Disciplines, de la Volonté dépensable et des leviers politiques sans transformer WoD-rpg en simple simulateur de jets.
