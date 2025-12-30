"""
Dashboard de Relación Comercial - Rio Futuro
Muestra análisis de ventas por cliente, programa, manejo y especie con datos en tiempo real desde Odoo.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import proteger_modulo, get_credenciales
from backend.services.comercial_service import ComercialService
from backend.utils.pdf_generator import generate_commercial_pdf

# --- Page Config ---
st.set_page_config(
    layout="wide", 
    page_title="Relación Comercial", 
    page_icon="📊",
    initial_sidebar_state="collapsed"
)

if not proteger_modulo("relacion_comercial"):
    st.stop()


# Obtener credenciales del usuario autenticado
username, password = get_credenciales()
if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()

# Instantiate service with user credentials
comercial_service = ComercialService(
    username=username, 
    password=password
)

# --- Exact Colors from Image ---
COLOR_NAVY = "#1b4f72"
COLOR_GREEN = "#27ae60"
COLOR_PINK = "#e74c3c"
COLOR_ORANGE = "#e67e22"
COLOR_PURPLE = "#8e44ad"
COLOR_TEAL = "#16a085"
BG_WHITE = "#ffffff"
GRAY_TEXT = "#000000"

# --- Custom Styling to Match Image ---
st.markdown(f"""
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

    /* Tables: AESTHETIC IMPROVEMENTS */
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
    /* Zebra striping */
    tbody tr:nth-child(even) {{
        background-color: #fcfcfc;
    }}
    /* Hover effect */
    tbody tr:hover td {{
        background-color: #f0f7ff !important;
        color: {COLOR_NAVY} !important;
        font-weight: 600;
    }}
    /* Last Row (Total) Styling */
    tr:last-child td {{
        background-color: {COLOR_NAVY} !important;
        color: #ffffff !important;
        font-weight: 800 !important;
        text-transform: uppercase;
        border-top: 2px solid #ffffff;
    }}
    /* Subtotal rows (Granel, Retail, Subproducto) */
    tr.row-subtotal td {{
        background-color: #d6eaf8 !important;
        color: {COLOR_NAVY} !important;
        font-weight: 700 !important;
        border-bottom: 2px solid {COLOR_NAVY} !important;
    }}
    /* Detail rows (Convencional, Orgánico) - indented */
    tr.row-detail td {{
        padding-left: 30px !important;
        font-weight: 400;
        color: #555555 !important;
    }}
    /* Indentation for readability */
    td:first-child {{
        font-weight: 600;
    }}

/* Global UI Tweaks - Force Labels to Navy */
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

