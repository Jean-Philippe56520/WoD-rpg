# Paris by Night — registre de référence

Paris by Night (`https://parisbynight.quelquesmots.fr/`) est une source récurrente majeure de WoD-rpg pour la continuité vampirique parisienne.

Le projet ne recopie pas le wiki. Il en extrait des faits structurés, les recoupe et enregistre leur provenance afin de construire un Paris 1435 cohérent puis une histoire divergente.

## Règle de provenance

- **A — officiel** : information issue d'une source WoD officielle identifiée ou signalée comme telle.
- **B — Paris by Night** : information de la continuité Paris by Night / Kaotic enrichie.
- **C — déduction WoD-rpg** : conclusion obtenue en croisant plusieurs faits compatibles.
- **D — création WoD-rpg** : création nécessaire au moteur ; elle ne doit jamais être présentée comme canon externe.

## Méthode obligatoire pour un personnage majeur

Avant d'intégrer ou de modifier un personnage parisien important :

1. lire sa fiche individuelle ;
2. contrôler sa lignée ;
3. contrôler la chronologie générale et les pages de règne concernées ;
4. contrôler les autres personnages qui le mentionnent ;
5. relever les éventuelles sources officielles citées ;
6. distinguer identité permanente et état à la date de jeu ;
7. consigner les contradictions au lieu de choisir silencieusement une version.

Un statut moderne ne doit jamais être projeté automatiquement vers 1435. Exemple : François Villon est Prince dans la continuité moderne, mais pas en 1435.

## Pages auditées pour V0.43

- Accueil / présentation du wiki
- Paris Vampire
- Chronologie
- Alexandre
- Alexandre au pouvoir
- François Villon
- Violetta
- Beatrix
- Magnerius de Sens
- Henri le Preux
- Pierre Emmanuel de Pompignan
- Lignées Ventrue
- Les principaux clans de l'an mil

## Faits 1435 actuellement retenus

### Alexandre

- Prince de Paris en 1435.
- Ancien Ventrue et centre du pouvoir princier.
- Son règne est déjà ancien et ses équilibres politiques sont sous pression.
- Sa destruction de 1481 appartient à la chronologie de référence, mais WoD-rpg la traite comme un futur possible, pas comme un événement forcé.

### Saviarre

- Compagne/conseillère ancienne d'Alexandre dans la continuité parisienne.
- Utilisée comme relation structurante du pouvoir princier, sans inventer des chiffres de fiche absents de l'audit.

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

### Beatrix

- Toréador ancienne et figure politique majeure de Paris.
- La V0.43 l'intègre comme force de clan et rivale potentielle au sein des futurs équilibres, sans lui attribuer prématurément le règne post-1481.

### Ventrue anciens

Magnerius de Sens, Henri le Preux et Pierre Emmanuel de Pompignan appartiennent au réseau historique utilisé par Paris by Night autour du pouvoir d'Alexandre. Leur état 1435 est intégré avec prudence : les chronologies personnelles et générales doivent rester arbitrables lorsqu'elles divergent.

## Canon divergent

Les événements postérieurs au début de partie servent de **pression historique** et de **réservoir de futurs possibles**.

Ils ne doivent pas être implémentés sous forme de scripts du type :

```python
if year == 1481:
    kill_alexandre()
```

Le moteur doit plutôt conserver des conditions : stabilité du pouvoir, relations, antagonismes, factions, dettes, domaines, influence, agitation anarch, etc. Une partie peut donc converger vers un événement proche du canon ou diverger fortement.

## Principe de développement

À chaque évolution liée à Paris, ses lignées, personnages, offices, factions ou événements historiques, revenir à ce registre et au wiki avant de coder. Paris by Night est une source permanente du projet, pas une consultation ponctuelle de V0.43.
