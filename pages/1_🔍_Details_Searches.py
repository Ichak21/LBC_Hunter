import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from frontend.layout import render_header
from frontend.data_loader import load_search_details_data
from core.search_manager import SearchManager

# 0. CONFIG & HEADER
st.set_page_config(page_title="LBC Hunter - Analyse Recherche",
                   page_icon="🔍", layout="wide")
render_header("Details Searches")

# --- HANDLER DE NAVIGATION ---


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


def handle_ad_click_details(df_key: str, selection: dict | None):
    """Prépare la navigation vers Details Ads (sans switch_page dans le callback)."""
    selected_ad_id = None

    # 1) Clic Plotly
    if selection and selection.get("points"):
        point_index = selection["points"][0]["pointIndex"]
        selected_ad_id = st.session_state[df_key].iloc[point_index]["ID"]

    # 2) Clic Table
    elif selection and selection.get("rows"):
        idx = selection["rows"][0]
        selected_ad_id = st.session_state[df_key].iloc[idx]["ID"]

    if selected_ad_id:
        request_nav("pages/2_📄_Details_Ads.py", selected_ad_id=selected_ad_id)


# =============================================================================
# 1. SÉLECTION DE LA RECHERCHE
# =============================================================================
searches_list = SearchManager.list_searches()
search_options = {s["name"]: s["id"] for s in searches_list}
search_names = list(search_options.keys())

# Gestion de l'état si on vient de la Home ou par défaut
initial_search_id = st.session_state.get("selected_search_id")
initial_index = 0
if initial_search_id and initial_search_id in search_options.values():
    try:
        initial_search_name = next(
            name for name, id_ in search_options.items() if id_ == initial_search_id)
        initial_index = search_names.index(initial_search_name)
    except StopIteration:
        pass

# Sélecteur de recherche
selected_name = st.selectbox(
    "Recherche Analysée :",
    options=search_names,
    index=initial_index,
    key="search_selector"
)
selected_id = search_options.get(selected_name)
st.session_state["selected_search_id"] = selected_id

st.title(f"🔍 Analyse Détaillée : {selected_name}")

# =============================================================================
# 2. CHARGEMENT DES DONNÉES
# =============================================================================

if not selected_id:
    st.info("Sélectionnez une recherche pour afficher les détails.")
    st.stop()

# Chargement de toutes les annonces de la recherche (y compris Sold/Scam)
search_name, r2_score, status_counts, df_ads = load_search_details_data(
    selected_id)

if df_ads.empty:
    st.info(f"Aucune annonce trouvée pour la recherche '{selected_name}'.")
    st.stop()

# Stockage du DataFrame complet pour les handlers de clic
st.session_state["df_details_search"] = df_ads


# =============================================================================
# 3. KPIS & PIE CHART
# =============================================================================

col_kpis_1, col_kpis_2, col_kpis_3, col_kpis_4 = st.columns(4)

with col_kpis_1:
    st.metric("Total Annonces", len(df_ads))

with col_kpis_2:
    r2_display = f"{float(r2_score):.2f}" if isinstance(
        r2_score, (int, float)) else r2_score
    st.metric("R² Modèle Prix", r2_display,
              help="Coefficient de détermination R² de la dernière régression du Price Engine.")

with col_kpis_3:
    active_ads = df_ads[df_ads["Statut"] == "ACTIVE"]
    if not active_ads.empty:
        best_deal = active_ads.sort_values(
            by="Score Final", ascending=False).iloc[0]
        st.metric("Meilleure Note", f"{best_deal['Score Final']:.1f}",
                  help=f"Annonce: {best_deal['Titre']} ({best_deal['Gain']:+.0f} €)")
    else:
        st.metric("Meilleure Note", "N/A")

with col_kpis_4:
    # PIE CHART (Répartition par Statut)
    df_status = pd.DataFrame(list(status_counts.items()),
                             columns=["Statut", "Count"])
    df_status = df_status[df_status["Count"] > 0]

    fig_pie = px.pie(df_status, values='Count', names='Statut', hole=0.5,
                     color='Statut',
                     color_discrete_map={'ACTIVE': '#4CAF50', 'SOLD': '#9E9E9E', 'SCAM': '#000000'})
    fig_pie.update_layout(
        margin=dict(t=0, b=0, l=0, r=0),
        height=150,
        showlegend=False
    )
    st.plotly_chart(fig_pie, use_container_width=True)


st.divider()

# =============================================================================
# 4. SCATTER PLOT (Kilométrage vs Prix vs Score)
# =============================================================================

st.subheader("📈 Carte du Marché (Prix vs Kilométrage)")

# Création du texte d'info au survol (Hover Text)
df_ads['Hover Text'] = df_ads.apply(
    lambda row: (
        f"<b>{row['Titre']}</b><br>"
        f"Prix: {row['Prix']:,.0f} €<br>"
        f"Kilométrage: {row['Kilométrage']:,.0f} km<br>"
        f"Statut: {row['Statut']}<br>"
        f"--- Calcul Score ---<br>"
        f"Note Brute: {row['Note Brute']:.0f}<br>"
        f"Deal/Conf/Prod: {row['Deal Score']:.0f}/{row['Conf Score']:.0f}/{row['Prod Score']:.0f}<br>"
        f"Indice K: {row['Indice K']:.0f}% ({row['K Mecanique']:.1f}x / {row['K Modification']:.1f}x / {row['K Arnaque']:.1f}x)<br>"
        f"<b>Score Final: {row['Score Final']:.1f}</b>"
    ), axis=1
)

