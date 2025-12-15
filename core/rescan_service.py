import logging
from datetime import datetime
import requests

from core.db_client import DatabaseClient
from core.scraper import LBCScraper
from core.ai_analyst import AIAnalyst
from core.price_engine import PriceEngine
from core import config

logger = logging.getLogger(__name__)


def _is_ad_alive(url: str) -> bool:
    """Check rapide, cohérent avec archive_old_ads()."""
    headers = config.get_random_headers()
    r = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
    return r.status_code == 200


def rescan_ad(ad_id: str) -> dict:
    """
    Re-scan manuel:
      - HEAD check
      - si KO -> status SOLD
      - sinon -> refresh description + IA + upsert + recalcul deal score
    Retourne un dict résultat pour l'UI.
    """
    db = DatabaseClient()
    ad = db.get_ad(ad_id)
    if not ad:
        return {"ok": False, "reason": "NOT_FOUND"}

    # Optionnel: ne pas rescanner une annonce TRASH
    if ad.user_status == "TRASH":
        return {"ok": False, "reason": "TRASHED"}

    url = ad.url
    logger.info("🔄 Re-scan demandé pour ad=%s url=%s", ad_id, url)

    try:
        alive = _is_ad_alive(url)
    except Exception:
        logger.exception("⚠️ Re-scan: erreur check alive")
        return {"ok": False, "reason": "ALIVE_CHECK_ERROR"}

    if not alive:
        db.mark_ad_sold(ad_id)
        logger.info("👻 Re-scan: annonce non accessible -> SOLD (%s)", ad_id)
        return {"ok": True, "reason": "MARKED_SOLD"}

    # 1) Refresh description
    full_desc = LBCScraper.get_ad_description(url)
    if not full_desc:
        full_desc = ad.description  # fallback

    # 2) Prépare un dict ad_data cohérent avec upsert_ads()
    # (on réutilise tes champs habituels)
    ad_dict = {
        "id": ad.id,
        "title": ad.title,
        "price": ad.price,
        "url": ad.url,
        "location": ad.location,
        "zipcode": ad.zipcode,
        "date": ad.publication_date.strftime("%Y-%m-%d %H:%M:%S") if ad.publication_date else None,
        "km": ad.mileage,
        "year": ad.year,
        "fuel": ad.fuel,
        "gearbox": ad.gearbox,
        "horsepower": ad.horsepower,
        "finition": ad.finition,
        "seller_rating": ad.seller_rating,
        "seller_rating_count": ad.seller_rating_count,
        "raw_attributes": ad.raw_data,
        "description": full_desc,
    }

    # 3) IA re-run
    analyst = AIAnalyst()
    ai_result = analyst.analyze_ad(ad_dict)
    if not ai_result:
        logger.warning("🧠 Re-scan: IA a retourné None (%s)", ad_id)
        # On met quand même last_seen à jour via upsert sans IA
    else:
        ad_dict.update(ai_result)

    # 4) Upsert (réutilise price_history, last_seen_at, status ACTIVE, etc.)
    # Important: on a besoin d’un search_id. On prend le premier.
    search_ids = list(ad.found_by_searches or [])
    if not search_ids:
        # fallback: pas idéal, mais on évite de planter
        # (à terme, on impose toujours found_by_searches non vide)
        logger.warning("Re-scan: annonce sans found_by_searches (%s)", ad_id)
        db.upsert_ads([ad_dict], search_id="manual_rescan")
        return {"ok": True, "reason": "UPDATED_NO_SEARCH"}

    primary_search_id = search_ids[0]
    db.upsert_ads([ad_dict], search_id=primary_search_id)

    # 5) Recalcul deal score pour les searches concernées
    price_engine = PriceEngine(db)
    for sid in search_ids:
        try:
            price_engine.update_deal_scores(sid)
        except Exception:
            logger.exception(
                "💰 Re-scan: deal score update failed for search=%s", sid)

    logger.info("✅ Re-scan terminé (%s)", ad_id)
    return {"ok": True, "reason": "UPDATED"}
