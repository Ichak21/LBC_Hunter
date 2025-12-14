import streamlit as st
from frontend.layout import render_header
from core.search_manager import SearchManager

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="LBC Hunter - Gestion des Recherches",
    page_icon="🎛️",
    layout="wide"
)
render_header("Searches Manager")

st.title("🎛️ Gestion des Recherches")
st.caption("Configuration et pilotage des recherches Leboncoin")

# -----------------------------------------------------------------------------
# DATA
# -----------------------------------------------------------------------------
searches = SearchManager.list_searches()

if not searches:
    st.info("Aucune recherche configurée pour le moment.")
    st.stop()

# -----------------------------------------------------------------------------
# TABLE (lecture seule pour l’instant)
# -----------------------------------------------------------------------------
st.subheader("📡 Recherches existantes")

st.dataframe(
    searches,
    use_container_width=True,
    hide_index=True
)

# -----------------------------------------------------------------------------
# PLACEHOLDER ACTIONS
# -----------------------------------------------------------------------------
st.divider()
st.subheader("🚧 Actions (à venir)")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.button("➕ Créer une recherche", disabled=True)

with col2:
    st.button("✏️ Modifier", disabled=True)

with col3:
    st.button("⏸️ Activer / Désactiver", disabled=True)

with col4:
    st.button("▶️ Lancer un scan", disabled=True)

st.info(
    "Cette page est un **placeholder fonctionnel**.\n\n"
    "Les actions seront activées lors du P1 :\n"
    "- création / édition de recherches\n"
    "- activation/désactivation\n"
    "- déclenchement manuel du worker"
)
