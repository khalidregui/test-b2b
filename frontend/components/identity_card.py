import streamlit as st


def render_identity_card(identity_data: dict):
    """Render the company identity card section.

    Args:
        identity_data: Dictionary containing company identity information
    """
    if not identity_data:
        st.error("Données d'identité non disponibles")
        return

    st.markdown(
        f"""
    <div
        class="carte-identite"
        style="
            background-color: #000000;
            color: #FFFFFF;
            padding: 25px 30px;
            border-radius: 8px;
            margin: 20px 0;
            position: relative;
        "
    >
        <div style="display: flex; justify-content: space-between;
        align-items: flex-start; margin-bottom: 20px;">
            <h2
                style="
                    color: #FF7900;
                    font-size: 24px;
                    font-weight: 600;
                    margin: 0;
                    border-bottom: 2px solid #FF7900;
                    padding-bottom: 10px;
                "
            >
                Carte d'identité
            </h2>
            <div class="social-icons">
                <a
                    href="{identity_data.get("linkedin_url", "#")}"
                    target="_blank"
                    class="social-icon"
                    style="color: #FF7900 !important;"
                >
                    <svg viewBox="0 0 24 24" style="fill: #FF7900 !important;">
                        <path
                            d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"
                        />
                    </svg>
                </a>
                <a
                    href="{identity_data.get("website_url", "#")}"
                    target="_blank"
                    class="social-icon"
                    style="color: #FF7900 !important;"
                >
                    <svg viewBox="0 0 24 24" style="fill: #FF7900 !important;">
                        <path
                            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.94-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"
                        />
                    </svg>
                    Site Web
                </a>
            </div>
        </div>
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 30px;">
            <div>
                <div style="margin-bottom: 15px;">
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">Raison Sociale</div>
                    <div style="color: #FF7900; font-size: 16px; font-weight: 400;">{identity_data.get("company_name", "N/A")}</div>
                </div>
                <div>
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">Dirigeant(s)</div>
                    <div style="color: #FF7900; font-size: 16px; font-weight: 400;">{identity_data.get("ceo", "N/A")}</div>
                </div>
            </div>
            <div>
                <div style="margin-bottom: 15px;">
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">Activité</div>
                    <div style="color: #FF7900; font-size: 16px; font-weight: 400;">{identity_data.get("activity", "N/A")}</div>
                </div>
                <div>
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">Effectifs</div>
                    <div style="color: #FF7900; font-size: 16px; font-weight: 400;">{identity_data.get("employees", "N/A")}</div>
                </div>
            </div>
            <div>
                <div style="margin-bottom: 15px;">
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">Adresse</div>
                    <a
                        href="{identity_data.get("address_link", "#")}"
                        target="_blank"
                        style="
                            color: #FF7900;
                            font-size: 16px;
                            font-weight: 400;
                            text-decoration: underline;
                            cursor: pointer;
                            transition: color 0.3s ease;
                        "
                    >
                        <div style="color: #FF7900; font-size: 16px; font-weight: 400;">
                            {identity_data.get("address", "N/A").replace(",", "<br>")}
                        </div>
                    </a>
                </div>
                <div>
                    <div style="color: #FFFFFF; font-size: 14px; font-weight: 600;">Autres Adresses</div>
                    <div style="color: #FF7900; font-size: 16px; font-weight: 400;">{identity_data.get("other_addresses", "N/A")}</div>
                </div>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
