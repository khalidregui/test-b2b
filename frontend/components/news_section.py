import streamlit as st


def render_news_section(news_data: dict):
    """Render the news and updates section.

    Args:
        news_data: Dictionary containing news and sector information
    """
    if not news_data:
        st.error("Données d'actualités non disponibles")
        return

    sector_context_html = ""
    if news_data.get("sector_context"):
        for item in news_data["sector_context"]:
            sector_context_html += f"<p>- <strong>{item}</strong></p>"

    cybersecurity_html = ""
    if news_data.get("cybersecurity_focus"):
        for item in news_data["cybersecurity_focus"]:
            if item == "Tendance régionale (Interpol 2025) :":
                cybersecurity_html += f"<p><strong>{item}</strong></p>"
            else:
                cybersecurity_html += f"<p>- {item}</p>"

    company_news_html = ""
    if news_data.get("company_news"):
        for item in news_data["company_news"]:
            company_news_html += f"<p>- {item}</p>"

    st.markdown(
        f"""
    <div class="dark-section">
        <h3>Actualités</h3>
        <div style="display: flex; gap: 30px;">
            <div class="dark-column" style="flex: 1;">
                <p><strong style="color: #FF7900; font-size: 16px;">Contexte Sectoriel</strong></p>
                {sector_context_html}
                <p><strong style="color: #FF7900; font-size: 16px;">Focus Cybersécurité</strong></p>
                {cybersecurity_html}
            </div>
            <div class="dark-column" style="flex: 1;">
                <p><strong style="color: #FF7900; font-size: 16px;">Actualités Entreprise (Q1 2025)</strong></p>
                {company_news_html}
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
