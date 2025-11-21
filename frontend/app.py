from pathlib import Path

import streamlit as st
from components import (
    contact_section,
    header,
    identity_card,
    search_bar,
    credit_status,
    partnership_description,
    revenue_chart,
    complaints_section,
    news_section,
    offers_potential,
)
from models.company_sheet import CompanySheet
from services.api_client import get_api_client


def load_css():
    """Load CSS styles from the static directory."""
    script_dir = Path(__file__).parent
    css_path = script_dir / "static" / "styles.css"

    with open(css_path) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)  # Cache pendant 1 heure pour éviter les re-appels backend/LLM
def load_company_data_cached(company_id: str):
    """Charge les données de l'entreprise avec mise en cache.
    
    Cette fonction sera appelée UNE SEULE FOIS même si st.rerun() est déclenché
    par le composant partnership_description. Les appels LLM/backend ne se feront
    qu'au premier chargement.
    """
    print(f"\n🔄 [BACKEND] Chargement des données pour {company_id}")
    print(f"💰 [BACKEND] Appel LLM/API en cours - Ceci ne devrait apparaître qu'UNE SEULE FOIS")
    
    # Chargement des données depuis le backend avec appels LLM
    sheet = CompanySheet(company_id)
    sheet.load_all_data()  # Appels backend + LLM coûteux
    
    print(f"✅ [BACKEND] Données chargées et mises en cache pour {company_id}")
    
    return {
        "identity_data": sheet.identity_data,
        "contact_data": sheet.contact_data,
        "credit_data": sheet.credit_data,
        "partnership_data": sheet.partnership_data,
        "revenue_data": sheet.revenue_data,
        "complaints_data": sheet.complaints_data,
        "news_data": sheet.news_data,
        "offers_data": sheet.offers_data,
        "potential_data": sheet.potential_data
    }


