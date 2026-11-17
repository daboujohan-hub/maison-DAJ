import os
import tempfile
import unittest
from pathlib import Path

from maison.copie import faire_copies, projets_recus, sont_identiques
from maison.maison import construire_maison


def _maison(d):
    racine, _ = construire_maison(d)
    return racine


class TestCopie(unittest.TestCase):
    def test_copie_un_fichier(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            jeu = racine / "entree" / "jeu.py"
            jeu.write_text("print('salut')")
            securite, copie = faire_copies(jeu, racine)
            self.assertEqual(securite.read_text(), "print('salut')")
            self.assertEqual(copie.read_text(), "print('salut')")
            self.assertNotEqual(securite, copie)

    def test_copie_un_dossier(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            projet = racine / "entree" / "monjeu"
            (projet / "sous").mkdir(parents=True)
            (projet / "main.py").write_text("x = 1")
            (projet / "sous" / "aide.py").write_text("y = 2")
            securite, copie = faire_copies(projet, racine)
            self.assertTrue(sont_identiques(projet, securite))
            self.assertTrue(sont_identiques(projet, copie))
            self.assertEqual((copie / "sous" / "aide.py").read_text(), "y = 2")

    def test_original_jamais_touche(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            jeu = racine / "entree" / "jeu.py"
            jeu.write_text("print('salut'")
            _, copie = faire_copies(jeu, racine)
            copie.write_text("print('salut')")  # on répare la copie
            self.assertEqual(jeu.read_text(), "print('salut'")

    def test_securite_reste_intacte_quand_on_repare(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            jeu = racine / "entree" / "jeu.py"
            jeu.write_text("cassé")
            securite, copie = faire_copies(jeu, racine)
            copie.write_text("réparé")
            self.assertEqual(securite.read_text(), "cassé")

    def test_ne_jamais_ecraser_une_copie_existante(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            jeu = racine / "entree" / "jeu.py"
            jeu.write_text("v1")
            s1, _ = faire_copies(jeu, racine)
            jeu.write_text("v2")
            s2, _ = faire_copies(jeu, racine)
            self.assertNotEqual(s1, s2)
            self.assertEqual(s1.read_text(), "v1")
            self.assertEqual(s2.read_text(), "v2")

    def test_projet_introuvable(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            with self.assertRaises(FileNotFoundError):
                faire_copies(racine / "entree" / "nexiste_pas.py", racine)

    def test_projets_recus_ignore_les_noms_caches(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            (racine / "entree" / "a.py").write_text("1")
            (racine / "entree" / ".cache").write_text("2")
            self.assertEqual([p.name for p in projets_recus(racine)], ["a.py"])

    @unittest.skipUnless(hasattr(os, "symlink"), "liens non supportés")
    def test_les_liens_ne_sont_pas_suivis(self):
        with tempfile.TemporaryDirectory() as d:
            racine = _maison(d)
            projet = racine / "entree" / "p"
            projet.mkdir()
            (projet / "lien").symlink_to("/etc")
            _, copie = faire_copies(projet, racine)
            self.assertTrue((copie / "lien").is_symlink())


if __name__ == "__main__":
    unittest.main()
