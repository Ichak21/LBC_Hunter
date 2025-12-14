import streamlit as st
import pandas as pd
import os
from core.db_client import DatabaseClient
from core.models import Ad
from core.search_manager import SearchManager
from core.scoring_config import SCORING_CONFIG
from core.app_config import load_app_config
import logging

logger = logging.getLogger(__name__)
CACHE_TTL = load_app_config().streamlit.cache_ttl_seconds


@st.cache_data(ttl=CACHE_TTL)
def load_home_data():
    """Charge les données globales pour le Dashboard"""
    db = DatabaseClient()
    session = db.Session()

    try:
        # 1. Stats globales
        status_counts = {"ACTIVE": 0, "SOLD": 0, "SCAM": 0}
        ads_all = session.query(Ad.status, Ad.user_status).all()
        for s, us in ads_all:
            if us == "SCAM_MANUAL" or s == "SCAM":
                status_counts["SCAM"] += 1
            elif s == "SOLD":
                status_counts["SOLD"] += 1
            elif s == "ACTIVE":
                status_counts["ACTIVE"] += 1

        # 2. Opportunités & Favoris
        query_active = session.query(Ad).filter(
            Ad.status == "ACTIVE", Ad.user_status != "TRASH")

        # Récupération des POIDS FRACTIONNELS (0.5, 0.3, 0.2)
        weights = SCORING_CONFIG.get(
            "weights", {"deal": 0.5, "conf": 0.3, "prod": 0.2})
        w_deal = weights.get("deal", 0.5)
        w_conf = weights.get("conf", 0.3)
        w_prod = weights.get("prod", 0.2)

        raw_data = []
        for ad in query_active.all():
            scores = ad.scores or {}
            base = scores.get("base", {})
            fin = scores.get("financial", {})
            sanity = scores.get("sanity_checks", {})

            # A. CALCUL GAIN/PERTE (Sécurisé)
            market_price = fin.get("market_estimation", 0)
            if market_price and market_price > 0:
                virtual_price = fin.get("virtual_price", ad.price)
                gain = market_price - virtual_price
            else:
                gain = 0  # Evite les pertes négatives si aucune cote marché n'est disponible

            # B. CALCUL NOTE BRUTE (Somme Pondérée Directe)
            s_deal = base.get("deal", 50)
            s_conf = base.get("conf", 50)
            s_prod = base.get("prod", 0)

            try:
                # Moyenne pondérée par poids fractionnels
                note_brute = (s_deal * w_deal) + \
                    (s_conf * w_conf) + (s_prod * w_prod)
            except:
                note_brute = 0

            # C. CALCUL INDICE K (K Final)
            k_meca = sanity.get("k_meca", 1.0)
            k_modif = sanity.get("k_modif", 1.0)
            k_arnaque = sanity.get("k_arnaque", 1.0)
            k_final = k_meca * k_modif * k_arnaque

            raw_data.append({
                "ID": ad.id,
                "Titre": ad.title,
                "Prix": ad.price,
                "Gain": gain,
                "Note Brute": int(note_brute),
                "Indice K": int(k_final * 100),
                "Favori": ad.is_favorite,
                "URL": ad.url,
                "Search": ad.found_by_searches[0] if ad.found_by_searches else "N/A"
            })

        df_ads = pd.DataFrame(raw_data)

        # 3. Recherches Actives
        searches = SearchManager.list_searches()
        df_searches = pd.DataFrame(searches)

        if not df_searches.empty:
            df_searches["Whitelist"] = df_searches["filters"].apply(
                lambda x: ", ".join(x.get("whitelist", [])))
            df_searches["Blacklist"] = df_searches["filters"].apply(
                lambda x: ", ".join(x.get("blacklist", [])))

            # FIX FINAL ANNEES : Extraction de regdate depuis lbc_params
            def get_year_display(lbc_params_dict):
                if not isinstance(lbc_params_dict, dict):
                    return "Tout"

                regdate_val = lbc_params_dict.get("regdate")

                if regdate_val and str(regdate_val).strip():
                    return str(regdate_val).strip()

                min_y = lbc_params_dict.get("min_year")
                max_y = lbc_params_dict.get("max_year")
                if min_y and max_y:
                    return f"{min_y}-{max_y}"
                if min_y:
                    return f"> {min_y}"
                if max_y:
                    return f"< {max_y}"

                return "Tout"

            # Utilisation de la colonne 'lbc_params' pour l'extraction
            df_searches["Année"] = df_searches["lbc_params"].apply(
                get_year_display)

            df_searches = df_searches[["name", "id", "Année",
                                       "last_run_at", "Whitelist", "Blacklist"]]

        return status_counts, df_ads, df_searches

    except Exception as e:
        logger.exeption(f"Erreur Data Loader: {e}")
        return {"ACTIVE": 0}, pd.DataFrame(), pd.DataFrame()
    finally:
        session.close()


