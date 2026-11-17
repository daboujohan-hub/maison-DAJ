"""Fonction 7 : réparer.

La maison ne corrige que les cas dont elle est SÛRE :
- une parenthèse / un crochet / une accolade qui manque en fin de ligne
- les deux-points « : » qui manquent après if, for, def, class...
- `print 'salut'` devenu `print('salut')`

Après CHAQUE correction, Python revérifie le fichier. Si la correction ne
fait pas avancer les choses, elle est annulée. Ce que la maison ne comprend
pas, elle n'y touche pas : elle le laisse dans le rapport.

Elle ne répare QUE la copie de travail (dossier `copie`), jamais l'original
ni la copie de sécurité.
"""

import ast
import io
import os
import re
import tokenize
from dataclasses import dataclass, field
from pathlib import Path

from .diagnostic import DOSSIERS_IGNORES, diagnostiquer

PAIRES = {"(": ")", "[": "]", "{": "}"}
MAX_CORRECTIONS = 200
FINS_INTERDITES = ",+-*/%=<>|&^~.([{\\"
MOTS_AVEC_DEUX_POINTS = {
    "if", "elif", "else", "for", "while", "def", "class",
    "try", "except", "finally", "with",
}


@dataclass
class Correction:
    fichier: str
    ligne: int
    avant: str
    apres: str
    explication: str


@dataclass
class ResultatReparation:
    corrections: list = field(default_factory=list)
    non_corriges: list = field(default_factory=list)  # des Probleme
    fichiers_modifies: int = 0


# ---------------------------------------------------------------- outils

def _scanner(contenu):
    """Lit une ligne de code. Retourne (ouverts, fin_du_code, nb_deux_points)
    ou None si la ligne est trop bizarre pour qu'on y touche."""
    pile = []
    deux_points = 0
    quote = None
    i, n = 0, len(contenu)
    while i < n:
        c = contenu[i]
        if quote:
            if c == "\\":
                i += 2
                continue
            if c == quote:
                quote = None
        elif c == "#":
            return pile, i, deux_points
        elif c in "'\"":
            if contenu[i:i + 3] == c * 3:
                return None  # texte sur plusieurs lignes : on n'y touche pas
            quote = c
        elif c in PAIRES:
            pile.append(c)
        elif c in ")]}":
            if not pile or PAIRES[pile[-1]] != c:
                return None
            pile.pop()
        elif c == ":" and not pile:
            deux_points += 1
        i += 1
    if quote:
        return None
    return pile, n, deux_points


def _se_termine_mal(reste):
    """Vrai si la ligne se termine comme si elle attendait la suite."""
    if not reste or reste[-1] in FINS_INTERDITES:
        return True
    return re.search(r"\b(and|or|not|in|is)$", reste) is not None


# ---------------------------------------------------------------- règles

def _regle_parenthese(contenu):
    scan = _scanner(contenu)
    if scan is None:
        return None
    pile, fin, _ = scan
    if not pile:
        return None
    code = contenu[:fin].rstrip()
    if not code:
        return None
    avec_deux_points = code.endswith(":")
    reste = code[:-1].rstrip() if avec_deux_points else code
    if _se_termine_mal(reste):
        return None
    fermants = "".join(PAIRES[o] for o in reversed(pile))
    nouveau = reste + fermants + (":" if avec_deux_points else "") + contenu[len(code):]
    return nouveau, f"j'ai ajouté « {fermants} » à la fin de la ligne"


def _regle_deux_points(contenu):
    scan = _scanner(contenu)
    if scan is None:
        return None
    pile, fin, deux_points = scan
    if pile or deux_points:
        return None
    code = contenu[:fin].rstrip()
    if not code or code.endswith(("\\", ",")) or _se_termine_mal(code):
        return None
    m = re.match(r"\s*([a-z]+)\b", code)
    if not m or m.group(1) not in MOTS_AVEC_DEUX_POINTS:
        return None
    if m.group(1) in ("else", "try", "finally") and code.strip() != m.group(1):
        return None
    nouveau = code + ":" + contenu[len(code):]
    return nouveau, "j'ai ajouté les deux-points « : » à la fin de la ligne"


