# V0.49e — Historiques et Avantages contextuels

## Principe

WoD-rpg ne transforme pas les Historiques en Compétences supplémentaires.

- le personnage fournit le **pool de dés** ;
- les Historiques modifient les **circonstances** ;
- une approche doit déclarer explicitement qu'un Historique peut l'aider ;
- un seul Historique principal peut réduire la difficulté d'une même approche.

## Sous-ensemble MVP

### Contacts

Un réseau peut faciliter une enquête politique, une rumeur ou la protection d'un intermédiaire. Lorsqu'il est explicitement pertinent, il réduit la difficulté cachée de 1.

### Ressources

Les moyens matériels peuvent financer une protection, un arbitrage ou une solution logistique. Ils réduisent la difficulté de 1 uniquement sur les approches prévues par le contenu.

### Statut

Le Statut utilisé par le moteur est celui du `PlayerCharacter`, qui évolue avec la chronique. L'ancien `backgrounds['status']` n'est pas une seconde source de vérité. Le Statut peut faciliter une prise de parole ou une démarche formelle lorsqu'il est reconnu dans la scène.

### Sire

Le Sire est surtout un Historique d'accès : protection initiale, scènes dédiées, droits de chasse et obligations. Il ne cumule pas un bonus de difficulté avec la mémoire relationnelle déjà gérée par le moteur.

## Règle d'empilement

Si plusieurs Historiques sont pertinents, WoD-rpg choisit le meilleur levier principal. Il n'y a donc pas de réduction automatique `Contacts + Ressources + Statut` sur la même action.

## Interface

L'interface peut annoncer :

> Historique — Contacts 1 : votre ressource extérieure améliore les circonstances de cette approche sans augmenter votre Compétence.

Elle continue à n'afficher qu'une catégorie qualitative de risque. Le seuil exact reste caché.

## Extension future

Les autres Historiques et Avantages V5 (Alliés, Refuge, Influence, etc.) ne seront ajoutés que lorsqu'ils produiront un effet utile dans la chronique politique. L'objectif n'est pas de recopier une liste exhaustive, mais de conserver les fonctions V5 pertinentes pour WoD-rpg.
