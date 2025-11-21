import pandas as pd
import plotly.express as px
import streamlit as st


def render_revenue_chart(revenue_data: pd.DataFrame):
    """Render the revenue chart with interactive filters.

    Args:
        revenue_data: DataFrame containing revenue data by product and date
    """
    if revenue_data is None or revenue_data.empty:
        st.error("Données de revenus non disponibles")
        return

    st.markdown(
        """
    <div class="white-section" style="text-align: left; margin-bottom: 15px;">
        <h3 class="section-title">Revenus Générés</h3>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """<div
        style="
            background-color: #FFFFFF;
            padding: 10px;
            border-radius: 8px;
            margin-bottom: 10px;
            border: 1px solid #E6E6E6;
        "
    >""",
        unsafe_allow_html=True,
    )

    label_col1, label_col2, label_col3 = st.columns(3)

    with label_col1:
        st.markdown(
            """<div style="text-align: center; margin-bottom: 5px;">
        <span
            style="
                color: #FF7900;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            "
            >Granularité Temporelle</span
        >
    </div>""",
            unsafe_allow_html=True,
        )

    with label_col2:
        st.markdown(
            """<div style="text-align: center; margin-bottom: 5px;">
        <span
            style="
                color: #FF7900;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            "
            >Segmentation Produit</span
        >
    </div>""",
            unsafe_allow_html=True,
        )

    with label_col3:
        st.markdown(
            """<div style="text-align: center; margin-bottom: 5px;">
        <span
            style="
                color: #FF7900;
                font-size: 10px;
                font-weight: bold;
                text-transform: uppercase;
                letter-spacing: 1px;
            "
            >Interval Temporelle</span
        >
    </div>""",
            unsafe_allow_html=True,
        )

    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        st.markdown('<div style="height: 28px;"></div>', unsafe_allow_html=True)
        periode = st.selectbox(
            "Période",
            options=["Mensuel", "Hebdomadaire", "Journalier"],
            index=0,
            key="periode_filter",
            label_visibility="collapsed",
        )

    with filter_col2:
        produits_disponibles = list(revenue_data["Produit"].unique())
        produits_options = ["Tout", *produits_disponibles]

        produits_selectionnes = st.multiselect(
            "Produits",
            options=produits_options,
            default=["Tout"],
            key="produit_filter",
        )

        if "Tout" in produits_selectionnes:
            produits_finaux = produits_disponibles
        else:
            produits_finaux = [p for p in produits_selectionnes if p != "Tout"]

    with filter_col3:
        dates_disponibles = sorted(list(revenue_data["Date"].dt.date.unique()))
        if len(dates_disponibles) > 1:
            fenetre_debut, fenetre_fin = st.select_slider(
                "Période",
                options=dates_disponibles,
                value=(dates_disponibles[0], dates_disponibles[-1]),
                format_func=lambda x: x.strftime("%d/%m/%Y"),
                key="fenetre_filter",
            )
        else:
            fenetre_debut = fenetre_fin = dates_disponibles[0] if dates_disponibles else None

    st.markdown("</div>", unsafe_allow_html=True)

    df_filtered = revenue_data.copy()

    if produits_finaux:
        df_filtered = df_filtered[df_filtered["Produit"].isin(produits_finaux)]

    if fenetre_debut and fenetre_fin:
        df_filtered = df_filtered[
            (df_filtered["Date"].dt.date >= fenetre_debut)
            & (df_filtered["Date"].dt.date <= fenetre_fin)
        ]

    if periode == "Mensuel":
        df_agg = df_filtered.groupby(["Mois", "Produit"])["Revenu"].sum().reset_index()
        x_col = "Mois"
    elif periode == "Hebdomadaire":
        df_agg = df_filtered.groupby(["Semaine", "Produit"])["Revenu"].sum().reset_index()
        x_col = "Semaine"
    else:
        df_agg = df_filtered.groupby(["Date", "Produit"])["Revenu"].sum().reset_index()
        x_col = "Date"

    st.markdown(
        """<div
        style="
            background-color: #FFFFFF;
            padding: 15px;
            border-radius: 8px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        "
    >""",
        unsafe_allow_html=True,
    )

    if len(produits_finaux) > 1:
        fig = px.bar(
            df_agg,
            x=x_col,
            y="Revenu",
            color="Produit",
            color_discrete_sequence=[
                "#FF7900",
                "#FF9933",
                "#FFAB4D",
                "#FFBD66",
                "#FFCF80",
                "#FFE199",
            ],
        )
    else:
        fig = px.bar(df_agg, x=x_col, y="Revenu", color_discrete_sequence=["#FF7900"])

    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="white",
        font=dict(color="#000000", family="Arial, sans-serif"),
        showlegend=True if len(produits_finaux) > 1 else False,
        xaxis=dict(
            showgrid=False,
            showline=True,
            linecolor="#E6E6E6",
            tickfont=dict(color="#000000", size=9, family="Arial, sans-serif"),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#E6E6E6",
            showline=False,
            tickfont=dict(color="#000000", size=9, family="Arial, sans-serif"),
            tickformat=".2s",
        ),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color="#000000", size=9, family="Arial, sans-serif"),
            title=dict(
                text="Produit", font=dict(color="#000000", size=10, family="Arial, sans-serif")
            ),
        )
        if len(produits_finaux) > 1
        else {},
        height=400,
        margin=dict(l=40, r=40, t=40, b=40),
    )

    fig.update_xaxes(
        title_font=dict(color="#000000", size=10),
        tickfont=dict(color="#000000", size=9),
        linecolor="#000000",
    )

    fig.update_yaxes(
        title_font=dict(color="#000000", size=10),
        tickfont=dict(color="#000000", size=9),
        gridcolor="#E6E6E6",
    )

    if len(produits_finaux) == 1:
        fig.update_traces(
            texttemplate="%{y:.2s}",
            textposition="outside",
            textfont=dict(color="#000000", size=8, family="Arial, sans-serif"),
        )
    else:
        fig.update_traces(
            texttemplate="%{y:.2s}",
            textposition="inside",
            textfont=dict(color="#000000", size=8, family="Arial, sans-serif"),
        )

    st.plotly_chart(fig, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