# Configuration des symboles (Formes)
symbol_map = {
    'ACTIVE': 'circle',  # Rond
    'SOLD': 'x',         # Croix
    'SCAM': 'square'     # Carré
}

# --- CRÉATION DU GRAPHE AVEC LOGIQUE DE COULEUR COMPLEXE ---
fig_scatter = go.Figure()

# Couleurs fixes pour SOLD (Gris) et SCAM (Noir)
STATUS_COLORS = {'SOLD': '#9E9E9E', 'SCAM': '#000000'}

# Ajout des annonces SOLD et SCAM (couleur et forme fixes, sans gradient)
for status, color in STATUS_COLORS.items():
    subset = df_ads[df_ads["Statut"] == status]
    if not subset.empty:
        fig_scatter.add_trace(go.Scatter(
            x=subset["Kilométrage"],
            y=subset["Prix"],
            mode='markers',
            name=f"Annonces {status}",
            marker=dict(
                size=12,
                color=color,
                symbol=symbol_map[status],
                line=dict(width=1, color='DarkSlateGrey'),
            ),
            text=subset['Hover Text'],  # Texte pour le survol
            hovertemplate='%{text}<extra></extra>'
        ))

# Ajout des annonces ACTIVE (forme fixe, couleur en gradient selon le Score Final)
subset_active = df_ads[df_ads["Statut"] == 'ACTIVE']
if not subset_active.empty:
    fig_scatter.add_trace(go.Scatter(
        x=subset_active["Kilométrage"],
        y=subset_active["Prix"],
        mode='markers',
        name="Annonces Actives",
        marker=dict(
            size=12,
            symbol=symbol_map['ACTIVE'],
            line=dict(width=1, color='DarkSlateGrey'),
            # GRADIENT ROUGE (0) -> VERT (100) basé sur le score final
            color=subset_active['Score Final'],
            colorscale=[[0, 'red'], [0.5, 'yellow'], [1, 'green']],
            cmin=0,
            cmax=100,
            colorbar=dict(title="Score Final", tickvals=[0, 50, 100], ticktext=[
                          "0 (Rouge)", "50 (Jaune)", "100 (Vert)"])
        ),
        text=subset_active['Hover Text'],
        hovertemplate='%{text}<extra></extra>'
    ))

fig_scatter.update_layout(
    xaxis_title="Kilométrage (km)",
    yaxis_title="Prix (€)",
    height=600,
    hovermode="closest",
    legend=dict(orientation="h", yanchor="bottom",
                y=1.02, xanchor="right", x=1)
)

# Affichage du graphique avec gestion du clic
st.plotly_chart(
    fig_scatter,
    use_container_width=True,
    on_select=lambda selection: handle_ad_click_details(
        "df_details_search", selection),
    selection_mode='points'
)


# =============================================================================
# 5. TABLEAU DE DONNÉES
# =============================================================================

st.subheader("Liste Complète des Annonces")

# Configuration des colonnes
ads_column_config = {
    "Titre": st.column_config.TextColumn("Annonce", width="large"),
    "Prix": st.column_config.NumberColumn("Prix (€)", format="%.0f €"),
    "Kilométrage": st.column_config.NumberColumn("Km", format="%.0f"),
    "Statut": st.column_config.TextColumn("Statut", width="small"),
    # La colonne Gain/Perte est gérée par le Pandas Styler pour la couleur du texte
    "Gain": st.column_config.TextColumn("Gain/Perte", width="small"),
    "Score Final": st.column_config.ProgressColumn("Note Finale", min_value=0, max_value=100, format="%.1f"),

    # Colonnes masquées
    "ID": None, "Année": None, "Favori": None, "URL": None, "Deal Score": None, "Conf Score": None, "Prod Score": None,
    "K Mecanique": None, "K Modification": None, "K Arnaque": None, "Note Brute": None, "Indice K": None
}

# Fonction de style pour la table (Couleur Rouge/Vert sur Gain/Perte)


def get_styled_dataframe_details(df_in):
    if df_in.empty:
        return df_in

    styler = df_in.style.format({
        "Prix": "{:.0f} €",
        "Gain": "{:+.0f} €",
        "Kilométrage": "{:.0f}",
        "Score Final": "{:.1f}"
    }).map(
        lambda v: f'color: {"#4CAF50" if v > 0 else "#F44336"}; font-weight: bold;',
        subset=['Gain']
    )
    return styler


df_sorted = df_ads.sort_values(
    by="Score Final", ascending=False).reset_index(drop=True)
st.session_state["df_details_search_sorted"] = df_sorted

TABLE_KEY = "details_ads_table"

st.dataframe(
    get_styled_dataframe_details(df_sorted),
    column_config=ads_column_config,
    use_container_width=True,
    hide_index=True,
    selection_mode="single-row",
    key=TABLE_KEY,
    on_select=lambda: handle_ad_click_details(
        "df_details_search_sorted",
        st.session_state[TABLE_KEY].selection
    ),
)

consume_nav()
