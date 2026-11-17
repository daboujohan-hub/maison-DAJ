"""Fonction 5 : diagnostic, trouver ce qui est cassé.

Pour le Python, on demande à Python lui-même (module `ast`) :
- erreurs d'écriture (parenthèse, guillemet, deux-points, décalage...)
- paquets importés qui ne sont pas dans le téléphone

IMPORTANT : le diagnostic ne LANCE jamais le code du projet et ne MODIFIE rien.
Il lit seulement.
"""

import ast
import importlib.util
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

DOSSIERS_IGNORES = {
    ".git", "__pycache__", "venv", ".venv", "env", "node_modules",
    "site-packages", ".mypy_cache", ".pytest_cache",
}

# nom utilisé dans `import`  ->  nom à installer avec pip (cas courants)
NOMS_PIP = {
    "PIL": "Pillow", "cv2": "opencv-python", "yaml": "pyyaml",
    "bs4": "beautifulsoup4", "sklearn": "scikit-learn",
    "dotenv": "python-dotenv", "serial": "pyserial", "Crypto": "pycryptodome",
    "jwt": "PyJWT", "dateutil": "python-dateutil", "OpenSSL": "pyOpenSSL",
    "attr": "attrs",
}


@dataclass
class Probleme:
    fichier: str
    ligne: object  # int ou None
    genre: str  # "syntaxe", "paquet_manquant" ou "illisible"
    explication: str  # en français simple
    detail: str = ""  # ce que Python a dit exactement
    extrait: str = ""  # la ligne concernée


@dataclass
class ResultatDiagnostic:
    problemes: list = field(default_factory=list)
    fichiers_python: int = 0
    fichiers_ignores: int = 0


# ---------------------------------------------------------------- syntaxe

def _expliquer_syntaxe(erreur):
    msg = erreur.msg or ""

    m = re.match(r"'(.)' was never closed", msg)
    if m:
        ouvrant = m.group(1)
        fermant = {"(": ")", "[": "]", "{": "}"}.get(ouvrant, "")
        return f"Il manque un « {fermant} » : le « {ouvrant} » de cette ligne n'est jamais fermé."
    if re.match(r"unmatched '.'", msg):
        return "Il y a un signe fermant en trop : rien n'est ouvert avant lui."
    if "does not match opening" in msg:
        return "Un signe fermant ne correspond pas au signe ouvert plus haut ( ) [ ] { }."
    if "unterminated triple-quoted" in msg:
        return "Un texte entre triples guillemets n'est jamais fermé."
    if "unterminated string literal" in msg or "EOL while scanning string" in msg:
        return "Un guillemet n'est pas fermé sur cette ligne."
    if "expected ':'" in msg:
        return "Il manque les deux-points « : » à la fin de cette ligne."
    if "Missing parentheses in call to 'print'" in msg:
        return "En Python 3, print s'écrit avec des parenthèses : print(...)."
    if "Perhaps you forgot a comma" in msg:
        return "Il manque peut-être une virgule."
    if "expected an indented block" in msg:
        return "Il manque une ligne décalée (indentée) après cette ligne."
    if "unexpected indent" in msg:
        return "Cette ligne est décalée à tort."
    if "unindent does not match" in msg:
        return "Le décalage de cette ligne ne correspond à aucun bloc au-dessus."
    if isinstance(erreur, TabError) or "inconsistent use of tabs" in msg:
        return "Le décalage mélange des tabulations et des espaces."
    if "outside function" in msg:
        return "Un « return » est écrit en dehors d'une fonction."
    if "Non-UTF-8" in msg or "unicode error" in msg:
        return "Le fichier contient un caractère mal enregistré (mauvais encodage)."
    if msg == "invalid syntax":
        return "Python ne comprend pas cette ligne (faute d'écriture). Regarde aussi la ligne juste avant."
    if "EOF" in msg:
        return "Le fichier se termine trop tôt : il manque sûrement un signe de fermeture."
    return "Python ne comprend pas cette ligne."


# ---------------------------------------------------------------- imports

def _attrape_import(gestionnaire):
    """Vrai si ce `except` attrape une erreur d'import (import optionnel)."""
    t = gestionnaire.type
    if t is None:
        return True
    noms = []
    elements = t.elts if isinstance(t, ast.Tuple) else [t]
    for e in elements:
        if isinstance(e, ast.Name):
            noms.append(e.id)
    return any(n in ("ImportError", "ModuleNotFoundError", "Exception", "BaseException")
               for n in noms)


