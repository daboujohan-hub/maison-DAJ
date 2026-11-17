"""Fonctions 3 et 4 : recevoir le projet et faire les 2 copies.

Pour chaque projet mis dans `entree`, la maison fait :
- une copie de sécurité (on n'y touche plus jamais)
- une copie de travail (c'est celle qu'on va réparer)

Rangement :
    travail/<nom>/securite/<nom>
    travail/<nom>/copie/<nom>

L'original dans `entree` n'est jamais modifié. Après la copie, on VÉRIFIE
que les copies sont identiques à l'original (la maison ne ment pas).
"""

import hashlib
import os
import re
import shutil
from pathlib import Path


def projets_recus(racine):
    """Liste ce que Johan a mis dans `entree` (les noms cachés sont ignorés)."""
    entree = Path(racine) / "entree"
    if not entree.is_dir():
        return []
    return sorted(p for p in entree.iterdir() if not p.name.startswith("."))


def _empreinte(fichier):
    h = hashlib.sha256()
    with open(fichier, "rb") as f:
        for morceau in iter(lambda: f.read(65536), b""):
            h.update(morceau)
    return h.hexdigest()


def _contenu(chemin):
    """Décrit tout ce qu'il y a dans un fichier ou un dossier."""
    chemin = Path(chemin)
    if not chemin.is_dir():
        return {".": ("fichier", _empreinte(chemin))}
    resultat = {}
    for p in sorted(chemin.rglob("*")):
        rel = str(p.relative_to(chemin))
        if p.is_symlink():
            resultat[rel] = ("lien", os.readlink(p))
        elif p.is_dir():
            resultat[rel] = ("dossier",)
        else:
            resultat[rel] = ("fichier", _empreinte(p))
    return resultat


def sont_identiques(a, b):
    """Vrai si a et b ont exactement le même contenu."""
    return _contenu(a) == _contenu(b)


def _dossier_libre(travail, nom):
    """Trouve un dossier qui n'existe pas encore : nom, nom-2, nom-3..."""
    candidat = Path(travail) / nom
    n = 2
    while candidat.exists():
        candidat = Path(travail) / f"{nom}-{n}"
        n += 1
    return candidat


def _copier(source, destination):
    if source.is_dir():
        # symlinks=True : on copie les liens tels quels, on ne sort jamais du projet
        shutil.copytree(source, destination, symlinks=True)
    else:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def faire_copies(source, racine):
    """Fait la copie de sécurité et la copie de travail de `source`.

    Retourne (chemin_securite, chemin_copie_de_travail).
    Une copie déjà faite n'est jamais écrasée : un nouveau dossier est créé.
    """
    source = Path(source)
    racine = Path(racine)
    if not source.exists():
        raise FileNotFoundError(f"Je ne trouve pas : {source}")

    dossier = _dossier_libre(racine / "travail", source.name)
    securite = dossier / "securite" / source.name
    copie = dossier / "copie" / source.name

    _copier(source, securite)
    _copier(source, copie)

    if not (sont_identiques(source, securite) and sont_identiques(source, copie)):
        raise RuntimeError("Les copies ne sont pas identiques à l'original. J'arrête.")

    return securite, copie


def derniere_copie(racine, nom):
    """Retrouve la copie de travail la plus récente du projet `nom` (ou None)."""
    travail = Path(racine) / "travail"
    if not travail.is_dir():
        return None
    motif = re.compile(rf"^{re.escape(nom)}(?:-(\d+))?$")
    meilleure, meilleur_n = None, 0
    for dossier in travail.iterdir():
        m = motif.match(dossier.name)
        if not m:
            continue
        n = int(m.group(1)) if m.group(1) else 1
        copie = dossier / "copie" / nom
        if copie.exists() and n > meilleur_n:
            meilleure, meilleur_n = copie, n
    return meilleure
