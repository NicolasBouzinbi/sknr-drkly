# Utilisation du template

## Setup initial (une seule fois)

1. Créer un repo GitHub avec ce contenu
2. Dans **Settings > General** : cocher **"Template repository"**

## Pour chaque nouveau projet

1. Sur GitHub : **"Use this template"** → **"Create a new repository"**
2. Cloner le nouveau repo localement
3. Rechercher-remplacer (VSCode : `Ctrl+Shift+H`) :
   - `{{PROJECT_NAME}}` → nom du projet
   - `{{PROJECT_DESCRIPTION}}` → description
   - `{{YEAR}}` → année en cours
   - `{{AUTHOR_NAME}}` → ton nom
4. LICENSE : mettre à jour ou supprimer selon le type de projet (client = supprimer, open source = garder)
5. Activer la CI : renommer `.github/workflows/ci.yml.disabled` → `ci.yml`
6. Supprimer ce fichier `TEMPLATE.md`
7. Setup :

**Prérequis** : Python 3.13+, [uv](https://github.com/astral-sh/uv) (`pip install uv`)

```bash
uv venv && .venv\Scripts\activate  # Windows
uv sync --group dev
pre-commit install
cp .env.example .env
```

8. Ajouter les dépendances spécifiques au projet :

```bash
uv add pandas duckdb  # etc.
```

9. Premier commit :

```bash
git add .
git commit -m "Initial setup from template"
git push
```
