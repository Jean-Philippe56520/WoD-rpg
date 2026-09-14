# WoD RPG — prototype politique

Prototype personnel d'un jeu politique vampirique asynchrone et persistant, développé en Python + Streamlit.

Application stable : https://wod-rpg.streamlit.app

## V0.2

Le prototype reste volontairement limité à **Brujah, Toreador et Ventrue**.

Chaque joueur dirige un clan mais incarne directement son **Primogène**. Les oppositions internes sont semi-autonomes : leur soutien dépend de leur loyauté politique et leur allié extérieur est conservé d'une nuit à l'autre.

### Boucle actuelle

- 2 actions politiques par clan et par nuit ;
- consolidation du courant du Primogène ;
- ralliement de l'opposition ;
- développement de l'influence ;
- diplomatie entre clans ;
- résolution autonome du soutien des oppositions ;
- règle de dissidence 50/50 ;
- vote des Primogènes pour la Praxis ;
- majorité stricte nécessaire pour reconnaître une Praxis ;
- perte de stabilité et de Mascarade en cas de Praxis contestée ;
- journal des événements ;
- état conservé pendant la session Streamlit.

Prince et Primogène restent deux fonctions incompatibles. Si un Primogène obtient une majorité de reconnaissance pour la Praxis, le moteur place la ville en **transition** : la succession de son siège devra être résolue avant son accession au titre de Prince.

## Règle de dissidence

Si l'opposition soutient son Primogène, toute l'influence du clan soutient son vote.

Si elle refuse :

- 50 % de l'influence du courant d'opposition reste avec le Primogène ;
- 50 % renforce le poids du vote d'un Primogène allié choisi préalablement par le chef d'opposition ;
- cette influence suit le choix de vote du Primogène allié.

Les valeurs sont centralisées dans `game/config.py`.

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

- `app.py` : interface Streamlit ;
- `game/models.py` : modèles de domaine ;
- `game/config.py` : paramètres configurables ;
- `game/actions.py` : actions politiques ;
- `game/politics.py` : oppositions et vote de Praxis ;
- `game/resolution.py` : résolution d'une nuit ;
- `game/world.py` : état initial ;
- `tests/` : tests automatisés.

Les règles restent indépendantes de Streamlit. GitHub contient le code, pas les sauvegardes vivantes.

## Suite prévue

1. succession d'un Primogène qui accède à la Praxis ;
2. Prince, autorité et capital politique ;
3. autorisations d'Étreinte ;
4. faveurs et relations plus riches ;
5. persistance multijoueur distante ;
6. territoires, Mascarade avancée et factions PNJ.