@st.cache_data(ttl=10)
def load_search_details_data(search_id):
    """Charge les données détaillées pour une recherche spécifique, incluant toutes les annonces (peu importe le statut) et le R²."""
    db = DatabaseClient()
    session = db.Session()

    try:
        # 1. Récupérer l'objet de recherche pour le R²
        search_obj = SearchManager.get_search(search_id)
        # Assurer la lecture du R²
        if search_obj:
            # On utilise .get() pour accéder aux clés du dictionnaire de manière sécurisée
            model_meta = search_obj.get("model_meta", {})
            r2_score = model_meta.get("r2_score", "N/A")
            search_name = search_obj.get("name", "Recherche Inconnue")
        else:
            r2_score = "N/A"
            search_name = "Recherche Inconnue"

        # 2. Récupérer toutes les annonces liées à cette recherche
        query_ads = session.query(Ad).filter(
            Ad.found_by_searches.contains([search_id]))

        # Récupération des POIDS FRACTIONNELS (0.5, 0.3, 0.2)
        weights_dict = SCORING_CONFIG.get("weights", {})
        w_deal = weights_dict.get("deal", 0.5)
        w_conf = weights_dict.get("conf", 0.3)
        w_prod = weights_dict.get("prod", 0.2)

        raw_data = []

        for ad in query_ads.all():
            scores = ad.scores or {}
            base = scores.get("base", {})
            fin = scores.get("financial", {})
            sanity = scores.get("sanity_checks", {})

            # Déterminer le statut final pour le graphique
            status = ad.status
            if ad.user_status == "SCAM_MANUAL" or status == "SCAM":
                status = "SCAM"
            elif status == "SOLD":
                status = "SOLD"
            else:
                status = "ACTIVE"

            # A. CALCUL GAIN/PERTE
            market_price = fin.get("market_estimation", 0)
            if market_price and market_price > 0:
                virtual_price = fin.get("virtual_price", ad.price)
                gain = market_price - virtual_price
            else:
                gain = 0

            # B. CALCUL NOTE BRUTE
            s_deal = base.get("deal", 50)
            s_conf = base.get("conf", 50)
            s_prod = base.get("prod", 0)

            try:
                # Somme Pondérée Directe (Base de la Note Finale)
                note_brute = (s_deal * w_deal) + \
                    (s_conf * w_conf) + (s_prod * w_prod)
            except:
                note_brute = 0

            # C. CALCUL INDICE K (K Final)
            k_meca = sanity.get("k_meca", 1.0)
            k_modif = sanity.get("k_modif", 1.0)
            k_arnaque = sanity.get("k_arnaque", 1.0)
            k_final = k_meca * k_modif * k_arnaque

            raw_data.append({
                "ID": ad.id,
                "Titre": ad.title,
                "Prix": ad.price,
                "Gain": gain,
                "Kilométrage": ad.mileage,
                "Année": ad.year,
                "Statut": status,  # Statut pour les filtres et graphiques
                "Note Brute": int(note_brute),
                "Indice K": int(k_final * 100),
                # Le score total inclut l'application des K
                "Score Final": scores.get("total", 0),
                "Favori": ad.is_favorite,
                "URL": ad.url,
                # Détails pour le Hover Plot
                "Deal Score": s_deal,
                "Conf Score": s_conf,
                "Prod Score": s_prod,
                "K Mecanique": k_meca,
                "K Modification": k_modif,
                "K Arnaque": k_arnaque,
            })

        df_ads = pd.DataFrame(raw_data)

        # S'assurer que les colonnes sont numériques pour les graphiques
        if not df_ads.empty:
            df_ads["Prix"] = df_ads["Prix"].astype(float)
            df_ads["Kilométrage"] = df_ads["Kilométrage"].astype(float)

        # Calculer le count status pour le Pie Chart
        status_counts = df_ads["Statut"].value_counts().to_dict()

        return search_name, r2_score, status_counts, df_ads

    except Exception as e:
        logger.exeption(f"Erreur Load Search Details: {e}")
        return "Erreur de Chargement", "N/A", {"ACTIVE": 0}, pd.DataFrame()
    finally:
        session.close()


def load_logs(lines=200):
    log_file = "logs/worker.log"
    if os.path.exists(log_file):
        with open(log_file, "r", encoding="utf-8", errors="replace") as f:
            return "".join(f.readlines()[-lines:])
    return "Aucun log disponible."
