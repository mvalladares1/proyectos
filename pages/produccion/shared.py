"""
Módulo compartido para Producción.
Contiene funciones de utilidad, formateo, gráficos y llamadas a API.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import httpx
import requests
import os
from datetime import datetime
from typing import List, Dict, Optional

# Determinar API_URL basado en ENV
ENV = os.getenv("ENV", "prod")
if ENV == "development":
    API_URL = "http://127.0.0.1:8002"
else:
    API_URL = "http://127.0.0.1:8000"


# --------------------- Constantes ---------------------

STATE_OPTIONS = {
    "Todos": None,
    "Borrador": "draft",
    "Confirmado": "confirmed",
    "En Progreso": "progress",
    "Por Cerrar": "to_close",
    "Hecho": "done",
    "Cancelado": "cancel"
}

ESTADOS_MAP = {
    'draft': 'Borrador',
    'confirmed': 'Confirmado',
    'progress': 'En Progreso',
    'to_close': 'Por Cerrar',
    'done': 'Hecho',
    'cancel': 'Cancelado'
}

CSS_FORCE_DARK = """
<style>
    /* Force Dark Theme Main Colors */
    [data-testid="stAppViewContainer"] { 
        background-color: #0e1117 !important; 
        color: #ffffff !important;
    }
    [data-testid="stHeader"] { 
        background-color: rgba(14, 17, 23, 0.9) !important; 
    }
    [data-testid="stSidebar"] { 
        background-color: #262730 !important; 
        color: #ffffff !important;
    }
    
    /* Text Colors */
    h1, h2, h3, h4, h5, h6, p, label, .stMarkdown {
        color: #ffffff !important;
    }
    
    /* Standard Card Style (Matches Recepciones/Enterprise) */
    .info-card {
        background-color: #1e293b;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #334155;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        margin-bottom: 20px;
    }
    
    /* Inputs */
    .stTextInput input, .stSelectbox, .stDateInput input {
        color: #ffffff !important; 
        background-color: #1a1c23 !important;
    }
    
    /* Global Overrides */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
