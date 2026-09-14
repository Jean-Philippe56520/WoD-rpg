# WoD RPG - prototype politique

Prototype personnel d'un jeu politique vampirique asynchrone et persistant en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.4

Le prototype reste volontairement limite a trois clans : **Brujah, Toreador et Ventrue**.

La V0.4 remplace le modele fixe "courant principal + opposition" par des **courants ideologiques dynamiques**.

Chaque vampire possede desormais :

- Humanite V5 (0 a 10) ;
- Humanisme politique (-100 a +100) ;
- Tradition politique (-100 a +100) ;
- influence personnelle ;
- loyaute et ambition.

Les axes Humanisme / Tradition produisent jusqu'a quatre courants par clan :

- Humanistes traditionnels ;
- Reformateurs humanistes ;
- Traditionalistes predateurs ;
- Radicaux predateurs.

Principes implementes :

- le courant d'un vampire est derive automatiquement de ses axes ;
- un vampire peut changer de courant si son evolution traverse un axe ;
- l'influence d'un courant est la somme de l'influence de ses membres ;
- chaque courant possede un chef derive de ses membres ;
- les proximites ideologiques produisent bonus ou malus dans le soutien et la diplomatie ;
- le courant du Primogene soutient toujours son representant ;
- chaque autre courant decide separement de le soutenir ou de faire dissidence ;
- chaque courant dissident peut avoir son propre Primogene allie exterieur ;
- en dissidence, 50 % de son influence reste avec le Primogene du clan et 50 % renforce son allie ;
- Prince, successions, capital politique et Etreintes continuent de fonctionner sur ce nouveau modele.

## Architecture

- `game/ideology.py` : axes, quadrants, courants derives et affinites ;
- `game/politics.py` : soutien courant par courant et vote de Praxis ;
- `game/offices.py` : Prince, Primogenes et successions ;
- `game/embrace.py` : demandes d'Etreinte et consequences ;
- `game/actions.py` : actions politiques et diplomatie ;
- `game/resolution.py` : resolution des nuits ;
- `game/config.py` : valeurs configurables ;
- `game/world.py` : etat initial ;
- `app.py` : interface Streamlit ;
- `tests/` : tests automatises.

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

1. relations personnelles et faveurs ;
2. evolution ideologique par evenements et consequences ;
3. persistance distante des parties et comptes joueurs ;
4. Etreintes clandestines et consequences ;
5. territoires, institutions, Mascarade et factions PNJ ;
6. Elysium et diplomatie persistante.
