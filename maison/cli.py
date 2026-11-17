"""La commande `maison`."""

import argparse
from pathlib import Path

from . import __version__

from .copie import derniere_copie, faire_copies, projets_recus
from .diagnostic import diagnostiquer
from .maison import NOM_DOSSIER, construire_maison
from .rapport import (
    ajouter_au_rapport, ecrire_rapport, texte_diagnostic, texte_reparation, texte_test,
)
from .reparer import reparer
from .tester import DELAI_PAR_DEFAUT, tester


def main(argv=None):
    parseur = argparse.ArgumentParser(
        prog="maison",
        description="LA MAISON : répare tes projets Python cassés, même sans internet.",
    )
    parseur.add_argument("--version", action="version", version=__version__)
    sous = parseur.add_subparsers(dest="commande")
    sous.add_parser("construire", help="construit le dossier ma-maison")
    sous.add_parser("copier", help="fait les copies des projets mis dans entree")
    sous.add_parser("diagnostiquer", help="cherche ce qui est cassé dans la copie")
    sous.add_parser("reparer", help="corrige les cas simples dans la copie de travail")
    p_test = sous.add_parser("tester", help="lance la copie pour voir si ça marche")
    p_test.add_argument("--oui", action="store_true", help="ne pas demander confirmation")
    p_test.add_argument("--fichier", help="le fichier à lancer (sinon je cherche)")
    p_test.add_argument("--delai", type=int, default=DELAI_PAR_DEFAUT,
                        help="secondes maximum avant d'arrêter (10 par défaut)")

    args = parseur.parse_args(argv)

    if args.commande == "construire":
        racine, nouvelle = construire_maison()
        if nouvelle:
            print(f"Maison construite : {racine}")
            print("Mets ton projet cassé dans le dossier 'entree'.")
        else:
            print("Ma maison existe déjà.")
        return 0

    if args.commande == "copier":
        return commande_copier()

    if args.commande == "diagnostiquer":
        return commande_diagnostiquer()

    if args.commande == "reparer":
        return commande_reparer()

    if args.commande == "tester":
        return commande_tester(args)

    parseur.print_help()
    return 0


def commande_copier():
    racine = Path.cwd() / NOM_DOSSIER
    if not racine.is_dir():
        print("Ma maison n'existe pas. Lance d'abord : maison construire")
        return 1

    projets = projets_recus(racine)
    if not projets:
        print("Il n'y a rien dans 'entree'. Mets-y ton projet cassé.")
        return 1

    for projet in projets:
        try:
            securite, copie = faire_copies(projet, racine)
        except (OSError, RuntimeError) as erreur:
            print(f"Je n'ai pas pu copier '{projet.name}' : {erreur}")
            return 1
        print(f"Projet '{projet.name}' : copies faites et vérifiées.")
        print(f"  sécurité : {securite}")
        print(f"  travail  : {copie}")
    return 0



def commande_diagnostiquer():
    racine = Path.cwd() / NOM_DOSSIER
    if not racine.is_dir():
        print("Ma maison n'existe pas. Lance d'abord : maison construire")
        return 1

    projets = projets_recus(racine)
    if not projets:
        print("Il n'y a rien dans 'entree'. Mets-y ton projet cassé.")
        return 1

    code = 0
    for projet in projets:
        copie = derniere_copie(racine, projet.name)
        if copie is None:
            print(f"Pas encore de copie de '{projet.name}'. Lance d'abord : maison copier")
            code = 1
            continue
        resultat = diagnostiquer(copie)
        texte = texte_diagnostic(projet.name, resultat)
        print(texte)
        rapport = ecrire_rapport(copie.parent.parent / "rapport.txt", texte)
        print(f"Rapport écrit : {rapport}")
    return code


def commande_reparer():
    racine = Path.cwd() / NOM_DOSSIER
    if not racine.is_dir():
        print("Ma maison n'existe pas. Lance d'abord : maison construire")
        return 1

    projets = projets_recus(racine)
    if not projets:
        print("Il n'y a rien dans 'entree'. Mets-y ton projet cassé.")
        return 1

    code = 0
    for projet in projets:
        copie = derniere_copie(racine, projet.name)
        if copie is None:
            print(f"Pas encore de copie de '{projet.name}'. Lance d'abord : maison copier")
            code = 1
            continue
        avant = diagnostiquer(copie)
        try:
            reparation = reparer(copie)
        except (OSError, ValueError) as erreur:
            print(f"Je n'ai pas pu réparer '{projet.name}' : {erreur}")
            code = 1
            continue
        apres = diagnostiquer(copie)
        texte = texte_reparation(projet.name, avant, reparation, apres)
        print(texte)
        rapport = ecrire_rapport(copie.parent.parent / "rapport.txt", texte)
        print(f"Rapport écrit : {rapport}")
        print(f"Copie réparée : {copie}")
    return code


def _confirmer_lancement():
    print("Je vais LANCER ton programme pour de vrai, dans la copie de travail.")
    print("La copie protège ton original, mais pas le reste du téléphone :")
    print("un programme peut effacer des fichiers ou utiliser internet.")
    print("Continuer ? (o/n)")
    try:
        reponse = input("> ").strip().lower()
    except EOFError:
        reponse = ""
    return reponse in ("o", "oui", "y", "yes")


def commande_tester(args):
    racine = Path.cwd() / NOM_DOSSIER
    if not racine.is_dir():
        print("Ma maison n'existe pas. Lance d'abord : maison construire")
        return 1

    projets = projets_recus(racine)
    if not projets:
        print("Il n'y a rien dans 'entree'. Mets-y ton projet cassé.")
        return 1

    if not args.oui and not _confirmer_lancement():
        print("D'accord, je ne le lance pas.")
        return 1

    code = 0
    for projet in projets:
        copie = derniere_copie(racine, projet.name)
        if copie is None:
            print(f"Pas encore de copie de '{projet.name}'. Lance d'abord : maison copier")
            code = 1
            continue
        try:
            resultat = tester(copie, fichier=args.fichier, delai=args.delai)
        except (OSError, ValueError) as erreur:
            print(f"Je n'ai pas pu tester '{projet.name}' : {erreur}")
            code = 1
            continue

        texte = texte_test(projet.name, resultat)
        print(texte)
        if resultat.verdict == "plante":
            # Fonction 9 -> retour à la Fonction 5 : on refait un diagnostic
            code = max(code, 1)
            nouveau = texte_diagnostic(projet.name, diagnostiquer(copie))
            print("Je refais un diagnostic :\n")
            print(nouveau)
            texte += "\n" + nouveau
        elif resultat.verdict != "marche":
            code = max(code, 2)
        rapport = ajouter_au_rapport(copie.parent.parent / "rapport.txt", texte)
        print(f"Rapport mis à jour : {rapport}")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
