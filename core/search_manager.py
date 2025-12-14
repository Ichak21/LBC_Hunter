import json
import os
import re
import uuid
from datetime import datetime
from .app_config import load_app_config
from pathlib import Path
import logging

logger = logging.getLogger(__name__)
SEARCH_DIR = load_app_config().paths.searches_dir
SEARCH_DIR.mkdir(exist_ok=True)


class SearchManager:
    @staticmethod
    def _save_file(search_data: dict):
        # On construit un nom lisible : nom_propre + _ + ID + .json
        safe_name = SearchManager._sanitize_filename(search_data['name'])
        filename = f"{safe_name}_{search_data['id']}.json"

        file_path = SEARCH_DIR / filename

        # Si le fichier existait sous un autre nom (cas update), on le cherche pour l'écraser ou le renommer
        old_path = SearchManager._find_file_by_id(search_data['id'])
        if old_path and old_path.name != filename:
            # On supprime l'ancien nom pour éviter les doublons
            os.remove(old_path)

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(search_data, f, indent=4, ensure_ascii=False)

    @staticmethod
    def _sanitize_filename(search_name: str) -> str:
        """Transforme 'Golf 7 GTI !' en 'golf_7_gti'"""
        # Met en minuscule, remplace espaces par _, garde que les chiffres/lettres
        clean = re.sub(r'[^a-z0-9]', '_', search_name.lower())
        # Enlève les _ multiples (ex: golf__7)
        clean = re.sub(r'_+', '_', clean).strip('_')
        return clean

    @staticmethod
    def _find_file_by_id(search_id: str) -> None:
        """Cherche le fichier qui contient l'ID dans son nom"""
        # On cherche un fichier qui finit par cet ID
        for file_path in SEARCH_DIR.glob(f"*{search_id}.json"):
            return file_path
        return None

    @staticmethod
    def build_params(search_text: str, min_year: str = None, max_year: str = None, min_price: str = None, max_price: str = None) -> dict:
        """
        Traduit des entrées utilisateur simples en dictionnaire technique LBC.
        """
        params = {
            "category": "2",       # Toujours "Voiture"
            "text": search_text,
            "sort": "time"         # Toujours "Plus récent"
        }

        # --- Gestion de l'Année (regdate) ---
        # LBC attend format: "min-max", "min-max", "min-" ou "-max"
        if min_year and max_year:
            params["regdate"] = f"{min_year}-{max_year}"
        elif min_year:
            # ou juste f"{min_year}-" selon version
            params["regdate"] = f"{min_year}-max"
        elif max_year:
            # On met une date arbitraire basse
            params["regdate"] = f"1900-{max_year}"

        # --- Gestion du Prix (price) ---
        if min_price and max_price:
            params["price"] = f"{min_price}-{max_price}"
        elif min_price:
            params["price"] = f"{min_price}-max"
        elif max_price:
            params["price"] = f"500-{max_price}"
        else:
            params["price"] = f"500-max"

        return params

    @staticmethod
    def list_searches(only_active: bool = False) -> list:
        lst_searches = []
        # On scanne tous les JSON du dossier
        for file_path in SEARCH_DIR.glob("*.json"):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    search_data = json.load(f)
                    if only_active and not search_data.get("active"):
                        continue
                    lst_searches.append(search_data)
            except:
                pass
        return lst_searches

    @staticmethod
    def create_search(name: str, lbc_params: dict, whitelist: list = None, blacklist: list = None) -> str:
        # 1. SÉCURITÉ ANTI-DOUBLON
        # On regarde si une recherche porte déjà ce nom exact
        existing_searches = SearchManager.list_searches()
        for s in existing_searches:
            if s['name'] == name:
                logger.info(
                    f"⚠️ La recherche '{name}' existe déjà (ID: {s['id']}). On ne la recrée pas.")
                return s['id']  # On renvoie l'ID existant sans rien faire
        # 2. CRÉATION NORMALE
        search_id = str(uuid.uuid4())
        search_data = {
            "id": search_id,
            "name": name,
            "active": True,
            "created_at": datetime.now().isoformat(),
            "last_run_at": None,
            "lbc_params": lbc_params,
            "filters": {
                "whitelist": whitelist if whitelist else [],
                "blacklist": blacklist if blacklist else []
            }
        }
        SearchManager._save_file(search_data)
        logger.info(f"✅ Recherche '{name}' créée (ID: {search_id})")
        return search_id

    @staticmethod
    def update_model_meta(search_id: str, new_meta: dict):
        """Met à jour le champ model_meta pour une recherche (utilisé par PriceEngine)."""
        search_file = SearchManager._find_file_by_id(search_id)
        if not search_file:
            # Cette erreur ne devrait jamais arriver si le worker est bien lancé
            return

        with open(search_file, 'r', encoding='utf-8') as f:
            search_data = json.load(f)

        # Fusionne le nouveau meta avec l'ancien
        search_data['model_meta'] = search_data.get('model_meta', {})
        search_data['model_meta'].update(new_meta)

        # Sauvegarde
        SearchManager._save_file(search_data)

    @staticmethod
    def get_search(search_id: str) -> dict | None:
        """Récupère la config. Plus complexe car le nom du fichier peut varier."""
        file_path = SearchManager._find_file_by_id(search_id)
        if file_path and file_path.exists():
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    @staticmethod
    def update_last_run(search_id: str) -> None:
        search_data = SearchManager.get_search(search_id)
        if search_data:
            search_data["last_run_at"] = datetime.now().isoformat()
            SearchManager._save_file(search_data)

    @staticmethod
    def delete_search(search_id: str) -> None:
        file_path = SearchManager._find_file_by_id(search_id)
        if file_path and file_path.exists():
            os.remove(file_path)
            logger.info(f"🗑️ Fichier supprimé : {file_path.name}")


