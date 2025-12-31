import streamlit as st
import time
from frontend.layout import render_header
from core.config_manager import ConfigManager

# -----------------------------------------------------------------------------
# CONFIG & HEADER
# -----------------------------------------------------------------------------
st.set_page_config(page_title="LBC Hunter - Paramètres",
                   page_icon="⚙️", layout="wide")
render_header("Settings")

st.title("⚙️ Paramètres")
st.caption("Ajustez la sensibilité de l'algorithme et le comportement du robot.")

# Chargement de la config actuelle
config = ConfigManager.get_config()
default_weights = config.get(
    "weights", {"deal": 0.5, "conf": 0.3, "prod": 0.2})
default_automation = config.get(
    "automation", {"min_interval_minutes": 30, "max_interval_minutes": 90})

# -----------------------------------------------------------------------------
# FORMULAIRE
# -----------------------------------------------------------------------------
with st.form("settings_form"):

    # --- SECTION 1 : SCORING ---
    st.subheader("📊 Pondération du Scoring (Total = 1.0)")

    col1, col2, col3 = st.columns(3)

    with col1:
        w_deal = st.slider(
            "💰 Poids Deal (Prix/Marché)",
            min_value=0.0, max_value=1.0,
            value=float(default_weights.get("deal", 0.5)),
            step=0.05,
            help="Importance du prix par rapport à la cote."
        )

    with col2:
        w_conf = st.slider(
            "🤝 Poids Confiance (Vendeur)",
            min_value=0.0, max_value=1.0,
            value=float(default_weights.get("conf", 0.3)),
            step=0.05,
            help="Importance de la qualité de l'annonce et du profil vendeur."
        )

    with col3:
        w_prod = st.slider(
            "💎 Poids Produit (Options)",
            min_value=0.0, max_value=1.0,
            value=float(default_weights.get("prod", 0.2)),
            step=0.05,
            help="Importance de la finition et des options détectées."
        )

    total_weights = w_deal + w_conf + w_prod
    if abs(total_weights - 1.0) > 0.01:
        st.warning(
            f"⚠️ La somme des poids fait {total_weights:.2f} (Idéalement 1.0)")
    else:
        st.success("✅ La somme des poids est correcte (1.0)")

    st.divider()

    # --- SECTION 2 : AUTOMATISATION ---
    st.subheader("🤖 Automatisation (Scheduler)")
    st.caption(
        "Définit l'intervalle de temps aléatoire entre deux scans automatiques.")

    c_auto1, c_auto2 = st.columns(2)
    with c_auto1:
        min_interval = st.number_input(
            "⏱️ Intervalle Min (minutes)",
            min_value=5, max_value=1440,
            value=int(default_automation.get("min_interval_minutes", 30))
        )
    with c_auto2:
        max_interval = st.number_input(
            "⏱️ Intervalle Max (minutes)",
            min_value=5, max_value=1440,
            value=int(default_automation.get("max_interval_minutes", 90))
        )

    if min_interval >= max_interval:
        st.error("⚠️ L'intervalle min doit être inférieur au max.")

    st.divider()

    # --- ACTIONS ---
    col_save, col_reset = st.columns([1, 5])

    with col_save:
        submitted = st.form_submit_button(
            "💾 Sauvegarder", type="primary", use_container_width=True)

# LOGIQUE DE SAUVEGARDE (Hors du layout form pour gérer le reset proprement)
if submitted:
    new_config = config.copy()

    # Update Weights
    new_config["weights"] = {
        "deal": round(w_deal, 2),
        "conf": round(w_conf, 2),
        "prod": round(w_prod, 2)
    }

    # Update Automation
    new_config["automation"] = {
        "min_interval_minutes": int(min_interval),
        "max_interval_minutes": int(max_interval)
    }

    ConfigManager.save_config(new_config)
    st.toast("Configuration sauvegardée avec succès !", icon="✅")
    time.sleep(1)
    st.rerun()

# BOUTON RESET (Hors du form)
st.markdown("---")
with st.expander("Danger Zone"):
    if st.button("♻️ Réinitialiser aux paramètres d'usine"):
        ConfigManager.reset_to_default()
        st.toast("Paramètres d'usine rétablis.", icon="♻️")
        time.sleep(1)
        st.rerun()
