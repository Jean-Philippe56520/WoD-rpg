# V0.48c — Leviers vampiriques de résolution

Cette passe complète le noyau de résolution de la Chronique solo sans modifier le schéma Supabase.

## Volonté

La Volonté courante devient une ressource dépensable et persistante.

- la Volonté maximale est égale à Résolution + Sang-froid ;
- dépenser 1 point permet de relancer jusqu'à trois dés ordinaires en échec ;
- les dés de Faim ne peuvent jamais être relancés par la Volonté ;
- si aucun dé ordinaire n'a besoin d'être relancé, aucun point n'est dépensé ;
- un échec mental ou social net, avec une marge de -2 ou moins, inflige 1 point d'usure de Volonté ;
- un échec physique ordinaire n'augmente pas automatiquement la Faim et n'inflige pas cette usure de Volonté.

À la fin d'une Nuit significative, le vampire récupère une partie de sa Volonté, plafonnée par le meilleur score entre Résolution et Sang-froid et sans dépasser sa Volonté maximale. Une Nuit significative sert ici d'équivalent asynchrone à une séance de jeu.

## Coup de Sang

Le joueur peut renforcer une action par le Sang avant sa résolution.

Le Coup de Sang :

- déclenche un Test d'Exaltation ;
- peut augmenter la Faim de 1 ;
- est indisponible lorsque la Faim est déjà à 5 ;
- ajoute temporairement des dés au groupement de l'action ;
- ne modifie jamais définitivement la fiche du vampire.

Bonus utilisé selon la Puissance du Sang :

| Puissance du Sang | Dés ajoutés |
| --- | ---: |
| 0 | +1 |
| 1–2 | +2 |
| 3–4 | +3 |
| 5–6 | +4 |
| 7–8 | +5 |
| 9–10 | +6 |

## Disciplines

Posséder une Discipline ne donne jamais un bonus générique à toutes les actions.

Un pouvoir doit être explicitement pertinent pour l'approche choisie. Cette première intégration représente :

- **Présence — Révérence** : renforce une tentative de Persuasion ;
- **Auspex — Sens accrus** : renforce l'observation et la lecture des détails ;
- **Force d'âme — Esprit résolu** : renforce certaines résistances à la pression ou à la coercition.

Les pouvoirs à effet essentiellement qualitatif, notamment **Grâce féline**, **Corps létal** et **Contrainte**, ne sont pas transformés artificiellement en bonus de dés. Ils devront être utilisés dans des scènes et actions qui représentent réellement leur effet.

## Interface

Pour chaque décision, l'interface affiche désormais :

- l'approche Attribut + Compétence ;
- le risque estimé sans révéler le seuil exact ;
- les pouvoirs de Discipline réellement applicables ;
- le Coup de Sang et son risque de Faim ;
- la dépense de Volonté disponible.

Le choix de décision est effectué hors du formulaire de résolution afin que les leviers proposés soient toujours recalculés immédiatement pour l'approche actuellement sélectionnée.

## Persistance et déterminisme

- la Volonté courante reste dans le profil JSON existant ;
- le bonus d'une action renforcée est transitoire et n'est jamais sérialisé ;
- aucun nouveau champ SQL ni aucune migration Supabase ne sont nécessaires ;
- les Tests d'Exaltation et les relances restent déterministes pour garantir la sûreté des nouvelles tentatives dans le moteur asynchrone.