</style>
"""


# --------------------- Funciones de formateo ---------------------

def skeleton_loader():
    """Muestra un skeleton loader mientras cargan los datos."""
    st.markdown("""
    <style>
    @keyframes shimmer {
        0% { background-position: -1000px 0; }
        100% { background-position: 1000px 0; }
    }
    .skeleton {
        background: linear-gradient(90deg, #2a2a4a 25%, #3a3a5a 50%, #2a2a4a 75%);
        background-size: 1000px 100%;
        animation: shimmer 2s infinite;
        border-radius: 8px;
        margin: 10px 0;
    }
    .skeleton-text {
        height: 20px;
        margin: 8px 0;
    }
    .skeleton-card {
        height: 120px;
        margin: 15px 0;
    }
    </style>
    <div class="skeleton skeleton-card"></div>
    <div class="skeleton skeleton-text" style="width: 80%;"></div>
    <div class="skeleton skeleton-text" style="width: 60%;"></div>
    <div class="skeleton skeleton-card"></div>
    <div class="skeleton skeleton-text" style="width: 90%;"></div>
    """, unsafe_allow_html=True)


def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal (formato chileno)"""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


def fmt_porcentaje(valor, decimales=1):
    """Formatea porcentaje"""
    return f"{fmt_numero(valor, decimales)}%"


def get_alert_color(rendimiento):
    """Retorna color/emoji según rendimiento"""
    if rendimiento >= 95:
        return "🟢"
    elif rendimiento >= 90:
        return "🟡"
    else:
        return "🔴"


def clean_name(val):
    """Limpia y formatea nombres para mostrar en el dashboard."""
    if val is None:
        return "-"
    if isinstance(val, dict) and "name" in val:
        return str(val["name"])
    return str(val)


def get_state_label(state):
    """Devuelve el label legible para el estado de la OF."""
    return ESTADOS_MAP.get(state, state)


def format_fecha(fecha_str):
    """Formatea fecha a DD/MM/AAAA HH:MM"""
    if not fecha_str or fecha_str == 'N/A':
        return 'N/A'
    try:
        if isinstance(fecha_str, str):
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y']:
                try:
                    dt = datetime.strptime(fecha_str, fmt)
                    return dt.strftime('%d/%m/%Y %H:%M')
                except:
                    continue
        return str(fecha_str)
    except:
        return str(fecha_str)


def format_num(val, decimals=2):
    """Formatea números con máximo N decimales"""
    if val is None or val == 'N/A':
        return 'N/A'
    try:
        num = float(val)
        if num == int(num):
            return f"{int(num):,}"
        return f"{num:,.{decimals}f}"
    except:
        return str(val)


# --------------------- Funciones de planta ---------------------

def detectar_planta(mo_name):
    """Detecta la planta basándose en el prefijo del nombre de la MO.
    RF/MO/... = RFP (default), VLK/... = VILKUN
    """
    if not mo_name:
        return "RIO FUTURO"
    mo_upper = str(mo_name).upper()
    if mo_upper.startswith("VLK"):
        return "VILKUN"
    return "RIO FUTURO"


def filtrar_mos_por_planta(lista_mos, filtro_rfp, filtro_vilkun):
    """Filtra una lista de MOs por planta basándose en el nombre de la MO."""
    if filtro_rfp and filtro_vilkun:
        return lista_mos
    if not filtro_rfp and not filtro_vilkun:
        return []
    
    resultado = []
    for item in lista_mos:
        mo_name = item.get('mo_name') or item.get('name') or ''
        planta = detectar_planta(mo_name)
        
        if planta == "RFP" and filtro_rfp:
            resultado.append(item)
        elif planta == "VILKUN" and filtro_vilkun:
            resultado.append(item)
    return resultado


# --------------------- Funciones de gráficos ---------------------

def build_pie_chart(labels: List[str], values: List[float], title: str) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:.2f} kg<extra></extra>",
        marker=dict(line=dict(color="#1e1e1e", width=1.5))
    ))
    fig.update_layout(
        height=420,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=20, r=140, t=30, b=30),
        title=dict(text=title, x=0.01, xanchor="left")
    )
    return fig


def build_horizontal_bar(labels: List[str], values: List[float], title: str) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=values,
        y=labels,
        orientation="h",
        marker=dict(color="#00cc66", line=dict(color="#00ff88", width=1.5)),
    ))
    fig.update_layout(
        height=380,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=60, r=20, t=30, b=30),
        title=dict(text=title, x=0.01, xanchor="left")
    )
    return fig


# --------------------- Llamadas API ---------------------

