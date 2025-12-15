import os

# --- CONFIGURATION ---
OUTPUT_FILENAME = "FULL_PROJECT_CONTEXT.txt"

# Dossiers et fichiers à IGNORER
IGNORE_DIRS = {
    'venv', '.venv', 'env', '.git', '__pycache__', '.idea', '.vscode',
    'node_modules', 'dist', 'build', 'site-packages', 'migrations',
    '__MACOSX', 'media', 'static'
}

IGNORE_EXTENSIONS = {
    '.pyc', '.pyo', '.pyd', '.db', '.sqlite3', '.log',
    '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf',
    '.zip', '.tar', '.gz', '.rar', '.7z', '.exe'
}

IGNORE_FILES = {
    os.path.basename(__file__),
    OUTPUT_FILENAME,
    'package-lock.json',
    '.DS_Store'
}


def is_ignored(path, filename):
    parts = path.split(os.sep)
    if any(part in IGNORE_DIRS for part in parts):
        return True
    if filename in IGNORE_FILES:
        return True
    if filename.startswith('.'):
        return True
    if any(filename.endswith(ext) for ext in IGNORE_EXTENSIONS):
        return True
    return False


def generate_tree(startpath):
    """Génère une arborescence visuelle pour l'IA"""
    tree_str = "PROJECT STRUCTURE:\n"
    tree_str += ".\n"

    for root, dirs, files in os.walk(startpath):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        level = root.replace(startpath, '').count(os.sep)
        indent = '│   ' * (level)
        subindent = '│   ' * (level + 1)

        # Ne pas ré-afficher la racine
        if root != startpath:
            tree_str += f"{indent}├── {os.path.basename(root)}/\n"

        for f in files:
            if not is_ignored(root, f):
                tree_str += f"{subindent}├── {f}\n"

    return tree_str


def merge_project():
    print(f"🚀 Démarrage de la fusion vers {OUTPUT_FILENAME}...")
    file_count = 0

    try:
        # 1. Générer l'arborescence en mémoire
        print("🌳 Génération de l'arborescence...")
        project_tree = generate_tree('.')

        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as outfile:
            # 2. Écrire l'en-tête et l'arborescence
            outfile.write(f"# CONTEXTE COMPLET DU PROJET\n")
            outfile.write(
                f"# NOTE A L'IA: Voici la structure du projet suivie du contenu des fichiers.\n\n")
            outfile.write(f"{'='*50}\n")
            outfile.write(project_tree)
            outfile.write(f"{'='*50}\n\n")

            # 3. Écrire le contenu des fichiers
            for root, dirs, files in os.walk('.'):
                dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

                for file in files:
                    if not is_ignored(root, file):
                        file_path = os.path.join(root, file)
                        relative_path = os.path.relpath(file_path, start='.')

                        print(f"📄 Ajout : {relative_path}")

                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as infile:
                                content = infile.read()

                                outfile.write(f"\n{'='*50}\n")
                                outfile.write(f"FILE_PATH: {relative_path}\n")
                                outfile.write(f"{'='*50}\n")
                                outfile.write(content + "\n")
                                file_count += 1
                        except Exception as e:
                            print(
                                f"⚠️ Erreur de lecture sur {relative_path}: {e}")

        print(f"\n✅ TERMINÉ ! Fichier généré : {OUTPUT_FILENAME}")
        print(f"📊 Total : {file_count} fichiers fusionnés.")

    except Exception as e:
        print(f"❌ Erreur critique : {e}")


if __name__ == "__main__":
    merge_project()
