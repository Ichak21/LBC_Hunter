from pathlib import Path
import streamlit as st
from streamlit_option_menu import option_menu


def _safe_switch_page(path: str):
    # Streamlit attend un chemin relatif type "pages/xxx.py" ou "dashboard.py"
    if Path(path).exists():
        st.switch_page(path)
    else:
        st.warning(f"Page indisponible pour le moment : `{path}`")


def render_header(current_page: str):
    """
    Affiche le menu de navigation horizontal et gère la redirection
    si la page sélectionnée dans le menu n'est pas la page courante.
    """
    # 1. Masquer la sidebar native
    st.markdown("""
        <style>
            [data-testid="stSidebarNav"] {display: none;}
        </style>
    """, unsafe_allow_html=True)

    # 2. Détermination de l'index par défaut (pour que l'onglet actuel soit mis en surbrillance)
    options = ["Home", "Details Searches",
               "Details Ads", "Searches Manager", "Settings"]
    try:
        default_index = options.index(current_page)
    except ValueError:
        default_index = 0  # Par défaut sur Home si la page n'est pas reconnue

    # 3. Affichage du Menu
    selected = option_menu(
        menu_title=None,
        options=options,  # Doit être une LISTE
        icons=['house', 'search', 'file-earmark-text',
               'sliders', 'gear'],  # Doit être une LISTE
        menu_icon="cast",
        default_index=default_index,  # Index par défaut
        orientation="horizontal",
        styles={
            "container": {"padding": "5px", "background-color": "#fafafa"},
            "icon": {"color": "#ff4b4b", "font-size": "18px"},
            "nav-link": {"font-size": "14px", "text-align": "center", "margin": "2px"},
            "nav-link-selected": {"background-color": "#ff4b4b", "color": "white"},
        }  # Doit être un DICTIONNAIRE
    )

    # 4. Navigation conditionnelle (empêche la boucle infinie)
    if selected == "Details Searches" and current_page != "Details Searches":
        _safe_switch_page("pages/1_🔍_Details_Searches.py")
    elif selected == "Details Ads" and current_page != "Details Ads":
        _safe_switch_page("pages/2_📄_Details_Ads.py")
    elif selected == "Searches Manager" and current_page != "Searches Manager":
        _safe_switch_page("pages/3_🎛️_Searches_Manager.py")
    elif selected == "Settings" and current_page != "Settings":
        _safe_switch_page("pages/4_⚙️_Settings.py")
    elif selected == "Home" and current_page != "Home":
        _safe_switch_page("dashboard.py")

    return selected