def main():
    """Main application function avec cache intelligent."""
    st.set_page_config(page_title="Fiche Client B2B", page_icon="🟠", layout="wide")

    load_css()

    # CSS pour créer un spinner orange centré qui ne perturbe pas la mise en page
    st.markdown("""
    <style>
    /* Container du spinner - centré et positionné */
    .stSpinner {
        position: relative !important;
        text-align: center !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
        margin: 20px auto !important;
        padding: 0 !important;
    }

    /* Spinner orange avec segments - taille et position fixes */
    .stSpinner > div {
        width: 32px !important;
        height: 32px !important;
        border: none !important;
        border-radius: 50% !important;
        background: conic-gradient(
            from 0deg,
            #FF7900 0deg 60deg,
            #E66A00 60deg 120deg,
            #FF8C1A 120deg 180deg,
            #FFB366 180deg 240deg,
            #FFE5CC 240deg 300deg,
            #FFFFFF 300deg 360deg
        ) !important;
        animation: orange-segments-spin 1s linear infinite !important;
        margin: 0 auto !important;
        position: relative !important;
        flex-shrink: 0 !important;
    }

    /* Animation de rotation fluide */
    @keyframes orange-segments-spin {
        0% { 
            transform: rotate(0deg);
        }
        100% { 
            transform: rotate(360deg);
        }
    }

    /* Message du spinner centré et stylé Orange */
    .stSpinner + div,
    .stSpinner ~ div {
        color: #FF7900 !important;
        font-weight: 600 !important;
        font-size: 14px !important;
        margin: 10px auto 0 auto !important;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
        text-align: center !important;
        max-width: 300px !important;
    }

    /* Assurer que le spinner ne fait pas déborder le container */
    .stSpinner {
        overflow: visible !important;
        box-sizing: border-box !important;
    }

    /* Centrage global du spinner dans son conteneur parent */
    [data-testid="stSpinner"] {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # FORCE CSS FOR SEARCH BAR BEFORE RENDERING IT
    st.markdown(
        """
        <style>
        /* FORCE ORANGE BUTTON - APPLIED BEFORE SEARCH BAR RENDER */
        button[kind="formSubmit"],
        .stFormSubmitButton button,
        [data-testid="stForm"] button[kind="formSubmit"],
        form button[kind="formSubmit"],
        button[type="submit"] {
            height: 40px !important;
            background-color: #FF7900 !important;
            background: #FF7900 !important;
            color: #000000 !important;
            border: 1px solid #FF7900 !important;
            border-radius: 4px !important;
            font-weight: 600 !important;
            font-size: 16px !important;
            padding: 8px 20px !important;
            width: 100% !important;
            box-sizing: border-box !important;
        }

        button[kind="formSubmit"]:hover,
        .stFormSubmitButton button:hover {
            background-color: #E66A00 !important;
            background: #E66A00 !important;
        }

        button[kind="formSubmit"]:focus,
        button[kind="formSubmit"]:active,
        .stFormSubmitButton button:focus,
        .stFormSubmitButton button:active {
            background-color: #FF7900 !important;
            background: #FF7900 !important;
            color: #000000 !important;
            border: 1px solid #FF7900 !important;
        }

        /* FORCE WHITE INPUTS */
        input,
        input[type="text"],
        .stTextInput input,
        .stTextInput > div > div > input,
        [data-testid="stTextInput"] input {
            height: 40px !important;
            border: 1px solid #CCCCCC !important;
            border-radius: 4px !important;
            padding: 8px 12px !important;
            font-size: 16px !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
            box-sizing: border-box !important;
        }

        /* SUGGESTION BUTTONS - LIGHT GRAY */
        button[kind="secondary"],
        .stButton button:not([kind="formSubmit"]) {
            background-color: #FFFFFF !important;
            color: #000000 !important;
            border: 1px solid #E6E6E6 !important;
            border-radius: 8px !important;
            padding: 12px 15px !important;
            text-align: left !important;
            width: 100% !important;
            margin: 2px 0 !important;
            font-size: 14px !important;
            font-weight: 500 !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
            transition: all 0.2s ease !important;
        }

        button[kind="secondary"]:hover,
        .stButton button:not([kind="formSubmit"]):hover {
            background-color: #F8F9FA !important;
            border-color: #FF7900 !important;
            box-shadow: 0 4px 8px rgba(255, 121, 0, 0.15) !important;
            transform: translateY(-1px) !important;
        }

        /* FORM ALIGNMENT */
        [data-testid="stForm"] {
            border: none !important;
            padding: 0 !important;
        }

        [data-testid="stForm"] [data-testid="column"] {
            gap: 0.7rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # CSS supplémentaire pour harmoniser les messages avec le thème Orange
    st.markdown(
        """
        <style>
        /* Styles pour harmoniser les messages avec le thème Orange */
        .stAlert > div {
            border-radius: 8px !important;
            border-left: 4px solid #FF7900 !important;
            box-shadow: 0 3px 6px rgba(255, 121, 0, 0.15) !important;
        }

        /* Style pour les messages d'information */
        .stInfo > div {
            background: linear-gradient(135deg, #E3F2FD, #BBDEFB) !important;
            border-color: #2196F3 !important;
            color: #1565C0 !important;
        }

        /* Style pour les messages d'erreur */
        .stError > div {
            background: linear-gradient(135deg, #FFEBEE, #FFCDD2) !important;
            border-color: #F44336 !important;
            color: #C62828 !important;
        }

        /* Amélioration générale des conteneurs */
        .main .block-container {
            padding-top: 2rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    header.render_header()

    search_bar.render_search_bar()

    # Get company ID from session state - only load if a search was performed
    company_id = st.session_state.get("searched_client_id")

    if company_id:
        try:
            # **CACHE INTELLIGENT** - Les données backend/LLM sont chargées UNE SEULE FOIS
            # Même si st.rerun() est appelé par partnership_description, cette fonction
            # ne fera pas d'appels backend supplémentaires
            with st.spinner(""):
                cached_data = load_company_data_cached(company_id)

            # Vérifier si les données ont été chargées
            if not cached_data.get("identity_data"):
                st.error("❌ Impossible de charger les données du client")
                st.info("💡 Vérifiez que le backend est accessible")
                return

            # Debug simple dans le terminal
            print(f"🔄 [APP] Rendu de l'interface - Données récupérées du cache")

            # Afficher un message de succès stylisé si les données viennent du backend
            api_client = get_api_client()
            if api_client.health_check():
                # Message de succès personnalisé avec style Orange
                st.markdown(
                    f"""
                    <div style="
                        background: linear-gradient(135deg, #E8F5E8, #D4F1D4);
                        border: 1px solid #90EE90;
                        border-left: 4px solid #FF7900;
                        border-radius: 8px;
                        padding: 12px 20px;
                        margin: 15px 0;
                        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
                        display: flex;
                        align-items: center;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    ">
                        <div style="
                            background: #FF7900;
                            color: white;
                            border-radius: 50%;
                            width: 24px;
                            height: 24px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin-right: 12px;
                            font-size: 14px;
                            font-weight: bold;
                        ">✓</div>
                        <div style="
                            color: #2D5A2D;
                            font-weight: 600;
                            font-size: 15px;
                        ">
                            Données chargées (avec cache) pour le client ID: <span style="color: #FF7900; font-weight: 700;">{company_id}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                # Message d'avertissement personnalisé
                st.markdown(
                    """
                    <div style="
                        background: linear-gradient(135deg, #FFF8E1, #FFECB3);
                        border: 1px solid #FFB74D;
                        border-left: 4px solid #FF7900;
                        border-radius: 8px;
                        padding: 12px 20px;
                        margin: 15px 0;
                        box-shadow: 0 3px 6px rgba(0, 0, 0, 0.1);
                        display: flex;
                        align-items: center;
                        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    ">
                        <div style="
                            background: #FF7900;
                            color: white;
                            border-radius: 50%;
                            width: 24px;
                            height: 24px;
                            display: flex;
                            align-items: center;
                            justify-content: center;
                            margin-right: 12px;
                            font-size: 14px;
                            font-weight: bold;
                        ">⚠</div>
                        <div style="
                            color: #8B4513;
                            font-weight: 600;
                            font-size: 15px;
                        ">
                            Backend non disponible - Affichage des données de démonstration (avec cache)
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            # **TOUTES CES SECTIONS UTILISENT LES DONNÉES MISES EN CACHE**
            # Elles ne sont PAS affectées par les st.rerun() du composant partnership
            identity_card.render_identity_card(cached_data["identity_data"])

            col_left, col_right = st.columns([1, 2], gap="medium")

            with col_left:
                contact_section.render_contact_section(cached_data["contact_data"])
                credit_status.render_credit_status(cached_data["credit_data"])

            with col_right:
                # **SEULE CETTE SECTION EST AFFECTÉE PAR st.rerun()**
                # Les données originales viennent du cache, mais les modifications de l'utilisateur
                # (notes personnalisées) sont stockées dans st.session_state
                # Créer un objet CompanySheet pour les appels API (léger, pas de chargement de données)
                company_sheet = CompanySheet(company_id)


                # OU si vous voulez éviter de créer un nouvel objet, vous pouvez directement créer une instance inline :
                partnership_description.render_partnership_description(
                    cached_data["partnership_data"], 
                    CompanySheet(company_id)
                    )

            graph_col, plaintes_col = st.columns([2, 1], gap="medium")

            with graph_col:
                revenue_chart.render_revenue_chart(cached_data["revenue_data"])

            with plaintes_col:
                complaints_section.render_complaints_section(cached_data["complaints_data"])

            news_section.render_news_section(cached_data["news_data"])

            offers_potential.render_offers_potential(cached_data["offers_data"], cached_data["potential_data"])

        except Exception as e:
            st.error(f"❌ Erreur lors du chargement des données : {e!s}")
            st.info("💡 Vérifiez que le backend est accessible")

            # Optionnel : Afficher les détails de l'erreur en mode debug
            if st.checkbox("Afficher les détails de l'erreur (debug)"):
                st.exception(e)
    else:
        # No client selected yet, show empty state
        pass


if __name__ == "__main__":
    main()
    