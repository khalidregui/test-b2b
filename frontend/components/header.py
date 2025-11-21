import streamlit as st


def render_header():
    """Render the application header with Orange logo and title."""
    st.markdown(
        """
    <div class="header-black" style="background-color: #000000; color: #FFFFFF; padding: 20px 40px;">
        <div style="display: flex; align-items: center; gap: 20px;">
            <img
                src="frontend/static/logo.svg"
                width="80"
                style="background: white; padding: 10px; border-radius: 4px;"
            >
            <h1 style="margin: 0; font-size: 36px; font-weight: 700;">Fiche Client B2B</h1>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
