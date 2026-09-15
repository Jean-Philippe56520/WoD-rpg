# Paris by Night — registre de référence

Paris by Night (`https://parisbynight.quelquesmots.fr/`) est une source récurrente majeure de WoD-rpg pour la continuité vampirique parisienne.

Le projet ne recopie pas le wiki. Il en extrait des faits structurés, les recoupe et enregistre leur provenance afin de construire un Paris 1435 cohérent puis une histoire divergente.

Le suivi de couverture du corpus se trouve dans `docs/lore/PARIS_CORPUS.md`. Le registre machine des sources se trouve dans `game/lore_catalog.py` et les faits temporels dans `game/paris_corpus.py`.

## Règle de provenance

- **A — officiel** : information issue d'une source WoD officielle identifiée ou signalée comme telle.
- **B — Paris by Night** : information de la continuité Paris by Night / Kaotic enrichie.
- **C — déduction WoD-rpg** : conclusion obtenue en croisant plusieurs faits compatibles.
- **D — création WoD-rpg** : création nécessaire au moteur ; elle ne doit jamais être présentée comme canon externe.

Depuis V0.47a, ce niveau s'applique **au fait**, pas au personnage entier. Un PNJ peut donc avoir un clan ou une date d'Étreinte sourcés, alors que son score d'influence, son agressivité ou son objectif actuel restent des données de simulation WoD-rpg.

## États d'audit des sources

- `audited` : source lue pour les faits actuellement utilisés ;
- `partial` : source consultée mais extraction/recoupement encore incomplet ;
- `indexed` : source connue et cataloguée, audit détaillé restant à faire ;
- `linked_unverified` : ressource repérée par l'index ou les liens du site, contenu à contrôler explicitement.

Une page connue n'est donc plus confondue avec une page déjà auditée.

## Méthode obligatoire pour un personnage majeur

Avant d'intégrer ou de modifier un personnage parisien important :

1. lire sa fiche individuelle ;
2. contrôler sa lignée ;
3. contrôler la chronologie générale et les pages de règne concernées ;
4. contrôler les autres personnages qui le mentionnent ;
5. relever les éventuelles sources officielles citées ;
6. distinguer identité permanente et état à la date de jeu ;
7. consigner les contradictions au lieu de choisir silencieusement une version ;
8. enregistrer chaque fait avec sa propre provenance et, si nécessaire, sa période de validité ;
9. ne pas injecter un acteur dans le roster actif lorsque sa présence à la date de jeu reste incertaine.

Un statut moderne ne doit jamais être projeté automatiquement vers 1435. Exemple : François Villon est Prince dans la continuité moderne, mais pas en 1435.

## Architecture V0.47a

### Catalogue des sources

`game/lore_catalog.py` conserve pour chaque ressource :

- identifiant stable ;
- titre et URL ;
- niveau de provenance ;
- catégories couvertes ;
- périodes concernées ;
- état d'audit ;
- période de pertinence lorsque nécessaire ;
- références officielles citées lorsqu'elles sont identifiées.

### Faits temporels

`game/paris_corpus.py` sépare :

- l'entité (`LoreEntity`) ;
- le fait (`LoreFact`) ;
- la période de validité ;
- la certitude ;
- les sources ;
- les contradictions ;
- la présence/localisation en 1435.

Les valeurs de simulation ne sont pas des `LoreFact` : loyauté, agressivité, influence chiffrée, agenda, objectif court terme et relations numériques restent dans le seed mécanique.

### Contradictions

Une contradiction possède son propre enregistrement. WoD-rpg peut définir une interprétation préférée pour le moteur, mais les autres claims restent conservés avec leur provenance.

Deux conflits sont désormais explicitement suivis :

- la date de l'accession de Violetta à la fonction de Justicar ;
- le rythme d'institutionnalisation de la Camarilla entre l'annonce de 1435, la mise en place donnée par Paris by Night en 1444, la consolidation transrégionale utilisée par le modèle WoD-rpg en 1486 et la Convention des Épines de 1493.

## Pages structurées dans le catalogue V0.47a

Le manifeste couvre désormais notamment :

- Paris Vampire ;
- Chronologie ;
- Alexandre / Alexandre au pouvoir ;
- Beatrix / Beatrix au pouvoir ;
- François Villon / Villon au pouvoir ;
- Violetta ;
- Magnerius de Sens ;
- Henri le Preux ;
- Pierre Emmanuel de Pompignan ;
- Lignées Ventrue ;
- Les principaux clans de l'an mil ;
- Paris Tremere ;
- Paris Gargouille ;
- Us et coutumes de Paris ;
- Secrets ;
- Dettes et Prestations ;
- liens de Sang ;
- influences ;
- salons ;
- exercice du pouvoir ;
- Archontes ;
- idées de scénarios.

