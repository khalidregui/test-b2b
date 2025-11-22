import streamlit as st
import base64
from pathlib import Path

logo_path = Path(__file__).parent / "static" / "logo.svg"
# Convertir le logo en base64
with open(logo_path, "rb") as f:
    logo_base64 = base64.b64encode(f.read()).decode("utf-8")


def render_header():
    """Render the application header with Orange logo and title."""
    st.markdown(
        """
    <div class="header-black" style="background-color: #000000; color: #FFFFFF; padding: 20px 40px;">
        <div style="display: flex; align-items: center; gap: 20px;">
            <img
                src="data:image/svg+xml;base64,{logo_base64}"
                width="80"
                style="background: white; padding: 10px; border-radius: 4px;"
            >
            <h1 style="margin: 0; font-size: 36px; font-weight: 700;">Fiche Client B2B</h1>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
