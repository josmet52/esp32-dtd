# Git / GitHub depuis VSCode

## Interface graphique (panneau Source Control)

- Ouvre le panneau avec **Ctrl+Shift+G**
- Les fichiers modifiés apparaissent sous **"Changes"**
- Clique **+** à côté d'un fichier pour le stager (`git add`)
- Saisis ton message de commit dans le champ en haut, puis **Ctrl+Enter** pour committer
- Clique **⋯ > Push** pour envoyer sur GitHub

---

## Terminal intégré (Ctrl+\`)

```bash
# Voir l'état des fichiers modifiés
git status

# Stager tous les fichiers modifiés
git add .

# Committer
git commit -m "description des changements"

# Pousser sur GitHub
git push

# Récupérer les changements depuis GitHub
git pull
```

---

## Workflow typique

1. Tu modifies des fichiers
2. `git add .` — tu prépares les changements
3. `git commit -m "..."` — tu enregistres un instantané
4. `git push` — tu envoies sur GitHub

---

## Extension utile

Installe **GitLens** dans VSCode (Extensions > chercher "GitLens") — elle affiche l'historique, les auteurs, et les diffs directement dans l'éditeur.
