from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from typing import Any, Dict, List, Optional
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy import and_
from .models import Base, Ad
from datetime import datetime, timedelta
import requests
from . import config
from .app_config import load_app_config
import logging

logger = logging.getLogger(__name__)


class DatabaseClient:
    def __init__(self, db_url: str | None = None):
        if db_url is None:
            db_url = load_app_config().db.url
        logger.info(f"🔌 Tentative de connexion à {db_url}...")
        try:
            self.engine = create_engine(db_url)
            Base.metadata.create_all(self.engine)
            self.Session = sessionmaker(bind=self.engine)
            logger.info("✅ Connecté à PostgreSQL et tables synchronisées.")
        except Exception as e:
            logger.exception(f"❌ ÉCHEC de connexion : {e}")
            raise e

    def upsert_ads(self, ads_data_list: list, search_id: str):
        session = self.Session()
        stats = {"new": 0, "updated": 0, "unchanged": 0}

        try:
            for ad_dict in ads_data_list:
                ad_id = ad_dict["id"]
                current_price = int(ad_dict["price"])

                existing_ad = session.query(Ad).filter_by(id=ad_id).first()

                if existing_ad:
                    # --- UPDATE ---
                    existing_ad.last_seen_at = datetime.now()
                    if existing_ad.status == "SOLD":
                        existing_ad.status = "ACTIVE"

                    # Update Found By
                    current_searches = list(
                        existing_ad.found_by_searches) if existing_ad.found_by_searches else []
                    if search_id not in current_searches:
                        current_searches.append(search_id)
                        existing_ad.found_by_searches = current_searches

                    # Update Price
                    if existing_ad.price != current_price:
                        history = list(
                            existing_ad.price_history) if existing_ad.price_history else []
                        history.append(
                            {"date": datetime.now().isoformat(), "price": existing_ad.price})
                        existing_ad.price_history = history
                        existing_ad.price = current_price
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1

                    # Update Intelligence if present
                    if "ai_analysis" in ad_dict:
                        existing_ad.ai_analysis = ad_dict["ai_analysis"]
                    if "scores" in ad_dict:
                        existing_ad.scores = ad_dict["scores"]

                else:
                    # --- INSERT (Avec les nouveaux champs) ---
                    new_ad = Ad(
                        id=ad_id,
                        found_by_searches=[search_id],
                        title=ad_dict["title"],
                        description=ad_dict.get("description"),  # <--- ICI
                        url=ad_dict["url"],
                        price=current_price,
                        mileage=self._safe_int(ad_dict.get("km")),
                        year=self._safe_int(ad_dict.get("year")),
                        fuel=ad_dict.get("fuel"),
                        gearbox=ad_dict.get("gearbox"),        # <--- ICI
                        horsepower=ad_dict.get("horsepower"),  # <--- ICI
                        finition=ad_dict.get("finition"),      # <--- ICI

                        location=ad_dict.get("location"),
                        zipcode=ad_dict.get("zipcode"),        # <--- ICI

                        seller_rating=ad_dict.get(
                            "seller_rating"),             # <--- ICI
                        seller_rating_count=ad_dict.get(
                            "seller_rating_count"),  # <--- ICI

                        publication_date=self._parse_date(ad_dict.get("date")),
                        raw_data=ad_dict.get("raw_attributes"),
                        price_history=[],
                        status="ACTIVE",
                        ai_analysis=ad_dict.get("ai_analysis"),
                        scores=ad_dict.get("scores")
                    )
                    session.add(new_ad)
                    stats["new"] += 1

            session.commit()
            logger.info(
                f"📊 BDD: {stats['new']} news | {stats['updated']} maj.")

        except Exception as e:
            session.rollback()
            logger.exception(f"❌ Erreur DB : {e}")
        finally:
            session.close()

    def archive_old_ads(self, days_threshold: int):
        """
        Vérifie les annonces qu'on n'a pas revues depuis X jours.
        PING l'URL pour voir si elle est encore en ligne.
        Si 404/Gone -> SOLD.
        Si 200 OK -> On met à jour la date (elle est juste passée en page 2+).
        """
        session = self.Session()
        try:
            limit_date = datetime.now() - timedelta(days=days_threshold)

            # On récupère les candidates à l'archivage
            ads_to_check = session.query(Ad).filter(
                Ad.status == "ACTIVE",
                Ad.last_seen_at < limit_date
            ).all()

            if not ads_to_check:
                logger.info("🧹 Ménage : Aucune annonce à vérifier.")
                return

            logger.info(
                f"🧹 Ménage : {len(ads_to_check)} annonces anciennes à vérifier (Ping URL)...")
            archived_count = 0
            rescued_count = 0

            for ad in ads_to_check:
                try:
                    # On tente d'accéder à la page (HEAD request est plus léger que GET)
                    # On utilise les headers pour ne pas se faire jeter
                    headers = config.get_random_headers()
                    r = requests.head(ad.url, headers=headers,
                                      timeout=5, allow_redirects=True)

                    # Leboncoin redirige souvent vers la home ou une page de recherche si l'annonce est off
                    # Si l'URL finale n'est pas l'URL de l'annonce, c'est suspect.

                    if r.status_code == 200:
                        # ATTENTION : Parfois LBC renvoie 200 même si supprimé (page "Cette annonce est désactivée")
                        # Pour être sûr à 100%, il faudrait faire un GET et chercher "Cette annonce est désactivée".
                        # Mais pour l'instant, faisons confiance au status code ou à la redirection.

                        # Si c'est toujours bon, on la "sauve"
                        # print(f"   ⛑️  Sauvetage : {ad.title[:20]} est toujours en ligne (Page 2+).")
                        ad.last_seen_at = datetime.now()
                        rescued_count += 1
                    else:
                        # 404, 410, ou autre erreur -> C'est fini
                        logger.info(
                            f"   👻 Disparue ({r.status_code}) : {ad.title[:20]} -> SOLD")
                        ad.status = "SOLD"
                        archived_count += 1

                except Exception:
                    # En cas d'erreur technique (timeout), dans le doute, on garde.
                    pass

            session.commit()
            logger.info(
                f"✅ Ménage terminé : {archived_count} archivées | {rescued_count} sauvées (toujours actives).")

        except Exception as e:
            logger.exception(f"❌ Erreur nettoyage : {e}")
            logger.info.rollback()
        finally:
            session.close()

    def is_ad_analyzed(self, ad_id: str) -> bool:
        """
        Vérifie si une annonce existe déjà ET possède une analyse IA.
        Retourne True si on peut éviter de la scrapper à nouveau.
        """
        session = self.Session()
        try:
            # On ne sélectionne que la colonne ai_analysis pour être très rapide
            # (Pas besoin de charger tout l'objet)
            ad = session.query(Ad.ai_analysis).filter_by(id=ad_id).first()

            # Si l'annonce existe et que le champ ai_analysis n'est pas vide -> True
            if ad and ad.ai_analysis:
                return True
            return False
        except Exception:
            return False
        finally:
            session.close()

    def _safe_int(self, value):
        if not value:
            return None
        if isinstance(value, (int, float)):
            return int(value)
        try:
            return int(''.join(filter(str.isdigit, str(value))))
        except:
            return None

    def _parse_date(self, date_str):
        if not date_str:
            return datetime.now()
        try:
            return datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        except:
            return datetime.now()

    def fetch_ads_for_price_training(self, search_id: str) -> List[Dict[str, Any]]:
        """
        Renvoie les champs nécessaires à la construction du dataset de training
        (y compris veto: k_arnaque, status, user_status, has_scores).
        """
        session = self.Session()
        try:
            ads = (
                session.query(
                    Ad.price, Ad.year, Ad.mileage, Ad.horsepower,
                    Ad.scores, Ad.status, Ad.user_status
                )
                .filter(Ad.found_by_searches.contains([search_id]))
                .all()
            )

            rows: List[Dict[str, Any]] = []
            for price, year, mileage, horsepower, scores, status, user_status in ads:
                scores_dict = scores or {}
                sanity = scores_dict.get("sanity_checks", {})
                rows.append({
                    "price": price,
                    "year": year,
                    "mileage": mileage,
                    "horsepower": horsepower,
                    "k_arnaque": sanity.get("k_arnaque"),
                    "status": status,
                    "user_status": user_status,
                    "has_scores": bool(scores),
                })
            return rows
        finally:
            session.close()

    def fetch_active_ads_for_deal_update(self, search_id: str) -> List[Dict[str, Any]]:
        """
        Renvoie les champs nécessaires pour recalculer S_Deal sur les annonces actives.
        On renvoie des dicts pour éviter de manipuler directement des objets ORM dans PriceEngine.
        """
        session = self.Session()
        try:
            ads = (
                session.query(
                    Ad.id, Ad.price, Ad.year, Ad.mileage, Ad.horsepower,
                    Ad.ai_analysis, Ad.scores
                )
                .filter(
                    Ad.found_by_searches.contains([search_id]),
                    Ad.status == "ACTIVE"
                )
                .all()
            )

            rows: List[Dict[str, Any]] = []
            for ad_id, price, year, mileage, horsepower, ai_analysis, scores in ads:
                rows.append({
                    "id": ad_id,
                    "price": price,
                    "year": year,
                    "mileage": mileage,
                    "horsepower": horsepower,
                    "ai_analysis": ai_analysis or {},
                    "scores": scores or {},
                })
            return rows
        finally:
            session.close()

    def bulk_update_scores(self, updates: List[Dict[str, Any]]) -> int:
        """
        updates = [{"id": "...", "scores": {...}}, ...]
        Retourne le nombre d'updates appliquées.
        """
        if not updates:
            return 0

        session = self.Session()
        try:
            count = 0
            for upd in updates:
                ad_id = upd["id"]
                new_scores = upd["scores"]
                ad = session.query(Ad).filter_by(id=ad_id).first()
                if not ad:
                    continue

                ad.scores = dict(new_scores)  # assignation explicite
                flag_modified(ad, "scores")
                count += 1

            session.commit()
            return count
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