class _Imports(ast.NodeVisitor):
    def __init__(self):
        self.trouves = []  # (nom_du_module, ligne)
        self._optionnel = 0

    def visit_Import(self, noeud):
        if not self._optionnel:
            for alias in noeud.names:
                self.trouves.append((alias.name.split(".")[0], noeud.lineno))

    def visit_ImportFrom(self, noeud):
        if not self._optionnel and noeud.level == 0 and noeud.module:
            self.trouves.append((noeud.module.split(".")[0], noeud.lineno))

    def visit_Try(self, noeud):
        optionnel = any(_attrape_import(h) for h in noeud.handlers)
        if optionnel:
            self._optionnel += 1
        for n in noeud.body:
            self.visit(n)
        if optionnel:
            self._optionnel -= 1
        for h in noeud.handlers:
            for n in h.body:
                self.visit(n)
        for n in noeud.orelse + noeud.finalbody:
            self.visit(n)

    visit_TryStar = visit_Try


def _module_connu(nom, dossiers):
    """Vrai si le module existe (bibliothèque Python, installé, ou dans le projet).

    En cas de doute, on répond « connu » : on ne signale que ce dont on est sûr.
    """
    if nom in getattr(sys, "stdlib_module_names", ()):
        return True
    for d in dossiers:
        if (d / f"{nom}.py").exists() or (d / nom).is_dir():
            return True
    try:
        return importlib.util.find_spec(nom) is not None
    except (ImportError, ValueError, AttributeError):
        return True


def _imports_manquants(arbre, rel, dossiers):
    visiteur = _Imports()
    visiteur.visit(arbre)
    problemes = []
    deja = set()
    for nom, ligne in visiteur.trouves:
        if nom in deja or _module_connu(nom, dossiers):
            continue
        deja.add(nom)
        pip = NOMS_PIP.get(nom, nom)
        problemes.append(Probleme(
            fichier=rel, ligne=ligne, genre="paquet_manquant",
            explication=f"Le paquet « {nom} » n'est pas dans ce téléphone.",
            detail=f"Pour l'installer (avec internet) : pip install {pip}",
        ))
    return problemes


# ---------------------------------------------------------------- fichier

def _analyser_fichier(fichier, rel, racine):
    try:
        donnees = Path(fichier).read_bytes()
    except OSError as e:
        return [Probleme(rel, None, "illisible", "Je n'arrive pas à ouvrir ce fichier.", str(e))]

    try:
        arbre = ast.parse(donnees, filename=rel)
    except SyntaxError as e:
        return [Probleme(
            fichier=rel, ligne=e.lineno, genre="syntaxe",
            explication=_expliquer_syntaxe(e),
            detail=f"Python dit : {e.msg}",
            extrait=(e.text or "").strip(),
        )]
    except (ValueError, RecursionError) as e:
        return [Probleme(rel, None, "illisible",
                         "Je n'arrive pas à lire ce fichier (caractère interdit ou trop compliqué).",
                         str(e))]

    return _imports_manquants(arbre, rel, [Path(racine), Path(fichier).parent])


# ---------------------------------------------------------------- projet

def diagnostiquer(chemin):
    """Diagnostique un fichier ou un dossier. Ne modifie rien, ne lance rien."""
    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(f"Je ne trouve pas : {chemin}")

    resultat = ResultatDiagnostic()

    if chemin.is_file():
        if chemin.suffix == ".py":
            resultat.fichiers_python = 1
            resultat.problemes += _analyser_fichier(chemin, chemin.name, chemin.parent)
        else:
            resultat.fichiers_ignores = 1
        return resultat

    for dossier, sous_dossiers, fichiers in os.walk(chemin):
        sous_dossiers[:] = sorted(d for d in sous_dossiers if d not in DOSSIERS_IGNORES)
        for nom in sorted(fichiers):
            complet = Path(dossier) / nom
            rel = str(complet.relative_to(chemin))
            if nom.endswith(".py"):
                resultat.fichiers_python += 1
                resultat.problemes += _analyser_fichier(complet, rel, chemin)
            else:
                resultat.fichiers_ignores += 1
    return resultat
