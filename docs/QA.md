# Environnement QA Streamlit

L'environnement QA sert à tester le vrai gameplay de la Chronique sans toucher à Supabase ni aux sauvegardes de production.

## Entrée Streamlit

```bash
streamlit run qa_app.py
```

`qa_app.py` utilise exclusivement `EditableSQLiteGameRepository`. Il ne lit ni n'écrit dans Supabase, même si des secrets de production sont présents dans l'environnement.

Chaque scénario possède sa propre base SQLite sous `data/qa/` par défaut. Le dossier peut être redirigé avec `WOD_QA_DATA_DIR`.

## Scénarios fournis

- `first_night` : première nuit Toréador nominale ;
- `high_hunger` : Brujah à Faim 4, chasse prioritaire ;
- `trusted_sire` : relation très favorable avec le sire ;
- `hostile_sire` : relation hostile avec griefs persistants ;
- `release_candidate` : émancipation disponible ;
- `convergence_ready` : fin de segment et convergence ;
- `prestation_due` : Prestation majeure due au PJ par son sire.

Le bouton **Réinitialiser ce scénario** supprime uniquement la base SQLite QA sélectionnée et reconstruit son état déterministe.

## Tests headless

`tests/test_qa_streamlit_harness.py` utilise `streamlit.testing.v1.AppTest` pour exécuter l'application sans navigateur et manipuler ses widgets.

Les tests vérifient notamment :

- démarrage de chaque scénario sans exception Streamlit ;
- Alexandre comme Prince du seed Paris 1435 ;
- priorité de la chasse à Faim élevée ;
- apparition de la situation d'émancipation ;
- résolution réelle d'une situation via le formulaire Streamlit ;
- mémoire relationnelle après interaction ;
- conséquences d'une relation favorable ou hostile sur la difficulté ;
- présence des Prestations ;
- convergence et passage au segment suivant ;
- reset reproductible du scénario.

## CI

GitHub Actions sépare désormais :

1. tests moteur/domaine ;
2. tests gameplay Streamlit headless ;
3. génération d'un rapport JSON des scénarios.

Chaque run produit l'artifact `wod-rpg-qa-report` avec :

- `qa-results.xml` : résultats des tests AppTest ;
- `qa-report.json` : snapshots déterministes des scénarios.

Ce rapport est destiné à permettre une inspection automatique et reproductible après chaque modification importante du gameplay.

## Règle de sécurité

Le harness QA ne doit jamais être modifié pour utiliser le repository Supabase de production. Un test qui nécessite Supabase doit utiliser un projet de test explicitement séparé ; aucun scénario QA actuel n'en dépend.
