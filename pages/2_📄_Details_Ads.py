# pages/2_📄_Details_Ads.py

import streamlit as st

# ----------------------------------------------------------------------
# ⚠️ Streamlit requirement: MUST be first executed statement in the page
# ----------------------------------------------------------------------
st.set_page_config(page_title="LBC Hunter - Fiche Annonce",
                   page_icon="📄", layout="wide")


def main():
    import pandas as pd
    import plotly.graph_objects as go
    from datetime import datetime

    from frontend.layout import render_header
    from frontend.data_loader import load_ad_details_data, load_ads_selector
    from core.db_client import DatabaseClient

    # Service re-scan (alive + IA + scoring)
    from core.rescan_service import rescan_ad

    render_header("Details Ads")

    # -------------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------------
    def fmt_dt(d) -> str:
        if not d:
            return "—"
        try:
            return d.strftime("%d/%m/%Y %H:%M")
        except Exception:
            return str(d)

    def safe_get(d: dict, path: str, default="—"):
        """
        path: "a.b.c"
        """
        cur = d
        for p in path.split("."):
            if not isinstance(cur, dict) or p not in cur:
                return default
            cur = cur[p]
        return cur if cur is not None else default

    def build_price_history_chart(ad: dict):
        history = ad.get("price_history") or []
        points = []

        # historique: [{"date": "...iso...", "price": 12345}, ...]
        for h in history:
            dt = h.get("date")
            price = h.get("price")
            if not dt or price is None:
                continue
            try:
                points.append(
                    {"date": pd.to_datetime(dt), "price": float(price)})
            except Exception:
                pass

        # point courant
        try:
            last_seen = ad.get("last_seen_at") or datetime.now()
            points.append(
                {"date": pd.to_datetime(last_seen), "price": float(
                    ad.get("price") or 0)}
            )
        except Exception:
            pass

        if not points:
            return None

        df = pd.DataFrame(points).sort_values("date")

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=df["date"],
                y=df["price"],
                mode="lines+markers",
                name="Prix",
            )
        )
        fig.update_layout(
            height=320,
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis_title="Date",
            yaxis_title="Prix (€)",
        )
        return fig

    def severity_progress(label: str, value_0_1: float):
        """
        Affiche une barre de 'pénalité' en % à partir d'un ratio 0..1.
        Ici on attend généralement (1-k) quand on part d'un K (0..1).
        """
        try:
            v = float(value_0_1)
        except Exception:
            v = 0.0
        v = max(0.0, min(1.0, v))
        pct = int(v * 100)
        st.progress(pct, text=f"{label} — {pct}%")

    def render_ai_list(title: str, items: list, max_items: int = 12):
        st.markdown(f"**{title}**")
        if not items:
            st.caption("—")
            return
        for it in items[:max_items]:
            nom = it.get("nom") or it.get("item") or "—"
            sev = it.get("severity")
            if sev is None:
                st.write(f"- {nom}")
            else:
                try:
                    st.write(f"- {nom} (severity={float(sev):.2f})")
                except Exception:
                    st.write(f"- {nom}")

    # -------------------------------------------------------------------------
    # 1) Sélecteur d'annonce (toujours visible)
    # -------------------------------------------------------------------------
    rows = load_ads_selector(limit=250)

    options = {}
    default_index = 0

    if rows:
        labels = []
        for r in rows:
            label = (
                f"{(r.get('title') or '—')[:60]} | {r.get('price','—')}€ | "
                f"{r.get('status','—')} | {r.get('id')}"
            )
            labels.append(label)
            options[label] = r["id"]

        current_id = st.session_state.get("selected_ad_id")

        # Calcule l'index par défaut si on vient d'un clic (Home / Search details)
        if current_id:
            try:
                current_label = next(
                    k for k, v in options.items() if v == current_id)
                default_index = labels.index(current_label)
            except StopIteration:
                default_index = 0

        selected_label = st.selectbox(
            "Annonce (navigation)",
            labels,
            index=default_index,
            key="ad_nav_selector",
        )

        selected_id = options[selected_label]
        if st.session_state.get("selected_ad_id") != selected_id:
            st.session_state["selected_ad_id"] = selected_id
            # rerun OK ici (pas dans callback)
            st.rerun()
    else:
        st.warning("Aucune annonce disponible (ou toutes sont TRASH).")
        st.stop()

    ad_id = st.session_state.get("selected_ad_id")

    # -------------------------------------------------------------------------
    # 2) Load details
    # -------------------------------------------------------------------------
    ad = load_ad_details_data(ad_id)
    if not ad:
        st.error(f"Annonce introuvable en base: {ad_id}")
        st.stop()

    # -------------------------------------------------------------------------
    # 3) HEADER
    # -------------------------------------------------------------------------
    col_h1, col_h2 = st.columns([4, 1], vertical_alignment="center")
    with col_h1:
        st.title(ad.get("title") or f"Annonce {ad_id}")
        st.caption(f"ID LBC: `{ad_id}`")
    with col_h2:
        if ad.get("url"):
            st.link_button("🔗 Ouvrir sur LBC",
                           ad["url"], use_container_width=True)

    st.divider()

    # -------------------------------------------------------------------------
    # 4) AI SUMMARY
    # -------------------------------------------------------------------------
    summary = safe_get(ad, "ai_analysis.summary", default=None)
    with st.container(border=True):
        st.subheader("🧠 AI Summary")
        if summary:
            st.write(summary)
        else:
            st.info("Pas encore d'analyse IA disponible pour cette annonce.")

    # -------------------------------------------------------------------------
    # 5) Infos clés / Vendeur / Véhicule
    # -------------------------------------------------------------------------
    c1, c2, c3 = st.columns([1.2, 1.2, 1.6])

    with c1:
        with st.container(border=True):
            st.subheader("📌 Infos clés")
            st.write(f"**Statut robot:** {ad.get('status') or '—'}")
            st.write(f"**Statut user:** {ad.get('user_status') or '—'}")
            st.write(f"**Publication:** {fmt_dt(ad.get('publication_date'))}")
            st.write(f"**First seen:** {fmt_dt(ad.get('first_seen_at'))}")
            st.write(f"**Last seen:** {fmt_dt(ad.get('last_seen_at'))}")
            st.write(
                f"**Favori:** {'❤️ Oui' if ad.get('is_favorite') else '—'}")

    with c2:
        with st.container(border=True):
            st.subheader("🧑‍💼 Vendeur")
            rating = ad.get("seller_rating")
            count = ad.get("seller_rating_count")
            st.write(f"**Note:** {rating if rating is not None else '—'}")
            st.write(f"**Avis:** {count if count is not None else '—'}")
            st.caption(
                "ℹ️ Le nom vendeur n'est pas disponible dans les données actuelles.")

    with c3:
        with st.container(border=True):
            st.subheader("🚗 Véhicule")
            st.write(
                f"**Prix:** {ad.get('price') if ad.get('price') is not None else '—'} €")
            st.write(
                f"**CP:** {ad.get('zipcode') or '—'} | **Ville:** {ad.get('location') or '—'}")
            st.write(
                f"**Année:** {ad.get('year') or '—'} | **Km:** {ad.get('mileage') or '—'}")
            st.write(
                f"**Carburant:** {ad.get('fuel') or '—'} | **Boîte:** {ad.get('gearbox') or '—'}")
            st.write(
                f"**Puissance:** {ad.get('horsepower') or '—'} | **Finition:** {ad.get('finition') or '—'}")

    # -------------------------------------------------------------------------
    # 6) ANALYSE PRIX (avant évaluation)
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("📈 Analyse Prix")

    fig = build_price_history_chart(ad)
    if fig is None:
        st.info("Pas d'historique de prix disponible pour cette annonce.")
    else:
        st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------------
    # 7) ÉVALUATION (scores + K + points IA)
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("🧮 Évaluation & Détail du scoring")

    scores = ad.get("scores") or {}
    base = scores.get("base", {}) if isinstance(scores, dict) else {}
    sanity = scores.get("sanity_checks", {}) if isinstance(
        scores, dict) else {}
    financial = scores.get("financial", {}) if isinstance(scores, dict) else {}

    col_s1, col_s2 = st.columns([1.2, 1.8])

    with col_s1:
        with st.container(border=True):
            st.markdown("### Score (piliers)")
            deal = base.get("deal", 50)
            conf = base.get("conf", 50)
            prod = base.get("prod", 0)
            total = scores.get("total", None)

            st.metric("Score Final", f"{total:.1f}" if isinstance(
                total, (int, float)) else "—")

            st.write("**Deal**")
            st.progress(int(deal), text=f"{int(deal)}/100")

            st.write("**Confiance**")
            st.progress(int(conf), text=f"{int(conf)}/100")

            st.write("**Produit**")
            st.progress(int(prod), text=f"{int(prod)}/100")

    with col_s2:
        with st.container(border=True):
            st.markdown("### Coefficients K + explications")
            k_meca = sanity.get("k_meca", 1.0)
            k_modif = sanity.get("k_modif", 1.0)
            k_arnaque = sanity.get("k_arnaque", 1.0)

            st.write("**K Mécanique**")
            severity_progress("Pénalité", 1.0 - float(k_meca or 1.0))

            st.write("**K Modifications**")
            severity_progress("Pénalité", 1.0 - float(k_modif or 1.0))

            st.write("**K Arnaque**")
            severity_progress("Pénalité", 1.0 - float(k_arnaque or 1.0))

            ai = ad.get("ai_analysis") or {}
            risques = ai.get("risques_meca", []) if isinstance(
                ai, dict) else []
            modifs = ai.get("modifications", []) if isinstance(
                ai, dict) else []
            scams = ai.get("indices_arnaque", []) if isinstance(
                ai, dict) else []

            render_ai_list("🛠️ Risques mécaniques", risques)
            render_ai_list("🔧 Modifications", modifs)
            render_ai_list("🕵️ Indices d’arnaque", scams)

    # -------------------------------------------------------------------------
    # 8) ESTIMATION ÉCONOMIQUE
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("💰 Estimation économique")

    posted = financial.get("posted_price", ad.get("price"))
    virtual = financial.get("virtual_price", ad.get("price"))
    repair = financial.get("repair_cost", 0)
    market = financial.get("market_estimation", None)

    col_e1, col_e2, col_e3, col_e4 = st.columns(4)
    col_e1.metric("Prix annonce", f"{posted} €" if posted is not None else "—")
    col_e2.metric("Coût réparations",
                  f"{repair} €" if repair is not None else "—")
    col_e3.metric("Prix virtuel",
                  f"{virtual} €" if virtual is not None else "—")
    col_e4.metric("Cote marché", f"{market} €" if market is not None else "—")

    gain = None
    if isinstance(market, (int, float)) and market > 0 and isinstance(virtual, (int, float)):
        gain = int(market - virtual)

    st.metric("Gain / Perte", f"{gain:+d} €" if gain is not None else "—")

    # -------------------------------------------------------------------------
    # 9) ACTIONS
    # -------------------------------------------------------------------------
    st.divider()
    st.subheader("⚙️ Actions")

    db = DatabaseClient()

    a1, a2, a3 = st.columns([1, 1, 2])

    with a1:
        fav_label = "❤️ Unfav" if ad.get("is_favorite") else "🤍 Favori"
        if st.button(fav_label, use_container_width=True):
            db.set_favorite(ad_id, not bool(ad.get("is_favorite")))
            load_ad_details_data.clear()
            st.rerun()

    with a2:
        if st.button("🗑️ Exclure (TRASH)", use_container_width=True):
            db.set_user_status(ad_id, "TRASH")
            load_ad_details_data.clear()
            st.rerun()

    with a3:
        if st.button("🔄 Re-scan (alive + IA + scoring)", use_container_width=True):
            with st.spinner("Re-scan en cours…"):
                res = rescan_ad(ad_id)

            if not res.get("ok"):
                st.error(f"Re-scan impossible: {res.get('reason')}")
            else:
                if res.get("reason") == "MARKED_SOLD":
                    st.warning("Annonce non accessible → marquée SOLD.")
                else:
                    st.success("Annonce mise à jour ✅")

            load_ad_details_data.clear()
            st.rerun()


main()
