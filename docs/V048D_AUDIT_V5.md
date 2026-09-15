# V0.48d — Conséquences graduées et audit V5

## Décision de conception

WoD-rpg n'a pas vocation à reproduire l'intégralité du livre de règles V5.

La cible est un **V5 simplifié fidèle** :

- conserver les mécaniques qui définissent l'identité de Vampire V5 ;
- adapter ce qui doit fonctionner dans une chronique solo, persistante et asynchrone ;
- écarter les sous-systèmes qui alourdissent le jeu sans renforcer politique, influence, information, relations et conséquences ;
- ne pas remplacer une règle V5 par une règle maison sans la signaler explicitement.

## Conséquences graduées

Le jet reste un jet V5. La marge ne crée pas un second système de réussite ; elle qualifie la portée de la conséquence persistante.

| Résultat | Interprétation WoD-rpg |
| --- | --- |
| critique propre ou marge +3 et plus | réussite exceptionnelle |
| marge +1 ou +2 | réussite nette |
| marge 0 | réussite coûteuse |
| critique bestial | réussite bestiale |
| marge -1 | échec limité |
| marge -2 à -3 | échec sérieux |
| marge -4 et moins ou échec bestial | échec grave |

Effets généraux :

- les échecs sociaux et mentaux sérieux ou graves peuvent user la Volonté ;
- un échec physique ordinaire ne produit ni Faim ni perte de Volonté automatiquement ;
- les échecs sérieux et graves consomment davantage de temps dans la Nuit significative ;
- le degré d'issue est enregistré dans l'historique de résolution ;
- les effets propres à la situation restent prioritaires : relation, réputation, influence, Domaine, Prestation, Faim, information, etc.

## Audit du noyau V5

### Solide aujourd'hui

- les neuf Attributs ;
- groupement Attribut + Compétence ;
- d10, succès sur 6+ ;
- difficulté ;
- Faim et dés de Faim ;
- critiques, critiques bestiaux et échecs bestiaux ;
- Volonté et relances ;
- Test d'Exaltation ;
- Coup de Sang ;
- Génération ;
- Humanité comme valeur ;
- Persistance des nuits, choix et conséquences ;
- mémoire relationnelle persistante.

### Partiel et à compléter

- **Compétences** : seulement un sous-ensemble de la liste V5 est actuellement disponible ;
- **Puissance du Sang** : structurée mais seulement utilisée par une partie de ses effets ;
- **Disciplines** : structure présente, mais seulement quelques pouvoirs réellement jouables ;
- **Fléaux de clan** : décrits, Ventrue déjà relié à la chasse, Brujah et Toreador encore incomplets ;
- **Historiques et Avantages** : Sire, Contacts, Ressources et Statut existent dans la fiche mais n'alimentent pas encore suffisamment les situations ;
- **Convictions** : structurées, mais leur bonus actuel de Compétence est une ancienne règle maison. La cible est de les relier à Humanité, Flétrissures et Remords ;
- **Ambition et Désir** : des équivalents existent, mais leur boucle de récompense reste à formaliser ;
- **Expérience** : elle existe, mais pas encore le système d'achat et de progression des traits.

### Prioritaire à ajouter

1. liste de Compétences suffisamment complète pour la Chronique ;
2. Santé et dégâts superficiels/aggravés ;
3. guérison vampirique ;
4. Humanité : Flétrissures et Remords ;
5. Frénésie et Compulsions ;
6. Fléaux Brujah/Toreador réellement mécaniques ;
7. Historiques/Avantages utilisés comme leviers des situations ;
8. Lien du Sang ;
9. Spécialités ;
10. progression XP des Attributs, Compétences, Disciplines et Avantages.

## Ce que nous simplifions volontairement

### Combat détaillé

Pas de moteur tactique complet pour le MVP. Un affrontement doit être traité comme une situation V5 avec :

- groupement pertinent ;
- opposition/difficulté ;
- Santé lorsque celle-ci sera ajoutée ;
- marge ;
- conséquences persistantes.

### Résonances et dyscrasies

Écartées du noyau pour l'instant. Elles ne seront ajoutées que si elles enrichissent réellement la chasse.

### Type de prédateur

Le modèle moderne de type de prédateur n'est pas repris tel quel pour Paris 1435. Les habitudes de chasse doivent émerger du Domaine, du clan, de la préférence de Sang et des choix du joueur.

### Coterie

Non prioritaire pour une chronique centrée sur un seul vampire. Les fonctions sociales sont portées par le sire, le lignage, les factions, les relations et les Prestations.

### Attaches humaines

Elles ne sont plus utilisées dans la création actuelle. Si cette décision reste définitive, le futur système d'Humanité devra compenser explicitement leur absence au lieu de prétendre reproduire V5 à l'identique.

## Règle d'architecture

`game/structure_v5.py` est le contrat de couverture mécanique. Chaque grand système y est classé :

- intégré ;
- partiel ;
- différé ;
- écarté.

Une fonctionnalité ne doit plus être présentée comme « V5 » uniquement parce qu'elle ressemble à Vampire. Les écarts et règles maison doivent être visibles dans ce registre.

Le moteur legacy peut conserver ses anciennes simplifications tant qu'il reste isolé. La Chronique solo doit, elle, utiliser exclusivement le noyau V5 simplifié documenté ici.
