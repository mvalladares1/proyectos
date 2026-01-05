"""
Módulo compartido para Relación Comercial.
Contiene colores, CSS y funciones de formateo.
"""
import streamlit as st

# --------------------- Colores ---------------------

COLOR_NAVY = "#1b4f72"
COLOR_GREEN = "#27ae60"
COLOR_PINK = "#e74c3c"
COLOR_ORANGE = "#e67e22"
COLOR_PURPLE = "#8e44ad"
COLOR_TEAL = "#16a085"
BG_WHITE = "#ffffff"
GRAY_TEXT = "#000000"

# Colores para gráficos de barras
BAR_COLORS_PROGRAMA = {
    'Granel': '#2ecc71',
    'Retail': '#3498db',
    'Subproducto': '#e74c3c'
}

BAR_COLORS_MANEJO = {
    'Convencional': '#1b4f72',
    'Orgánico': '#27ae60'
}

# Colores para gráficos de pie
PIE_COLORS = {
    'Arándano': '#1a5276',
    'Frambuesa': '#c0392b',
    'Cereza': '#27ae60',
    'Mix': '#e67e22',
    'Mora': '#8e44ad',
    'Frutilla': '#16a085'
}

# Mapeo de meses
MONTH_MAP = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}
MONTH_MAP_REV = {v: k for k, v in MONTH_MAP.items()}
MONTH_MAP_SHORT = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr",
    5: "May", 6: "Jun", 7: "Jul", 8: "Ago",
    9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
}

# --------------------- CSS Global ---------------------

