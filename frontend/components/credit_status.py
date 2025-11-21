import streamlit as st


def render_credit_status(credit_data: dict):
    """Render the credit status section.

    Args:
        credit_data: Dictionary containing credit status information
    """
    if not credit_data:
        st.error("Données de crédit non disponibles")
        return

    status_color = "green" if credit_data.get("status") == "À jour" else "red"

    st.markdown(
        f"""
    <div class="creances-section">
        <h3 class="section-title">État des créances</h3>
        <p style="color: #000000 !important;">Statut : <span style="color: {status_color}; font-weight: bold;">{credit_data.get("status", "N/A")}</span></p>
        <p style="color: #000000 !important;">Montant des créances : {credit_data.get("amount", "N/A")}</p>
        <p style="color: #000000 !important;">Ancienneté Moyenne : {credit_data.get("average_age", "N/A")}j</p>
        <p style="color: #000000 !important;">Niveau de Risque client : {credit_data.get("risk_level", "N/A")}</p>
    </div>
    """,
        unsafe_allow_html=True,
    )
