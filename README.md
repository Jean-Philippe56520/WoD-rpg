# WoD RPG — prototype politique

Prototype personnel d'un jeu politique vampirique asynchrone et persistant, développé en Python + Streamlit.

## V0.1

Le prototype se concentre volontairement sur trois clans : **Brujah, Toreador et Ventrue**.

Chaque joueur dirige son clan mais incarne directement son **Primogène**. Chaque clan possède un courant dominant et un courant d'opposition.

Règle centrale actuelle :

- le Primogène vote au Conseil pour un candidat à la Praxis ;
- si l'opposition soutient son Primogène, toute l'influence du clan porte son vote ;
- si elle refuse de le soutenir, 50 % de l'influence du courant d'opposition reste dans le poids du vote du Primogène ;
- les 50 % restants renforcent le poids du vote d'un **Primogène allié**, choisi par le chef de l'opposition ;
- l'influence transférée suit donc le choix de vote de ce Primogène allié ;
- un candidat au titre de Prince n'est pas obligé d'être Primogène ;
- Prince et Primogène sont des fonctions distinctes : si un Primogène devient Prince, son siège doit devenir vacant.

## Lancer localement

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pytest -q
```

## Architecture

- `app.py` : interface Streamlit uniquement.
- `game/models.py` : modèles de domaine.
- `game/politics.py` : règles politiques et résolution du vote.
- `game/world.py` : état initial du prototype.
- `tests/` : tests du moteur.

Les règles de jeu doivent rester indépendantes de Streamlit afin de permettre une évolution ultérieure vers une architecture plus robuste et une base persistante distante.

## Prochaines étapes

1. Persistance des parties et comptes joueurs.
2. Cycle de nuits et actions asynchrones.
3. Relations, faveurs et influence interne des courants.
4. Élection/contestation du Prince et stabilité de la Camarilla.
5. Autorisations d'Étreinte et coût politique du Prince.
6. Succession d'un Primogène devenu Prince.
7. Elysium et diplomatie persistante.

> Le dépôt contient le moteur et le prototype technique. Les règles et contenus inspirés de *Vampire: The Masquerade* restent à traiter selon les conditions applicables aux créations de fans si le projet est distribué publiquement.
