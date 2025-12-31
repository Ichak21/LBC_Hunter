import argparse
import logging
import time
import sys
from core.search_manager import SearchManager
from core.scraper import LBCScraper
from core.db_client import DatabaseClient
from core.ai_analyst import AIAnalyst, AIConfigError
from core.price_engine import PriceEngine
from core.logging_config import setup_logging
from core.app_config import load_app_config

# Setup logging
setup_logging(level=logging.INFO)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("google").setLevel(logging.WARNING)
logging.getLogger("requests").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)


def run_worker(target_search_id=None, smart_mode=False):
    logger.info("🚀 --- LBC HUNTER WORKER ---")
    cfg = load_app_config()
    db = DatabaseClient()

    try:
        analyst = AIAnalyst()
    except AIConfigError as e:
        logger.error("🛑 IA non utilisable: %s", e)
        return

    price_engine = PriceEngine(db)

    # 1. DÉTERMINATION DES TÂCHES
    tasks = []

    if target_search_id:
        # Mode : Scan manuel unique
        s = SearchManager.get_search(target_search_id)
        if s:
            logger.info(f"🎯 Mode CIBLÉ : {s['name']}")
            tasks = [s]
        else:
            logger.error(f"❌ Recherche introuvable : {target_search_id}")
            return

    elif smart_mode:
        # Mode : Le plus urgent uniquement
        s = SearchManager.get_oldest_active_search()
        if s:
            logger.info(
                f"🧠 Mode SMART : Priorité à '{s['name']}' (Plus ancienne maj)")
            tasks = [s]
        else:
            logger.info("💤 Aucune recherche active à traiter.")
            return

    else:
        # Mode : Tout (Comportement par défaut)
        logger.info(
            "📋 Mode COMPLET : Traitement de toutes les recherches actives")
        tasks = SearchManager.list_searches(only_active=True)

    # 2. EXÉCUTION
    for task in tasks:
        logger.info(f"\n🔎 Traitement : {task['name']}")

        # A. SCRAPE
        html = LBCScraper.fetch_html(task['lbc_params'])
        if not html:
            logger.warning("   ⚠️ HTML vide ou erreur réseau.")
            continue

        raw_data = LBCScraper.parse_data(html)

        # B. FILTER
        clean_ads = LBCScraper.process_ads(
            raw_data, task['filters']['whitelist'], task['filters']['blacklist'])

        # C. ENRICH (IA)
        ads_to_save = []
        if clean_ads:
            logger.info(
                f"   🎯 {len(clean_ads)} annonces détectées. Vérification...")

            for ad in clean_ads:
                if db.is_ad_analyzed(ad['id']):
                    logger.info(
                        f"      👻 Connue (Skip IA) : {ad['title'][:20]}...")
                    ads_to_save.append(ad)
                    continue

                full_desc = LBCScraper.get_ad_description(ad['url'])
                if full_desc:
                    ad['description'] = full_desc

                logger.info(
                    f"      🧠 NOUVEAU -> Analyse IA : {ad['title'][:20]}...")
                ai_result = analyst.analyze_ad(ad)
                time.sleep(cfg.worker.gemini_sleep_seconds)

                if ai_result:
                    ad.update(ai_result)
                    if ai_result["scores"]["sanity_checks"]["k_arnaque"] < 0.3:
                        logger.info("          💀 SCAM DÉTECTÉ !")

                ads_to_save.append(ad)

        # D. SAVE
        if ads_to_save:
            db.upsert_ads(ads_to_save, search_id=task['id'])

        # Toujours mettre à jour la date de run, même si 0 annonce (pour que le smart mode tourne)
        SearchManager.update_last_run(task['id'])

        # E. MARKET ANALYSIS
        logger.info(f"   📐 Calcul de la cote marché...")
        price_engine.update_deal_scores(task['id'])

    # 3. NETTOYAGE (Uniquement si on fait un run complet ou smart, pas ciblé)
    if not target_search_id:
        logger.info("\n🧹 Vérification des annonces disparues...")
        db.archive_old_ads(days_threshold=cfg.worker.archive_days_threshold)

    logger.info("\n✅ Job terminé.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--smart", action="store_true",
                        help="Lance uniquement la recherche la plus ancienne")
    parser.add_argument("--search_id", type=str,
                        help="Lance une recherche spécifique par son ID")
    args = parser.parse_args()

    run_worker(target_search_id=args.search_id, smart_mode=args.smart)
