from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SystemeV5:
    id: str
    nom: str
    statut: str
    cible: str
    fichiers: tuple[str, ...]
    note: str


STATUTS_V5 = {"intégré", "partiel", "différé", "écarté"}


SYSTEMES_V5: tuple[SystemeV5, ...] = (
    SystemeV5("resolution", "Attribut + Compétence, D10, réussites sur 6+", "intégré", "conserver", ("game/dice.py", "game/situations.py"), "Socle de résolution de la Chronique."),
    SystemeV5("difficulte", "Difficulté", "intégré", "adapter", ("game/dice.py", "game/situations.py"), "Le seuil exact reste caché ; le joueur reçoit un indice narratif."),
    SystemeV5("faim", "Faim et dés de Faim", "intégré", "conserver", ("game/dice.py", "game/chronicle.py"), "Les dés de Faim remplacent des dés ordinaires dans le groupement."),
    SystemeV5("critiques", "Critiques, réussite bestiale et échec bestial", "intégré", "conserver", ("game/dice.py", "game/consequences.py"), "Les conséquences persistantes sont graduées autour du résultat V5."),
    SystemeV5("volonte", "Volonté", "intégré", "simplifier", ("game/vampire_profile.py", "game/night_cycle.py"), "Relance de dés ordinaires, usure et récupération adaptées au rythme asynchrone."),
    SystemeV5("exaltation", "Test d’Exaltation", "intégré", "conserver", ("game/dice.py", "game/night_cycle.py"), "Utilisé pour le Coup de Sang et destiné aux pouvoirs qui le requièrent."),
    SystemeV5("coup_de_sang", "Coup de Sang", "intégré", "conserver", ("game/mecaniques_vampiriques.py",), "Bonus selon la Puissance du Sang."),
    SystemeV5("generation", "Génération", "intégré", "conserver", ("game/vampire_profile.py",), "Déduite du sire lors de la création."),
    SystemeV5("puissance_sang", "Puissance du Sang", "partiel", "compléter", ("game/vampire_profile.py", "game/mecaniques_vampiriques.py"), "Le Coup de Sang est géré ; restent notamment guérison, contraintes alimentaires et bonus de pouvoirs."),
    SystemeV5("sante", "Santé", "différé", "prioritaire", (), "La piste de Santé et les dégâts superficiels/aggravés doivent être ajoutés avant le combat physique avancé."),
    SystemeV5("humanite", "Humanité, Flétrissures et Remords", "partiel", "prioritaire", ("game/chronicle.py", "game/creation_rules.py"), "Humanité et Convictions existent ; Flétrissures et Remords ne sont pas encore structurés."),
    SystemeV5("frenesie", "Frénésie et Compulsions", "différé", "prioritaire", ("game/clans.py",), "Les déclencheurs de Fléau sont décrits mais la résolution de frénésie/Compulsion reste à créer."),
    SystemeV5("fleaux", "Fléaux de clan", "partiel", "compléter", ("game/clans.py", "game/situations.py"), "Ventrue est déjà relié à la chasse ; Brujah et Toreador doivent recevoir une mécanique explicite."),
    SystemeV5("disciplines", "Disciplines et pouvoirs", "partiel", "progressif", ("game/mecaniques_vampiriques.py", "game/chronicle.py"), "Ne modéliser que les pouvoirs réellement accessibles et utiles aux scènes."),
    SystemeV5("historiques", "Historiques et Avantages", "partiel", "compléter", ("game/vampire_profile.py",), "Sire, Contacts, Ressources et Statut sont stockés mais pas encore tous exploités par les situations."),
    SystemeV5("convictions", "Convictions", "partiel", "compléter", ("game/creation_rules.py", "game/vampire_profile.py"), "Elles modifient actuellement la fiche ; elles devront surtout interagir avec Humanité et Remords."),
    SystemeV5("ambition_desir", "Ambition et Désir", "partiel", "compléter", ("game/chronicle.py", "game/vampire_profile.py"), "Objectif long, objectif de chapitre et désir existent mais leur boucle de récompense reste incomplète."),
    SystemeV5("historique_chronique", "Historique persistant de la chronique", "intégré", "renforcer", ("game/chronicle_store.py", "game/relationship_memory.py"), "Les nuits, décisions, conséquences et mémoires relationnelles sont persistées."),
    SystemeV5("experience", "Expérience et progression", "partiel", "compléter", ("game/chronicle_store.py",), "L'XP existe ; les coûts d'achat de traits ne sont pas encore structurés."),
    SystemeV5("combat", "Combat détaillé", "écarté", "simplifier", (), "WoD-rpg doit résoudre les affrontements importants comme des situations à conséquences plutôt que comme un simulateur tactique complet."),
    SystemeV5("resonances", "Résonances et dyscrasies", "écarté", "optionnel", (), "À ajouter seulement si la chasse a besoin de davantage de profondeur."),
    SystemeV5("predateur", "Type de prédateur moderne", "écarté", "adapter", (), "Peu adapté à un infant parisien de 1435 ; les habitudes de chasse émergeront des choix et du Domaine."),
    SystemeV5("memoriam", "Memoriam", "différé", "optionnel", (), "Le journal persistant couvre déjà le besoin principal ; des retours jouables dans le passé peuvent venir plus tard."),
    SystemeV5("coterie", "Coterie", "écarté", "non prioritaire", (), "La Chronique est centrée sur un joueur ; relations, lignage et factions remplacent la fiche de coterie pour le MVP."),
)


def valider_structure_v5() -> None:
    ids: set[str] = set()
    for systeme in SYSTEMES_V5:
        if systeme.id in ids:
            raise ValueError(f"Système V5 dupliqué : {systeme.id}")
        ids.add(systeme.id)
        if systeme.statut not in STATUTS_V5:
            raise ValueError(f"Statut V5 inconnu : {systeme.statut}")


def rapport_structure_v5() -> dict[str, object]:
    valider_structure_v5()
    comptes = {statut: 0 for statut in STATUTS_V5}
    for systeme in SYSTEMES_V5:
        comptes[systeme.statut] += 1
    priorites = tuple(
        systeme.id
        for systeme in SYSTEMES_V5
        if systeme.cible in {"prioritaire", "compléter"}
    )
    return {
        "total": len(SYSTEMES_V5),
        "comptes": comptes,
        "priorites": priorites,
    }
