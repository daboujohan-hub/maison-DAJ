import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

RACINE_PROJET = str(Path(__file__).resolve().parent.parent)


def _lancer(dossier, *args, entree=""):
    env = dict(os.environ, PYTHONPATH=RACINE_PROJET)
    return subprocess.run(
        [sys.executable, "-m", "maison.cli", *args],
        cwd=dossier, env=env, capture_output=True, text=True, input=entree,
    )


class TestCommandes(unittest.TestCase):
    def test_de_bout_en_bout(self):
        with tempfile.TemporaryDirectory() as d:
            r = _lancer(d, "construire")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("Maison construite", r.stdout)

            (Path(d) / "ma-maison" / "entree" / "jeu.py").write_text(
                "import zzz_absent\nprint('salut')\n")

            r = _lancer(d, "diagnostiquer")
            self.assertEqual(r.returncode, 1)
            self.assertIn("maison copier", r.stdout)

            r = _lancer(d, "copier")
            self.assertEqual(r.returncode, 0, r.stderr)

            r = _lancer(d, "diagnostiquer")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("zzz_absent", r.stdout)
            rapports = list(Path(d).rglob("rapport.txt"))
            self.assertEqual(len(rapports), 1)
            self.assertIn("zzz_absent", rapports[0].read_text(encoding="utf-8"))

            original = (Path(d) / "ma-maison" / "entree" / "jeu.py").read_text()
            self.assertEqual(original, "import zzz_absent\nprint('salut')\n")

    def test_reparer_de_bout_en_bout(self):
        with tempfile.TemporaryDirectory() as d:
            _lancer(d, "construire")
            original = Path(d) / "ma-maison" / "entree" / "jeu.py"
            original.write_text("print('salut'\n")

            r = _lancer(d, "reparer")
            self.assertEqual(r.returncode, 1)
            self.assertIn("maison copier", r.stdout)

            _lancer(d, "copier")
            r = _lancer(d, "reparer")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("J'ai corrigé 1 problème", r.stdout)

            copie = next(Path(d).rglob("copie/jeu.py"))
            securite = next(Path(d).rglob("securite/jeu.py"))
            self.assertEqual(copie.read_text(), "print('salut')\n")
            self.assertEqual(securite.read_text(), "print('salut'\n")
            self.assertEqual(original.read_text(), "print('salut'\n")
            rapport = next(Path(d).rglob("rapport.txt")).read_text(encoding="utf-8")
            self.assertIn("RÉPARATION", rapport)

    def test_tester_marche_et_plante(self):
        with tempfile.TemporaryDirectory() as d:
            _lancer(d, "construire")
            original = Path(d) / "ma-maison" / "entree" / "jeu.py"
            original.write_text("print('salut')\n")
            _lancer(d, "copier")
            r = _lancer(d, "tester", "--oui")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("ÇA MARCHE", r.stdout)

            original.write_text("x = zzz\n")
            _lancer(d, "copier")
            r = _lancer(d, "tester", "--oui")
            self.assertEqual(r.returncode, 1)
            self.assertIn("ÇA PLANTE", r.stdout)
            self.assertIn("Je refais un diagnostic", r.stdout)
            rapport = next(Path(d).rglob("jeu.py-2/rapport.txt")).read_text(encoding="utf-8")
            self.assertIn("TEST DE", rapport)

    def test_tester_demande_confirmation(self):
        with tempfile.TemporaryDirectory() as d:
            _lancer(d, "construire")
            (Path(d) / "ma-maison" / "entree" / "jeu.py").write_text(
                "open('marqueur.txt', 'w').write('lancé')\n")
            _lancer(d, "copier")

            r = _lancer(d, "tester", entree="n\n")
            self.assertEqual(r.returncode, 1)
            self.assertIn("je ne le lance pas", r.stdout)
            self.assertEqual(list(Path(d).rglob("marqueur.txt")), [])

            r = _lancer(d, "tester")  # pas de réponse du tout : on ne lance pas
            self.assertEqual(list(Path(d).rglob("marqueur.txt")), [])

            r = _lancer(d, "tester", entree="o\n")
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertEqual(len(list(Path(d).rglob("marqueur.txt"))), 1)

    def test_sans_maison(self):
        with tempfile.TemporaryDirectory() as d:
            for commande in ("copier", "diagnostiquer", "reparer", "tester"):
                r = _lancer(d, commande)
                self.assertEqual(r.returncode, 1)
                self.assertIn("maison construire", r.stdout)


if __name__ == "__main__":
    unittest.main()
