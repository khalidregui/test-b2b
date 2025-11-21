import streamlit as st


def render_contact_section(contact_data: dict):
    """Render the contact information section.

    Args:
        contact_data: Dictionary containing contact information
    """
    if not contact_data:
        st.error("Données de contact non disponibles")
        return

    st.markdown(
        f"""
    <div class="contact-section">
        <h3 class="section-title">Contact</h3>
        <p style="margin: 8px 0; color: #000000 !important;">Nom complet : <strong>{contact_data.get("name", "N/A")}</strong></p>
        <p style="margin: 8px 0; color: #000000 !important;">Numéro de téléphone : {contact_data.get("phone", "N/A")}</p>
        <p style="margin: 8px 0;"><a href="mailto:Email: {contact_data.get("email", "")}" style="color: #FF7900;">{contact_data.get("email", "N/A")}</a></p>
    </div>
    """,
        unsafe_allow_html=True,
    )
