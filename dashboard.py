import streamlit as st
import pandas as pd
import os
import plotly.express as px
from frontend.layout import render_header
from frontend.data_loader import load_home_data, load_logs

# 0. CONFIG & HEADER
st.set_page_config(page_title="LBC Hunter - Home",
                   page_icon="🦅", layout="wide")
render_header("Home")

# Chargement données
status_counts, df_ads, df_searches = load_home_data()

st.title("🦅 Dashboard")


def request_nav(page_path: str, **state_updates):
    """Demande une navigation. À exécuter dans le flux principal, pas dans un callback."""
    for k, v in state_updates.items():
        st.session_state[k] = v
    st.session_state["_nav_target"] = page_path


def consume_nav():
    """Exécute la navigation demandée (si présente) puis nettoie."""
    target = st.session_state.pop("_nav_target", None)
    if target:
        st.switch_page(target)


def handle_search_selection():
    sel = st.session_state["search_table"].selection
    rows = sel.get("rows", [])
    if rows:
        idx = rows[0]
        selected_id = st.session_state["df_searches"].iloc[idx]["id"]
        request_nav("pages/1_🔍_Details_Searches.py",
                    selected_search_id=selected_id)


def handle_ad_selection(df_key, table_key):
    sel = st.session_state[table_key].selection
    rows = sel.get("rows", [])
    if rows:
        idx = rows[0]
        selected_id = st.session_state[df_key].iloc[idx]["ID"]
        request_nav("pages/2_📄_Details_Ads.py", selected_ad_id=selected_id)


# On stocke les DataFrames de base en Session State pour les handlers
if not df_searches.empty:
    st.session_state["df_searches"] = df_searches


# =============================================================================
# BLOC 1 : RECHERCHES
# =============================================================================
c1, c2 = st.columns([2, 1])

with c1:
    st.subheader("📡 Recherches Actives")
    if not df_searches.empty:
        st.dataframe(
            df_searches,
            column_config={
                "name": st.column_config.TextColumn("Nom", width="medium"),
                "Année": st.column_config.TextColumn("Année", width="small"),
                "Whitelist": st.column_config.TextColumn("White", width="small"),
                "Blacklist": st.column_config.TextColumn("Black", width="small"),
                "last_run_at": st.column_config.DatetimeColumn("Dernier Scan", format="DD/MM HH:mm", width="small"),
                "id": st.column_config.TextColumn("ID", width="small")
            },
            use_container_width=True,
            hide_index=True,
            selection_mode="single-row",
            key="search_table",
            on_select=handle_search_selection
        )
    else:
        st.info("Aucune recherche.")

with c2:
    st.subheader("📊 Parc Global")
    if status_counts:
        df_status = pd.DataFrame(
            list(status_counts.items()), columns=["Statut", "Count"])
        fig = px.pie(df_status, values='Count', names='Statut', hole=0.5,
                     color='Statut',
                     color_discrete_map={'ACTIVE': '#4CAF50',
                                         'SOLD': '#9E9E9E', 'SCAM': '#F44336'})
        fig.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom",
                        y=-0.2, xanchor="center", x=0.5),
            margin=dict(t=0, b=20, l=0, r=0),
            height=200
        )
        st.plotly_chart(fig, use_container_width=True)

st.divider()

# =============================================================================
# BLOC 2 : PÉPITES & FAVORIS
# =============================================================================
st.subheader("💰 Opportunités")

col_left, col_right = st.columns(2)

# FONCTION DE STYLE HYBRIDE


def get_styled_dataframe(df_in):
    if df_in.empty:
        return df_in

    df_view = df_in[["ID", "Titre", "Prix", "Gain",
                     "Note Brute", "Indice K", "Favori", "URL"]]

    styler = df_view.style.format({
        "Prix": "{:.0f} €",
        "Gain": "{:+.0f} €"
    }).map(
        lambda v: f'color: {"#4CAF50" if v > 0 else "#F44336"}; font-weight: bold;',
        subset=['Gain']
    )
    return styler


# CONFIGURATION DES COLONNES
common_config = {
    "Titre": st.column_config.TextColumn("Annonce", width="medium"),
    "Gain": st.column_config.TextColumn("Gain/Perte", width="small"),

    "Note Brute": st.column_config.ProgressColumn(
        "Note Brute", format="%d", min_value=0, max_value=100, width="small", color="#4CAF50"
    ),
    "Indice K": st.column_config.ProgressColumn(
        "Indice K", format="%d%%", min_value=0, max_value=100, width="small", color="#2196F3"
    ),
    "ID": None, "Favori": None, "URL": None
}

# --- TABLE GAUCHE ---
with col_left:
    min_score = st.slider("Note Brute Min.", 0, 100,
                          50, label_visibility="collapsed", key="score_slider")
    st.markdown(f"**🎯 Pépites (Note Brute > {min_score})**")

    if not df_ads.empty:
        df_pepites = df_ads[df_ads["Note Brute"] >=
                            min_score].sort_values(by="Note Brute", ascending=False)
        # Stockage pour le handler
        st.session_state["df_pepites"] = df_pepites

        st.dataframe(
            get_styled_dataframe(df_pepites),
            column_config=common_config,
            use_container_width=True,
            hide_index=True,
            height=400,
            selection_mode="single-row",
            key="pepites_table",
            on_select=lambda: handle_ad_selection(
                "df_pepites", "pepites_table")
        )
    else:
        st.info("Aucune pépite.")

# --- TABLE DROITE ---
with col_right:
    st.markdown("**❤️ Mes Favoris**")

    if not df_ads.empty:
        df_fav = df_ads[df_ads["Favori"] == True].sort_values(
            by="Note Brute", ascending=False)
        # Stockage pour le handler
        st.session_state["df_fav"] = df_fav

        if not df_fav.empty:
            st.dataframe(
                get_styled_dataframe(df_fav),
                column_config=common_config,
                use_container_width=True,
                hide_index=True,
                height=400,
                selection_mode="single-row",
                key="fav_table",
                on_select=lambda: handle_ad_selection("df_fav", "fav_table")
            )
        else:
            st.info("Aucun favori.")
    else:
        st.info("Base vide.")

st.divider()

# =============================================================================
# BLOC 3 : LOGS
# =============================================================================
st.subheader("📟 Logs Worker")
logs_content = load_logs(lines=200)
st.markdown(f"""
<div style="
    height: 600px; width: 100%; overflow-y: scroll; 
    background-color: #0e1117; color: #c9d1d9; 
    padding: 15px; border: 1px solid #30333d; border-radius: 5px; 
    font-family: 'Consolas', monospace; font-size: 12px; line-height: 1.5;
    white-space: pre-wrap;">{logs_content}</div>
""", unsafe_allow_html=True)
st.write("")
st.write("")

# =============================================================================
# BLOC 4 : consume la navigation demandée
# =============================================================================
consume_nav()
