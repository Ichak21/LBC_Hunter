from sqlalchemy import Column, String, Integer, DateTime, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from datetime import datetime

Base = declarative_base()


class Ad(Base):
    __tablename__ = "ads"

    # --- 1. IDENTIFICATION ---
    id = Column(String, primary_key=True)
    url = Column(String, nullable=False)

    # --- 2. LIEN RECHERCHES ---
    found_by_searches = Column(JSONB, default=list)

    # --- 3. INFOS VÉHICULE ---
    title = Column(String)
    description = Column(Text)
    price = Column(Integer)
    mileage = Column(Integer, nullable=True)
    year = Column(Integer, nullable=True)
    fuel = Column(String, nullable=True)
    gearbox = Column(String, nullable=True)
    horsepower = Column(Integer, nullable=True)
    finition = Column(String, nullable=True)

    # --- 4. LOCALISATION ---
    location = Column(String, nullable=True)
    zipcode = Column(String, nullable=True)

    # --- 5. INFOS VENDEUR ---
    seller_rating = Column(Float, nullable=True)
    seller_rating_count = Column(Integer, default=0)

    # --- 6. TEMPOREL ---
    publication_date = Column(DateTime)
    first_seen_at = Column(DateTime, default=datetime.now)
    last_seen_at = Column(DateTime, default=datetime.now)

    # --- 7. STATUS ROBOT ---
    status = Column(String, default="ACTIVE")  # ACTIVE, SOLD, DELETED

    # --- 8. MÉMOIRE ---
    price_history = Column(JSONB, default=list)

    # --- 9. INTELLIGENCE ---
    scores = Column(JSONB, nullable=True)
    ai_analysis = Column(JSONB, nullable=True)

    # --- 10. DATA BRUTE ---
    raw_data = Column(JSONB)

    # --- 11. GESTION UTILISATEUR (NOUVEAU) ---
    # Permet de flaguer une annonce comme favori (cœur)
    is_favorite = Column(Boolean, default=False)

    # Permet de masquer une annonce (poubelle) ou de la signaler manuellement
    # Valeurs possibles : 'NORMAL', 'TRASH', 'SCAM_MANUAL'
    user_status = Column(String, default="NORMAL")

    def __repr__(self):
        return f"<Ad {self.id} [{self.status}] : {self.title} ({self.price}€)>"
