# Paris 1435 — roster vampirique audité

Ce document décrit la photographie de disponibilité des acteurs pour **1435**. Il ne cherche pas à remplir Paris avec des noms plausibles : il distingue explicitement ce qui est établi, collectif, extérieur, absent ou encore incertain.

Le registre machine est `game/paris_roster.py`.

## Principe

Une fiche moderne Paris by Night ne suffit jamais à faire d'un personnage un résident de Paris en 1435.

Chaque entrée possède :

- un type : `named_vampire` ou `collective` ;
- un statut : `present`, `external`, `absent`, `historical` ou `unverified` ;
- une localisation ;
- une certitude ;
- des sources ;
- une politique de simulation : `active_named`, `context_only` ou `forbidden`.

`active_named` est réservé aux personnages nommés suffisamment étayés pour participer à la simulation. Un collectif peut peser politiquement sans qu'un chef soit inventé.

## Acteurs nommés actifs

Le seed de simulation reste volontairement limité à :

- Alexandre ;
- Saviarre ;
- Béatrix ;
- François Villon ;
- Violetta ;
- Magnerius de Sens ;
- Pierre Emmanuel de Pompignan ;
- Henri le Preux, acteur extérieur basé à Bourges.

Le test V0.48a impose que cette liste corresponde **exactement** aux entrées `active_named` du roster.

Magnerius et Pompignan restent classés avec une certitude de localisation plus prudente que les figures parisiennes les mieux documentées : leur appartenance au réseau d'Alexandre est nette, mais la chronologie indique qu'ils sont en province lors de la succession de 1481. Cette information ultérieure ne doit pas être transformée automatiquement en preuve de leur localisation exacte en 1435.

## Cour des Miracles

La Cour des Miracles est représentée par quatre présences collectives :

- Brujah ;
- Malkaviens ;
- Gangrels ;
- Nosferatus.

Ces quatre clans sont établis comme composants du contre-pouvoir. Aucun chef ni membre individuel de 1435 n'est actuellement assez sourcé pour être créé uniquement afin de remplir la faction.

Cette représentation collective permet aux prochaines versions de faire agir la faction sans produire de faux canon.

## Tremeres

Le corpus établit :

- l'arrivée de Goratrix à Paris en 1133 ;
- une implantation importante dans l'histoire parisienne ;
- un revers majeur au démantèlement du Temple en 1307.

Ces éléments prouvent une histoire parisienne ancienne, mais **pas une présence continue explicitement attestée en 1435**. Le collectif `collective_tremere_paris` reste donc `unverified`, avec une certitude moyenne et une politique `context_only`.

Aucun Magus nommé n'est créé et aucun `NpcState` Tremere n'est injecté tant qu'une source ne confirme pas la présence à la date exacte. Cette distinction évite de transformer une continuité plausible entre 1307 et le XVIe siècle en certitude historique.

## Gargouilles

Paris by Night indique qu'après l'arrivée de Goratrix, Paris conserva durablement quelques Gargouilles au service des Tremeres. Le registre accepte donc une présence **collective** sans transformer automatiquement Ferox, Ange ou un autre personnage connu d'une période différente en résident de 1435.

## Lasombra

La chronologie indique l'expulsion des Lasombra de la capitale en **1226**. En l'absence d'une réinstallation auditée avant 1435, le collectif `collective_lasombra_paris` est explicitement `absent` et `forbidden`.

Une absence explicite vaut mieux qu'un silence du roster : elle empêche une génération future de PNJ de réintroduire le clan par défaut.

## Puissances extérieures et historiques

Le registre sépare les acteurs présents des puissances capables d'influencer Paris à distance, et distingue aussi une influence historiquement attestée d'une activité personnelle démontrée précisément en 1435.

### Mithras

Puissance extérieure liée aux offensives contre Alexandre. Il reste `external/context_only` : il ne devient pas un résident parisien.

### Henri le Preux

Installé à Bourges et intégré au réseau français. Il reste un acteur nommé de simulation, mais son statut est `external` : les routines d'action locale de Paris ne doivent pas le traiter comme résident.

### Louis d'Orléans, Anne de Bourgogne, Henri d'Orléans

La chronologie documente leurs jeux d'influence autour de Paris à la fin du XIVe et au début du XVe siècle. Elle ne suffit pas à elle seule à établir pour chacun une présence personnelle continue ou une activité certaine pendant 1435.

Louis d'Orléans et Anne de Bourgogne sont donc conservés comme acteurs `historical/forbidden` lorsque l'audit prouve leur rôle passé sans établir leur activité exacte en 1435 ; Henri d'Orléans reste `unverified/forbidden`. Aucun clan n'est inventé lorsqu'il n'est pas établi par les sources déjà auditées.

## Personnages explicitement non injectés

Exemples :

- **Childeberd** : rôle important en 1148, survie et présence 1435 non établies ;
- **Hélène**, sire de Villon : lien de lignée établi, mais aucune résidence parisienne 1435 n'est déduite de ce seul lien ;
- **Ferox** : son existence médiévale ne suffit pas à prouver sa résidence parisienne en 1435.

## Conflit conservé : Pompignan

La fiche personnelle de Pompignan et la chronologie générale présentent une tension sur sa torpeur et son activité autour de la succession de 1481.

V0.48a ne choisit pas artificiellement une version : le conflit est enregistré dans `ROSTER_CONFLICTS` et reste visible dans le rapport QA.

## Lacunes encore ouvertes

Le rapport doit continuer à afficher au minimum :

- absence de noms Brujah spécifiquement établis pour la Cour des Miracles en 1435 ;
- absence de noms Malkaviens ;
- absence de noms Gangrels ;
- absence de noms Nosferatus ;
- présence et roster individuel Tremere 1435 non confirmés ;
- roster individuel Gargouille inconnu ;
- statut exact en 1435 des acteurs d'Orléans et de Bourgogne ;
- localisation exacte de certains Ventrue provinciaux autour de cette période.

Ces lacunes ne sont pas des bugs à masquer. Elles sont des limites documentaires à résoudre progressivement.

## Règle pour les développements suivants

V0.48b et les versions ultérieures doivent consommer cette distinction :

**acteur nommé confirmé → peut agir individuellement** ;

**collectif confirmé → peut influencer le monde comme faction/groupe** ;

**acteur extérieur → agit par relais, pression ou déplacement** ;

**incertain/absent/historique → aucune apparition automatique**.
