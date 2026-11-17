# LA MAISON 🏠

Un petit mécanicien pour les projets Python cassés.
Il vit dans le téléphone (Termux) et travaille **sans internet**.

> **État : version 0.1.0, en développement.**
> Pas encore publiée sur PyPI. Python seulement.
> Voir `SUIVI.md` pour savoir ce qui est fait et ce qui reste à faire.

## Les 3 règles

1. **Elle ne touche jamais à l'original.** Elle travaille sur une copie.
2. **Elle ne ment jamais.** Si elle n'a pas pu réparer, elle le dit.
3. **Elle parle en français simple.**

## Installer

Dans Termux, depuis le dossier du projet :

```
cd la-maison
pip install -e .
maison --version
```

Avec `-e`, si tu modifies le code, tu n'as pas besoin de réinstaller.

## Utiliser, pas à pas

**Important :** lance toutes les commandes **depuis le même dossier**
(par exemple `~/ESPACE.DE.TRAVAIL`). C'est là que `ma-maison` est créée,
et c'est là que les commandes la retrouvent.

**1. Construire la maison** (une seule fois)

```
maison construire
```

**2. Mettre le projet cassé dans `entree`** (un fichier ou un dossier)

```
cp mon_jeu.py ma-maison/entree/
cp -r mon_projet ma-maison/entree/
```

**3. Faire les copies**

```
maison copier
```

**4. Voir ce qui est cassé** (facultatif, `reparer` le fait déjà)

```
maison diagnostiquer
```

**5. Réparer**

```
maison reparer
```

**6. Tester** (elle demande confirmation avant de lancer ton programme)

```
maison tester
```

**7. Récupérer le projet réparé**

La Fonction 10 (rendre dans `sortie`) n'est pas encore faite. Pour l'instant,
le projet réparé reste dans le dossier `copie`. Chaque commande affiche son
chemin (« Copie réparée : ... »). Copie-le où tu veux :

```
cp ma-maison/travail/jeu.py/copie/jeu.py ~/mon_jeu_repare.py
```

Si tu relances `maison copier`, un nouveau dossier est créé (`jeu.py-2`,
`jeu.py-3`...). **Le plus grand numéro est le plus récent**, et c'est
toujours celui que les commandes utilisent. Rien n'est jamais écrasé.

## Où sont les fichiers

```
ma-maison/
├── entree/                  ← ton projet cassé (jamais modifié)
├── travail/
│   └── jeu.py/              ← un dossier par passage (jeu.py-2, jeu.py-3...)
│       ├── securite/jeu.py  ← copie de sécurité (on n'y touche plus)
│       ├── copie/jeu.py     ← copie de travail (celle qu'on répare)
│       └── rapport.txt      ← le carnet : tout ce qu'elle a fait
└── sortie/                  ← vide pour l'instant
```

## Les commandes

| Commande | Ce qu'elle fait |
|---|---|
| `maison construire` | crée `ma-maison` (si elle existe, rien n'est effacé) |
| `maison copier` | copie de sécurité + copie de travail, puis vérifie qu'elles sont identiques à l'original |
| `maison diagnostiquer` | cherche ce qui est cassé, écrit `rapport.txt`. Ne modifie rien, ne lance rien |
| `maison reparer` | corrige les cas simples dans la copie de travail |
| `maison tester` | lance la copie et dit si ça marche |

Options de `maison tester` :
`--oui` (ne pas demander confirmation), `--fichier nom.py` (quel fichier
lancer), `--delai 30` (secondes maximum, 10 par défaut).

## Ce qu'elle sait réparer toute seule

Seulement les cas dont elle est **sûre** :

| Avant | Après |
|---|---|
| `print('salut'` | `print('salut')` |
| `if x == 1` | `if x == 1:` |
| `print 'salut'` | `print('salut')` |

Après chaque correction, Python revérifie le fichier. Si la correction
n'améliore rien, elle est annulée.

## Ce qu'elle ne répare pas

Tout le reste. Dans ce cas elle ne touche à rien et le rapport dit
« Celui-là, je ne l'ai pas compris : regarde ici (fichier, ligne) ».

Un **paquet manquant** (comme `pygame`) : sans internet elle ne peut pas
l'installer. Le rapport donne la commande (`pip install pygame`) à faire
quand tu seras connecté.

## Les 4 résultats du test

| Résultat | Ce que ça veut dire |
|---|---|
| **ÇA MARCHE** | le programme s'est lancé et terminé sans erreur (ça ne prouve pas qu'il fait ce que tu veux) |
| **ÇA PLANTE** | il s'est arrêté avec une erreur, expliquée en français, puis elle refait un diagnostic |
| **TOURNE ENCORE** | il tournait encore après le délai (jeu, serveur...). Elle ne dit pas « ça marche » |
| **JE NE SAIS PAS** | elle ne sait pas quel fichier lancer : utilise `--fichier` |

## Sécurité du test

- Elle demande confirmation, car lancer un programme, c'est l'exécuter pour de vrai.
  La copie protège ton original, **pas le reste du téléphone**.
- Elle ne lance jamais l'original ni la copie de sécurité.
- Le programme n'a pas de clavier (il ne peut pas attendre une réponse).
- Les fichiers que le programme crée ou change sont listés dans le rapport.

## Pour les développeurs

```
la-maison/
├── pyproject.toml
├── maison/
│   ├── cli.py          # la commande `maison`
│   ├── maison.py       # Fonction 1 : construire la maison
│   ├── copie.py        # Fonctions 3 et 4 : recevoir, copies
│   ├── diagnostic.py   # Fonction 5 : diagnostic (Python lui-même, module ast)
│   ├── reparer.py      # Fonction 7 : réparer (les règles sont dans REGLES)
│   ├── tester.py       # Fonction 9 : tester
│   └── rapport.py      # le rapport.txt
└── tests/
```

Lancer les tests :

```
python -m unittest discover
```

Ajouter une règle de réparation : écrire une fonction dans `reparer.py`
(elle reçoit une ligne, rend la ligne corrigée ou `None`), l'ajouter à
`REGLES`, puis écrire ses tests dans `tests/test_reparer.py`.

## Limites actuelles

- Python seulement.
- Python s'arrête au premier problème d'écriture de chaque fichier :
  la maison corrige donc un par un, en revérifiant.
- Pas encore faits : Fonction 2 (préparer proprement), Fonction 8 (chercher
  un outil déjà présent dans le téléphone), Fonction 10 (rendre dans `sortie`),
  Fonction 11 (autres langages).