/* --- MULTISELECT & INPUT FIXES --- */
    
    /* 1. Force Input itself - white text on blue background */
    input {{
        color: #ffffff !important;
        caret-color: #ffffff !important;
        background-color: {COLOR_NAVY} !important;
    }}
    
    /* 2. Standard Placeholder - white text */
    ::placeholder {{
        color: rgba(255,255,255,0.7) !important;
        opacity: 1 !important;
    }}
    
    /* 3. Multiselect container styling - BLUE BACKGROUND */
    div[data-baseweb="select"] > div {{
        background-color: {COLOR_NAVY} !important;
        border: 2px solid {COLOR_NAVY} !important;
        border-radius: 8px !important;
    }}
    
    /* 4. Text inside multiselect - WHITE */
    div[data-baseweb="select"] span {{
        color: #ffffff !important;
    }}
    div[data-baseweb="select"] div {{
        color: #ffffff !important;
    }}

    /* 5. Tags (Selected Items) - Lighter blue background */
    span[data-baseweb="tag"] {{
        background-color: #2980b9 !important;
    }}
    span[data-baseweb="tag"] span {{
        color: #ffffff !important;
    }}
    
    /* 6. Dropdown Menu Items (Options) - Keep white background */
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
""", unsafe_allow_html=True)


# --- Filters Section (Always Visible) ---
filter_options = comercial_service.get_filter_values()

with st.form("filtros_form"):
    f1, f2, f3, f4, f5 = st.columns(5)
    with f1: s_anio = st.multiselect("Año", options=filter_options.get('anio', []), placeholder="ELEGIR")
    with f2: 
        MONTH_MAP = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
        MONTH_MAP_REV = {v:k for k,v in MONTH_MAP.items()}
        s_mes_names = st.multiselect("Mes", options=list(MONTH_MAP.values()), placeholder="ELEGIR")
    with f3: s_trim = st.multiselect("Trimestre", options=["Q1", "Q2", "Q3", "Q4"], placeholder="ELEGIR")
    with f4: s_cliente = st.multiselect("Cliente", options=filter_options.get('cliente', []), placeholder="ELEGIR")
    with f5: s_especie = st.multiselect("Tipo Fruta", options=filter_options.get('especie', []), placeholder="ELEGIR")
    
    col_met, col_btn = st.columns([2, 1])
    with col_met: 
        metric_type = st.radio("Ver Datos por:", ["Kilos", "Ventas ($)"], horizontal=True)
        metric_key = 'kilos' if metric_type == "Kilos" else 'monto'
        metric_label = "Kilos" if metric_type == "Kilos" else "CLP"
        val_format = ",.0f" if metric_type == "Kilos" else ",.0f"
        prefix = "" if metric_type == "Kilos" else "$"
    with col_btn: 
        st.write(" ") # Spacer
        submitted = st.form_submit_button("APLICAR FILTROS", use_container_width=True)

if 'applied_filters' not in st.session_state:
    st.session_state.applied_filters = {}

if submitted:
    new_f = {}
    if s_anio: new_f['anio'] = s_anio
    if s_mes_names: new_f['mes'] = [MONTH_MAP_REV[m] for m in s_mes_names]
    if s_trim: new_f['trimestre'] = s_trim
    if s_cliente: new_f['cliente'] = s_cliente
    if s_especie: new_f['especie'] = s_especie
    st.session_state.applied_filters = new_f

# --- Caching PDF generation ---
def get_pdf_bytes(df, kpis, filters):
    return generate_commercial_pdf(df, kpis, filters)

# --- Data Fetching ---
data = comercial_service.get_relacion_comercial_data(filters=st.session_state.applied_filters)
df_raw = pd.DataFrame(data.get('raw_data', []))
kpis_data = data.get('kpis', {
    "total_ventas": 0,
    "total_kilos": 0,
    "total_comprometido": 0,
    "kpi_label": "Total Ventas",
    "has_filters": False
})

# --- Dashboard Header ---
head_col1, head_col2 = st.columns([3, 1])
with head_col1:
    st.markdown('<div class="dashboard-title">Data Relación Comercial</div>', unsafe_allow_html=True)

    with head_col2:
        st.write("") # Spacer
        if not df_raw.empty:
            try:
                # Generar PDF (usando la función con caché)
                pdf_bytes = get_pdf_bytes(df_raw, kpis_data, st.session_state.applied_filters)
                
                st.download_button(
                    label="📄 DESCARGAR INFORME PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_Detallado_{st.session_state.applied_filters.get('cliente', ['General'])[0]}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")

# --- KPI Section (Matching Image) ---
def fmt_kpi(val):
    return f"${val:,.0f}"

def fmt_kilos(val):
    return f"{val:,.0f}"

st.markdown(f"""
<div class="kpi-container">
    <div class="kpi-card">
        <div class="kpi-value">{fmt_kpi(kpis_data['total_ventas'])}</div>
        <div class="kpi-label">{kpis_data.get('kpi_label', 'Total Ventas')} (CLP)</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value">{fmt_kilos(kpis_data['total_kilos'])}</div>
        <div class="kpi-label">{kpis_data.get('kpi_label', 'Total Ventas')} (KG)</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-value">{fmt_kpi(kpis_data['total_comprometido'])}</div>
        <div class="kpi-label">Total Comprometido (CLP)</div>
    </div>
