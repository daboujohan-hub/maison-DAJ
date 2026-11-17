"""Fonction 9 : tester, lancer pour voir.

La maison lance le projet réparé (la COPIE DE TRAVAIL seulement) et regarde ce
qui se passe. Elle ne dit « ÇA MARCHE » que si c'est vrai :

- marche         : le programme s'est lancé et terminé sans erreur
- plante         : le programme s'est arrêté avec une erreur
- tourne_encore  : il tournait encore après le délai (jeu, serveur...) :
                   on ne peut PAS dire qu'il marche
- inconnu        : on ne sait pas quel fichier lancer

Précautions : pas de clavier (le programme ne peut pas attendre une réponse),
délai maximum, et on note les fichiers que le programme a créés ou changés.
"""

import os
import re
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from .copie import _contenu

NOMS_PRINCIPAUX = ("__main__.py", "main.py", "app.py", "run.py")
DELAI_PAR_DEFAUT = 10
LIMITE_SORTIE = 3000

ERREURS_SIMPLES = {
    "NameError": "Un nom n'existe pas (faute de frappe ou oubli)",
    "AttributeError": "Un objet n'a pas la chose demandée (faute de nom ?)",
    "TypeError": "Un type de valeur ne convient pas",
    "ValueError": "Une valeur ne convient pas",
    "KeyError": "Une clé est introuvable",
    "IndexError": "Un numéro de case n'existe pas dans la liste",
    "ZeroDivisionError": "Une division par zéro",
    "FileNotFoundError": "Un fichier est introuvable",
    "EOFError": "Le programme attendait une réponse au clavier",
    "IndentationError": "Un décalage de ligne est faux",
    "SyntaxError": "Une ligne est mal écrite",
}


@dataclass
class ResultatTest:
    verdict: str
    fichier: str = ""
    explication: str = ""
    sortie: str = ""
    erreur: str = ""
    code_retour: object = None
    delai: int = DELAI_PAR_DEFAUT
    fichiers_changes: list = field(default_factory=list)


def trouver_fichier_principal(chemin):
    """Devine quel fichier lancer. Retourne un Path ou None si on ne sait pas."""
    chemin = Path(chemin)
    if chemin.is_file():
        return chemin if chemin.suffix == ".py" else None
    for nom in NOMS_PRINCIPAUX:
        if (chemin / nom).is_file():
            return chemin / nom
    seuls = sorted(p for p in chemin.glob("*.py") if p.is_file())
    return seuls[0] if len(seuls) == 1 else None


def _changements(avant, apres):
    res = []
    for cle in sorted(set(avant) | set(apres)):
        if cle not in avant:
            res.append(f"créé : {cle}")
        elif cle not in apres:
            res.append(f"supprimé : {cle}")
        elif avant[cle] != apres[cle]:
            res.append(f"modifié : {cle}")
    return res


def _tuer(processus):
    """Arrête le programme ET ce qu'il a lancé."""
    try:
        if os.name == "posix":
            os.killpg(os.getpgid(processus.pid), signal.SIGKILL)
        else:
            processus.kill()
    except (ProcessLookupError, PermissionError, OSError):
        pass


def _fin(texte):
    texte = texte or ""
    return texte if len(texte) <= LIMITE_SORTIE else "[...]\n" + texte[-LIMITE_SORTIE:]


def _expliquer_plantage(erreur, dossier):
    lignes = [l for l in (erreur or "").strip().splitlines() if l.strip()]
    derniere = lignes[-1].strip() if lignes else ""

    m = re.match(r"(?:ModuleNotFoundError|ImportError): No module named '([^']+)'", derniere)
    if m:
        paquet = m.group(1).split(".")[0]
        return f"Il manque le paquet « {paquet} » dans ce téléphone."

    endroit = ""
    racine = Path(dossier).resolve()
    for l in lignes:
        m2 = re.match(r'\s*File "(.+)", line (\d+)', l)
        if m2:
            try:
                rel = Path(m2.group(1)).resolve().relative_to(racine)
                endroit = f" (fichier {rel}, ligne {m2.group(2)})"
            except (ValueError, OSError):
                pass

    nom_erreur = derniere.split(":")[0].strip()
    phrase = ERREURS_SIMPLES.get(nom_erreur, "Le programme s'est arrêté avec une erreur")
    return phrase + endroit + "."


def tester(chemin, fichier=None, delai=DELAI_PAR_DEFAUT):
    """Lance le projet (copie de travail) et dit honnêtement ce qui s'est passé."""
    chemin = Path(chemin)
    if not chemin.exists():
        raise FileNotFoundError(f"Je ne trouve pas : {chemin}")
    if chemin.parent.name != "copie":
        raise ValueError(
            "Je ne lance que la copie de travail, jamais l'original "
            "ni la copie de sécurité."
        )

    dossier = chemin if chemin.is_dir() else chemin.parent

    if fichier:
        script = (dossier / fichier).resolve()
        try:
            script.relative_to(dossier.resolve())
        except ValueError:
            raise ValueError("Le fichier à lancer doit être dans le projet.")
        if not script.is_file():
            raise FileNotFoundError(f"Je ne trouve pas : {fichier}")
    else:
        script = trouver_fichier_principal(chemin)
        if script is None:
            return ResultatTest(
                verdict="inconnu", delai=delai,
                explication=(
                    "Je ne sais pas quel fichier lancer. "
                    "Dis-le-moi : maison tester --fichier nom.py"
                ),
            )
        script = script.resolve()

    nom_script = str(script.relative_to(dossier.resolve()))
    avant = _contenu(dossier)

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONUNBUFFERED="1")
    options = {"start_new_session": True} if os.name == "posix" else {}
    processus = subprocess.Popen(
        [sys.executable, str(script)],
        cwd=str(dossier), env=env,
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        encoding="utf-8", errors="replace", **options,
    )
    trop_long = False
    try:
        sortie, erreur = processus.communicate(timeout=delai)
    except subprocess.TimeoutExpired:
        trop_long = True
        _tuer(processus)
        sortie, erreur = processus.communicate()

    resultat = ResultatTest(
        verdict="", fichier=nom_script, delai=delai,
        sortie=_fin(sortie), erreur=_fin(erreur), code_retour=processus.returncode,
        fichiers_changes=_changements(avant, _contenu(dossier)),
    )

    if trop_long:
        resultat.verdict = "tourne_encore"
        resultat.explication = (
            f"Le programme tournait encore après {delai} secondes "
            "(normal pour un jeu ou un serveur). Il ne plante pas au démarrage, "
            "mais je ne peux pas dire qu'il marche."
        )
    elif processus.returncode == 0:
        resultat.verdict = "marche"
        resultat.explication = "Le programme s'est lancé et terminé sans erreur."
    else:
        resultat.verdict = "plante"
        resultat.explication = _expliquer_plantage(erreur, dossier)
    return resultat
