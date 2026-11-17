"""Fonction 1 : construire la maison.

Crée le dossier `ma-maison` avec 3 pièces :
- entree : là où on met le projet cassé
- travail : là où la maison travaille
- sortie : là où elle met le projet réparé

Si la maison existe déjà, on ne la recrée pas et on ne supprime rien.
"""

from pathlib import Path

NOM_DOSSIER = "ma-maison"
PIECES = ("entree", "travail", "sortie")


def construire_maison(base=None):
    """Construit la maison dans `base` (par défaut : le dossier actuel).

    Retourne (chemin_de_la_maison, nouvelle) :
    - nouvelle = True  : la maison vient d'être construite
    - nouvelle = False : la maison existait déjà
    """
    base = Path(base) if base is not None else Path.cwd()
    racine = base / NOM_DOSSIER
    nouvelle = not racine.exists()

    # exist_ok=True : on ne casse et on n'efface jamais rien
    for piece in PIECES:
        (racine / piece).mkdir(parents=True, exist_ok=True)

    return racine, nouvelle
