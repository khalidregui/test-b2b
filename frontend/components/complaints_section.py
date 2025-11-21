import streamlit as st


def render_complaints_section(complaints_data: dict):
    """Render the complaints section.

    Args:
        complaints_data: Dictionary containing complaint information
    """
    if not complaints_data:
        st.error("Données de plaintes non disponibles")
        return

    st.markdown(
        f"""
    <div class="white-section" style="height: 700px; display: flex; flex-direction: column;">
        <h3 class="section-title">Plaintes enregistrées</h3>
        <div
            style="
                flex: 1;
                display: flex;
                flex-direction: column;
                justify-content: flex-start;
                margin-top: 15px;
            "
        >
            <div>
                <p style="color: #FF7900; font-weight: bold; margin-bottom: 10px;">• {complaints_data.get("title", "N/A")}</p>
                <p style="color: #000000; margin-bottom: 15px; line-height: 1.6;">
                    {complaints_data.get("description", "N/A")}
                </p>
                <p style="color: #000000; margin-bottom: 0; line-height: 1.6;">
                    {complaints_data.get("resolution", "N/A")}
                </p>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
