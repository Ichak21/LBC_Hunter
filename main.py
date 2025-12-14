from core.search_manager import SearchManager
from core.scraper import LBCScraper
from core.db_client import DatabaseClient
from core.ai_analyst import AIAnalyst, AIConfigError
from core.price_engine import PriceEngine
from datetime import datetime
import time
import sys
import os
import logging
from core.logging_config import setup_logging
from core.app_config import load_app_config

setup_logging(level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


def initialize_default_search():
    searches = SearchManager.list_searches()
    for searche in searches:
        logger.info(f"🔍 {searche['id']}-{searche['name']}")


def run_bot():
    logger.info("🚀 --- LBC HUNTER ---")
    cfg = load_app_config()

    try:
        db = DatabaseClient()
        analyst = AIAnalyst()
        price_engine = PriceEngine(db)
    except AIConfigError as e:
        logger.error("🛑 IA non utilisable: %s", e)
        return
    except Exception as e:
        logger.exception("🛑 Erreur Init worker: %s", e)
        return

    # Init
    initialize_default_search()
    tasks = SearchManager.list_searches(only_active=True)

    for task in tasks:
        logger.info(f"\n🔎 Traitement : {task['name']}")

        # 1. SCRAPE LISTE
        html = LBCScraper.fetch_html(task['lbc_params'])
        raw_data = LBCScraper.parse_data(html)
        if not raw_data:
            continue

        # 2. FILTER & TRANSFORM
        clean_ads = LBCScraper.process_ads(
            raw_data, task['filters']['whitelist'], task['filters']['blacklist'])

        # 3. ENRICHISSEMENT INTELLIGENT
        ads_to_save = []

        if clean_ads:
            logger.info(
                f"   🎯 {len(clean_ads)} annonces détectées. Vérification du cache...")

            for ad in clean_ads:
                # Cache Check
                already_analyzed = db.is_ad_analyzed(ad['id'])

                if already_analyzed:
                    logger.info(
                        f"      👻 Connue (Skip IA) : {ad['title'][:20]}...")
                    ads_to_save.append(ad)
                    continue

                # Deep Scraping
                full_desc = LBCScraper.get_ad_description(ad['url'])
                if full_desc:
                    ad['description'] = full_desc
                else:
                    logger.info(
                        f"      ⚠️ Pas de description pour {ad['title']}")

                # Analyse Gemini
                logger.info(
                    f"      🧠 NOUVEAU -> Analyse IA : {ad['title'][:20]}...")
                ai_result = analyst.analyze_ad(ad)
                time.sleep(cfg.worker.gemini_sleep_seconds)

                if ai_result:
                    ad.update(ai_result)
                    if ai_result["scores"]["sanity_checks"]["k_arnaque"] < 0.3:
                        logger.info("         💀 SCAM DÉTECTÉ !")

                ads_to_save.append(ad)

        # 4. SAVE (Sauvegarde des nouvelles données)
        if ads_to_save:
            db.upsert_ads(ads_to_save, search_id=task['id'])
            SearchManager.update_last_run(task['id'])

        # 5. MARKET ANALYSIS (Le Sprint 4 !)
        # Une fois qu'on a toutes les données à jour, on lance les maths
        logger.info(f"   📐 Calcul de la cote marché (Random Forest)...")
        price_engine.update_deal_scores(task['id'])

    # 6. NETTOYAGE (Une fois que toutes les recherches sont finies)
    # On vérifie les annonces qu'on n'a pas vues depuis 3 jours (par exemple)
    logger.info("\n🧹 Vérification des annonces disparues...")
    db.archive_old_ads(days_threshold=cfg.worker.archive_days_threshold)

    logger.info("\n✅ Job terminé.")


if __name__ == "__main__":
    run_bot()