def main() -> None:
    print("==== Starter Searches ====")
    # # --- Peugeot 106 Rallye (Phase 1 & 2) ---
    # # Phase 1: 1993-1996 (1.3) / Phase 2: 1996-1998 (1.6)
    # RALLYE_106 = SearchManager.build_params(
    #     "106 rallye", min_year="1993", max_year="1999")
    # SearchManager.create_search(
    #     name="Peugeot 106 Rallye",
    #     lbc_params=RALLYE_106,
    #     whitelist=["rallye", "1.3", "1.6", "phase 1", "phase 2"],
    #     blacklist=[
    #         "s16", "xsi", "sport", "enfant", "quiksilver", "kid", "xn", "xr", "xt",
    #         "diesel", "1.5d", "1.4", "jante", "piece", "recherche", "demande",
    #         "accident", "export", "carte grise", "vends pieces"
    #     ]
    # )

    # # --- Mazda MX-5 NA (Mk1) ---
    # # Production 1989-1997
    # MX5_NA = SearchManager.build_params(
    #     "mx5", min_year="1989", max_year="1998")
    # SearchManager.create_search(
    #     name="Mazda MX-5 NA (Mk1)",
    #     lbc_params=MX5_NA,
    #     whitelist=["na", "mk1", "miata", "eunos",
    #                "115", "90", "130", "pop up"],
    #     blacklist=[
    #         "nb", "mk2", "nc", "mk3", "nd", "mk4", "nbfl", "140", "145", "1.8 vvt",
    #         "hardtop", "jante", "piece", "recherche", "demande", "location",
    #         "accident", "export", "catalyseur"
    #     ]
    # )

    # # --- Mazda MX-5 NB (Mk2 & NBFL) ---
    # # Production 1998-2005
    # MX5_NB = SearchManager.build_params(
    #     "mx5", min_year="1998", max_year="2005")
    # SearchManager.create_search(
    #     name="Mazda MX-5 NB (Mk2)",
    #     lbc_params=MX5_NB,
    #     whitelist=["nb", "mk2", "nbfl", "1.6", "1.8",
    #                "140", "145", "10th", "eterna", "phoenix"],
    #     blacklist=[
    #         "na", "mk1", "nc", "mk3", "nd", "mk4", "pop up", "miata",
    #         "hardtop", "jante", "piece", "recherche", "demande", "location",
    #         "accident", "export"
    #     ]
    # )

    # # --- Ford Focus RS MK2 ---
    # # Production 2009-2011 (Le 5 cylindres 2.5L)
    # FOCUS_RS_MK2 = SearchManager.build_params(
    #     "focus rs", min_year="2009", max_year="2011")
    # SearchManager.create_search(
    #     name="Ford Focus RS MK2",
    #     lbc_params=FOCUS_RS_MK2,
    #     whitelist=["mk2", "305", "2.5", "500", "5 cylindres"],
    #     blacklist=[
    #         "mk1", "mk3", "st", "st225", "diesel", "tdci", "titanium", "ghia", "trend",
    #         "ecoboost", "2.3", "2.0", "1.6", "look rs", "kit rs", "replica", "pack rs",
    #         "jante", "piece", "recherche", "demande", "accident", "export", "ligne"
    #     ]
    # )


if __name__ == "__main__":
    main()
