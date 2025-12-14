import streamlit as st
from frontend.layout import render_header

st.set_page_config(page_title="LBC Hunter - Fiche Annonce",
                   page_icon="📄", layout="wide")
render_header("Details Ads")

ad_id = st.session_state.get("selected_ad_id")
st.title("📄 Fiche Annonce (WIP)")

if not ad_id:
    st.info("Aucune annonce sélectionnée. Retourne sur Home ou Details Searches.")
else:
    st.success(f"Annonce sélectionnée : {ad_id}")
