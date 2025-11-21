import streamlit as st
from services.api_client import get_api_client


def render_search_bar():
    """Render the client search bar interface with real-time autocomplete using only autocomplete route."""
    # Initialize API client
    api_client = get_api_client()

    # Label centered
    st.markdown(
        """
        <div style="text-align: center; margin: 20px 0 15px 0;">
            <label style="color: #000000; font-size: 16px; font-weight: 600;">Recherche Client</label>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Create columns for perfect centering
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        # Initialize session state
        if "show_suggestions" not in st.session_state:
            st.session_state.show_suggestions = False
        if "suggestions_list" not in st.session_state:
            st.session_state.suggestions_list = []
        if "search_results" not in st.session_state:
            st.session_state.search_results = []
        if "client_selected" not in st.session_state:
            st.session_state.client_selected = False

        # Create form for search functionality
        with st.form(key="search_form", clear_on_submit=False):
            # Create two sub-columns for input and button
            search_col1, search_col2 = st.columns([3, 1.3])

            with search_col1:
                # Text input for search
                search_query = st.text_input(
                    label="search_query",
                    value=st.session_state.get("last_search_query", ""),
                    placeholder="Tapez pour rechercher (3, 3.487, BIZART...)",
                    key="search_query_input",
                    label_visibility="collapsed",
                    help="Tapez quelques lettres pour voir les suggestions",
                )

            with search_col2:
                search_clicked = st.form_submit_button("Chercher", use_container_width=True)

        # Handle manual search button click
        if search_clicked and search_query.strip():
            # Store last search query
            st.session_state["last_search_query"] = search_query.strip()
            st.session_state.show_suggestions = False
            st.session_state.client_selected = False

            if api_client.health_check():
                # CORRECTION: Logique de recherche améliorée
                search_results = []
                search_query_clean = search_query.strip()

                # Essayer d'abord par identifiant (si ça ressemble à un ID)
                if search_query_clean.replace(".", "").isdigit():
                    search_results = api_client.search_clients(identifier=search_query_clean)

                # Si pas de résultats par identifiant OU si ce n'est pas un ID, essayer par nom
                if not search_results:
                    search_results = api_client.search_clients(company_name=search_query_clean)

                # Store search results in session state
                st.session_state.search_results = search_results

            else:
                st.error("❌ Backend non disponible")
                st.session_state.search_results = []

        # REAL-TIME AUTOCOMPLETE: Outside the form for instant updates
        if (
            len(search_query) >= 2
            and search_query != st.session_state.get("last_processed_query", "")
            and not st.session_state.search_results
            and not st.session_state.client_selected
        ):
            st.session_state.last_processed_query = search_query

            if api_client.health_check():
                # CORRECTION: Ajouter le paramètre country
                autocomplete_results = api_client.autocomplete_clients(search_query, "BF")

                # Transform to suggestions list
                all_suggestions = []
                for suggestion in autocomplete_results:
                    company_name = suggestion.get("company_name", "")
                    client_id = suggestion.get("identifier", "")
                    if company_name and client_id:
                        all_suggestions.append(
                            {
                                "text": f"{company_name} (ID: {client_id})",
                                "company_name": company_name,
                                "client_id": client_id,
                            }
                        )

                st.session_state.suggestions_list = all_suggestions[:5]  # Limit to 5
                st.session_state.show_suggestions = len(all_suggestions) > 0

            else:
                st.session_state.suggestions_list = []
                st.session_state.show_suggestions = False
        elif len(search_query) < 2:
            st.session_state.show_suggestions = False
            st.session_state.suggestions_list = []
            st.session_state.search_results = []
            st.session_state.client_selected = False

        # Show search results if available (from manual search)
        if st.session_state.search_results and not st.session_state.client_selected:
            st.markdown(
                """
                <div style="margin-top: 15px; margin-bottom: 10px;">
                    <div style="background: linear-gradient(135deg, #FF7900, #E66A00); color: white; padding: 8px 15px; border-radius: 8px 8px 0 0; font-weight: 600; font-size: 14px;">
                        Résultats de recherche
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Create buttons for each search result
            for i, client in enumerate(st.session_state.search_results):
                client_name = client.get("company_name", "N/A")
                client_id = client.get("identifier", client.get("client_id", "N/A"))

                # Use a unique key that includes the client_id
                button_key = f"search_result_{client_id}_{i}"

                if st.button(
                    f"{client_name} (ID: {client_id})",
                    key=button_key,
                    help="Cliquez pour sélectionner ce client",
                    use_container_width=True,
                ):
                    # Set the selected client
                    st.session_state["searched_client_id"] = str(client_id)
                    st.session_state["last_search_query"] = client_name
                    st.session_state.search_results = []
                    st.session_state.show_suggestions = False
                    st.session_state.client_selected = True
                    st.rerun()  # Force page refresh

        # Show suggestions if available (from autocomplete) and no search results
        elif (
            st.session_state.show_suggestions
            and st.session_state.suggestions_list
            and not st.session_state.client_selected
        ):
            st.markdown(
                """
                <div style="margin-top: 15px; margin-bottom: 10px;">
                    <div style="background: linear-gradient(135deg, #FF7900, #E66A00); color: white; padding: 8px 15px; border-radius: 8px 8px 0 0; font-weight: 600; font-size: 14px;">
                        Clients disponibles
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Create buttons for each suggestion
            for i, suggestion in enumerate(st.session_state.suggestions_list):
                suggestion_text = suggestion["text"]
                client_id = suggestion["client_id"]
                company_name = suggestion["company_name"]

                # Use a unique key that includes the client_id
                button_key = f"suggestion_{client_id}_{i}"

                if st.button(
                    suggestion_text,
                    key=button_key,
                    help="Cliquez pour sélectionner ce client",
                    use_container_width=True,
                ):
                    # Set the selected client
                    st.session_state["searched_client_id"] = str(client_id)
                    st.session_state["last_search_query"] = company_name
                    st.session_state.show_suggestions = False
                    st.session_state.suggestions_list = []
                    st.session_state.client_selected = True
                    st.rerun()  # Force page refresh

        # Show message if no results found
        elif (
            search_clicked
            and search_query.strip()
            and not st.session_state.search_results
            and not st.session_state.client_selected
        ):
            st.info(f"Aucun client trouvé pour '{search_query.strip()}'")

    # Display search help with improved styling
    with col2:
        st.markdown(
            """
            <div style="
                text-align: center;
                margin: 15px 0 10px 0;
                padding: 8px 15px;
                background: linear-gradient(135deg, #FFF8F0, #FFEBDB);
                border: 1px solid #FFD4A8;
                border-radius: 8px;
                font-size: 13px;
                color: #8B4513;
                box-shadow: 0 2px 4px rgba(255, 121, 0, 0.1);
            ">
                <span style="color: #FF7900; font-weight: 600;">💡</span>
                Tapez au moins 2 caractères pour voir les suggestions
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Enhanced CSS for better button styling
    st.markdown(
        """
        <style>
        /* BACKUP CSS - Ensure styles persist after interactions */
        button[kind="formSubmit"], .stFormSubmitButton button {
            background-color: #FF7900 !important;
            color: #000000 !important;
        }

        /* Enhanced styling for suggestion/result buttons */
        .stButton > button {
            width: 100% !important;
            text-align: left !important;
            padding: 12px 15px !important;
            margin: 3px 0 !important;
            border-radius: 8px !important;
            border: 1px solid #E6E6E6 !important;
            background-color: #FFFFFF !important;
            color: #000000 !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }

        .stButton > button:hover {
            background-color: #F8F9FA !important;
            border-color: #FF7900 !important;
            box-shadow: 0 4px 8px rgba(255, 121, 0, 0.15) !important;
            transform: translateY(-1px) !important;
        }

        .stButton > button:active {
            transform: translateY(0) !important;
            box-shadow: 0 2px 4px rgba(255, 121, 0, 0.2) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