Toutes ne sont pas considérées comme intégralement auditées. Leur état est volontairement visible dans le catalogue et dans le rapport QA.

## Faits 1435 actuellement retenus

### Alexandre

- Prince de Paris en 1435.
- Ventrue ancien et centre du pouvoir princier.
- Son règne est déjà ancien et ses équilibres politiques sont sous pression.
- Sa destruction de 1481 appartient à la chronologie de référence, mais WoD-rpg la traite comme un futur possible, pas comme un événement forcé.

### Saviarre

- Ventrue.
- Infante d'Alexandre dans la lignée recensée.
- Étreinte en 481 dans cette continuité.
- Conseillère ancienne et relation structurante du pouvoir princier.

La valeur historique `clan_id="unknown"` du seed V0.43 est donc corrigée en V0.47a.

### François Villon

- Toréador.
- Né en 1197 dans la continuité Paris by Night.
- Étreint en 1230 par Hélène.
- 5e génération selon sa fiche.
- A déjà Étreint Violetta en 1250.
- Est donc déjà un vampire ancien en 1435 et ne doit pas être confondu avec la chronologie du poète historique du XVe siècle.
- N'est pas Prince de Paris en 1435.

### Violetta

- Infante de François Villon, Étreinte en 1250.
- Son statut futur de Justicar ne doit pas être appliqué à 1435.
- La divergence documentaire sur la date de cette fonction est conservée dans le registre des contradictions.

### Beatrix

- Toréador ancienne et figure politique majeure de Paris.
- La simulation l'intègre comme force de clan et rivale potentielle au sein des futurs équilibres, sans lui attribuer prématurément le règne post-1481.

### Ventrue anciens

Magnerius de Sens, Henri le Preux et Pierre Emmanuel de Pompignan appartiennent au réseau historique utilisé par Paris by Night autour du pouvoir d'Alexandre.

Henri le Preux est localisé à Bourges en 1435 ; il peut influencer Paris mais ne doit pas agir comme s'il se trouvait physiquement à la Cour parisienne.

### Cour des Miracles

Paris by Night décrit pendant la crise parisienne une puissance parallèle composée de :

- Brujah ;
- Malkaviens ;
- Gangrels ;
- Nosferatus.

Ces quatre clans sont désormais enregistrés dans la faction. Aucun dirigeant ou membre nommé n'est inventé tant que l'audit ne le confirme pas.

### Childeberd et les Tremeres

Le rôle historique de Childeberd auprès d'Alexandre au XIIe siècle est enregistré, mais sa présence en 1435 reste non vérifiée.

L'implantation historique des Tremeres à Paris et leur revers de 1307 sont également enregistrés, mais leur roster précis en 1435 reste à auditer.

Ces éléments existent donc dans le corpus **sans être injectés comme certitudes dans le monde actif**.

## Données modernes

Les pages modernes — Prestations, influences, liens de Sang, salons, structures de pouvoir, secrets, etc. — sont utiles pour le modèle de données et pour les périodes futures.

Elles ne doivent jamais être rétroprojetées directement vers 1435. Les dates `relevant_from` du catalogue servent de **garde-fous de moteur**, pas de déclaration selon laquelle la notion n'existait pas auparavant.

## Canon divergent

Les événements postérieurs au début de partie servent de **pression historique** et de **réservoir de futurs possibles**.

Ils ne doivent pas être implémentés sous forme de scripts du type :

```python
if year == 1481:
    kill_alexandre()
```

Le moteur doit plutôt conserver des conditions : stabilité du pouvoir, relations, antagonismes, factions, dettes, Domaines, influence, agitation anarch, etc. Une partie peut donc converger vers un événement proche du canon ou diverger fortement.

## QA de complétude

`scripts/lore_audit_report.py` produit un état mesurable du corpus : sources totales, sources auditées/partielles/indexées, couverture 1435, nombre de faits, contradictions, présences confirmées et présences encore non vérifiées.

L'objectif n'est pas d'obtenir artificiellement 100 % en inventant des données, mais de rendre les trous **visibles et traçables**.

## Principe de développement

À chaque évolution liée à Paris, ses lignées, personnages, offices, factions ou événements historiques, revenir à ce registre et au wiki avant de coder. Paris by Night est une source permanente du projet, pas une consultation ponctuelle.
