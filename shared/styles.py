"""
Estilos CSS compartidos para todas las páginas del dashboard.
"""
import streamlit as st

SIDEBAR_ICONS_CSS = """
<style>
    /* Iconos en la sidebar */
    [data-testid="stSidebarNav"] li:nth-child(1) span::before { content: "🏠 "; }
    [data-testid="stSidebarNav"] li:nth-child(2) span::before { content: "📥 "; }
    [data-testid="stSidebarNav"] li:nth-child(3) span::before { content: "🏭 "; }
    [data-testid="stSidebarNav"] li:nth-child(4) span::before { content: "📊 "; }
    [data-testid="stSidebarNav"] li:nth-child(5) span::before { content: "📦 "; }
    [data-testid="stSidebarNav"] li:nth-child(6) span::before { content: "🚢 "; }
    [data-testid="stSidebarNav"] li:nth-child(7) span::before { content: "💰 "; }
    [data-testid="stSidebarNav"] li:nth-child(8) span::before { content: "⚙️ "; }
</style>
"""

def inject_sidebar_icons():
    """Inyecta los iconos CSS en la sidebar. Llamar después de st.set_page_config()"""
    st.markdown(SIDEBAR_ICONS_CSS, unsafe_allow_html=True)
