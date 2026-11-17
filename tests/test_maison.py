import tempfile
import unittest
from pathlib import Path

from maison.maison import NOM_DOSSIER, PIECES, construire_maison


class TestConstruireMaison(unittest.TestCase):
    def test_cree_les_trois_pieces(self):
        with tempfile.TemporaryDirectory() as d:
            racine, nouvelle = construire_maison(d)
            self.assertTrue(nouvelle)
            self.assertEqual(racine.name, NOM_DOSSIER)
            for piece in PIECES:
                self.assertTrue((racine / piece).is_dir())

    def test_maison_existante_pas_recreee(self):
        with tempfile.TemporaryDirectory() as d:
            construire_maison(d)
            _, nouvelle = construire_maison(d)
            self.assertFalse(nouvelle)

    def test_ne_supprime_jamais_rien(self):
        with tempfile.TemporaryDirectory() as d:
            racine, _ = construire_maison(d)
            fichier = racine / "entree" / "jeu.py"
            fichier.write_text("print('salut')")
            construire_maison(d)
            self.assertEqual(fichier.read_text(), "print('salut')")

    def test_repare_une_piece_manquante(self):
        with tempfile.TemporaryDirectory() as d:
            racine, _ = construire_maison(d)
            (racine / "sortie").rmdir()
            _, nouvelle = construire_maison(d)
            self.assertFalse(nouvelle)
            self.assertTrue((racine / "sortie").is_dir())


if __name__ == "__main__":
    unittest.main()
