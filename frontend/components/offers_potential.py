import streamlit as st


def render_offers_potential(offers_data: dict, potential_data: dict):
    """Render the offers and potential sections.

    Args:
        offers_data: Dictionary containing current offers information
        potential_data: Dictionary containing potential opportunities
    """
    if not offers_data or not potential_data:
        st.error("Données d'offres ou de potentiel non disponibles")
        return

    o_col1, o_col2 = st.columns(2, gap="medium")

    with o_col1:
        internet_offers_html = ""
        if offers_data.get("internet"):
            for offer in offers_data["internet"]:
                internet_offers_html += f"<li>{offer}</li>"

        voice_offers_html = ""
        if offers_data.get("voice"):
            for offer in offers_data["voice"]:
                voice_offers_html += f"<li>{offer}</li>"

        st.markdown(
            f"""
        <div class="white-section" style="margin-bottom: 50px;">
            <h3 class="section-title">Offres et Services</h3>
            <div style="margin-top: 20px;">
                <p class="custom-subheader">INTERNET</p>
                <ul style="color: #000000 !important; margin-left: 20px; margin-bottom: 25px;">
                    {internet_offers_html}
                </ul>
                <p class="custom-subheader">VOIX</p>
                <ul style="color: #000000 !important; margin-left: 20px;">
                    {voice_offers_html}
                </ul>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with o_col2:
        ongoing_acquisitions_html = ""
        if potential_data.get("ongoing_acquisitions"):
            for item in potential_data["ongoing_acquisitions"]:
                ongoing_acquisitions_html += (
                    f"<p style='color: #155724 !important; margin: 0;'>- {item}</p>"
                )

        upsell_cross_sell_html = ""
        if potential_data.get("upsell_cross_sell"):
            for item in potential_data["upsell_cross_sell"]:
                upsell_cross_sell_html += (
                    f"<p style='color: #155724 !important; margin: 0;'>- {item}</p>"
                )

        st.markdown(
            f"""
        <div class="white-section" style="margin-bottom: 50px;">
            <h3 class="section-title">Potentiel</h3>
            <div style="margin-top: 20px;">
                <p style="color: #000000 !important; font-weight: bold;">Acquisition en cours :</p>
                <div
                    style="
                        background-color: #d4edda;
                        border: 1px solid #c3e6cb;
                        border-radius: 4px;
                        padding: 10px;
                        margin-bottom: 15px;
                    "
                >
                    {ongoing_acquisitions_html}
                </div>
                <p style="color: #000000 !important; font-weight: bold;">Upsell / Cross-sell :</p>
                <div
                    style="
                        background-color: #d4edda;
                        border: 1px solid #c3e6cb;
                        border-radius: 4px;
                        padding: 10px;
                    "
                >
                    {upsell_cross_sell_html}
                </div>
            </div>
        </div>
        """,
            unsafe_allow_html=True,
        )
