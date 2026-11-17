import tempfile
import unittest
from pathlib import Path

from maison.copie import faire_copies
from maison.maison import construire_maison
from maison.reparer import reparer


def _copie(d, nom, contenu, binaire=False):
    """Met un projet dans entree, fait les copies, retourne (original, securite, copie)."""
    racine, _ = construire_maison(d)
    original = racine / "entree" / nom
    original.parent.mkdir(parents=True, exist_ok=True)
    if binaire:
        original.write_bytes(contenu)
    else:
        original.write_text(contenu, encoding="utf-8")
    securite, copie = faire_copies(original, racine)
    return original, securite, copie


def _compile(texte):
    compile(texte, "x", "exec")


class TestCasSimples(unittest.TestCase):
    def _reparer(self, avant, apres):
        with tempfile.TemporaryDirectory() as d:
            original, securite, copie = _copie(d, "a.py", avant)
            r = reparer(copie)
            self.assertEqual(copie.read_text(encoding="utf-8"), apres)
            self.assertEqual(r.non_corriges, [])
            _compile(copie.read_text(encoding="utf-8"))
            # l'original et la sécurité ne bougent jamais
            self.assertEqual(original.read_text(encoding="utf-8"), avant)
            self.assertEqual(securite.read_text(encoding="utf-8"), avant)
            return r

    def test_parenthese_manquante(self):
        r = self._reparer("print('salut'\n", "print('salut')\n")
        self.assertEqual(len(r.corrections), 1)
        self.assertEqual(r.corrections[0].ligne, 1)
        self.assertEqual(r.fichiers_modifies, 1)

    def test_crochet_et_parenthese(self):
        self._reparer("x = list([1, 2\n", "x = list([1, 2])\n")

    def test_parenthese_et_commentaire(self):
        self._reparer("print('salut'  # dit bonjour\n", "print('salut')  # dit bonjour\n")

    def test_signe_dans_un_texte_pas_compte(self):
        self._reparer('print("("\n', 'print("(")\n')

    def test_deux_points_manquants(self):
        self._reparer("x = 1\nif x == 1\n    print(x)\n", "x = 1\nif x == 1:\n    print(x)\n")

    def test_else_sans_deux_points(self):
        self._reparer("x = 1\nif x:\n    pass\nelse\n    pass\n",
                      "x = 1\nif x:\n    pass\nelse:\n    pass\n")

    def test_def_sans_deux_points(self):
        self._reparer("def f(a, b)\n    return a\n", "def f(a, b):\n    return a\n")

    def test_parenthese_avant_deux_points(self):
        self._reparer("x = 2\nif (x > 1:\n    print(x)\n", "x = 2\nif (x > 1):\n    print(x)\n")

    def test_print_python2(self):
        self._reparer("print 'salut'\n", "print('salut')\n")

    def test_print_python2_avec_format_et_commentaire(self):
        self._reparer("x = 3\nprint 'x vaut %s' % x  # affiche\n",
                      "x = 3\nprint('x vaut %s' % x)  # affiche\n")

    def test_plusieurs_erreurs_dans_un_fichier(self):
        avant = (
            "print 'debut'\n"
            "x = 1\n"
            "if x == 1\n"
            "    print('un'\n"
            "def f(a)\n"
            "    return a\n"
        )
        apres = (
            "print('debut')\n"
            "x = 1\n"
            "if x == 1:\n"
            "    print('un')\n"
            "def f(a):\n"
            "    return a\n"
        )
        r = self._reparer(avant, apres)
        self.assertEqual(len(r.corrections), 4)


class TestSurete(unittest.TestCase):
    def test_cas_incompris_pas_touche(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "def f(:\n    pass\n")
            r = reparer(copie)
            self.assertEqual(r.corrections, [])
            self.assertEqual(copie.read_text(), "def f(:\n    pass\n")
            self.assertEqual(len(r.non_corriges), 1)

    def test_correction_annulee_si_python_n_avance_pas(self):
        # "foo(1 2" + ")" serait encore faux : on garde le fichier tel quel
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "foo(1 2\n")
            r = reparer(copie)
            self.assertEqual(r.corrections, [])
            self.assertEqual(copie.read_text(), "foo(1 2\n")
            self.assertEqual(len(r.non_corriges), 1)

    def test_ligne_qui_continue_pas_touchee(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "x = foo(1,\n")
            r = reparer(copie)
            self.assertEqual(r.corrections, [])
            self.assertEqual(copie.read_text(), "x = foo(1,\n")

    def test_fichier_correct_pas_reecrit(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "print('ok')\n")
            r = reparer(copie)
            self.assertEqual(r.corrections, [])
            self.assertEqual(r.fichiers_modifies, 0)
            self.assertEqual(r.non_corriges, [])

    def test_refuse_de_reparer_l_original_et_la_securite(self):
        with tempfile.TemporaryDirectory() as d:
            original, securite, _ = _copie(d, "a.py", "print('salut'\n")
            with self.assertRaises(ValueError):
                reparer(original)
            with self.assertRaises(ValueError):
                reparer(securite)
            self.assertEqual(original.read_text(), "print('salut'\n")
            self.assertEqual(securite.read_text(), "print('salut'\n")

    def test_introuvable(self):
        with self.assertRaises(FileNotFoundError):
            reparer("/chemin/qui/nexiste/pas")

    def test_fins_de_ligne_et_accents_gardes(self):
        with tempfile.TemporaryDirectory() as d:
            _, _, copie = _copie(d, "a.py", "print('é'\r\nx = 1\r\n".encode("utf-8"), binaire=True)
            reparer(copie)
            self.assertEqual(copie.read_bytes(), "print('é')\r\nx = 1\r\n".encode("utf-8"))

    def test_bom_garde(self):
        with tempfile.TemporaryDirectory() as d:
            donnees = b"\xef\xbb\xbfprint('salut'\n"
            _, _, copie = _copie(d, "a.py", donnees, binaire=True)
            reparer(copie)
            self.assertEqual(copie.read_bytes(), b"\xef\xbb\xbfprint('salut')\n")


class TestProjetDossier(unittest.TestCase):
    def test_plusieurs_fichiers_et_autres_intacts(self):
        with tempfile.TemporaryDirectory() as d:
            racine, _ = construire_maison(d)
            projet = racine / "entree" / "jeu"
            (projet / "sous").mkdir(parents=True)
            (projet / "main.py").write_text("print('a'\n")
            (projet / "sous" / "aide.py").write_text("x = 1\nif x\n    pass\n")
            (projet / "ok.py").write_text("y = 2\n")
            (projet / "page.html").write_text("<p>pas de python (")
            _, copie = faire_copies(projet, racine)
            r = reparer(copie)
            self.assertEqual(len(r.corrections), 2)
            self.assertEqual(r.fichiers_modifies, 2)
            self.assertEqual((copie / "main.py").read_text(), "print('a')\n")
            self.assertEqual((copie / "sous" / "aide.py").read_text(), "x = 1\nif x:\n    pass\n")
            self.assertEqual((copie / "page.html").read_text(), "<p>pas de python (")
            self.assertEqual((projet / "main.py").read_text(), "print('a'\n")


if __name__ == "__main__":
    unittest.main()
