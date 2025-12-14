import streamlit as st
from frontend.layout import render_header

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LBC Hunter - Paramètres",
    page_icon="⚙️",
    layout="wide"
)
render_header("Settings")

st.title("⚙️ Paramètres")
st.caption("Configuration globale de LBC Hunter")

# -----------------------------------------------------------------------------
# WARNING
# -----------------------------------------------------------------------------
st.warning(
    "⚠️ Cette page est un **placeholder**.\n\n"
    "À terme, **tous les paramètres de l'application** "
    "(scoring, IA, scraping, performance, sécurité) "
    "seront centralisés ici."
)

# -----------------------------------------------------------------------------
# SECTIONS (structure cible)
# -----------------------------------------------------------------------------
with st.expander("🧠 Intelligence Artificielle", expanded=False):
    st.markdown("""
    **À venir :**
    - activation / désactivation de l’IA
    - seuils de sévérité (mécanique, modifications, arnaque)
    - paramètres du modèle Gemini
    """)

with st.expander("📊 Scoring & Pondérations", expanded=False):
    st.markdown("""
    **À venir :**
    - poids Deal / Confiance / Produit
    - règles de veto (annonces exclues du marché)
    - seuils de pénalité / bonus
    """)

with st.expander("🌐 Scraping & Réseau", expanded=False):
    st.markdown("""
    **À venir :**
    - délais min / max
    - timeouts
    - user-agents
    - fréquence des scans
    """)

with st.expander("⚡ Performance & Cache", expanded=False):
    st.markdown("""
    **À venir :**
    - TTL du cache Streamlit
    - pagination / limites UI
    - stratégie de rafraîchissement
    """)

with st.expander("🔐 Sécurité & Secrets", expanded=False):
    st.markdown("""
    **À venir :**
    - état des clés API
    - configuration DB (lecture seule)
    - avertissements sécurité
    """)

# -----------------------------------------------------------------------------
# FOOTER
# -----------------------------------------------------------------------------
st.info(
    "🎯 Objectif P1 :\n"
    "- une **config unique** (dataclass / pydantic)\n"
    "- persistée (JSON)\n"
    "- modifiable ici via l’UI\n"
    "- sans **aucune** valeur codée en dur ailleurs"
)
