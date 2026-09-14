# WoD RPG - prototype politique

Prototype personnel d'un jeu politique vampirique asynchrone et persistant en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.3

Le prototype reste volontairement limite a trois clans : **Brujah, Toreador et Ventrue**.

Principes implementes :

- le joueur represente un clan et incarne son Primogene ;
- chaque clan possede un courant principal et une opposition semi-autonome ;
- une opposition dissidente conserve 50 % de son influence avec son Primogene et transfere 50 % au vote d'un Primogene allie prealablement choisi ;
- une majorite politique stricte est necessaire pour faire reconnaitre une Praxis ;
- un candidat Prince n'est pas oblige d'etre Primogene ;
- Prince et Primogene ne peuvent jamais etre la meme fonction ;
- si un Primogene devient Prince, une succession interne designe automatiquement un nouveau Primogene ;
- les membres importants du clan possedent influence, Humanite, loyaute et ambition ;
- le Prince dispose d'un capital politique ;
- les vampires peuvent demander l'autorisation d'Etreindre ;
- le cout varie selon le clan du Prince, le courant du demandeur et la position du Primogene ;
- autorisations et refus ont des consequences politiques ;
- le monde avance par cycles de nuit et conserve un journal d'evenements pendant la session Streamlit.

## Architecture

- `game/models.py` : modeles de domaine.
- `game/politics.py` : vote de Praxis et dissidence.
- `game/offices.py` : Prince, Primogenes et successions.
- `game/embrace.py` : demandes d'Etreinte, couts et decisions.
- `game/actions.py` : actions politiques de nuit.
- `game/resolution.py` : resolution des nuits.
- `game/config.py` : valeurs configurables.
- `game/world.py` : etat initial du prototype.
- `app.py` : interface Streamlit.
- `tests/` : tests du moteur.

GitHub contient le code et les contenus statiques, jamais les sauvegardes dynamiques des parties.

## Lancer localement

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Tests

```bash
pytest -q
```

## Suite cible

1. relations et faveurs plus riches ;
2. persistance distante des parties et comptes joueurs ;
3. autorisations clandestines et consequences ;
4. territoires et institutions ;
5. Mascarade, crises et factions PNJ ;
6. Elysium et diplomatie persistante.