</div>
""", unsafe_allow_html=True)

# --- Layout: Charts Side by Side ---
chart_col1, chart_col2 = st.columns(2)

# Colores mejorados para gráficos
BAR_COLORS_PROGRAMA = {
    'Granel': '#2ecc71',      # Verde brillante
    'Retail': '#3498db',      # Azul brillante
    'Subproducto': '#e74c3c'  # Rojo coral
}
BAR_COLORS_MANEJO = {
    'Convencional': '#1b4f72',  # Navy
    'Orgánico': '#27ae60'       # Verde esmeralda
}

with chart_col1:
    st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">VENTAS POR PROGRAMA ({metric_label})</p>', unsafe_allow_html=True)
    
    if not df_raw.empty:
        has_time_filter = len(st.session_state.applied_filters.get('mes', [])) > 0 or len(st.session_state.applied_filters.get('trimestre', [])) > 0
        x_axis = 'mes_nombre' if has_time_filter else 'anio'
        
        df_m = df_raw[df_raw['tipo'].isin(['Factura', 'Nota de Crédito'])].copy()
        
        if has_time_filter:
            MONTH_MAP = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
            df_m['mes_nombre'] = df_m['mes'].map(MONTH_MAP)
            df_m = df_m.sort_values('mes')
        
        group_cols = [x_axis, 'programa']
        df_m_plot = df_m.groupby(group_cols)[[metric_key]].sum().reset_index()
        if not has_time_filter:
            df_m_plot['anio'] = df_m_plot['anio'].astype(str)
        
        if not df_m_plot.empty:
            fig_m = px.bar(df_m_plot, x=x_axis, y=metric_key, color='programa', barmode='group',
                           color_discrete_map=BAR_COLORS_PROGRAMA,
                           text=metric_key)
            fig_m.update_traces(
                texttemplate='<b>%{text:,.0f}</b>', 
                textposition='outside', 
                textfont=dict(size=11, color="#333", family="Inter"),
                marker=dict(
                    line=dict(width=0),
                    cornerradius=5
                ),
                width=0.35
            )
            fig_m.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                margin=dict(t=40, b=20, l=20, r=20), 
                height=380,
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="center", 
                    x=0.5, 
                    title=None, 
                    font=dict(color="#333", size=11),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='#ddd',
                    borderwidth=1
                ),
                xaxis=dict(
                    title=None, 
                    showgrid=False, 
                    showline=True,
                    linecolor="#ddd", 
                    tickfont=dict(color="#333", size=12, family="Inter"),
                    type='category'
                ),
                yaxis=dict(
                    title=None, 
                    showgrid=True, 
                    gridcolor="rgba(0,0,0,0.05)", 
                    tickfont=dict(color="#999", size=10),
                    showline=False,
                    range=[0, df_m_plot[metric_key].max() * 1.2]
                ),
                bargap=0.3,
                bargroupgap=0.1
            )
            st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False}, key="chart_manejo")

with chart_col2:
    st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">VENTAS POR MANEJO ({metric_label})</p>', unsafe_allow_html=True)
    
    if not df_raw.empty:
        has_time_filter = len(st.session_state.applied_filters.get('mes', [])) > 0 or len(st.session_state.applied_filters.get('trimestre', [])) > 0
        x_axis = 'mes_nombre' if has_time_filter else 'anio'

        df_p = df_raw[df_raw['tipo'].isin(['Factura', 'Nota de Crédito'])].copy()
        
        if has_time_filter:
            MONTH_MAP = {1:"Ene", 2:"Feb", 3:"Mar", 4:"Abr", 5:"May", 6:"Jun", 7:"Jul", 8:"Ago", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dic"}
            df_p['mes_nombre'] = df_p['mes'].map(MONTH_MAP)
            df_p = df_p.sort_values('mes')

        group_cols = [x_axis, 'manejo']
        df_p_plot = df_p.groupby(group_cols)[[metric_key]].sum().reset_index()
        if not has_time_filter:
            df_p_plot['anio'] = df_p_plot['anio'].astype(str)
        
        if not df_p_plot.empty:
            fig_p = px.bar(df_p_plot, x=x_axis, y=metric_key, color='manejo', barmode='group',
                           color_discrete_map=BAR_COLORS_MANEJO,
                           text=metric_key)
            fig_p.update_traces(
                texttemplate='<b>%{text:,.0f}</b>', 
                textposition='outside', 
                textfont=dict(size=11, color="#333", family="Inter"),
                marker=dict(
                    line=dict(width=0),
                    cornerradius=5
                ),
                width=0.35
            )
            fig_p.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', 
                plot_bgcolor='rgba(0,0,0,0)', 
                margin=dict(t=40, b=20, l=20, r=20), 
                height=380,
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="center", 
                    x=0.5, 
                    title=None, 
                    font=dict(color="#333", size=11),
                    bgcolor='rgba(255,255,255,0.8)',
                    bordercolor='#ddd',
                    borderwidth=1
                ),
                xaxis=dict(
                    title=None, 
                    showgrid=False, 
                    showline=True,
                    linecolor="#ddd", 
                    tickfont=dict(color="#333", size=12, family="Inter"),
                    type='category'
                ),
                yaxis=dict(
                    title=None, 
                    showgrid=True, 
                    gridcolor="rgba(0,0,0,0.05)", 
                    tickfont=dict(color="#999", size=10),
                    showline=False,
                    range=[0, df_p_plot[metric_key].max() * 1.2]
                ),
                bargap=0.3,
                bargroupgap=0.1
            )
            st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False}, key="chart_programa")

# --- TABLE SECTION (Full Width) ---
st.markdown(f'<p class="section-header">VOLUMEN TOTAL (FACTURADO + COMPROMETIDO) ({metric_label.upper()})</p>', unsafe_allow_html=True)
if not df_raw.empty:
    df_table = df_raw[df_raw['tipo'].isin(['Factura', 'Nota de Crédito', 'Comprometido'])].copy()
    if not df_table.empty:
        pivot_base = df_table.pivot_table(index=['programa', 'manejo'], columns='especie', values=metric_key, aggfunc='sum', fill_value=0)
        
        final_rows = []
        all_specs = pivot_base.columns.tolist()
        
        programas_orden = [p for p in ["Granel", "Retail", "Subproducto"] if p in df_table['programa'].unique()]
        for p in df_table['programa'].unique():
            if p not in programas_orden: programas_orden.append(p)

        for prog in programas_orden:
            if prog in pivot_base.index.get_level_values(0):
                prog_data = pivot_base.loc[prog]
                prog_sub = prog_data.sum(axis=0)
                row_h = {'Etiqueta': f"<b>{prog}</b>", '_row_type': 'subtotal'}
                for s in all_specs: row_h[s] = prog_sub[s]
                row_h['Total'] = sum(prog_sub)
                final_rows.append(row_h)
                
                for mane in prog_data.index:
                    row_d = {'Etiqueta': f"{mane}", '_row_type': 'detail'}
                    for s in all_specs: row_d[s] = prog_data.loc[mane, s]
                    row_d['Total'] = sum(prog_data.loc[mane])
                    final_rows.append(row_d)
        
        grand_row = {'Etiqueta': '<b>TOTAL</b>', '_row_type': 'total'}
        for s in all_specs: grand_row[s] = pivot_base.sum()[s]
        grand_row['Total'] = pivot_base.sum().sum()
        final_rows.append(grand_row)
        
        # Generate custom HTML with row classes
        def fmt_val(val):
            if isinstance(val, (int, float)): return f"{prefix}{val:{val_format}}"
            return val
        
        columns = ['Etiqueta'] + all_specs + ['Total']
        html_rows = []
        for row in final_rows:
            row_type = row.get('_row_type', '')
            row_class = f'row-{row_type}' if row_type else ''
            cells = ''.join([f'<td>{fmt_val(row.get(c, ""))}</td>' for c in columns])
            html_rows.append(f'<tr class="{row_class}">{cells}</tr>')
        
        header_cells = ''.join([f'<th>{c}</th>' for c in columns])
        table_html = f'''
        <table class="custom-table">
            <thead><tr>{header_cells}</tr></thead>
            <tbody>{''.join(html_rows)}</tbody>
        </table>
        '''
        st.write(table_html, unsafe_allow_html=True)
    else:
        st.warning("No hay datos para los filtros seleccionados.")

# --- PIE CHARTS SECTION (Side by Side Below Table) ---
st.markdown('<div style="margin-top: 40px;"></div>', unsafe_allow_html=True)
pie_col1, pie_col2 = st.columns(2)

# Definir colores más vibrantes
PIE_COLORS = {
    'Arándano': '#1a5276',      # Navy oscuro
    'Frambuesa': '#c0392b',     # Rojo intenso
    'Cereza': '#27ae60',        # Verde esmeralda
    'Mix': '#e67e22',           # Naranja
    'Mora': '#8e44ad',          # Púrpura
    'Frutilla': '#16a085'       # Teal
}

with pie_col1:
    st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">DISTRIBUCIÓN CONVENCIONAL ({metric_label})</p>', unsafe_allow_html=True)
    
    df_c = df_raw[(df_raw['manejo'] == 'Convencional') & (df_raw['tipo'].isin(['Factura', 'Nota de Crédito', 'Comprometido']))] if not df_raw.empty else pd.DataFrame()
    if not df_c.empty:
        df_pie1 = df_c.groupby('especie')[metric_key].sum().reset_index()
        df_pie1 = df_pie1[df_pie1[metric_key] > 0].sort_values(metric_key, ascending=False)
        
        if not df_pie1.empty:
            # Calcular el total para mostrar en el centro
            total_conv = df_pie1[metric_key].sum()
            
            fig_pie1 = px.pie(df_pie1, values=metric_key, names='especie', 
                              color='especie', color_discrete_map=PIE_COLORS,
                              hole=0.45)
            fig_pie1.update_layout(
                showlegend=False,
                margin=dict(t=30, b=30, l=80, r=80), 
                height=350, 
                paper_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(
                    text=f'<b>{prefix}{total_conv:,.0f}</b><br><span style="font-size:10px">Total</span>',
                    x=0.5, y=0.5, font_size=14, showarrow=False,
                    font=dict(color='#1b4f72')
                )]
            )
            fig_pie1.update_traces(
                textposition='outside',
                textinfo='label+percent',
                texttemplate='<b>%{label}</b><br>%{percent:.1%}',
                textfont=dict(color="#333", size=11),
                marker=dict(line=dict(color='#ffffff', width=2)),
                pull=[0.05 if i == 0 else 0 for i in range(len(df_pie1))],  # Resaltar el mayor
                hovertemplate='<b>%{label}</b><br>Valor: ' + prefix + '%{value:,.0f}<br>Porcentaje: %{percent:.1%}<extra></extra>'
            )
            st.plotly_chart(fig_pie1, use_container_width=True, config={'displayModeBar': False}, key="pie_convencional")
            
            # Mostrar tabla resumen debajo
            st.markdown('<div style="margin-top:-20px;">', unsafe_allow_html=True)
            for _, row in df_pie1.iterrows():
                pct = (row[metric_key] / total_conv) * 100
                color = PIE_COLORS.get(row['especie'], '#666')
                st.markdown(f'''
                <div style="display:flex; justify-content:space-between; padding:5px 10px; 
                            border-bottom:1px solid #eee; font-size:0.85rem;">
                    <span style="color:{color}; font-weight:600;">● {row['especie']}</span>
                    <span style="color:#333;">{prefix}{row[metric_key]:,.0f}</span>
                </div>
                ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay datos positivos.")

with pie_col2:
    st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">DISTRIBUCIÓN ORGÁNICO ({metric_label})</p>', unsafe_allow_html=True)
    
    df_o = df_raw[(df_raw['manejo'] == 'Orgánico') & (df_raw['tipo'].isin(['Factura', 'Nota de Crédito', 'Comprometido']))] if not df_raw.empty else pd.DataFrame()
    if not df_o.empty:
        df_pie2 = df_o.groupby('especie')[metric_key].sum().reset_index()
        df_pie2 = df_pie2[df_pie2[metric_key] > 0].sort_values(metric_key, ascending=False)
        
        if not df_pie2.empty:
            total_org = df_pie2[metric_key].sum()
            
            fig_pie2 = px.pie(df_pie2, values=metric_key, names='especie', 
                              color='especie', color_discrete_map=PIE_COLORS,
                              hole=0.45)
            fig_pie2.update_layout(
                showlegend=False,
                margin=dict(t=30, b=30, l=80, r=80), 
                height=350, 
                paper_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(
                    text=f'<b>{prefix}{total_org:,.0f}</b><br><span style="font-size:10px">Total</span>',
                    x=0.5, y=0.5, font_size=14, showarrow=False,
                    font=dict(color='#155724')
                )]
            )
            fig_pie2.update_traces(
                textposition='outside',
                textinfo='label+percent',
                texttemplate='<b>%{label}</b><br>%{percent:.1%}',
                textfont=dict(color="#333", size=11),
                marker=dict(line=dict(color='#ffffff', width=2)),
                pull=[0.05 if i == 0 else 0 for i in range(len(df_pie2))],
                hovertemplate='<b>%{label}</b><br>Valor: ' + prefix + '%{value:,.0f}<br>Porcentaje: %{percent:.1%}<extra></extra>'
            )
            st.plotly_chart(fig_pie2, use_container_width=True, config={'displayModeBar': False}, key="pie_organico")
            
            # Mostrar tabla resumen debajo
            st.markdown('<div style="margin-top:-20px;">', unsafe_allow_html=True)
            for _, row in df_pie2.iterrows():
                pct = (row[metric_key] / total_org) * 100
                color = PIE_COLORS.get(row['especie'], '#666')
                st.markdown(f'''
                <div style="display:flex; justify-content:space-between; padding:5px 10px; 
                            border-bottom:1px solid #eee; font-size:0.85rem;">
                    <span style="color:{color}; font-weight:600;">● {row['especie']}</span>
                    <span style="color:#333;">{prefix}{row[metric_key]:,.0f}</span>
                </div>
                ''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("No hay datos positivos.")
