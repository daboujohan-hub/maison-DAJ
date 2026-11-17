# SUIVI DU PROJET : LA MAISON

*Dernière mise à jour : 17 novembre 2026*
*À lire en premier quand on reprend le travail.*

## Où on en est

| Fonction du cahier des charges | État |
|---|---|
| 1. Construire la maison | fait |
| 2. Préparer proprement (ménage, vérifier ce qui manque) | **à faire** |
| 3. Recevoir le projet | fait |
| 4. Faire les copies (sécurité + travail) | fait |
| 5. Diagnostic | fait (Python) |
| 6. Utiliser les outils du langage | fait pour Python (module `ast`) |
| 7. Réparer | fait (3 cas simples) |
| 8. Outils manquants sans internet | **à faire** (aujourd'hui : le rapport dit quoi installer) |
| 9. Tester | fait |
| 10. Rendre la copie dans `sortie` | **à faire** (aujourd'hui : copier à la main) |
| 11. Toutes les langues | **à faire** (Python seulement) |

73 tests automatiques, tous verts. Installé et essayé dans Termux.

## Décisions prises

- Version 0.1 : **Python seulement**. Les autres langages viendront un par un.
- **On ne publie pas sur PyPI pour l'instant.** On crée d'abord le dépôt Git.
- La maison ne ment jamais : un test qui tourne encore n'est pas « ça marche ».
- Elle ne corrige que ce dont elle est sûre, et revérifie avec Python après chaque correction.
- Elle ne lance et ne répare jamais l'original ni la copie de sécurité.

## Prochaines étapes (dans cet ordre conseillé)

1. **Fonction 10** : mettre le projet réparé dans `sortie` sous le nom
   `<nom>-repare`, avec le `rapport.txt`.
2. **Fonction 2** : préparer proprement (fichiers vides, rapport vide,
   vérifier que les fichiers cités existent).
3. **Plus de règles de réparation** : guillemet non fermé, décalage (indentation),
   mélange tabulations/espaces. Une règle à la fois, avec ses tests.
4. **Fonction 8** : chercher les paquets déjà présents dans le téléphone
   (par exemple un dossier de paquets téléchargés avec internet).
5. **Autres langages** : HTML, JavaScript, Bash, un par un, avec les outils de ce langage.
6. **Avant de publier sur PyPI** : vérifier que le nom `la-maison` est libre,
   choisir la licence et le titulaire (`pyproject.toml` dit MIT), ajouter un
   `LICENSE`, anglais + français pour les messages, essayer l'installation
   dans un environnement vide.

## Mettre le dépôt en ligne (Termux)

```
cd ~/ESPACE.DE.TRAVAIL/la-maison
git config --global user.name "TON NOM"
git config --global user.email "ton@email"
git init
git add .
git status
git commit -m "LA MAISON 0.1.0 : base (Python seulement)"
git branch -M main
git remote add origin https://github.com/TON-COMPTE/la-maison.git
git push -u origin main
```

Avant le `git commit`, regarde le résultat de `git status` : il ne doit y avoir
**aucun fichier secret** (clé, mot de passe, `.json` de configuration).
Crée le dépôt GitHub **privé** et **vide** (sans README) avant le `git push`.
GitHub demande un *token* (jeton d'accès) à la place du mot de passe.

## Reprendre le travail avec Claude

Dire : « Je reprends LA MAISON », coller le contenu de ce fichier et de
`README.md`, et dire quelle étape on fait. Les fichiers du code se trouvent
dans le dossier `maison/`.

## Habitudes à garder

- Toujours lancer les commandes depuis le même dossier (celui qui contient `ma-maison`).
- Après chaque changement : `python -m unittest discover`.
- Une fonction à la fois, avec ses tests, avant de passer à la suivante.
