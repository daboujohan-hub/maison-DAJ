import sys
import tempfile
import unittest
from pathlib import Path

from maison.copie import derniere_copie, faire_copies
from maison.diagnostic import diagnostiquer
from maison.maison import construire_maison
from maison.rapport import texte_diagnostic


def _ecrire(dossier, nom, texte):
    p = Path(dossier) / nom
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte, encoding="utf-8")
    return p


class TestSyntaxe(unittest.TestCase):
    def _un_probleme(self, code):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", code)
            r = diagnostiquer(f)
            self.assertEqual(len(r.problemes), 1, r.problemes)
            return r.problemes[0]

    def test_fichier_correct(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "import os, json\nprint('ok')\n")
            r = diagnostiquer(f)
            self.assertEqual(r.problemes, [])
            self.assertEqual(r.fichiers_python, 1)

    def test_parenthese_manquante(self):
        p = self._un_probleme("print('salut'\n")
        self.assertEqual(p.genre, "syntaxe")
        if sys.version_info >= (3, 10):
            self.assertEqual(p.ligne, 1)
            self.assertIn("Il manque un « ) »", p.explication)

    def test_guillemet_non_ferme(self):
        p = self._un_probleme("x = 'salut\n")
        self.assertEqual(p.genre, "syntaxe")
        self.assertEqual(p.ligne, 1)
        self.assertIn("guillemet", p.explication)

    def test_deux_points_manquants(self):
        p = self._un_probleme("x = 1\nif x == 1\n    print(x)\n")
        self.assertEqual(p.ligne, 2)
        self.assertIn("deux-points", p.explication)

    def test_decalage_manquant(self):
        p = self._un_probleme("def f():\nprint(1)\n")
        self.assertEqual(p.genre, "syntaxe")
        self.assertIn("décal", p.explication)

    def test_print_python2(self):
        p = self._un_probleme("print 'salut'\n")
        self.assertEqual(p.genre, "syntaxe")
        self.assertEqual(p.ligne, 1)

    def test_extrait_de_la_ligne(self):
        p = self._un_probleme("x = 1\nif x == 1\n    print(x)\n")
        self.assertIn("if x == 1", p.extrait)

    def test_mauvais_encodage(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "a.py"
            f.write_bytes(b"x = '\xff\xfe'\n")
            r = diagnostiquer(f)
            self.assertEqual(len(r.problemes), 1)


class TestImports(unittest.TestCase):
    def test_paquet_manquant(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "x = 1\nimport un_paquet_qui_nexiste_pas_123\n")
            r = diagnostiquer(f)
            self.assertEqual(len(r.problemes), 1)
            p = r.problemes[0]
            self.assertEqual(p.genre, "paquet_manquant")
            self.assertEqual(p.ligne, 2)
            self.assertIn("pip install un_paquet_qui_nexiste_pas_123", p.detail)

    def test_nom_pip_different(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "import PIL_introuvable_xyz\nimport yaml_non\n")
            r = diagnostiquer(f)
            self.assertEqual(len(r.problemes), 2)

    def test_module_du_projet_pas_signale(self):
        with tempfile.TemporaryDirectory() as d:
            _ecrire(d, "main.py", "import aide\nfrom outils import x\n")
            _ecrire(d, "aide.py", "y = 1\n")
            _ecrire(d, "outils/__init__.py", "x = 1\n")
            r = diagnostiquer(d)
            self.assertEqual(r.problemes, [])

    def test_import_optionnel_pas_signale(self):
        code = "try:\n    import paquet_optionnel_xyz\nexcept ImportError:\n    paquet_optionnel_xyz = None\n"
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", code)
            self.assertEqual(diagnostiquer(f).problemes, [])

    def test_import_relatif_pas_signale(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "from . import quelquechose\nfrom .truc import x\n")
            self.assertEqual(diagnostiquer(f).problemes, [])

    def test_meme_paquet_signale_une_fois(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "import zzz_absent\nimport zzz_absent\nfrom zzz_absent import b\n")
            self.assertEqual(len(diagnostiquer(f).problemes), 1)


class TestProjet(unittest.TestCase):
    def test_dossier_ignores_et_autres_fichiers(self):
        with tempfile.TemporaryDirectory() as d:
            _ecrire(d, "main.py", "print(1)\n")
            _ecrire(d, "__pycache__/cache.py", "print(1\n")
            _ecrire(d, ".git/x.py", "print(1\n")
            _ecrire(d, "page.html", "<p>")
            _ecrire(d, "notes.txt", "salut")
            r = diagnostiquer(d)
            self.assertEqual(r.problemes, [])
            self.assertEqual(r.fichiers_python, 1)
            self.assertEqual(r.fichiers_ignores, 2)

    def test_nom_relatif_dans_un_dossier(self):
        with tempfile.TemporaryDirectory() as d:
            _ecrire(d, "sous/a.py", "print(1\n")
            r = diagnostiquer(d)
            self.assertEqual(r.problemes[0].fichier, str(Path("sous") / "a.py"))

    def test_ne_modifie_rien(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "print('salut'\n")
            avant = f.read_bytes()
            diagnostiquer(d)
            self.assertEqual(f.read_bytes(), avant)

    def test_ne_lance_jamais_le_code(self):
        with tempfile.TemporaryDirectory() as d:
            _ecrire(d, "piege.py", "open('piege.txt', 'w').write('lancé')\n")
            diagnostiquer(d)
            self.assertFalse((Path(d) / "piege.txt").exists())
            self.assertFalse(Path("piege.txt").exists())

    def test_introuvable(self):
        with self.assertRaises(FileNotFoundError):
            diagnostiquer("/chemin/qui/nexiste/pas")


class TestRapportEtCopie(unittest.TestCase):
    def test_rapport_avec_problemes(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "print('salut'\n")
            texte = texte_diagnostic("a.py", diagnostiquer(f))
            self.assertIn("J'ai trouvé 1 problème", texte)
            self.assertIn("a.py", texte)
            self.assertIn("premier problème", texte)
            self.assertIn("pas encore vérifiés", texte)

    def test_rapport_sans_probleme_reste_honnete(self):
        with tempfile.TemporaryDirectory() as d:
            f = _ecrire(d, "a.py", "print(1)\n")
            texte = texte_diagnostic("a.py", diagnostiquer(f))
            self.assertIn("ne prouve pas", texte)

    def test_derniere_copie(self):
        with tempfile.TemporaryDirectory() as d:
            racine, _ = construire_maison(d)
            jeu = racine / "entree" / "jeu.py"
            jeu.write_text("v1")
            self.assertIsNone(derniere_copie(racine, "jeu.py"))
            _, c1 = faire_copies(jeu, racine)
            self.assertEqual(derniere_copie(racine, "jeu.py"), c1)
            jeu.write_text("v2")
            _, c2 = faire_copies(jeu, racine)
            self.assertEqual(derniere_copie(racine, "jeu.py"), c2)
            self.assertNotEqual(c1, c2)


if __name__ == "__main__":
    unittest.main()