def _regle_print(contenu):
    scan = _scanner(contenu)
    if scan is None:
        return None
    pile, fin, _ = scan
    if pile:
        return None
    code = contenu[:fin].rstrip()
    m = re.match(r"^(\s*)print\s+(\S.*)$", code)
    if not m:
        return None
    indentation, argument = m.groups()
    if argument.startswith(("(", "=", ">>")) or argument.endswith(",") or ";" in argument:
        return None
    nouveau = f"{indentation}print({argument})" + contenu[len(code):]
    return nouveau, "j'ai ajouté les parenthèses de print (Python 3)"


REGLES = (_regle_print, _regle_deux_points, _regle_parenthese)


# ---------------------------------------------------------------- réparation

def _etat(texte):
    """Retourne ("ok", None), ("erreur", SyntaxError) ou ("inconnu", None)."""
    try:
        ast.parse(texte)
    except SyntaxError as e:
        return "erreur", e
    except (ValueError, RecursionError):
        return "inconnu", None
    return "ok", None


def _essayer(lignes, numero_erreur, rel, corrections):
    """Essaie de corriger autour de la ligne en erreur. Vrai si une correction a été gardée."""
    for idx in (numero_erreur - 1, numero_erreur - 2):
        if idx < 0 or idx >= len(lignes):
            continue
        ligne = lignes[idx]
        contenu = ligne.rstrip("\r\n")
        fin_de_ligne = ligne[len(contenu):]
        for regle in REGLES:
            resultat = regle(contenu)
            if resultat is None:
                continue
            nouveau, explication = resultat
            if nouveau == contenu:
                continue
            essai = lignes[:idx] + [nouveau + fin_de_ligne] + lignes[idx + 1:]
            etat, erreur = _etat("".join(essai))
            # On garde seulement si Python avance : plus d'erreur, ou erreur plus loin.
            if etat == "inconnu" or (etat == "erreur" and (erreur.lineno or 0) <= idx + 1):
                continue
            corrections.append(
                Correction(rel, idx + 1, contenu.strip(), nouveau.strip(), explication)
            )
            lignes[idx] = nouveau + fin_de_ligne
            return True
    return False


def _reparer_fichier(complet, rel):
    donnees = Path(complet).read_bytes()
    try:
        encodage, _ = tokenize.detect_encoding(io.BytesIO(donnees).readline)
        texte = donnees.decode(encodage)
    except (SyntaxError, LookupError, UnicodeDecodeError):
        return []

    # newline="" : on garde les fins de ligne exactement comme elles sont
    lignes = io.StringIO(texte, newline="").readlines()
    corrections = []
    for _ in range(MAX_CORRECTIONS):
        etat, erreur = _etat("".join(lignes))
        if etat != "erreur" or not erreur.lineno:
            break
        if not _essayer(lignes, erreur.lineno, rel, corrections):
            break

    if corrections:
        Path(complet).write_bytes("".join(lignes).encode(encodage))
    return corrections


def _fichiers_python(chemin):
    if chemin.is_file():
        if chemin.suffix == ".py":
            yield chemin, chemin.name
        return
    for dossier, sous_dossiers, fichiers in os.walk(chemin):
        sous_dossiers[:] = sorted(d for d in sous_dossiers if d not in DOSSIERS_IGNORES)
        for nom in sorted(fichiers):
            if nom.endswith(".py"):
                complet = Path(dossier) / nom
                yield complet, str(complet.relative_to(chemin))


def reparer(chemin):
    """Répare la copie de travail `chemin` (le dossier `copie/<nom>`)."""
    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(f"Je ne trouve pas : {chemin}")
    if chemin.parent.name != "copie":
        raise ValueError(
            "Je ne répare que la copie de travail, jamais l'original "
            "ni la copie de sécurité."
        )

    resultat = ResultatReparation()
    for complet, rel in _fichiers_python(chemin):
        corrections = _reparer_fichier(complet, rel)
        if corrections:
            resultat.corrections += corrections
            resultat.fichiers_modifies += 1

    reste = diagnostiquer(chemin)
    resultat.non_corriges = [p for p in reste.problemes if p.genre in ("syntaxe", "illisible")]
    return resultat
