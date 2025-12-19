"""
Órdenes de fabricación: seguimiento de producción, rendimientos y consumo de materias primas.
Versión 2: Reorganizado con tabs - Reportería General y Detalle de OF
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import altair as alt
import httpx
import requests
import os
import sys
import io
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

# Importar utilidades compartidas
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import proteger_pagina, get_credenciales, tiene_acceso_dashboard

# Configuración de página
st.set_page_config(
    page_title="Producción",
    page_icon="🏭",
    layout="wide"
)

# Verificar autenticación
if not proteger_pagina():
    st.stop()

if not tiene_acceso_dashboard("produccion"):
    st.error("No tienes permisos para ver este dashboard.")
    st.stop()

# Obtener credenciales y API URL
username, password = get_credenciales()
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

# ============================================
# FUNCIONES DE FORMATEO (reutilizables)
# ============================================

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
    ESTADOS = {
        'draft': 'Borrador',
        'confirmed': 'Confirmado',
        'progress': 'En Progreso',
        'to_close': 'Por Cerrar',
        'done': 'Hecho',
        'cancel': 'Cancelado'
    }
    return ESTADOS.get(state, state)

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

# ============================================
# FUNCIONES DE GRÁFICOS
# ============================================

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

# ============================================
# FUNCIONES DE API - PRODUCCIÓN
# ============================================

STATE_OPTIONS = {
    "Todos": None,
    "Borrador": "draft",
    "Confirmado": "confirmed",
    "En Progreso": "progress",
    "Por Cerrar": "to_close",
    "Hecho": "done",
    "Cancelado": "cancel"
}

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

# ============================================
# FUNCIONES DE API - RENDIMIENTO (para reportería general)
# ============================================

@st.cache_data(ttl=120, show_spinner=False)
def fetch_dashboard_completo(username: str, password: str, fecha_inicio: str, fecha_fin: str):
    """
    OPTIMIZADO: Obtiene TODOS los datos del dashboard en UNA sola llamada.
    Retorna: overview, consolidado, salas, mos - todo junto.
    Reduce significativamente las llamadas a la API.
    """
    try:
        resp = requests.get(f"{API_URL}/api/v1/rendimiento/dashboard", params={
            "username": username, "password": password,
            "fecha_inicio": fecha_inicio, "fecha_fin": fecha_fin
        }, timeout=180)
        if resp.status_code == 200:
            return resp.json()
    except Exception as e:
        st.warning(f"Error cargando datos: {e}")
    return None

# Funciones individuales (legacy, para compatibilidad)
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

# ============================================
# FUNCIONES DE RENDER PARA DETALLE OF
# ============================================

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

# ============================================
# CSS GLOBAL
# ============================================
st.markdown("""
<style>
.info-card {
    background: linear-gradient(145deg, #1a1a2e 0%, #16213e 100%);
    padding: 24px;
    border-radius: 16px;
    margin-bottom: 20px;
    border: 1px solid #2a2a4a;
    box-shadow: 0 4px 15px rgba(0,0,0,0.3);
}
.info-card h4 {
    margin: 0 0 20px 0;
    color: #00cc66;
    font-size: 1.1em;
    font-weight: 600;
    padding-bottom: 12px;
    border-bottom: 2px solid #00cc6633;
}
.info-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px 0;
    border-bottom: 1px solid #ffffff10;
}
.info-row:last-child {
    border-bottom: none;
}
.info-label {
    color: #8892b0;
    font-size: 0.95em;
}
.info-value {
    color: #ffffff;
    font-weight: 500;
    font-size: 0.95em;
    text-align: right;
    max-width: 60%;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# TÍTULO PRINCIPAL
# ============================================
st.title("🏭 Dashboard de Producción")
st.caption("Monitorea rendimientos productivos y detalle de órdenes de fabricación")

# ============================================
# TABS PRINCIPALES
# ============================================
tab_general, tab_detalle = st.tabs(["📊 Reportería General", "📋 Detalle de OF"])

# ============================================
# TAB 1: REPORTERÍA GENERAL
# ============================================
with tab_general:
    st.subheader("📊 Reportería General de Producción")
    
    # --- Estado de sesión para reportería (simplificado) ---
    if 'prod_dashboard_data' not in st.session_state:
        st.session_state.prod_dashboard_data = None
    
    # --- Filtros de fecha ---
    col_f1, col_f2 = st.columns([1, 1])
    with col_f1:
        fecha_inicio_rep = st.date_input(
            "Desde", 
            datetime.now() - timedelta(days=30), 
            format="DD/MM/YYYY",
            key="prod_rep_fecha_inicio"
        )
    with col_f2:
        fecha_fin_rep = st.date_input(
            "Hasta", 
            datetime.now(), 
            format="DD/MM/YYYY",
            key="prod_rep_fecha_fin"
        )
    
    # Checkbox para filtrar solo OFs terminadas (similar a Recepciones)
    solo_terminadas = st.checkbox(
        "Solo fabricaciones terminadas (done/to_close)", 
        value=True, 
        key="solo_terminadas_prod",
        help="Activa para ver solo OFs completadas o por cerrar. Desactiva para incluir todas."
    )
    
    if st.button("🔄 Consultar Reportería", type="primary", key="btn_consultar_reporteria"):
        with st.spinner("Cargando datos de rendimiento (optimizado - 1 consulta)..."):
            fi = fecha_inicio_rep.strftime("%Y-%m-%d")
            ff = fecha_fin_rep.strftime("%Y-%m-%d")
            
            # UNA SOLA LLAMADA que obtiene TODO
            st.session_state.prod_dashboard_data = fetch_dashboard_completo(username, password, fi, ff)
            
            if st.session_state.prod_dashboard_data:
                st.success("✅ Datos cargados correctamente")
            else:
                st.warning("No se pudieron cargar los datos. Verifica la conexión al servidor.")
    
    # --- Extraer datos del dashboard unificado ---
    dashboard = st.session_state.prod_dashboard_data
    data = dashboard.get('overview') if dashboard else None
    consolidado = dashboard.get('consolidado') if dashboard else None
    salas = dashboard.get('salas') if dashboard else None
    mos = dashboard.get('mos') if dashboard else None
    
    if data:
        st.markdown("---")
        
        # === KPIs de PROCESO (Vaciado) - EL NÚMERO REAL ===
        st.subheader("🏭 KPIs de Proceso (Vaciado)")
        st.caption("Salas de vaciado, líneas retail/granel - generan merma real")
        
        proc_cols = st.columns(5)
        with proc_cols[0]:
            st.metric("Kg MP Procesados", fmt_numero(data.get('proceso_kg_mp', 0), 0))
        with proc_cols[1]:
            st.metric("Kg PT Producidos", fmt_numero(data.get('proceso_kg_pt', 0), 0))
        with proc_cols[2]:
            rend = data.get('proceso_rendimiento', 0)
            alert = get_alert_color(rend)
            st.metric(f"Rendimiento {alert}", fmt_porcentaje(rend), delta=f"{rend-85:.1f}% vs 85%")
        with proc_cols[3]:
            st.metric("Merma Proceso", fmt_numero(data.get('proceso_merma_kg', 0), 0) + " Kg")
        with proc_cols[4]:
            st.metric("Kg/HH", fmt_numero(data.get('proceso_kg_por_hh', 0), 1))
        
        proc_cols2 = st.columns(4)
        with proc_cols2[0]:
            st.metric("MOs Proceso", data.get('proceso_mos', 0))
        with proc_cols2[1]:
            st.metric("HH Proceso", fmt_numero(data.get('proceso_hh', 0), 1))
        with proc_cols2[2]:
            st.metric("Merma %", fmt_porcentaje(data.get('proceso_merma_pct', 0)))
        with proc_cols2[3]:
            st.metric("Lotes Únicos", data.get('lotes_unicos', 0))
        
        st.markdown("---")
        
        # === KPIs de CONGELADO (Túneles) ===
        with st.expander("❄️ KPIs de Congelado (Túneles Estáticos)", expanded=False):
            st.caption("Túneles de congelación - solo congelan, rendimiento ~100%")
            
            cong_cols = st.columns(5)
            with cong_cols[0]:
                st.metric("Kg Entrada", fmt_numero(data.get('congelado_kg_mp', 0), 0))
            with cong_cols[1]:
                st.metric("Kg Salida", fmt_numero(data.get('congelado_kg_pt', 0), 0))
            with cong_cols[2]:
                cong_rend = data.get('congelado_rendimiento', 0)
                st.metric("Rendimiento", fmt_porcentaje(cong_rend))
            with cong_cols[3]:
                st.metric("MOs Congelado", data.get('congelado_mos', 0))
            with cong_cols[4]:
                costo_elec = data.get('total_costo_electricidad', 0)
                st.metric("⚡ Costo Elec.", f"${fmt_numero(costo_elec, 0)}")
        
        st.markdown("---")
        
        # === Resumen por Tipo de Fruta y Manejo (Estilo Recepciones) ===
        if consolidado:
            st.subheader("📊 Resumen por Tipo de Fruta y Manejo")
            
            por_fruta = consolidado.get('por_fruta', [])
            por_fm = consolidado.get('por_fruta_manejo', [])
            
            if por_fruta and por_fm:
                # Construir tabla anidada estilo Recepciones
                tabla_rows = []
                total_kg_mp = 0
                total_kg_pt = 0
                total_merma = 0
                
                # Ordenar frutas por kg_pt descendente
                for fruta_data in sorted(por_fruta, key=lambda x: x.get('kg_pt', 0), reverse=True):
                    tipo_fruta = fruta_data.get('tipo_fruta', 'N/A')
                    
                    # Fila de tipo de fruta (totalizador)
                    tabla_rows.append({
                        'tipo': 'fruta',
                        'Descripción': tipo_fruta,
                        'Kg MP': fruta_data.get('kg_mp', 0),
                        'Kg PT': fruta_data.get('kg_pt', 0),
                        'Rendimiento': None,  # Se muestra en las filas de manejo
                        'Merma': fruta_data.get('merma', 0)
                    })
                    total_kg_mp += fruta_data.get('kg_mp', 0)
                    total_kg_pt += fruta_data.get('kg_pt', 0)
                    total_merma += fruta_data.get('merma', 0)
                    
                    # Filas de manejo para esta fruta
                    manejos_fruta = [fm for fm in por_fm if fm.get('tipo_fruta') == tipo_fruta]
                    for manejo_data in sorted(manejos_fruta, key=lambda x: x.get('kg_pt', 0), reverse=True):
                        manejo = manejo_data.get('manejo', 'N/A')
                        if 'orgánico' in manejo.lower() or 'organico' in manejo.lower():
                            icono = '🌱'
                        elif 'convencional' in manejo.lower():
                            icono = '🏭'
                        else:
                            icono = '📋'
                        
                        tabla_rows.append({
                            'tipo': 'manejo',
                            'Descripción': f"    → {icono} {manejo}",
                            'Kg MP': manejo_data.get('kg_mp', 0),
                            'Kg PT': manejo_data.get('kg_pt', 0),
                            'Rendimiento': manejo_data.get('rendimiento', 0),
                            'Merma': manejo_data.get('merma', 0)
                        })
                
                # Fila total
                rend_total = (total_kg_pt / total_kg_mp * 100) if total_kg_mp > 0 else 0
                tabla_rows.append({
                    'tipo': 'total',
                    'Descripción': 'TOTAL GENERAL',
                    'Kg MP': total_kg_mp,
                    'Kg PT': total_kg_pt,
                    'Rendimiento': rend_total,
                    'Merma': total_merma
                })
                
                # Crear DataFrame
                df_resumen = pd.DataFrame(tabla_rows)
                
                # Formatear para mostrar
                df_display = df_resumen.copy()
                df_display['Kg MP'] = df_display['Kg MP'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
                df_display['Kg PT'] = df_display['Kg PT'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
                df_display['Rendimiento'] = df_display['Rendimiento'].apply(
                    lambda x: f"{get_alert_color(x)} {fmt_porcentaje(x)}" if pd.notna(x) and x > 0 else "—"
                )
                df_display['Merma'] = df_display['Merma'].apply(lambda x: fmt_numero(x, 0) if pd.notna(x) else "—")
                
                # Calcular altura dinámica basada en filas
                num_filas = len(df_display)
                table_height = min(600, max(200, num_filas * 40 + 60))
                
                # Mostrar tabla con ancho completo
                df_show = df_display[['Descripción', 'Kg MP', 'Kg PT', 'Rendimiento', 'Merma']]
                st.dataframe(
                    df_show,
                    use_container_width=True,
                    hide_index=True,
                    height=table_height,
                    column_config={
                        'Descripción': st.column_config.TextColumn('Tipo / Manejo', width=250),
                        'Kg MP': st.column_config.TextColumn('Kg MP', width=120),
                        'Kg PT': st.column_config.TextColumn('Kg PT', width=120),
                        'Rendimiento': st.column_config.TextColumn('Rendimiento', width=150),
                        'Merma': st.column_config.TextColumn('Merma (Kg)', width=120),
                    }
                )
            
            st.markdown("---")
            
            # === Gráfico de Rendimiento por Tipo de Fruta ===
            if por_fruta:
                st.subheader("📈 Rendimiento por Tipo de Fruta")
                
                df_fruta = pd.DataFrame(por_fruta)
                
                # Calcular altura dinámica basada en cantidad de frutas
                num_frutas = len(df_fruta)
                chart_height = max(300, min(500, num_frutas * 80))
                bar_size = max(30, min(60, 400 // num_frutas)) if num_frutas > 0 else 50
                
                # Gráfico de barras horizontales para mejor lectura de etiquetas
                bars = alt.Chart(df_fruta).mark_bar(size=bar_size).encode(
                    y=alt.Y('tipo_fruta:N', sort='-x', title='Tipo de Fruta', 
                           axis=alt.Axis(labelFontSize=14, labelLimit=200)),
                    x=alt.X('rendimiento:Q', title='Rendimiento %', 
                           scale=alt.Scale(domain=[0, 105]),
                           axis=alt.Axis(labelFontSize=12)),
                    color=alt.condition(
                        alt.datum.rendimiento >= 90,
                        alt.value('#22c55e'),  # Verde más vibrante
                        alt.condition(
                            alt.datum.rendimiento >= 80,
                            alt.value('#f59e0b'),  # Amarillo/Naranja
                            alt.value('#ef4444')   # Rojo
                        )
                    ),
                    tooltip=[
                        alt.Tooltip('tipo_fruta:N', title='Fruta'),
                        alt.Tooltip('rendimiento:Q', title='Rendimiento %', format='.1f'),
                        alt.Tooltip('kg_mp:Q', title='Kg MP', format=',.0f'),
                        alt.Tooltip('kg_pt:Q', title='Kg PT', format=',.0f'),
                        alt.Tooltip('num_lotes:Q', title='Lotes')
                    ]
                )
                
                # Etiquetas de valor en las barras
                text = alt.Chart(df_fruta).mark_text(
                    align='left', 
                    baseline='middle', 
                    dx=5,
                    fontSize=14,
                    fontWeight='bold',
                    color='white'
                ).encode(
                    y=alt.Y('tipo_fruta:N', sort='-x'),
                    x=alt.X('rendimiento:Q'),
                    text=alt.Text('rendimiento:Q', format='.1f')
                )
                
                # Líneas de referencia
                rule_90 = alt.Chart(pd.DataFrame({'x': [90]})).mark_rule(
                    color='#ef4444', strokeDash=[6,4], strokeWidth=2
                ).encode(x='x:Q')
                rule_85 = alt.Chart(pd.DataFrame({'x': [85]})).mark_rule(
                    color='#f59e0b', strokeDash=[6,4], strokeWidth=2
                ).encode(x='x:Q')
                
                chart = (bars + text + rule_90 + rule_85).properties(
                    height=chart_height
                ).configure_view(
                    strokeWidth=0
                ).configure_axis(
                    grid=True,
                    gridColor='#333'
                )
                
                st.altair_chart(chart, use_container_width=True)
                st.caption("📊 **Línea roja**: 90% (Meta) | **Línea naranja**: 85% (Mínimo)")
        
        
        # === Productividad por Sala ===
        if salas:
            st.markdown("---")
            st.subheader("🏠 Productividad por Sala de Proceso")
            
            df_salas = pd.DataFrame(salas)
            
            for _, sala in df_salas.iterrows():
                alert = get_alert_color(sala['rendimiento'])
                with st.expander(f"{alert} **{sala['sala']}** | {fmt_numero(sala['kg_pt'])} Kg PT | {sala['num_mos']} MOs"):
                    cols = st.columns(4)
                    with cols[0]:
                        st.metric("Rendimiento", fmt_porcentaje(sala['rendimiento']))
                    with cols[1]:
                        st.metric("Kg/Hora", fmt_numero(sala['kg_por_hora'], 1))
                    with cols[2]:
                        st.metric("Kg/HH", fmt_numero(sala['kg_por_hh'], 1))
                    with cols[3]:
                        st.metric("Kg/Operario", fmt_numero(sala['kg_por_operario'], 1))
                    
                    cols2 = st.columns(4)
                    with cols2[0]:
                        st.markdown(f"**Kg MP:** {fmt_numero(sala['kg_mp'])}")
                    with cols2[1]:
                        st.markdown(f"**Kg PT:** {fmt_numero(sala['kg_pt'])}")
                    with cols2[2]:
                        st.markdown(f"**HH Total:** {fmt_numero(sala['hh_total'], 1)}")
                    with cols2[3]:
                        st.markdown(f"**Dotación Prom:** {sala['dotacion_promedio']:.1f}")
        
        # === Detalle de Fabricaciones (Tabla de MOs) ===
        if mos:
            st.markdown("---")
            st.subheader("📋 Detalle de Fabricaciones")
            
            df_mos_original = pd.DataFrame(mos)
            
            # === FILTROS INTERACTIVOS ===
            with st.expander("🔍 Filtros de Fabricaciones", expanded=True):
                filter_cols = st.columns(5)
                
                # Filtro por OF (búsqueda de texto)
                with filter_cols[0]:
                    of_buscar = st.text_input("🔎 Buscar OF", "", key="filtro_of_detalle", placeholder="Ej: WH/MO/00123")
                
                # Filtro por Producto
                with filter_cols[1]:
                    productos_unicos = sorted(df_mos_original['product_name'].dropna().unique().tolist())
                    productos_sel = st.multiselect("📦 Producto", productos_unicos, key="filtro_producto_detalle")
                
                # Filtro por Especie
                with filter_cols[2]:
                    if 'especie' in df_mos_original.columns:
                        especies_unicas = sorted(df_mos_original['especie'].dropna().unique().tolist())
                        especies_sel = st.multiselect("🍓 Especie", especies_unicas, key="filtro_especie_detalle")
                    else:
                        especies_sel = []
                
                # Filtro por Manejo
                with filter_cols[3]:
                    if 'manejo' in df_mos_original.columns:
                        manejos_unicos = sorted(df_mos_original['manejo'].dropna().unique().tolist())
                        manejos_sel = st.multiselect("🏷️ Manejo", manejos_unicos, key="filtro_manejo_detalle")
                    else:
                        manejos_sel = []
                
                # Filtro por Sala
                with filter_cols[4]:
                    salas_unicas = sorted(df_mos_original['sala'].dropna().unique().tolist())
                    salas_sel = st.multiselect("🏭 Sala", salas_unicas, key="filtro_sala_detalle")
            
            # Segunda fila de filtros
            filter_cols2 = st.columns([1, 1, 2])
            with filter_cols2[0]:
                # Filtro por Tipo (PROCESO vs CONGELADO)
                if 'sala_tipo' in df_mos_original.columns:
                    tipos_unicos = sorted(df_mos_original['sala_tipo'].dropna().unique().tolist())
                    tipo_labels = {'PROCESO': '🏭 Proceso (Vaciado)', 'CONGELADO': '❄️ Congelado (Túneles)', 'SIN_SALA': '⚠️ Sin Sala'}
                    tipos_display = [tipo_labels.get(t, t) for t in tipos_unicos]
                    tipo_sel_display = st.multiselect("📌 Tipo Operación", tipos_display, key="filtro_tipo_detalle")
                    # Convertir de vuelta a valores originales
                    tipo_reverse = {v: k for k, v in tipo_labels.items()}
                    tipos_sel = [tipo_reverse.get(t, t) for t in tipo_sel_display]
                else:
                    tipos_sel = []
            
            # Aplicar filtros
            df_mos = df_mos_original.copy()
            
            if of_buscar:
                df_mos = df_mos[df_mos['mo_name'].str.contains(of_buscar, case=False, na=False)]
            
            if productos_sel:
                df_mos = df_mos[df_mos['product_name'].isin(productos_sel)]
            
            if especies_sel and 'especie' in df_mos.columns:
                df_mos = df_mos[df_mos['especie'].isin(especies_sel)]
            
            if manejos_sel and 'manejo' in df_mos.columns:
                df_mos = df_mos[df_mos['manejo'].isin(manejos_sel)]
            
            if salas_sel:
                df_mos = df_mos[df_mos['sala'].isin(salas_sel)]
            
            # Filtro por Tipo de Operación (PROCESO/CONGELADO)
            if tipos_sel and 'sala_tipo' in df_mos.columns:
                df_mos = df_mos[df_mos['sala_tipo'].isin(tipos_sel)]
            
            # Agregar columna de estado/alerta
            df_mos['estado'] = df_mos['rendimiento'].apply(get_alert_color)
            
            # Verificar columnas disponibles
            cols_to_show = ['estado', 'mo_name', 'product_name']
            col_names = ['', 'OF', 'Producto']
            
            if 'especie' in df_mos.columns:
                cols_to_show.append('especie')
                col_names.append('Especie')
            if 'manejo' in df_mos.columns:
                cols_to_show.append('manejo')
                col_names.append('Manejo')
            
            # Agregar tipo de operación simplificado
            if 'sala_tipo' in df_mos.columns:
                cols_to_show.append('sala_tipo')
                col_names.append('Tipo')
            
            cols_to_show.extend(['sala', 'kg_mp', 'kg_pt', 'rendimiento', 'merma'])
            col_names.extend(['Sala', 'Kg MP', 'Kg PT', 'Rend %', 'Merma'])
            
            # Agregar costo electricidad si existe
            if 'costo_electricidad' in df_mos.columns:
                cols_to_show.append('costo_electricidad')
                col_names.append('⚡ Elec $')
            
            cols_to_show.append('fecha')
            col_names.append('Fecha')
            
            # Formatear para mostrar
            df_mos_display = df_mos[cols_to_show].copy()
            df_mos_display.columns = col_names
            
            # Aplicar formato chileno
            df_mos_display['Kg MP'] = df_mos_display['Kg MP'].apply(lambda x: fmt_numero(x, 0))
            df_mos_display['Kg PT'] = df_mos_display['Kg PT'].apply(lambda x: fmt_numero(x, 0))
            df_mos_display['Rend %'] = df_mos_display['Rend %'].apply(lambda x: fmt_porcentaje(x))
            df_mos_display['Merma'] = df_mos_display['Merma'].apply(lambda x: fmt_numero(x, 0))
            if '⚡ Elec $' in df_mos_display.columns:
                df_mos_display['⚡ Elec $'] = df_mos_display['⚡ Elec $'].apply(lambda x: f"${fmt_numero(x, 0)}" if x > 0 else "-")
            
            # Mostrar resumen de datos filtrados
            total_registros = len(df_mos_original)
            filtrados = len(df_mos)
            if filtrados < total_registros:
                st.caption(f"📊 Mostrando **{filtrados}** de {total_registros} órdenes de fabricación (filtrado)")
            else:
                st.caption(f"📊 Mostrando {filtrados} órdenes de fabricación")
            
            if filtrados > 0:
                st.dataframe(df_mos_display, use_container_width=True, hide_index=True, height=400)
            else:
                st.warning("No hay fabricaciones que coincidan con los filtros seleccionados.")
            
            # === Botones de exportación ===
            st.markdown("---")
            st.subheader("📥 Descargar Datos de Producción")
            
            col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 1])
            
            # Preparar DataFrame para exportación (valores numéricos sin formato)
            export_cols = ['mo_name', 'product_name']
            export_names = ['OF', 'Producto']
            if 'especie' in df_mos.columns:
                export_cols.append('especie')
                export_names.append('Especie')
            if 'manejo' in df_mos.columns:
                export_cols.append('manejo')
                export_names.append('Manejo')
            export_cols.extend(['sala', 'kg_mp', 'kg_pt', 'rendimiento', 'merma'])
            export_names.extend(['Sala', 'Kg MP', 'Kg PT', 'Rendimiento %', 'Merma Kg'])
            if 'sala_tipo' in df_mos.columns:
                export_cols.append('sala_tipo')
                export_names.append('Tipo Operación')
            if 'costo_electricidad' in df_mos.columns:
                export_cols.append('costo_electricidad')
                export_names.append('Costo Electricidad $')
            export_cols.extend(['duracion_horas', 'dotacion', 'fecha'])
            export_names.extend(['Horas', 'Dotación', 'Fecha'])
            
            df_export = df_mos[export_cols].copy()
            df_export.columns = export_names
            
            with col_exp1:
                csv = df_export.to_csv(index=False).encode('utf-8')
                st.download_button(
                    "📄 Descargar CSV", 
                    csv, 
                    "produccion_fabricaciones.csv", 
                    "text/csv", 
                    key="download_csv_prod"
                )
            
            with col_exp2:
                # Excel export
                try:
                    excel_buffer = io.BytesIO()
                    df_export.to_excel(excel_buffer, index=False, engine='openpyxl')
                    excel_buffer.seek(0)
                    st.download_button(
                        "📊 Descargar Excel",
                        excel_buffer,
                        "produccion_fabricaciones.xlsx",
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        key="download_excel_prod"
                    )
                except Exception as e:
                    st.warning(f"No se pudo generar Excel: {e}")
            
            with col_exp3:
                # PDF export - temporalmente deshabilitado
                st.info("📕 PDF próximamente")
                st.caption("El informe PDF está en desarrollo. Usa Excel o CSV por ahora.")
    
    else:
        st.info("👆 Selecciona un rango de fechas y haz clic en **Consultar Reportería** para ver los datos consolidados de producción.")
        
        with st.expander("ℹ️ ¿Qué incluye la reportería general?"):
            st.markdown("""
            ### Métricas Disponibles
            
            | Métrica | Descripción |
            |---------|-------------|
            | **Rendimiento %** | Kg PT / Kg MP × 100 (ponderado por volumen) |
            | **Merma** | Kg MP - Kg PT |
            | **Kg/HH** | Productividad: Kg PT / Horas Hombre |
            | **Kg/Hora** | Velocidad: Kg PT / Horas de proceso |
            
            ### Alertas de Rendimiento
            
            - 🟢 **≥ 95%** - Excelente
            - 🟡 **90-95%** - Atención
            - 🔴 **< 90%** - Crítico
            """)

# ============================================
# TAB 2: DETALLE DE OF (código original)
# ============================================
with tab_detalle:
    st.subheader("📋 Detalle de Órdenes de Fabricación")
    
    # --- KPIs rápidos de estado de OFs ---
    with st.spinner("Cargando indicadores..."):
        try:
            kpis = fetch_kpis(username, password)
        except Exception as exc:
            st.warning(f"No fue posible cargar los KPIs: {exc}")
            kpis = {}

    if kpis:
        cols = st.columns(5)
        metrics = [
            ("Total órdenes", kpis.get("total_ordenes", 0), ""),
            ("En progreso", kpis.get("ordenes_progress", 0), ""),
            ("Confirmadas", kpis.get("ordenes_confirmed", 0), ""),
            ("Completadas", kpis.get("ordenes_done", 0), ""),
            ("Por cerrar", kpis.get("ordenes_to_close", 0), ""),
        ]
        render_metrics_row(cols, metrics)

    st.markdown("---")

    # --- Estado de sesión para detalle ---
    if "production_ofs" not in st.session_state:
        st.session_state["production_ofs"] = []
    if "production_current_of" not in st.session_state:
        st.session_state["production_current_of"] = None

    # --- Filtros de búsqueda ---
    with st.expander("🔍 Filtros de búsqueda", expanded=True):
        col1, col2, col3 = st.columns([1, 1, 1])
        start_date = col1.date_input("Desde", value=date.today() - timedelta(days=30), key="prod_filter_start", format="DD/MM/YYYY")
        end_date = col2.date_input("Hasta", value=date.today(), key="prod_filter_end", format="DD/MM/YYYY")
        state_label = col3.selectbox("Estado", options=list(STATE_OPTIONS.keys()), index=0, key="prod_filter_state")
        state_filter = STATE_OPTIONS[state_label]

        btn_col1, btn_col2 = st.columns(2)
        if btn_col1.button("Buscar órdenes", type="primary", key="btn_buscar_ordenes"):
            with st.spinner("Consultando órdenes..."):
                try:
                    results = fetch_ordenes(
                        username,
                        password,
                        start_date.isoformat(),
                        end_date.isoformat(),
                        state_filter
                    )
                    st.session_state["production_ofs"] = results
                    if results:
                        st.success(f"{len(results)} órdenes encontradas")
                    else:
                        st.info("No se encontraron órdenes en el rango solicitado")
                except Exception as error:
                    st.error(f"Error al buscar órdenes: {error}")
        if btn_col2.button("Limpiar resultados", type="secondary", key="btn_limpiar_ordenes"):
            st.session_state["production_ofs"] = []
            st.session_state["production_current_of"] = None
            st.cache_data.clear()
            st.rerun()

    # --- Tabla de órdenes ---
    if st.session_state["production_ofs"]:
        df = pd.DataFrame(st.session_state["production_ofs"])
        st.subheader("📋 Tabla de órdenes encontradas")
        if not df.empty:
            display_cols = [col for col in [
                "name", "state", "date_planned_start", "product_id",
                "product_qty", "qty_produced", "date_start", "date_finished", "user_id"
            ] if col in df.columns]
            df_display = df[display_cols].copy()
            if "product_id" in df_display.columns:
                df_display["producto"] = df_display["product_id"].apply(clean_name)
                df_display.drop(columns=["product_id"], inplace=True)
            if "user_id" in df_display.columns:
                df_display["responsable"] = df_display["user_id"].apply(clean_name)
                df_display.drop(columns=["user_id"], inplace=True)
            for col in ["date_planned_start", "date_start", "date_finished"]:
                if col in df_display.columns:
                    df_display[col] = df_display[col].apply(lambda x: pd.to_datetime(x).strftime("%d/%m/%Y %H:%M") if pd.notna(x) and x else "")
            df_display = df_display.rename(columns={
                "name": "Orden",
                "state": "Estado",
                "date_planned_start": "Fecha Planificada",
                "product_qty": "Cant. Planificada",
                "qty_produced": "Cant. Producida",
                "date_start": "Fecha Inicio",
                "date_finished": "Fecha Fin"
            })
            st.dataframe(df_display, use_container_width=True, height=350)
            csv = df_display.to_csv(index=False)
            st.download_button("📥 Descargar órdenes", csv, "ordenes_produccion.csv", "text/csv")

        st.markdown("---")
        options = {
            f"{of.get('name', 'OF')} — {clean_name(of.get('product_id'))}": of["id"]
            for of in st.session_state["production_ofs"]
        }
        selected_label = st.selectbox("Seleccionar orden para detalle", options=list(options.keys()), key="prod_selector")
        selected_id = options[selected_label]
        if st.button("Cargar detalle", type="primary", key="btn_cargar_detalle"):
            with st.spinner("Cargando la orden..."):
                try:
                    detail = fetch_of_detail(selected_id, username, password)
                    st.session_state["production_current_of"] = detail
                    st.success("Detalle cargado correctamente")
                except Exception as error:
                    st.error(f"No se pudo cargar la orden: {error}")
    else:
        st.info("Busca una orden para comenzar")

    # --- Detalle de OF seleccionada ---
    if st.session_state["production_current_of"]:
        st.markdown("---")
        data_of = st.session_state["production_current_of"]
        of = data_of.get("of", {})
        componentes = data_of.get("componentes", [])
        subproductos = data_of.get("subproductos", [])
        detenciones = data_of.get("detenciones", [])
        consumo = data_of.get("consumo", [])

        # Filtrar componentes y subproductos para cálculos dinámicos
        componentes_fruta = [item for item in componentes if str(item.get('product_category_name', '')).upper().startswith('PRODUCTOS')]
        subproductos_filtrados = [item for item in subproductos if not str(item.get('product_category_name', '')).upper().startswith('PROCESOS')]
        subproductos_sin_merma = [item for item in subproductos_filtrados if 'merma' not in str(item.get('product_category_name', '')).lower()]

        # Calcular KG in y out
        kg_in = sum([item.get('qty_done', 0) or 0 for item in componentes_fruta])
        kg_out = sum([item.get('qty_done', 0) or 0 for item in subproductos_sin_merma])
        merma = sum([item.get('qty_done', 0) or 0 for item in subproductos_filtrados if 'merma' in str(item.get('product_category_name', '')).lower()])

        # Calcular PxQ
        total_pxq_comp = sum([(item.get('x_studio_precio_unitario', 0) or 0) * (item.get('qty_done', 0) or 0) for item in componentes])
        total_pxq_sub = sum([(item.get('x_studio_precio_unitario', 0) or 0) * (item.get('qty_done', 0) or 0) for item in subproductos_filtrados])

        # Calcular rendimiento
        rendimiento_val = (kg_out / kg_in * 100) if kg_in > 0 else 0

        # Detalle de la orden
        st.markdown("### 📋 Detalle de la Orden")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"""
            <div class="info-card">
                <h4>📌 Información General</h4>
                <div class="info-row">
                    <span class="info-label">Responsable</span>
                    <span class="info-value">{clean_name(of.get('user_id'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Cliente</span>
                    <span class="info-value">{clean_name(of.get('x_studio_clientes')) if clean_name(of.get('x_studio_clientes')) != 'False' else 'N/A'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Producto</span>
                    <span class="info-value">{clean_name(of.get('product_id'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Estado</span>
                    <span class="info-value">{get_state_label(of.get('state'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Sala</span>
                    <span class="info-value">{clean_name(of.get('x_studio_sala_de_proceso'))}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col2:
            st.markdown(f"""
            <div class="info-card">
                <h4>⏱️ Tiempos y Dotación</h4>
                <div class="info-row">
                    <span class="info-label">Hora inicio</span>
                    <span class="info-value">{format_fecha(of.get('x_studio_inicio_de_proceso'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Hora término</span>
                    <span class="info-value">{format_fecha(of.get('x_studio_termino_de_proceso'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Horas detención</span>
                    <span class="info-value">{format_num(of.get('x_studio_horas_detencion_totales'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Dotación</span>
                    <span class="info-value">{format_num(of.get('x_studio_dotacin'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">Horas hombre</span>
                    <span class="info-value">{format_num(of.get('x_studio_hh'))}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        col3, col4 = st.columns(2)
        with col3:
            st.markdown(f"""
            <div class="info-card">
                <h4>📈 Eficiencia</h4>
                <div class="info-row">
                    <span class="info-label">HH efectiva</span>
                    <span class="info-value">{format_num(of.get('x_studio_hh_efectiva'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">KG/hora efectiva</span>
                    <span class="info-value">{format_num(of.get('x_studio_kghora_efectiva'))}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">KG/HH efectiva</span>
                    <span class="info-value">{format_num(of.get('x_studio_kghh_efectiva'))}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col4:
            po_asociada = clean_name(of.get('x_studio_po_asociada'))
            po_asociada_display = po_asociada if po_asociada not in ['-', 'False'] else 'N/A'
            st.markdown(f"""
            <div class="info-card">
                <h4>📦 PO Asociada</h4>
                <div class="info-row">
                    <span class="info-label">Para PO</span>
                    <span class="info-value">{'Sí' if of.get('x_studio_odf_es_para_una_po_en_particular') else 'No'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">PO asociada</span>
                    <span class="info-value">{po_asociada_display}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">KG totales PO</span>
                    <span class="info-value">{format_num(of.get('x_studio_kg_totales_po', 0))} kg</span>
                </div>
                <div class="info-row">
                    <span class="info-label">KG consumidos</span>
                    <span class="info-value">{format_num(of.get('x_studio_kg_consumidos_po', 0))} kg</span>
                </div>
                <div class="info-row">
                    <span class="info-label">KG disponibles</span>
                    <span class="info-value">{format_num(of.get('x_studio_kg_disponibles_po', 0))} kg</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # KPIs de Producción
        st.markdown("### 📊 KPIs de Producción")
        kpi_col1, kpi_col2, kpi_col3, kpi_col4, kpi_col5 = st.columns(5)
        kpi_col1.metric("KG Entrada (Fruta)", f"{kg_in:,.0f} kg")
        kpi_col2.metric("KG Salida (Producto)", f"{kg_out:,.0f} kg")
        kpi_col3.metric("Merma", f"{merma:,.0f} kg")
        kpi_col4.metric("Rendimiento", f"{rendimiento_val:.2f}%")
        kpi_col5.metric("Total PxQ", f"${total_pxq_comp + total_pxq_sub:,.2f}")

        # Gauge de rendimiento
        col_gauge, col_pxq = st.columns([2, 1])
        with col_gauge:
            fig_gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=rendimiento_val,
                number={"suffix": "%", "valueformat": ".2f"},
                gauge={
                    "axis": {"range": [0, 120]},
                    "bar": {"color": "#00cc66"},
                    "steps": [
                        {"range": [0, 50], "color": "#ff4444"},
                        {"range": [50, 80], "color": "#ffb347"},
                        {"range": [80, 100], "color": "#00cc66"},
                        {"range": [100, 120], "color": "#00ff88"},
                    ],
                }
            ))
            fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280)
            st.plotly_chart(fig_gauge, use_container_width=True)

        with col_pxq:
            st.markdown(f"""
            <div style='background:#1e1e1e;padding:20px;border-radius:12px;height:260px'>
                <h4 style='margin:0 0 16px 0;color:#00cc66'>Resumen PxQ</h4>
                <p style='margin:8px 0;font-size:1.1em'><span style='color:#888'>Componentes:</span> <b>${total_pxq_comp:,.2f}</b></p>
                <p style='margin:8px 0;font-size:1.1em'><span style='color:#888'>Subproductos:</span> <b>${total_pxq_sub:,.2f}</b></p>
                <hr style='border-color:#333;margin:16px 0'>
                <p style='margin:8px 0;font-size:1.3em'><span style='color:#888'>Total:</span> <b style='color:#00cc66'>${total_pxq_comp + total_pxq_sub:,.2f}</b></p>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Tabs de componentes/subproductos/detenciones/consumo
        tab_comp, tab_sub, tab_det, tab_consumo = st.tabs([
            "Componentes",
            "Subproductos",
            "Detenciones",
            "Consumo"
        ])

        with tab_comp:
            render_component_tab(componentes, "componentes")

        with tab_sub:
            render_component_tab(subproductos_filtrados, "subproductos")

        with tab_det:
            if detenciones:
                df_det = pd.DataFrame([{
                    "Responsable": clean_name(det.get("x_studio_responsable")),
                    "Motivo": clean_name(det.get("x_motivodetencion")),
                    "Hora inicio": format_fecha(det.get("x_horainiciodetencion")),
                    "Hora fin": format_fecha(det.get("x_horafindetencion")),
                    "Horas detención": format_num(det.get("x_studio_horas_de_detencin", 0) or 0),
                } for det in detenciones])
                st.dataframe(df_det, use_container_width=True, height=320)
            else:
                st.info("No hay detenciones registradas")

        with tab_consumo:
            if consumo:
                df_consumo = pd.DataFrame([{
                    "Pallet": item.get("x_name", "N/A"),
                    "Producto": item.get("producto", "Desconocido"),
                    "Lote": item.get("lote", ""),
                    "Tipo": item.get("type", "Desconocido"),
                    "Hora inicio": format_fecha(item.get("x_studio_hora_inicio")),
                    "Hora fin": format_fecha(item.get("x_studio_hora_fin")),
                } for item in consumo])
                st.dataframe(df_consumo, use_container_width=True, height=360)
            else:
                st.info("No hay registros de consumo")