if __name__ == "__main__":
    logger.info("🚀 Démarrage du test COMPLET BDD...")

    # 1. Connexion
    db = DatabaseClient()

    # 2. Test Insertion
    print("\n--- TEST 1 : Insertion ---")
    fake_data = [{
        "id": "test_archive_logic",
        "title": "Voiture qui va disparaître",
        "price": 1000,
        "url": "http://test",
        "date": "2023-01-01 12:00:00"
    }]
    db.upsert_ads(fake_data, search_id="test_uuid")

    # 3. Test Archivage (Simulation)
    print("\n--- TEST 2 : Archivage ---")
    # Pour tester, on va tricher et changer la date 'last_seen_at' en base directement via SQL
    # (C'est juste pour le test ici, en vrai ça se fera avec le temps)
    session = db.Session()
    ad = session.query(Ad).filter_by(id="test_archive_logic").first()
    if ad:
        # On fait croire qu'on l'a vue il y a 10 jours
        ad.last_seen_at = datetime.now() - timedelta(days=10)
        session.commit()
        print("🕒 (Triche) On a vieilli l'annonce de 10 jours pour le test.")
    session.close()

    # On lance le nettoyage avec un seuil de 2 jours.
    # Comme l'annonce a 10 jours, elle doit passer en SOLD.
    db.archive_old_ads(days_threshold=2)

    print("\n✅ Si tu vois 'Ménage terminé : 1 annonces...', tout fonctionne !")
