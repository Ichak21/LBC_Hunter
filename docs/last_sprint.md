### 🚀 2. Plan d'Action Final (Intégrant le Reset & l'Automatisation)

Ce plan est votre feuille de route définitive pour terminer le projet.

### 🏗️ PHASE 1 : Architecture & Configuration (Fondations)

*Objectif : Rendre le bot configurable sans toucher au code.*

- **1.1. Créer le `ConfigManager` (Nouveau Fichier) :**
    - Créer `core/config_manager.py`.
    - y déplacer le dictionnaire `SCORING_CONFIG` actuel  comme constante `DEFAULT_CONFIG`.
    - Implémenter `load_config()` : charge depuis un JSON s'il existe, sinon renvoie `DEFAULT_CONFIG`.
    - Implémenter `save_config(new_config)` : écrit dans le JSON.
    - Implémenter `reset_to_default()` : supprime le JSON (le système retombera sur `DEFAULT_CONFIG`).
- **1.2. Refactoring Config :**
    - Mettre à jour `ai_analyst.py`, `price_engine.py` et `frontend/data_loader.py` pour qu'ils utilisent `ConfigManager.get_config()` au lieu d'importer la constante statique.

### 🧠 PHASE 2 : Intelligence du Worker (Automatisation)

*Objectif : Scannez intelligemment pour éviter le ban.*

- **2.1. Stratégie "Least Recently Updated" :**
    - Dans `SearchManager`, créer une méthode `get_oldest_active_search()` :
        - Liste toutes les recherches actives.
        - Trie par `last_run_at` (les `None` ou les dates les plus anciennes en premier).
        - Renvoie uniquement l'ID de la recherche gagnante.
- **2.2. Mode "Smart Single Run" dans `main.py` :**
    - Modifier `main.py` pour accepter un argument (ex: `-smart`).
    - Si `-smart` est présent : le script récupère **une seule** recherche (via 2.1), la traite, et s'arrête.
- **2.3. Le Scheduler (Script de lancement) :**
    - Créer un script `scheduler.py` (ou `auto_run.py`) à la racine.
    - Boucle infinie (`while True`):
        1. Charge la config pour lire `min_interval` et `max_interval` (ex: 30 min / 120 min).
        2. Calcule un temps d'attente aléatoire (`random.randint`).
        3. Attend (`time.sleep`).
        4. Lance le worker : `subprocess.run(["python", "main.py", "--smart"])`.

### 🖥️ PHASE 3 : Interface Utilisateur (Finalisation UX)

*Objectif : Remplacer les placeholders par les vrais contrôles.*

- **3.1. Page Settings (`pages/4_⚙️_Settings.py`) :**
    - Connecter au `ConfigManager`.
    - Ajouter les Sliders pour les poids (Deal/Confiance/Produit).
    - Ajouter les inputs pour l'automatisation (Intervalle Min/Max en minutes).
    - **Bouton "💾 Sauvegarder"** : appelle `save_config`.
    - **Bouton "revenir aux réglages d'usine"** : appelle `reset_to_default` puis recharge la page.
- **3.2. Page Searches Manager (`pages/3_🎛️_Searches_Manager.py`) :**
    - Activer le bouton "Créer" (Formulaire).
    - Activer le Toggle Actif/Inactif.
    - Activer le bouton "Scan manuel" (lance `main.py` sur cette recherche spécifique).

