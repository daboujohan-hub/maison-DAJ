"""Le carnet `rapport.txt` : ce que la maison a trouvé et fait, en français simple.

La maison ne ment jamais : le rapport dit aussi ce qu'elle ne sait pas.
"""

from pathlib import Path


def _lignes_problemes(problemes):
    lignes = []
    for i, p in enumerate(problemes, 1):
        endroit = f"{p.fichier}, ligne {p.ligne}" if p.ligne else p.fichier
        lignes.append(f"{i}. {endroit}")
        lignes.append(f"   {p.explication}")
        if p.extrait:
            lignes.append(f"   > {p.extrait}")
        if p.detail:
            lignes.append(f"   {p.detail}")
        lignes.append("")
    return lignes


def texte_diagnostic(nom, resultat):
    """Écrit le diagnostic en français simple."""
    n = len(resultat.problemes)
    lignes = [f"DIAGNOSTIC DE « {nom} »", ""]
    lignes.append(f"Fichiers Python regardés : {resultat.fichiers_python}")
    if resultat.fichiers_ignores:
        lignes.append(
            f"Autres fichiers ignorés : {resultat.fichiers_ignores} "
            "(version 0.1 : Python seulement)"
        )
    lignes.append("")

    if n == 0:
        lignes.append("Je n'ai trouvé aucun problème d'écriture ni de paquet manquant.")
        lignes.append("Attention : cela ne prouve pas que le programme marche.")
        lignes.append("On le saura seulement au test.")
        return "\n".join(lignes) + "\n"

    lignes.append(f"J'ai trouvé {n} problème{'s' if n > 1 else ''} :")
    lignes.append("")
    lignes += _lignes_problemes(resultat.problemes)

    if any(p.genre == "syntaxe" for p in resultat.problemes):
        lignes.append(
            "Note : Python s'arrête au premier problème d'écriture de chaque fichier. "
            "Il peut y en avoir d'autres cachés derrière."
        )
        lignes.append(
            "Les paquets manquants de ces fichiers ne sont pas encore vérifiés : "
            "on le fera quand l'écriture sera corrigée."
        )
    return "\n".join(lignes) + "\n"


def ecrire_rapport(chemin, texte):
    chemin = Path(chemin)
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_text(texte, encoding="utf-8")
    return chemin


def texte_reparation(nom, avant, reparation, apres):
    """Diagnostic de départ + ce qui a été corrigé + l'état final."""
    trait = "-" * 40
    lignes = [texte_diagnostic(nom, avant).rstrip("\n"), "", trait, "",
              f"RÉPARATION DE « {nom} »", ""]

    n = len(reparation.corrections)
    if n:
        lignes.append(
            f"J'ai corrigé {n} problème{'s' if n > 1 else ''} "
            "(dans la copie de travail seulement) :"
        )
        lignes.append("")
        for i, c in enumerate(reparation.corrections, 1):
            lignes.append(f"{i}. {c.fichier}, ligne {c.ligne} : {c.explication}")
            lignes.append(f"   avant : {c.avant}")
            lignes.append(f"   après : {c.apres}")
            lignes.append("")
    else:
        lignes.append("Je n'ai rien corrigé.")
        lignes.append("")

    for p in reparation.non_corriges:
        endroit = f"{p.fichier}, ligne {p.ligne}" if p.ligne else p.fichier
        lignes.append(f"Celui-là, je ne l'ai pas compris : regarde ici ({endroit}).")
    if reparation.non_corriges:
        lignes.append("")

    lignes += [trait, "", "APRÈS LA RÉPARATION", ""]
    if not apres.problemes:
        lignes.append("Je ne trouve plus de problème d'écriture ni de paquet manquant.")
        lignes.append("Attention : cela ne prouve pas que le programme marche.")
        lignes.append("On le saura seulement au test.")
    else:
        k = len(apres.problemes)
        lignes.append(f"Il reste {k} problème{'s' if k > 1 else ''} :")
        lignes.append("")
        lignes += _lignes_problemes(apres.problemes)
        if any(p.genre == "paquet_manquant" for p in apres.problemes):
            lignes.append(
                "Sans internet, je ne peux pas installer un paquet : "
                "fais la commande indiquée quand tu seras connecté."
            )
    return "\n".join(lignes) + "\n"


_TITRES_VERDICT = {
    "marche": "ÇA MARCHE",
    "plante": "ÇA PLANTE",
    "tourne_encore": "JE NE SAIS PAS (il tourne encore)",
    "inconnu": "JE NE SAIS PAS (quel fichier lancer ?)",
}


def _fin_de_texte(texte, nb_lignes=12):
    lignes = texte.strip().splitlines()
    if len(lignes) > nb_lignes:
        lignes = ["[...]"] + lignes[-nb_lignes:]
    return ["   " + l for l in lignes]


def texte_test(nom, resultat):
    """Raconte le test, sans jamais dire « ça marche » si ce n'est pas sûr."""
    lignes = [f"TEST DE « {nom} »", ""]
    if resultat.fichier:
        lignes.append(f"Fichier lancé : {resultat.fichier}")
    lignes.append(f"Résultat : {_TITRES_VERDICT.get(resultat.verdict, resultat.verdict)}")
    lignes.append(resultat.explication)

    if resultat.verdict == "marche":
        lignes.append("Attention : cela ne prouve pas qu'il fait exactement ce que tu veux.")

    if resultat.sortie.strip():
        lignes += ["", "Ce que le programme a affiché :"] + _fin_de_texte(resultat.sortie)
    if resultat.verdict == "plante" and resultat.erreur.strip():
        lignes += ["", "Le message d'erreur de Python :"] + _fin_de_texte(resultat.erreur, 6)
    if resultat.fichiers_changes:
        lignes += ["", "Pendant le test, le programme a touché ces fichiers (dans la copie seulement) :"]
        lignes += [f"   {c}" for c in resultat.fichiers_changes[:15]]
    return "\n".join(lignes) + "\n"


def ajouter_au_rapport(chemin, texte):
    """Ajoute une partie au rapport.txt (le crée s'il n'existe pas)."""
    chemin = Path(chemin)
    ancien = chemin.read_text(encoding="utf-8") if chemin.exists() else ""
    separation = "\n" + "-" * 40 + "\n\n" if ancien.strip() else ""
    return ecrire_rapport(chemin, ancien.rstrip("\n") + ("\n" if ancien.strip() else "") + separation + texte)
