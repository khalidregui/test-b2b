import streamlit as st


def render_partnership_description(partnership_data: dict, company_sheet=None):
    """Render the partnership description section.

    Args:
        partnership_data: Dictionary containing partnership information
        company_sheet: CompanySheet instance for API calls
    """
    if not partnership_data:
        st.error("Données de partenariat non disponibles")
        return

    # Créer un identifiant unique pour éviter les conflits de clés
    unique_id = hash(str(partnership_data.get('start_date', '')))

    # CSS intégré pour le style professionnel
    st.markdown("""
        <style>
        /* CSS professionnel pour Orange Business Services - Notes de partenariat */
        
        /* Bouton principal "Ajouter une note" */
        button[key*="add_note_partnership"] {
            background: #FF7900 !important;
            border: none !important;
            color: #FFFFFF !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            border-radius: 4px !important;
            padding: 10px 20px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12) !important;
            letter-spacing: 0.02em !important;
        }
        
        button[key*="add_note_partnership"]:hover {
            background: #E66A00 !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15) !important;
            transform: translateY(-1px) !important;
        }
        
        /* Bouton Enregistrer */
        button[key*="save_partnership_note"] {
            background: #FF7900 !important;
            border: none !important;
            color: #FFFFFF !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            border-radius: 4px !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.12) !important;
        }
        
        button[key*="save_partnership_note"]:hover {
            background: #E66A00 !important;
            box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15) !important;
        }
        
        /* Bouton Annuler */
        button[key*="cancel_partnership_note"] {
            background: #FFFFFF !important;
            border: 1px solid #DEE2E6 !important;
            color: #6C757D !important;
            font-weight: 500 !important;
            font-size: 14px !important;
            border-radius: 4px !important;
            padding: 8px 16px !important;
            transition: all 0.2s ease !important;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05) !important;
        }
        
        button[key*="cancel_partnership_note"]:hover {
            background: #F8F9FA !important;
            border-color: #ADB5BD !important;
            color: #495057 !important;
        }
        
        /* Bouton Modifier */
        button[key*="edit_partnership_note"] {
            background: #FFFFFF !important;
            border: 1px solid #FF7900 !important;
            color: #FF7900 !important;
            font-weight: 500 !important;
            font-size: 13px !important;
            border-radius: 4px !important;
            padding: 6px 12px !important;
            transition: all 0.2s ease !important;
        }
        
        button[key*="edit_partnership_note"]:hover {
            background: #FF7900 !important;
            color: #FFFFFF !important;
        }
        
        /* Bouton Supprimer */
        button[key*="delete_partnership_note"] {
            background: #FFFFFF !important;
            border: 1px solid #DC3545 !important;
            color: #DC3545 !important;
            font-weight: 500 !important;
            font-size: 13px !important;
            border-radius: 4px !important;
            padding: 6px 12px !important;
            transition: all 0.2s ease !important;
        }
        
        button[key*="delete_partnership_note"]:hover {
            background: #DC3545 !important;
            color: #FFFFFF !important;
        }
        
        /* Champ de texte */
        .stTextArea textarea {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
            font-size: 14px !important;
            line-height: 1.5 !important;
            border: 1px solid #DEE2E6 !important;
            border-radius: 4px !important;
            padding: 12px !important;
            background: #FFFFFF !important;
            color: #2C3E50 !important;
            transition: border-color 0.2s ease !important;
            resize: vertical !important;
        }
        
        .stTextArea textarea:focus {
            border-color: #FF7900 !important;
            box-shadow: 0 0 0 2px rgba(255, 121, 0, 0.1) !important;
            outline: none !important;
        }
        
        .stTextArea textarea::placeholder {
            color: #6C757D !important;
            font-style: italic !important;
        }
        
        /* Messages d'alerte */
        .stSuccess > div {
            background: linear-gradient(90deg, #D4EDDA, #C3E6CB) !important;
            border-left: 4px solid #28A745 !important;
            color: #155724 !important;
            border-radius: 4px !important;
            padding: 12px 16px !important;
            font-weight: 500 !important;
        }
        
        .stWarning > div {
            background: linear-gradient(90deg, #FFF3CD, #FFEAA7) !important;
            border-left: 4px solid #FFC107 !important;
            color: #856404 !important;
            border-radius: 4px !important;
            padding: 12px 16px !important;
            font-weight: 500 !important;
        }
        
        /* Section description avec hauteur automatique */
        .description-section {
            background-color: #FFFFFF !important;
            border: 1px solid #E6E6E6 !important;
            border-radius: 8px !important;
            padding: 20px !important;
            margin-bottom: 20px !important;
            color: #000000 !important;
            position: relative !important;
            min-height: 200px !important;
            height: auto !important;
            box-sizing: border-box !important;
        }
        </style>
    """, unsafe_allow_html=True)

    # ✅ Utiliser la note sauvegardée ou description vide par défaut
    current_description = st.session_state.get("partnership_saved_note") or partnership_data.get("description", "")
    
    # ✅ Gestion des points vides
    points_html = ""
    if partnership_data.get("points") and partnership_data["points"]:
        for point in partnership_data["points"]:
            if point:  # Vérifier que le point n'est pas vide
                points_html += f'<li style="margin-bottom: 10px;">{point}</li>'

    st.markdown(
        f"""
    <div class="description-section">
        <div class="date-box">
            <div class="date-label">Date de début du<br>partenariat :</div>
            <div class="date-value">{partnership_data.get("start_date", "N/A")}</div>
        </div>
        <h3 class="section-title">Description du partenariat</h3>
        <div class="content-with-date">
            <p style="color: {'#6C757D' if not current_description else '#000000'} !important; margin-bottom: 15px; font-style: {'italic' if not current_description else 'normal'};">
                {current_description if current_description else "Aucune description de partenariat disponible."}
            </p>
            {f'<ul style="color: #000000 !important; margin-left: 20px; padding-left: 0;">{points_html}</ul>' if points_html else ''}</div></div>
    """,
        unsafe_allow_html=True,
    )
    
    # Section boutons d'action avec style professionnel
    st.markdown(
        """
        <div style="
            border-top: 1px solid #E6E6E6;
            margin-top: 20px;
            padding-top: 20px;
        "></div>
        """,
        unsafe_allow_html=True,
    )
    
    # Conteneur pour le bouton principal avec style professionnel Orange
    button_container = st.container()
    with button_container:
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col2:
            # Bouton principal avec clé unique
            add_note = st.button(
                "Ajouter une note",
                key=f"add_note_partnership_{unique_id}",
                help="Ajouter un commentaire ou une observation concernant ce partenariat",
                use_container_width=True
            )
            
            if add_note:
                st.session_state.show_partnership_note_field = True
    
    # Interface de saisie de note avec design professionnel
    if st.session_state.get("show_partnership_note_field", False):
        st.markdown(
            """
            <div style="
                background: linear-gradient(145deg, #FFFFFF, #F8F9FA);
                border: 1px solid #E6E6E6;
                border-left: 4px solid #FF7900;
                border-radius: 8px;
                padding: 24px;
                margin: 24px 0;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
                display: flex;
                align-items: center;
                gap: 12px;
            ">
                <div style="
                    width: 3px;
                    height: 24px;
                    background: #FF7900;
                    border-radius: 2px;
                "></div>
                <h4 style="
                    color: #2C3E50;
                    margin: 0;
                    font-size: 18px;
                    font-weight: 600;
                    letter-spacing: -0.02em;
                ">Description du partenariat :</h4>
                <p style="
                    color: #6C757D;
                    margin: 0;
                    font-size: 14px;
                    line-height: 1.5;
                ">
                    Décrivez les détails du partenariat avec ce client.
                </p></div>
            """,
            unsafe_allow_html=True,
        )
        
        # Champ de texte avec clé unique
        note_content = st.text_area(
            label="Description du partenariat",
            placeholder="Exemple :\n• Partenariat stratégique depuis 2020\n• Focus sur la transformation digitale\n• Services de connectivité et sécurité\n• Accompagnement technique personnalisé",
            height=150,
            key=f"partnership_note_content_{unique_id}",
            label_visibility="collapsed",
            value=st.session_state.get("partnership_saved_note", "")
        )
        
        # Boutons d'action avec design professionnel
        st.markdown("<div style='margin-top: 20px;'></div>", unsafe_allow_html=True)
        
        action_col1, action_col2, action_col3 = st.columns([1, 1, 2])
        
        with action_col1:
            save_note = st.button(
                "Enregistrer",
                key=f"save_partnership_note_{unique_id}",
                use_container_width=True,
                type="primary"
            )
            
        with action_col2:
            cancel_note = st.button(
                "Annuler",
                key=f"cancel_partnership_note_{unique_id}",
                use_container_width=True
            )
        
        # ✅ Logique de sauvegarde avec appel API
        if save_note:
            if note_content.strip():
                # Appel à la nouvelle route API
                if company_sheet:
                    success = company_sheet.update_partnership_description(note_content.strip())
                    if success:
                        st.session_state.partnership_saved_note = success
                        st.session_state.show_partnership_note_field = False
                        st.success("Description enregistrée avec succès")
                        st.rerun()
                    else:
                        st.error("Erreur lors de l'enregistrement")
                else:
                    # Fallback si pas de company_sheet
                    st.session_state.partnership_saved_note = note_content.strip()
                    st.session_state.show_partnership_note_field = False
                    st.success("Description enregistrée localement")
                    st.rerun()
            else:
                st.warning("Veuillez saisir une description avant d'enregistrer")
        
        if cancel_note:
            st.session_state.show_partnership_note_field = False
            st.rerun()
    
    # Affichage séparé de la note avec troncature (pour montrer au client ce qu'il a écrit)
    if st.session_state.get("partnership_saved_note"):
        # Fonction pour tronquer le texte selon vos spécifications
        def truncate_note(text, start_words=5, end_words=2):
            words = text.split()
            if len(words) <= start_words + end_words:
                return text
            
            start_part = " ".join(words[:start_words])
            end_part = " ".join(words[-end_words:])
            return f"{start_part} ... {end_part}"
        
        truncated_note = truncate_note(st.session_state.partnership_saved_note)
        
        # Encart séparé pour montrer ce que le client a écrit
        st.markdown(
            f"""
            <div style="
                background: linear-gradient(145deg, #F8FDF8, #FFFFFF);
                border: 1px solid #D1ECF1;
                border-left: 4px solid #28A745;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
            ">
                <div style="
                    display: flex;
                    align-items: flex-start;
                    gap: 10px;
                    margin-bottom: 12px;
                ">
                    <div style="
                        width: 8px;
                        height: 8px;
                        background: #28A745;
                        border-radius: 50%;
                        margin-top: 8px;
                        flex-shrink: 0;
                    "></div>
                    <div style="flex: 1;">
                        <span style="
                            color: #155724;
                            font-size: 16px;
                            font-weight: 600;
                            margin-right: 8px;
                        ">Description enregistrée :</span>
                        <span style="
                            color: #2C3E50;
                            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                            line-height: 1.6;
                            font-size: 14px;
                        ">{truncated_note}</span></div></div></div>
            """,
            unsafe_allow_html=True,
        )
        
        # Actions sur la note avec design minimaliste
        note_actions_col1, note_actions_col2, note_actions_col3 = st.columns([1, 1, 2])
        
        with note_actions_col1:
            edit_note = st.button(
                "Modifier",
                key=f"edit_partnership_note_{unique_id}",
                use_container_width=True,
                help="Modifier cette description"
            )
            
        with note_actions_col2:
            reset_note = st.button(
                "Réinitialiser",
                key=f"delete_partnership_note_{unique_id}",
                use_container_width=True,
                help="Supprimer la description personnalisée"
            )
        
        if edit_note:
            st.session_state.partnership_note_content = st.session_state.partnership_saved_note
            st.session_state.show_partnership_note_field = True
            st.rerun()
        
        if reset_note:
            del st.session_state.partnership_saved_note
            if "partnership_note_content" in st.session_state:
                del st.session_state.partnership_note_content
            st.success("Description réinitialisée")
            st.rerun()
