# WoD RPG - prototype politique multijoueur

Jeu politique vampirique persistant et principalement asynchrone, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.5

Le MVP reste limité à **Brujah, Toreador et Ventrue**.

### Partie multijoueur asynchrone

- un joueur contrôle un seul clan ;
- le joueur incarne le Primogène actuel de ce clan ;
- sa session charge son clan en détail, mais seulement les informations publiques des autres clans ;
- chaque joueur prépare ses choix puis clique sur **Valider ma nuit** ;
- les ordres soumis deviennent persistants et ne sont plus modifiables pour cette nuit ;
- aucune action n'est résolue immédiatement ;
- la nuit globale est résolue automatiquement lorsque les trois clans ont soumis leurs ordres ;
- le verrou `RESOLVING` empêche qu'une même nuit soit résolue deux fois ;
- chaque clan reçoit ensuite son propre rapport selon les événements qu'il pouvait connaître ;
- la nuit suivante s'ouvre automatiquement.

L'Elysium est indépendant de ce cycle : un joueur qui a déjà validé ses ordres peut toujours discuter avec les autres joueurs.

### Politique

Le moteur conserve les systèmes précédents :

- Praxis et vote pondéré des Primogènes ;
- Prince et Primogène incompatibles ;
- succession automatique d'un Primogène devenu Prince ;
- axes politiques Humanisme / Tradition ;
- jusqu'à quatre courants idéologiques dynamiques par clan ;
- influence des courants dérivée de leurs membres ;
- dissidence 50/50 courant par courant ;
- affinité idéologique ;
- capital politique du Prince ;
- autorisations d'Étreinte.

Une demande au Prince est désormais portée officiellement par le **Primogène**, au nom d'un membre précis de son clan.

## Persistance

La couche métier ne dépend pas de Streamlit.

`game/persistence.py` définit une interface de dépôt et fournit actuellement `SQLiteGameRepository` pour le développement et les tests multijoueurs.

SQLite n'est **jamais commité dans Git**. Le fichier est ignoré par `.gitignore`.

Sur Streamlit Cloud, SQLite permet de partager l'état entre sessions tant que l'instance conserve son disque, mais ce stockage n'est pas garanti après un redéploiement ou un redémarrage. La persistance durable cible PostgreSQL / Supabase. Le schéma préparatoire se trouve dans `supabase/schema.sql`.

## Architecture

- `game/models.py` : modèles de domaine ;
- `game/ideology.py` : axes et courants dynamiques ;
- `game/politics.py` : dissidences et vote de Praxis ;
- `game/actions.py` : actions politiques ;
- `game/offices.py` : Prince, Primogènes et successions ;
- `game/embrace.py` : demandes d'Étreinte et décisions du Prince ;
- `game/resolution.py` : résolution globale d'une nuit ;
- `game/serialization.py` : sérialisation JSON stable ;
- `game/persistence.py` : stockage des parties, ordres, rapports et Elysium ;
- `game/multiplayer.py` : orchestration asynchrone joueur/clan/nuit ;
- `game/world.py` : monde initial ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatisés.

## Tests

```bash
pytest -q
```

## Suite cible

1. brancher la persistance distante PostgreSQL/Supabase ;
2. authentification réelle des joueurs ;
3. déclarations de candidatures à la Praxis ;
4. demandes internes autonomes des membres au Primogène ;
5. événements et informations avec brouillard de guerre plus fin ;
6. relations, faveurs et dettes ;
7. territoires, institutions et Mascarade avancée.