CSS_GLOBAL = f"""
<style>
    /* Main Background */
    .stApp {{
        background-color: {BG_WHITE};
    }}
    
    /* Font styles */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] {{
        font-family: 'Inter', sans-serif;
    }}

    /* Main Title */
    .dashboard-title {{
        border-left: 6px solid {COLOR_NAVY};
        padding-left: 20px;
        font-size: 2.2rem;
        font-weight: 800;
        color: {COLOR_NAVY};
        margin-top: 10px;
        margin-bottom: 5px;
        letter-spacing: -0.02em;
    }}
    .dashboard-subtitle {{
        padding-left: 26px;
        font-size: 1rem;
        color: {COLOR_NAVY};
        margin-bottom: 30px;
        font-weight: 400;
    }}

    /* Section Titles */
    .section-header {{
        font-weight: 800;
        color: {COLOR_NAVY};
        font-size: 1.2rem;
        margin-bottom: 5px;
        letter-spacing: -0.01em;
        text-transform: uppercase;
    }}
    .section-metric {{
        font-style: italic;
        color: {COLOR_PINK};
        font-size: 0.85rem;
        margin-bottom: 20px;
        font-weight: 600;
    }}

    /* Tables */
    table {{
        width: 100%;
        border-collapse: separate; 
        border-spacing: 0;
        border-radius: 12px;
        overflow: hidden;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
        margin-bottom: 20px;
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
    }}
    thead tr {{
        background-color: {COLOR_NAVY};
    }}
    th {{
        color: #ffffff !important;
        text-align: left !important;
        padding: 16px 20px !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        font-size: 0.85rem;
        letter-spacing: 0.05em;
        border-bottom: none !important;
    }}
    td {{
        color: {COLOR_NAVY} !important;
        padding: 14px 20px !important;
        border-bottom: 1px solid #f0f0f0 !important;
        font-size: 0.95rem;
        transition: background-color 0.2s ease;
    }}
    tbody tr:nth-child(even) {{
        background-color: #fcfcfc;
    }}
    tbody tr:hover td {{
        background-color: #f0f7ff !important;
        color: {COLOR_NAVY} !important;
        font-weight: 600;
    }}
    tr:last-child td {{
        background-color: {COLOR_NAVY} !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        border-top: 2px solid #ffffff;
    }}
    tr.row-subtotal td {{
        background-color: #d6eaf8 !important;
        color: {COLOR_NAVY} !important;
        font-weight: 700 !important;
        border-bottom: 2px solid {COLOR_NAVY} !important;
    }}
    tr.row-detail td {{
        padding-left: 30px !important;
        font-weight: 400;
        color: #555555 !important;
    }}
    td:first-child {{
        font-weight: 600;
    }}

    /* Labels */
    label[data-testid="stWidgetLabel"],
    div[data-testid="stWidgetLabel"],
    div[data-testid="stWidgetLabel"] p,
    .stMultiSelect label,
    .stSelectbox label,
    div[data-testid="stMarkdownContainer"] p {{
        color: {COLOR_NAVY} !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
    }}
    
    .stMarkdown p {{
        color: {COLOR_NAVY} !important;
    }}
    
    div[role="radiogroup"] label p {{
        color: {COLOR_NAVY} !important;
        font-weight: 600 !important;
    }}

    /* Multiselect */
    input {{
        color: #ffffff !important;
        caret-color: #ffffff !important;
        background-color: {COLOR_NAVY} !important;
    }}
    ::placeholder {{
        color: rgba(255,255,255,0.7) !important;
        opacity: 1 !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {COLOR_NAVY} !important;
        border: 2px solid {COLOR_NAVY} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="select"] span {{
        color: #ffffff !important;
    }}
    div[data-baseweb="select"] div {{
        color: #ffffff !important;
    }}
    span[data-baseweb="tag"] {{
        background-color: #2980b9 !important;
    }}
    span[data-baseweb="tag"] span {{
        color: #ffffff !important;
    }}
    ul[data-baseweb="menu"] li {{
        color: {COLOR_NAVY} !important;
    }}
    ul[data-baseweb="menu"] {{
        background-color: #ffffff !important;
    }}

    /* Submit Button */
    .stApp [data-testid="stFormSubmitButton"] button {{
        background-color: {COLOR_NAVY} !important;
        color: #ffffff !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.6rem 1rem !important;
        font-weight: 700 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        box-shadow: 0 4px 6px rgba(27, 79, 114, 0.2);
        transition: all 0.3s ease;
    }}
    .stApp [data-testid="stFormSubmitButton"] button:hover {{
        background-color: #154360 !important;
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(27, 79, 114, 0.3);
    }}
    .stApp [data-testid="stFormSubmitButton"] button p {{
        color: #ffffff !important;
    }}

    /* KPI Cards */
    .kpi-container {{
        display: flex;
        justify-content: space-between;
        margin-bottom: 40px;
        gap: 20px;
    }}
    .kpi-card {{
        background: #ffffff;
        border-radius: 12px;
        padding: 24px;
        flex: 1;
        text-align: center;
        border: 1px solid #f0f0f0;
        border-bottom: 4px solid {COLOR_NAVY};
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.025);
        transition: transform 0.2s ease-in-out;
    }}
    .kpi-card:hover {{
        transform: translateY(-5px);
    }}
    .kpi-value {{
        font-size: 2rem;
        font-weight: 800;
        color: {COLOR_NAVY};
        margin-bottom: 8px;
        letter-spacing: -0.03em;
    }}
    .kpi-label {{
        font-size: 0.85rem;
        color: {COLOR_NAVY};
        text-transform: uppercase;
        font-weight: 600;
        letter-spacing: 0.05em;
    }}

    /* Charts Container */
    .chart-container {{
        background: #ffffff;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }}

    /* Download Button */
    .stDownloadButton > button {{
        background-color: #ffffff !important;
        color: {COLOR_PINK} !important;
        border: 2px solid {COLOR_PINK} !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
    }}
    .stDownloadButton > button:hover {{
        background-color: {COLOR_PINK} !important;
        color: #ffffff !important;
    }}

    /* Clean up Layout */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
</style>
"""


# --------------------- Funciones de formateo ---------------------

def fmt_moneda(val, currency="CLP"):
    """Formatea valor como moneda."""
    fmt = ",.2f" if currency == "USD" else ",.0f"
    return f"${val:{fmt}}"

def fmt_kilos(val):
    """Formatea valor como kilos."""
    return f"{val:,.0f} KG"

def fmt_val(val, prefix="", val_format=",.0f"):
    """Formatea valor genérico."""
    if isinstance(val, (int, float)):
        return f"{prefix}{val:{val_format}}"
    return val


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo."""
    if 'applied_filters' not in st.session_state:
        st.session_state.applied_filters = {}
