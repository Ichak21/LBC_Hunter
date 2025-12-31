import json
import os
import logging
from pathlib import Path
from copy import deepcopy
from typing import Dict, Any

# On importe la config statique comme "Défaut d'usine"
from .scoring_config import SCORING_CONFIG as DEFAULT_CONFIG

logger = logging.getLogger(__name__)

# Le fichier JSON sera stocké à la racine du projet
CONFIG_FILE = Path("scoring.json")


class ConfigManager:
    """
    Gère la configuration dynamique de l'application.
    Source de vérité : scoring.json (si présent) > scoring_config.py (défaut).
    """

    @staticmethod
    def get_config() -> Dict[str, Any]:
        """
        Charge la configuration active.
        """
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Optionnel : On pourrait merger avec DEFAULT_CONFIG ici
                    # pour s'assurer qu'il ne manque pas de clés en cas de mise à jour code.
                    return data
            except Exception as e:
                logger.error(
                    f"⚠️ Erreur lecture scoring.json (corrompu ?). Retour aux défauts. Erreur: {e}")
                return deepcopy(DEFAULT_CONFIG)

        # Si pas de fichier JSON, on renvoie la config d'usine
        return deepcopy(DEFAULT_CONFIG)

    @staticmethod
    def save_config(new_config: Dict[str, Any]) -> None:
        """
        Sauvegarde la configuration modifiée dans le JSON.
        """
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(new_config, f, indent=4, ensure_ascii=False)
            logger.info("💾 Configuration sauvegardée dans scoring.json")
        except Exception as e:
            logger.exception(f"❌ Erreur sauvegarde configuration : {e}")
            raise e

    @staticmethod
    def reset_to_default() -> None:
        """
        Supprime le fichier JSON pour revenir à la configuration d'usine.
        """
        if CONFIG_FILE.exists():
            try:
                os.remove(CONFIG_FILE)
                logger.info(
                    "♻️ Configuration réinitialisée aux paramètres d'usine.")
            except Exception as e:
                logger.exception(
                    f"❌ Impossible de supprimer scoring.json : {e}")
                raise e
        else:
            logger.info("ℹ️ Déjà en configuration d'usine.")
