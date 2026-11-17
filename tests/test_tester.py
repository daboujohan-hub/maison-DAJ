import tempfile
import time
import unittest
from pathlib import Path

from maison.copie import faire_copies
from maison.maison import construire_maison
from maison.tester import tester


def _copie(d, nom, contenu):
    racine, _ = construire_maison(d)
    original = racine / "entree" / nom
    original.parent.mkdir(parents=True, exist_ok=True)
    original.write_text(contenu, encoding="utf-8")
    securite, copie = faire_copies(original, racine)
    return original, securite, copie


class TestVerdicts(unittest.TestCase):
    def test_marche(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "print('salut')\n")
            r = tester(copie)
            self.assertEqual(r.verdict, "marche")
            self.assertIn("salut", r.sortie)
            self.assertEqual(r.fichier, "a.py")

    def test_plante_nom_inconnu(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "x = 1\ny = x + zzz\n")
            r = tester(copie)
            self.assertEqual(r.verdict, "plante")
            self.assertIn("ligne 2", r.explication)
            self.assertIn("NameError", r.erreur)

    def test_paquet_manquant_a_l_execution(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "import zzz_absent\n")
            r = tester(copie)
            self.assertEqual(r.verdict, "plante")
            self.assertIn("Il manque le paquet « zzz_absent »", r.explication)

    def test_tourne_encore_n_est_pas_un_succes(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "import time\nprint('debut', flush=True)\ntime.sleep(60)\n")
            debut = time.time()
            r = tester(copie, delai=1)
            self.assertLess(time.time() - debut, 15)
            self.assertEqual(r.verdict, "tourne_encore")
            self.assertIn("debut", r.sortie)

    def test_pas_de_clavier(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "nom = input('nom ? ')\n")
            r = tester(copie, delai=5)
            self.assertEqual(r.verdict, "plante")
            self.assertIn("EOFError", r.erreur)


class TestSurete(unittest.TestCase):
    def test_ne_lance_jamais_l_original_ni_la_securite(self):
        with tempfile.TemporaryDirectory() as d:
            marque = "open('marqueur.txt', 'w').write('lancé')\n"
            original, securite, _ = _copie(d, "a.py", marque)
            with self.assertRaises(ValueError):
                tester(original)
            with self.assertRaises(ValueError):
                tester(securite)
            self.assertFalse((original.parent / "marqueur.txt").exists())
            self.assertFalse((securite.parent / "marqueur.txt").exists())

    def test_le_programme_travaille_dans_la_copie(self):
        with tempfile.TemporaryDirectory() as d:
            original, _, copie = _copie(d, "a.py", "open('sortie.txt', 'w').write('x')\n")
            r = tester(copie)
            self.assertEqual(r.verdict, "marche")
            self.assertIn("créé : sortie.txt", r.fichiers_changes)
            self.assertTrue((copie.parent / "sortie.txt").exists())
            self.assertFalse((original.parent / "sortie.txt").exists())
            self.assertFalse(Path("sortie.txt").exists())

    def test_pas_de_pycache_dans_la_copie(self):
        with tempfile.TemporaryDirectory() as d:
            racine, _ = construire_maison(d)
            projet = racine / "entree" / "jeu"
            projet.mkdir()
            (projet / "main.py").write_text("import aide\nprint(aide.X)\n")
            (projet / "aide.py").write_text("X = 42\n")
            _, copie = faire_copies(projet, racine)
            r = tester(copie)
            self.assertEqual(r.verdict, "marche")
            self.assertIn("42", r.sortie)
            self.assertEqual(r.fichiers_changes, [])
            self.assertFalse((copie / "__pycache__").exists())

    def test_introuvable(self):
        with self.assertRaises(FileNotFoundError):
            tester("/chemin/qui/nexiste/pas")


class TestChoixDuFichier(unittest.TestCase):
    def _projet(self, d, fichiers):
        racine, _ = construire_maison(d)
        projet = racine / "entree" / "jeu"
        projet.mkdir()
        for nom, contenu in fichiers.items():
            (projet / nom).write_text(contenu)
        _, copie = faire_copies(projet, racine)
        return copie

    def test_main_py_trouve(self):
        with tempfile.TemporaryDirectory() as d:
            copie = self._projet(d, {"main.py": "print('principal')\n", "autre.py": "print('autre')\n"})
            r = tester(copie)
            self.assertEqual(r.verdict, "marche")
            self.assertEqual(r.fichier, "main.py")

    def test_un_seul_fichier(self):
        with tempfile.TemporaryDirectory() as d:
            copie = self._projet(d, {"jeu.py": "print('seul')\n"})
            self.assertEqual(tester(copie).fichier, "jeu.py")

    def test_plusieurs_fichiers_sans_principal(self):
        with tempfile.TemporaryDirectory() as d:
            copie = self._projet(d, {"a.py": "print(1)\n", "b.py": "print(2)\n"})
            r = tester(copie)
            self.assertEqual(r.verdict, "inconnu")
            self.assertIn("--fichier", r.explication)

    def test_option_fichier(self):
        with tempfile.TemporaryDirectory() as d:
            copie = self._projet(d, {"a.py": "print(1)\n", "b.py": "print('deux')\n"})
            r = tester(copie, fichier="b.py")
            self.assertEqual(r.verdict, "marche")
            self.assertIn("deux", r.sortie)

    def test_option_fichier_hors_du_projet_refusee(self):
        with tempfile.TemporaryDirectory() as d:
            copie = self._projet(d, {"a.py": "print(1)\n"})
            with self.assertRaises(ValueError):
                tester(copie, fichier="../../../../../../etc/passwd")


if __name__ == "__main__":
    unittest.main()
