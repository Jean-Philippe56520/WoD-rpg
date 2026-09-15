# Paris — corpus historique et graphe temporel

Ce document suit la **couverture du corpus**, pas seulement les faits déjà utilisés par le moteur.

Objectif : éviter qu'une page, une période, une famille de données ou une contradiction importante soit oubliée lors du développement de la Chronique.

## Règles

1. **Une page connue n'est pas forcément auditée.**
2. **Un fait sourcé n'est pas une valeur de simulation.** Les scores d'influence, loyauté, agressivité, agendas et relations chiffrées restent des créations WoD-rpg.
3. **La provenance s'attache au fait**, pas au personnage entier.
4. **Tout fait historique est temporel** dès qu'il peut changer avec les siècles.
5. **Une contradiction est conservée**, avec l'interprétation retenue par le moteur documentée séparément.
6. **Les pages modernes sont bloquées pour 1435** tant qu'une continuité historique n'est pas explicitement établie.
7. **Un acteur incertain n'est pas injecté** dans la simulation comme une certitude.
8. Le wiki est une source de continuité et d'indexation ; il n'est jamais recopié intégralement dans le dépôt.
9. **Une famille de données importante doit rester visible même si aucune page n'est encore complètement auditée.**

## États d'audit des sources

| État | Sens |
|---|---|
| `audited` | page lue pour les faits actuellement utilisés |
| `partial` | page consultée, mais certaines informations restent à extraire/recouper |
| `indexed` | page connue et enregistrée, audit détaillé restant à faire |
| `linked_unverified` | ressource repérée par les index/liens du site, contenu à vérifier explicitement |

Le registre machine des sources est `game/lore_catalog.py`.

## Contrat de couverture V0.47d

Paris by Night possède un sommaire maître, **Paris Vampire**, qui expose beaucoup plus que des fiches de PNJ : histoire, clans, Anarchs/Sabbat, institutions, Cour, Domaines, coteries, secrets, autres créatures et une série de notes de campagne (lignées, chronologies, présence des PNJ, Prestations, liens de Sang, influences, incidents, cartes, soleil, etc.).

Le site indique lui-même dans sa liste de tâches que plusieurs de ces ensembles sont encore incomplets. WoD-rpg ne doit donc jamais assimiler « indexé dans Paris by Night » à « canon complet et vérifié ».

`game/paris_coverage.py` transforme ce sommaire en **contrat de couverture obligatoire**. Chaque famille possède :

- un identifiant stable ;
- un ou plusieurs ancrages de source ;
- une priorité spécifique pour 1435 ;
- un état de couverture `structured`, `partial`, `indexed` ou `missing` ;
- la partie du moteur qu'elle doit alimenter ;
- un garde-fou lorsque les données disponibles sont surtout modernes.

La CI verrouille la liste des familles obligatoires. Supprimer accidentellement, par exemple, les **liens de Sang**, la **chronologie de présence des PNJ** ou les **puissances extérieures** devient un échec de test.

### Familles obligatoires

Le contrat suit actuellement :

- histoire générale et chronologie vampirique ;
- contexte et chronologie mortels ;
- personnages ;
- lignées ;
- clans et groupes de sang ;
- présence/localisation/torpeur/disparition ;
- Anarchs et contre-pouvoirs ;
- Sabbat et héritages associés ;
- naissance de la Camarilla ;
- offices et exercice du pouvoir ;
- Praxis et succession ;
- factions, coteries et salons ;
- alliances, rivalités et patronages ;
- Prestations et dettes ;
- liens de Sang ;
- influences mortelles ;
- Domaines, fiefs et droits de chasse ;
- géographie historique et lieux ;
- Cour, Elysium et usages ;
- secrets, rumeurs et désinformation ;
- événements, incidents et crises ;
- puissances extérieures ;
- autres créatures du Monde des Ténèbres ;
- chronologies individuelles ;
- chronologies des offices ;
- chronologie de présence des PNJ ;
- soleil, saisons et contraintes calendaires ;
- amorces et matière de scénario.

`structured` ne signifie pas « toutes les données historiques sont connues ». Cela signifie que **le moteur sait déjà où cette famille doit vivre et qu'un premier corpus utilisable existe**. `partial` et `indexed` sont volontairement conservés tant que l'audit n'est pas suffisant.

## Photographie de départ : Paris 1435

### Confirmés ou fortement étayés

- **Alexandre** : Prince de Paris, Ventrue ancien.
- **Saviarre** : Ventrue, infante/conseillère ancienne d'Alexandre ; son ancienne valeur `clan=unknown` a été supprimée.
- **Béatrix** : figure toréador majeure.
- **François Villon** : Toréador ancien, pas Prince en 1435.
- **Violetta** : infante de Villon ; sa présence 1435 est retenue avec une certitude plus faible que celle d'Alexandre ou Béatrix.
- **Magnerius de Sens** : ancien Ventrue du réseau d'Alexandre.
- **Pierre Emmanuel de Pompignan** : ancien Ventrue du réseau d'Alexandre.
- **Henri le Preux** : acteur extérieur installé à Bourges en 1435, pas acteur physiquement présent à Paris.
- **Mithras** : puissance extérieure exerçant une pression sur Paris, pas résident parisien.