@st.cache_data(ttl=300)
def fetch_ordenes(username: str, password: str, start_date: str, end_date: str, estado: Optional[str]) -> List[Dict]:
    params = {
        "username": username,
        "password": password,
        "fecha_desde": start_date,
        "fecha_hasta": end_date,
    }
    if estado:
        params["estado"] = estado
    response = httpx.get(f"{API_URL}/api/v1/produccion/ordenes", params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def fetch_of_detail(of_id: int, username: str, password: str) -> Dict:
    response = httpx.get(
        f"{API_URL}/api/v1/produccion/ordenes/{of_id}",
        params={"username": username, "password": password},
        timeout=60.0
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300)
def fetch_kpis(username: str, password: str) -> Dict:
    response = httpx.get(
        f"{API_URL}/api/v1/produccion/kpis",
        params={"username": username, "password": password},
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_dashboard_completo(username: str, password: str, fecha_inicio: str, fecha_fin: str, solo_terminadas: bool = True):
    """
    OPTIMIZADO: Obtiene TODOS los datos del dashboard en UNA sola llamada.
    Retorna: overview, consolidado, salas, mos - todo junto.
    """
    try:
        resp = requests.get(f"{API_URL}/api/v1/rendimiento/dashboard", params={
            "username": username, "password": password,
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin,
            "solo_terminadas": solo_terminadas
        }, timeout=180)
        
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 401:
            st.error(f"❌ Error de autenticación (401). Verifica tus credenciales.")
        elif resp.status_code == 500:
            st.error(f"❌ Error del servidor (500). Detalle: {resp.text[:200]}")
        else:
            st.error(f"❌ Error HTTP {resp.status_code}: {resp.text[:200]}")
    except requests.exceptions.ConnectionError:
        st.error(f"❌ No se pudo conectar al servidor en {API_URL}. Verifica que el backend esté corriendo.")
    except requests.exceptions.Timeout:
        st.error(f"⏱️ Timeout después de 180 segundos. La consulta tardó demasiado.")
    except Exception as e:
        st.error(f"❌ Error inesperado: {type(e).__name__}: {str(e)}")
    return None


@st.cache_data(ttl=120, show_spinner=False)
def fetch_rendimiento_overview(username: str, password: str, fecha_inicio: str, fecha_fin: str):
    """Obtiene KPIs consolidados de rendimiento"""
    try:
        resp = requests.get(f"{API_URL}/api/v1/rendimiento/overview", params={
            "username": username, "password": password,
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin
        }, timeout=120)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None


# --------------------- Funciones de render ---------------------

def render_component_tab(items: List[Dict], label: str):
    if not items:
        st.info("No hay registros disponibles")
        return

    categories = sorted({item.get("product_category_name", "N/A") for item in items})
    selected_categories = st.multiselect(
        "Filtrar por categoría",
        options=categories,
        default=categories,
        key=f"prod_cat_{label}"
    )
    filtered = [item for item in items if item.get("product_category_name", "N/A") in selected_categories]

    if not filtered:
        st.warning("No hay registros para las categorías seleccionadas")
        return

    df = pd.DataFrame([{
        "Producto": clean_name(item.get("product_id")),
        "Lote": clean_name(item.get("lot_id")),
        "Cantidad (kg)": format_num(item.get("qty_done", 0) or 0),
        "Precio unitario": format_num(item.get("x_studio_precio_unitario", 0) or 0),
        "PxQ": format_num((item.get("x_studio_precio_unitario", 0) or 0) * (item.get("qty_done", 0) or 0)),
        "Ubicación origen": clean_name(item.get("location_id")),
        "Pallet": clean_name(item.get("package_id"))
    } for item in filtered])
    st.dataframe(df, use_container_width=True, height=320)
    total_pxq = sum([(item.get("x_studio_precio_unitario", 0) or 0) * (item.get("qty_done", 0) or 0) for item in filtered])
    st.markdown(f"<div style='margin-top:8px;font-size:1.1em'><b>Total PxQ:</b> {format_num(total_pxq)}</div>", unsafe_allow_html=True)

    dist_product = {}
    for item in filtered:
        prod_name = clean_name(item.get("product_id"))
        qty = item.get("qty_done", 0) or 0
        dist_product[prod_name] = dist_product.get(prod_name, 0) + qty

    sorted_product = sorted(dist_product.items(), key=lambda x: x[1], reverse=True)
    product_labels = [lbl for lbl, _ in sorted_product]
    product_values = [value for _, value in sorted_product]

    col1, col2 = st.columns([2, 3])
    with col1:
        st.plotly_chart(build_pie_chart(product_labels, product_values, f"Distribución por producto ({label})"), use_container_width=True)
    with col2:
        st.plotly_chart(build_horizontal_bar(product_labels, product_values, f"Cantidad por producto ({label})"), use_container_width=True)


def render_metrics_row(columns, metrics):
    for col, (label, value, suffix) in zip(columns, metrics):
        if label.lower().startswith("rendimiento"):
            try:
                value = float(value)
                text = f"{value:.2f}%"
            except Exception:
                text = f"{value}{suffix if suffix else ''}"
        else:
            text = f"{value}{suffix if suffix else ''}"
        col.metric(label, text)


# --------------------- Inicialización de Session State ---------------------

def init_session_state():
    """Inicializa variables de session_state para el módulo Producción."""
    defaults = {
        'theme_mode': 'Dark',
        'prod_dashboard_data': None,
        'production_ofs': [],
        'production_current_of': None,
        'prod_reporteria_loading': False,
        'prod_detalle_loading': False,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
