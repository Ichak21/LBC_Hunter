import streamlit as st
import subprocess
import sys
import pandas as pd
import time
from datetime import datetime
from frontend.layout import render_header
from core.search_manager import SearchManager

# -----------------------------------------------------------------------------
# CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(page_title="LBC Hunter - Gestion Recherches",
                   page_icon="🎛️", layout="wide")
render_header("Searches Manager")

st.title("🎛️ Gestion des Recherches")

# -----------------------------------------------------------------------------
# HELPER : TOGGLE ACTIVE
# -----------------------------------------------------------------------------


def toggle_search_state(search_id, current_state):
    """
    Change le statut actif/inactif d'une recherche.
    Note: Idéalement, cette méthode devrait être dans SearchManager.
    """
    s = SearchManager.get_search(search_id)
    if s:
        s['active'] = not current_state
        # On utilise la méthode privée _save_file (accessible car on est en python)
        # Pour faire plus propre, on ajoutera une méthode publique plus tard.
        SearchManager._save_file(s)

# -----------------------------------------------------------------------------
# MODAL DE CRÉATION
# -----------------------------------------------------------------------------


@st.dialog("Nouvelle Recherche")
def show_create_modal():
    with st.form("create_search_form"):
        name = st.text_input("Nom de la recherche (ex: Golf 7 GTI)")
        search_text = st.text_input("Mots-clés LBC (ex: golf gti)")

        c1, c2 = st.columns(2)
        min_p = c1.number_input("Prix Min", value=1000, step=500)
        max_p = c2.number_input("Prix Max", value=20000, step=500)

        c3, c4 = st.columns(2)
        min_y = c3.number_input("Année Min", value=2010, step=1)
        max_y = c4.number_input("Année Max", value=2024, step=1)

        st.markdown("**Filtres Avancés**")
        whitelist_str = st.text_input(
            "Whitelist (mots obligatoires, séparés par virgule)", placeholder="gti, performance")
        blacklist_str = st.text_input(
            "Blacklist (mots interdits, séparés par virgule)", placeholder="tdi, diesel, accident")

        if st.form_submit_button("Créer"):
            if not name or not search_text:
                st.error("Nom et Mots-clés obligatoires.")
            else:
                # Parsing listes
                whitelist = [w.strip()
                             for w in whitelist_str.split(",") if w.strip()]
                blacklist = [b.strip()
                             for b in blacklist_str.split(",") if b.strip()]

                # Build Params
                lbc_params = SearchManager.build_params(
                    search_text,
                    min_year=str(min_y), max_year=str(max_y),
                    min_price=str(min_p), max_price=str(max_p)
                )

                SearchManager.create_search(
                    name, lbc_params, whitelist, blacklist)
                st.success(f"Recherche '{name}' créée !")
                st.rerun()


# -----------------------------------------------------------------------------
# TABLEAU DE BORD
# -----------------------------------------------------------------------------
col_create, _ = st.columns([1, 5])
if col_create.button("➕ Créer une recherche"):
    show_create_modal()

searches = SearchManager.list_searches()

if not searches:
    st.info("Aucune recherche. Créez-en une !")
    st.stop()

# --- TABLEAU INTERACTIF ---
# On affiche les recherches sous forme de cartes ou tableau avec actions
st.divider()

for s in searches:
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([0.5, 2, 2, 1, 1])

        # 1. Statut (Icone)
        is_active = s.get("active", True)
        icon = "🟢" if is_active else "⏸️"
        c1.markdown(f"### {icon}")

        # 2. Nom & ID
        with c2:
            st.markdown(f"**{s['name']}**")
            st.caption(f"ID: `{s['id']}`")

        # 3. Détails (Prix / Année / Keywords)
        with c3:
            p = s.get('lbc_params', {})
            txt = p.get('text', 'N/A')
            year = p.get('regdate', 'N/A')
            st.text(f"🔍 {txt} | 📅 {year}")

        # 4. Toggle Active
        with c4:
            # On utilise un key unique pour éviter les conflits
            btn_label = "Désactiver" if is_active else "Activer"
            if st.button(btn_label, key=f"btn_toggle_{s['id']}", use_container_width=True):
                toggle_search_state(s['id'], is_active)
                st.rerun()

        # 5. Scan Manuel
        with c5:
            if st.button("▶️ Scan", key=f"btn_scan_{s['id']}", use_container_width=True, disabled=not is_active):
                with st.spinner(f"Scan de '{s['name']}' en cours..."):
                    try:
                        # Lancement du subprocess main.py avec l'argument --search_id
                        subprocess.run(
                            [sys.executable, "main.py", "--search_id", s['id']], check=True)
                        st.success("Terminé !")
                        time.sleep(1)
                        # On recharge pour mettre à jour la date de last_run
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erreur: {e}")
