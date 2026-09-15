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
    SystemeV5("attributs", "Neuf Attributs", "intégré", "conserver", ("game/vampire_profile.py",), "Les neuf Attributs V5 sont structurés."),
    SystemeV5("competences", "Compétences", "intégré", "conserver", ("game/vampire_profile.py",), "Les 27 Compétences V5 sont structurées avec des libellés 1435 adaptés."),
    SystemeV5("specialites", "Spécialités", "intégré", "conserver", ("game/vampire_profile.py",), "Les Spécialités sont persistées et ajoutent un dé lorsqu'elles s'appliquent."),
    SystemeV5("resolution", "Attribut + Compétence, D10, réussites sur 6+", "intégré", "conserver", ("game/dice.py", "game/situations.py"), "Socle de résolution de la Chronique."),
    SystemeV5("difficulte", "Difficulté", "intégré", "adapter", ("game/dice.py", "game/situations.py"), "Le seuil exact reste caché ; le joueur reçoit un indice narratif."),
    SystemeV5("faim", "Faim et dés de Faim", "intégré", "conserver", ("game/dice.py", "game/chronicle.py"), "Les dés de Faim remplacent des dés ordinaires dans le groupement."),
    SystemeV5("critiques", "Critiques, réussite bestiale et échec bestial", "intégré", "conserver", ("game/dice.py", "game/consequences.py"), "Les conséquences persistantes sont graduées autour du résultat V5."),
    SystemeV5("volonte", "Volonté", "intégré", "simplifier", ("game/vampire_profile.py", "game/night_cycle.py"), "Relance de dés ordinaires, usure et récupération adaptées au rythme asynchrone ; la piste détaillée de dégâts de Volonté reste simplifiée."),
    SystemeV5("exaltation", "Test d’Exaltation", "intégré", "conserver", ("game/dice.py", "game/night_cycle.py", "game/health.py"), "Utilisé pour le Coup de Sang et la guérison vampirique."),
    SystemeV5("reveil", "Réveil nocturne", "différé", "adapter", (), "Une Nuit significative n'est pas nécessairement une nuit civile ; l'Exaltation du réveil exige une adaptation temporelle explicite avant automatisation."),
    SystemeV5("coup_de_sang", "Coup de Sang", "intégré", "conserver", ("game/mecaniques_vampiriques.py",), "Bonus selon la Puissance du Sang."),
    SystemeV5("generation", "Génération", "intégré", "conserver", ("game/vampire_profile.py",), "Déduite du sire lors de la création."),
    SystemeV5("puissance_sang", "Puissance du Sang", "partiel", "compléter", ("game/vampire_profile.py", "game/mecaniques_vampiriques.py", "game/health.py"), "Coup de Sang, Sévérité du Fléau et quantité de dégâts superficiels guéris sont structurés ; restent les bonus complets de Disciplines et contraintes alimentaires."),
    SystemeV5("guerison", "Guérison vampirique", "intégré", "conserver", ("game/health.py",), "Un Test d'Exaltation soigne les dégâts superficiels selon la Puissance du Sang ; trois Tests peuvent soigner un aggravé, avec blocage à Faim 5."),
    SystemeV5("sante", "Santé et dégâts", "intégré", "conserver", ("game/vampire_profile.py", "game/health.py"), "Santé = Vigueur + 3, dégâts superficiels/aggravés, altération physique, conversion, torpeur et guérison sont structurés."),
    SystemeV5("humanite", "Humanité, Flétrissures et Remords", "partiel", "compléter", ("game/chronicle.py", "game/humanity.py", "game/night_cycle_store.py"), "La piste, les Flétrissures et le Remord sont structurés ; les situations de production doivent encore déclarer explicitement leurs transgressions morales et la surcharge de piste reste simplifiée."),
    SystemeV5("convictions", "Convictions", "partiel", "compléter", ("game/creation_rules.py", "game/vampire_profile.py", "game/humanity.py"), "Les nouveaux personnages n'obtiennent plus le bonus de Compétence maison ; une Conviction pertinente peut atténuer une Flétrissure. Les anciennes fiches ne sont pas rétroactivement recalculées."),
    SystemeV5("attaches", "Attaches humaines", "écarté", "adapter", ("game/vampire_profile.py",), "Les Attaches ont été retirées du parcours joueur ; Humanité repose sur Convictions, Principes, relations et conséquences persistantes."),
    SystemeV5("principes_chronique", "Principes de chronique", "intégré", "conserver", ("game/humanity.py", "game/morality_stakes.py"), "Trois Principes par défaut sont structurés et les transgressions doivent être déclarées explicitement par le contenu."),
    SystemeV5("frenesie", "Frénésie", "partiel", "compléter", ("game/beast.py", "game/night_cycle.py", "game/night_cycle_ui.py"), "La Frénésie de Faim est branchée sur une chasse réussie commencée à Faim 4+ avec résistance ou Chevaucher la vague. Fureur et Terreur restent disponibles dans le moteur mais doivent encore être reliées à des provocations explicitement déclarées par les scènes."),
    SystemeV5("compulsions", "Compulsions", "intégré", "conserver", ("game/beast.py", "game/vampire_profile.py", "game/night_cycle.py", "game/night_cycle_ui.py"), "Rébellion Brujah, Obsession Toreador et Arrogance Ventrue se déclenchent sur les résultats bestiaux hors chasse, imposent -2 dés aux actions non alignées, peuvent être satisfaites par une réussite alignée et sont visibles dans l'interface."),
    SystemeV5("fleaux", "Fléaux de clan", "partiel", "compléter", ("game/clans.py", "game/beast.py", "game/mecaniques_vampiriques.py"), "La Sévérité du Fléau et le malus Brujah aux Frénésies de Fureur sont structurés. La restriction Ventrue est décrite dans la chasse ; l'effet Toreador doit encore recevoir un déclencheur explicite."),
    SystemeV5("disciplines", "Disciplines et pouvoirs", "partiel", "progressif", ("game/mecaniques_vampiriques.py", "game/chronicle.py"), "Ne modéliser que les pouvoirs réellement accessibles et utiles aux scènes."),
    SystemeV5("liens_sang", "Lien du Sang", "différé", "compléter", (), "Important pour un jeu politique vampirique, mais distinct des relations ordinaires et pas encore structuré."),
    SystemeV5("historiques", "Historiques et Avantages", "partiel", "prioritaire", ("game/vampire_profile.py",), "Sire, Contacts, Ressources et Statut sont stockés mais pas encore tous exploités par les situations."),
    SystemeV5("ambition_desir", "Ambition et Désir", "partiel", "compléter", ("game/chronicle.py", "game/vampire_profile.py"), "Objectif long, objectif de chapitre et désir existent mais leur boucle de récompense reste incomplète."),
    SystemeV5("historique_chronique", "Historique persistant de la chronique", "intégré", "renforcer", ("game/chronicle_store.py", "game/relationship_memory.py"), "Les nuits, décisions, conséquences et mémoires relationnelles sont persistées."),
    SystemeV5("experience", "Expérience et progression", "partiel", "compléter", ("game/chronicle_store.py",), "L'XP existe ; les coûts d'achat de traits et l'évolution des Disciplines ne sont pas encore structurés."),
    SystemeV5("chasse", "Chasse et alimentation", "partiel", "compléter", ("game/situations.py", "game/chronicle_simulation.py", "game/night_cycle.py"), "La chasse, les droits de chasse, la restriction Ventrue et la Frénésie de Faim après goût du sang existent ; les Résonances restent volontairement absentes."),
    SystemeV5("combat", "Combat détaillé", "écarté", "simplifier", (), "Les affrontements importants doivent rester des situations à conséquences plutôt qu'un simulateur tactique complet."),
    SystemeV5("resonances", "Résonances et dyscrasies", "écarté", "optionnel", (), "À ajouter seulement si la chasse a besoin de davantage de profondeur."),
    SystemeV5("predateur", "Type de prédateur moderne", "écarté", "adapter", (), "Peu adapté à un infant parisien de 1435 ; les habitudes de chasse émergent des choix et du Domaine."),
    SystemeV5("memoriam", "Memoriam", "différé", "optionnel", (), "Le journal persistant couvre déjà le besoin principal."),
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
        systeme.id for systeme in SYSTEMES_V5 if systeme.cible in {"prioritaire", "compléter", "brancher"}
    )
    return {"total": len(SYSTEMES_V5), "comptes": comptes, "priorites": priorites}
