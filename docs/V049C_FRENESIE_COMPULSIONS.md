# V0.49c — Frénésie, Compulsions et Fléaux

## Cible

WoD-rpg utilise un **V5 simplifié fidèle** : les règles qui modélisent la Bête sont conservées, mais les provocations doivent être déclarées explicitement par le contenu. Le moteur ne doit jamais inventer qu'une scène paisible provoque une Frénésie simplement parce qu'un personnage est affamé.

## Frénésie

Le moteur distingue :

- Frénésie de Fureur ;
- Frénésie de Faim ;
- Frénésie de Terreur.

Le pool est :

`Volonté restante + floor(Humanité / 3)`

Le résultat est un test sans dés de Faim. Un joueur peut aussi **Chevaucher la vague** : il ne tente alors pas de résister, mais conserve l'interprétation de son personnage à l'intérieur de l'impulsion de la Frénésie.

### Brujah

La Sévérité du Fléau est structurée à partir de la Puissance du Sang. Pour une Frénésie de Fureur, elle est retranchée au pool Brujah. Elle ne pénalise ni la Faim ni la Terreur.

## Compulsions

Les trois clans jouables possèdent leur Compulsion de clan :

- Brujah : **Rébellion** ;
- Toreador : **Obsession** ;
- Ventrue : **Arrogance**.

Une Compulsion active impose `-2 dés` aux actions qui n'expriment pas l'impulsion. Une action alignée n'est pas pénalisée ; si elle réussit, le moteur peut considérer la Compulsion satisfaite.

Dans le format asynchrone de WoD-rpg, une Compulsion est scoped à la **Nuit significative** qui l'a produite. Elle ne doit pas contaminer indéfiniment les Cycles suivants.

Les états de Compulsion sont persistables dans le JSON du profil (schéma 5), sans migration SQL.

## Déclenchement

V0.49c structure volontairement le moteur avant de le brancher aux scènes. Les résultats suivants sont reconnus comme capables de produire une Compulsion :

- échec bestial ;
- critique bestial.

Mais le branchement automatique doit rester une étape séparée et testée, parce que le moteur de Nuit doit décider :

1. quelle complication bestiale est retenue ;
2. si une provocation de Frénésie existe réellement dans la scène ;
3. comment le résultat modifie la chasse, les relations, la Mascarade et le temps restant.

Cette séparation évite qu'un résultat de dés déclenche simultanément plusieurs conséquences incompatibles.

## Reste à brancher

- goût du sang à Faim 4+ → provocation de Frénésie de Faim ;
- échec d'Exaltation forcée à Faim 5 → provocation de Faim ;
- feu / soleil → Terreur ;
- insultes, humiliation, violence ou provocation explicitement déclarées → Fureur ;
- résultat bestial → Compulsion lorsqu'aucune complication plus spécifique n'est déjà retenue ;
- affichage joueur de la Compulsion et de son impact sur une approche.

Le Fléau Toreador et la restriction Ventrue restent partiels tant que les scènes ne déclarent pas explicitement les circonstances nécessaires à leur effet.