### Factions structurantes

#### Cour fidèle d'Alexandre

Réseau de pouvoir autour du Prince, notamment Alexandre, Saviarre, Magnerius et Pompignan dans le seed actuel.

#### Réseaux toréador

Béatrix, Villon et Violetta constituent le noyau actuellement modélisé.

#### Cour des Miracles

Paris by Night décrit pendant la crise de la Cour une puissance parallèle rassemblant :

- Brujah ;
- Malkaviens ;
- Gangrels ;
- Nosferatus.

Ces quatre clans sont maintenant enregistrés dans le corpus et le seed de faction. **Aucun dirigeant nommé n'est inventé** tant que l'audit ne l'établit pas.

### Acteurs connus mais non injectés faute de preuve 1435 suffisante

#### Childeberd

Son rôle auprès d'Alexandre au XIIe siècle est documenté, mais sa survie et sa présence effective à Paris en 1435 ne le sont pas encore suffisamment. Il reste donc dans le corpus historique, pas dans le roster actif.

#### Tremeres de Paris

Le corpus enregistre leur implantation ancienne et le revers majeur lié au démantèlement du Temple en 1307. Le roster précis, la Fondation, les survivants et leur influence en **1435** restent à auditer. Aucune présence individuelle n'est inventée.

## Contradictions ouvertes

### Violetta — date de la fonction de Justicar

Deux affirmations sont conservées :

- la continuité Paris by Night place sa désignation dans le contexte de la mise en place de la Camarilla ;
- sa fiche cite *Giovanni Chronicles II* et *III* pour une élection en **1666**.

WoD-rpg retient actuellement **1666** pour l'état de simulation, tout en conservant la version Paris by Night comme claim contradictoire.

### Institutionnalisation de la Camarilla

Le corpus conserve séparément :

- **1435** : annonce/fondation ;
- **1444** : mise en place effective dans la chronologie Paris by Night ;
- **1486** : consolidation/conclave transrégional retenu par le modèle d'ère WoD-rpg après audit des références ;
- **1493** : Convention des Épines et étape institutionnelle majeure.

Le moteur ne transforme donc pas Paris 1435 en Cour de Camarilla moderne.

## Données modernes interdites en rétroprojection

Les ressources suivantes sont utiles pour la mécanique future mais ne doivent pas être appliquées directement à 1435 :

- Us et coutumes de Paris ;
- liste moderne des Prestations/dettes ;
- liste moderne des liens de Sang ;
- liste moderne des influences ;
- salons/coteries modernes ;
- organisation moderne du pouvoir ;
- Bourgmestres et Bourgs modernes ;
- Archontes ;
- secrets et idées de scénarios modernes.

Elles peuvent inspirer des **types de données** ou servir lorsque la Chronique atteint leur période, jamais justifier seules l'état médiéval.

## Priorités d'audit restantes

### Priorité 1 — 1435 immédiat

- identifier les dirigeants/membres nommés de la Cour des Miracles s'ils sont réellement sourcés ;
- établir le statut exact des Brujah parisiens en 1435 ;
- établir le statut exact des Tremeres en 1435 après 1307 ;
- recenser les Nosferatus, Malkaviens et Gangrels réellement présents ;
- recenser les puissances extérieures actives sur Paris : Angleterre/Mithras, Bourgogne, Orléans, Normandie, Bourges ;
- consolider les lieux/refuges/fiefs réellement valides au XVe siècle ;
- recenser les relations, Prestations et éventuels liens de Sang explicitement attestés à cette date ;
- exploiter la chronologie de présence des PNJ pour sécuriser les futures ellipses.

### Priorité 2 — chronologie longue

- succession après Alexandre ;
- règne de Béatrix ;
- règne de Villon ;
- évolution des offices ;
- lignées actives/disparues ;
- changements de Domaines ;
- événements de la Camarilla, Révolte Anarch et Sabbat ;
- dates d'apparition des institutions et coutumes modernes.

### Priorité 3 — matière pour le moteur émergent

- informations connues/publiques/secrètes ;
- sources et fiabilité des rumeurs ;
- objectifs historiques des factions ;
- dettes et liens structurants ;
- réseaux d'influence mortelle ;
- événements pouvant devenir des pressions conditionnelles plutôt que des scripts.

## Sortie QA

`scripts/lore_audit_report.py` produit désormais un rapport JSON de schéma V2 indiquant notamment :

- nombre de sources cataloguées ;
- nombre audité / partiel / indexé / non vérifié ;
- couverture pertinente pour 1435 ;
- **nombre de familles de données obligatoires** ;
- nombre de familles `structured`, `partial`, `indexed` et `missing` ;
- **liste nominative des familles prioritaires 1435 encore incomplètes** ;
- nombre d'entités et de faits ;
- contradictions ouvertes ;
- présences confirmées ou externes ;
- présences encore non vérifiées ;
- factions structurées.

Ce rapport est exécuté dans la CI : **une zone non auditée reste visible au lieu de disparaître dans les notes de développement**, et une famille importante ne peut plus être supprimée silencieusement du périmètre.
