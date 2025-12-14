import requests
import json
from bs4 import BeautifulSoup
import time
import random
from . import config
import logging
from .app_config import load_app_config


logger = logging.getLogger(__name__)


class LBCScraper:
    @staticmethod
    def fetch_html(lbc_params: dict) -> str | None:
        """Fait la requête HTTP de recherche."""
        try:
            cfg = load_app_config().scraper
            sleep_time = random.uniform(
                cfg.min_sleep_seconds, cfg.max_sleep_seconds)
            logger.info(f"   💤 Pause sécu de {sleep_time:.2f}s...")
            time.sleep(sleep_time)

            headers = config.get_random_headers()
            logger.info(
                f"   🌐 GET Search (Recherche: {lbc_params.get('text')})...")

            response = requests.get(
                config.LBC_BASE_URL,
                headers=headers,
                params=lbc_params,
                timeout=cfg.request_timeout_seconds
            )
            if response.status_code == 403:
                logger.exception("   🛑 ERREUR 403 : IP Bloquée (Datadome).")
                return None
            response.raise_for_status()
            return response.text

        except Exception as e:
            logger.exception(f"   ❌ Erreur réseau : {e}")
            return None

    @staticmethod
    def parse_data(html: str) -> list:
        """Extrait la liste des annonces depuis la recherche."""
        if not html:
            return []
        soup = BeautifulSoup(html, 'html.parser')
        script = soup.find("script", id="__NEXT_DATA__")
        if not script:
            return []
        try:
            return json.loads(script.string)["props"]["pageProps"]["searchData"]["ads"]
        except:
            return []

    @staticmethod
    def process_ads(ads_raw: list, whitelist: list, blacklist: list) -> list:
        """Filtre la liste brute et extrait les données structurées."""
        clean_ads = []
        rejected_count = 0  # Compteur

        for ad in ads_raw:
            if "list_id" not in ad:
                continue

            title = ad.get("subject", "").lower()

            # --- FILTRAGE ---
            is_blacklisted = any(bad in title for bad in blacklist)
            is_whitelisted = (not whitelist) or any(
                good in title for good in whitelist)

            if is_blacklisted or not is_whitelisted:
                rejected_count += 1
                continue

            # --- 1. TRANSFORMATION DES ATTRIBUTS ---
            raw_attrs_list = ad.get("attributes", [])
            attrs_dict = {item["key"]: item["value"]
                          for item in raw_attrs_list}
            attrs_labels = {item["key"]: item.get(
                "value_label") for item in raw_attrs_list}

            price = LBCScraper._extract_price(ad)

            # --- 2. EXTRACTION DES CHAMPS ---
            ad_obj = {
                "id": str(ad.get("list_id")),
                "title": ad.get("subject"),
                "price": price,
                "url": ad.get("url"),
                "location": ad.get("location", {}).get("city"),
                "zipcode": ad.get("location", {}).get("zipcode"),
                "date": ad.get("first_publication_date"),
                "img": ad.get("images", {}).get("small_url"),
                "km": LBCScraper._safe_int(attrs_dict.get("mileage")),
                "year": LBCScraper._safe_int(attrs_dict.get("regdate")),
                "fuel": attrs_labels.get("fuel"),
                "gearbox": attrs_labels.get("gearbox"),
                "horsepower": LBCScraper._safe_int(attrs_dict.get("horse_power_din")),
                "finition": attrs_labels.get("u_car_finition"),
                "seller_rating": float(attrs_dict.get("rating_score", 0)) if "rating_score" in attrs_dict else None,
                "seller_rating_count": int(attrs_dict.get("rating_count", 0)) if "rating_count" in attrs_dict else 0,
                "raw_attributes": ad.get("attributes"),
                "description": None
            }
            clean_ads.append(ad_obj)

        # --- LOG DU FILTRAGE ---
        total = len(ads_raw)
        kept = len(clean_ads)
        logger.info(
            f"   🧹 Filtre : {total} reçues -> {rejected_count} rejetées -> {kept} gardées.")

        return clean_ads

    @staticmethod
    def get_ad_description(ad_url: str) -> str | None:
        """Va sur la page de l'annonce et extrait la description complète."""
        try:
            cfg = load_app_config().scraper
            time.sleep(random.uniform(cfg.ad_page_min_sleep_seconds,
                       cfg.ad_page_max_sleep_seconds))
            headers = config.get_random_headers()

            response = requests.get(
                ad_url, headers=headers, timeout=cfg.request_timeout_seconds)
            if response.status_code != 200:
                return None

            soup = BeautifulSoup(response.text, 'html.parser')

            # Méthode 1 : Via JSON caché (souvent présent)
            script = soup.find("script", id="__NEXT_DATA__")
            if script:
                try:
                    data = json.loads(script.string)
                    return data["props"]["pageProps"]["ad"]["body"]
                except:
                    pass

            # Méthode 2 : Via HTML direct
            desc_div = soup.find(
                "div", {"data-qa-id": "adview_description_container"})
            if desc_div:
                return desc_div.get_text(separator="\n").strip()

            return None

        except Exception as e:
            logger.exception(
                f"      ⚠️ Impossible de lire la description : {e}")
            return None

    @staticmethod
    def _safe_int(val):
        try:
            return int(val)
        except:
            return None

    @staticmethod
    def _extract_price(ad):
        p = ad.get("price", [0])
        return float(p[0]) if isinstance(p, list) and p else 0
