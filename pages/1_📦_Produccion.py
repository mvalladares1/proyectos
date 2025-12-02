"""
Dashboard de Producción - Órdenes de Fabricación
"""
from datetime import date, timedelta
from typing import Dict, List, Optional

import httpx
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from shared.auth import get_credenciales, proteger_pagina

API_URL = st.secrets.get("API_URL", "http://localhost:8000")
STATE_OPTIONS = {
    "Todos": None,
    "Borrador": "draft",
    "Confirmadas": "confirmed",
    "Planificadas": "planned",
    "En Progreso": "progress",
    "Completadas": "done",
    "Canceladas": "cancel",
}


st.set_page_config(
    page_title="Producción - Rio Futuro",
    page_icon="📦",
    layout="wide",
)

if not proteger_pagina():
    st.stop()

username, password = get_credenciales()
if not (username and password):
    st.warning("Inicia sesión para acceder a los datos de producción.")
    st.stop()


def get_state_label(state: Optional[str]) -> str:
    state_map = {
        "draft": "Borrador",
        "confirmed": "Confirmada",
        "planned": "Planificada",
        "progress": "En Progreso",
        "done": "Finalizada",
        "cancel": "Cancelada",
        "to_close": "Por Cerrar",
    }
    return state_map.get(state, state.title() if state else "N/A")


def clean_name(value) -> str:
    if isinstance(value, dict):
        return value.get("name", "N/A")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return value[1]
    return "N/A"


@st.cache_data(ttl=300)
def fetch_ordenes(
    username: str,
    password: str,
    start_date: str,
    end_date: str,
    estado: Optional[str]
) -> List[Dict]:
    params = {
        "username": username,
        "password": password,
        "fecha_desde": start_date,
        "fecha_hasta": end_date,
    }
    if estado:
        params["estado"] = estado

    response = httpx.get(
        f"{API_URL}/api/v1/produccion/ordenes",
        params=params,
        timeout=30.0
    )
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


def build_pie_chart(labels: List[str], values: List[float], title: str) -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        textinfo="percent",
        hovertemplate="<b>%{label}</b><br>%{value:.2f} kg<extra></extra>",
        marker=dict(line=dict(color="#1e1e1e", width=2))
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
        height=400,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="white"),
        margin=dict(l=60, r=20, t=30, b=30),
        title=dict(text=title, x=0.01, xanchor="left")
    )
    return fig


def render_component_tab(items: List[Dict], label: str):
    if not items:
        st.info("No hay datos registrados")
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
        "Cantidad (kg)": item.get("qty_done", 0) or 0,
        "Ubicación origen": clean_name(item.get("location_id")),
        "Pallet": clean_name(item.get("package_id"))
    } for item in filtered])
    st.dataframe(df, use_container_width=True, height=320)

    dist_product = {}
    for item in filtered:
        prod_name = clean_name(item.get("product_id"))
        qty = item.get("qty_done", 0) or 0
        dist_product[prod_name] = dist_product.get(prod_name, 0) + qty

    sorted_product = sorted(dist_product.items(), key=lambda x: x[1], reverse=True)
    product_labels = [label for label, _ in sorted_product]
    product_values = [value for _, value in sorted_product]

    col1, col2 = st.columns([2, 3])
    with col1:
        st.plotly_chart(build_pie_chart(product_labels, product_values, f"Distribución por producto ({label})"), use_container_width=True)
    with col2:
        st.plotly_chart(build_horizontal_bar(product_labels, product_values, f"Cantidad por producto ({label})"), use_container_width=True)


def render_metrics_row(columns, metrics):
    for col, (label, value, suffix) in zip(columns, metrics):
        col.metric(label, f"{value}{suffix if suffix else ''}")


st.sidebar.header("Buscar órdenes de fabricación")
st.sidebar.markdown("Selecciona rango de fechas y estado antes de buscar")
start_date = st.sidebar.date_input("Desde", value=date.today() - timedelta(days=30), key="prod_start")
end_date = st.sidebar.date_input("Hasta", value=date.today(), key="prod_end")
state_label = st.sidebar.selectbox("Estado", options=list(STATE_OPTIONS.keys()), index=0, key="prod_state")
state_filter = STATE_OPTIONS[state_label]

if "production_ofs" not in st.session_state:
    st.session_state["production_ofs"] = []

if "production_current_of" not in st.session_state:
    st.session_state["production_current_of"] = None

if st.sidebar.button("Buscar OFs", type="primary"):
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
                st.info("No se encontraron órdenes en el rango seleccionado")
        except Exception as error:
            st.error(f"Error al buscar órdenes: {error}")

if st.sidebar.button("Limpiar selección", type="secondary"):
    st.session_state["production_ofs"] = []
    st.session_state["production_current_of"] = None
    st.cache_data.clear()
    st.experimental_rerun()

st.sidebar.markdown("---")
if st.session_state["production_ofs"]:
    of_options = {
        f"{of.get('name', 'OF')} — {clean_name(of.get('product_id'))}": of["id"]
        for of in st.session_state["production_ofs"]
    }
    selected_label = st.sidebar.selectbox("Seleccionar OF", options=list(of_options.keys()), key="of_selector")
    selected_id = of_options[selected_label]
    if st.sidebar.button("Cargar OF", type="primary"):
        with st.spinner("Cargando OF..."):
            try:
                detail = fetch_of_detail(selected_id, username, password)
                st.session_state["production_current_of"] = detail
                st.success("Orden cargada exitosamente")
            except Exception as error:
                st.error(f"No se pudo cargar la OF: {error}")
else:
    st.sidebar.info("Busca y carga una OF para ver el detalle completo")

if not st.session_state["production_current_of"]:
    st.info("Selecciona una orden de fabricación en el panel lateral para comenzar")
else:
    st.title("Detalle de la orden")
    data = st.session_state["production_current_of"]
    of = data.get("of", {})
    componentes = data.get("componentes", [])
    subproductos = data.get("subproductos", [])
    detenciones = data.get("detenciones", [])
    consumo = data.get("consumo", [])
    kpis = data.get("kpis", {})

    st.subheader("Resumen general")
    row1 = st.columns(4)
    resumen_metrics = [
        ("Responsable", clean_name(of.get("user_id")), ""),
        ("Cliente", clean_name(of.get("x_studio_clientes")), ""),
        ("Producto", clean_name(of.get("product_id")), ""),
        ("Estado", get_state_label(of.get("state")), ""),
    ]
    render_metrics_row(row1, resumen_metrics)

    st.markdown("---")
    row2 = st.columns(4)
    po_metrics = [
        ("Para PO", "Sí" if of.get("x_studio_odf_es_para_una_po_en_particular") else "No", ""),
        ("Número PO", of.get("x_studio_nmero_de_po_1", "N/A"), ""),
        ("PO asociada", clean_name(of.get("x_studio_po_asociada")), ""),
        ("KG totales PO", f"{of.get('x_studio_kg_totales_po', 0):,.0f}", " kg"),
    ]
    render_metrics_row(row2, po_metrics)

    row3 = st.columns(4)
    po_consumo_metrics = [
        ("KG consumidos", f"{of.get('x_studio_kg_consumidos_po', 0):,.0f}", " kg"),
        ("KG disponibles", f"{of.get('x_studio_kg_disponibles_po', 0):,.0f}", " kg"),
        ("Dotación", str(of.get("x_studio_dotacin", "N/A")), ""),
        ("Sala", clean_name(of.get("x_studio_sala_de_proceso")), ""),
    ]
    render_metrics_row(row3, po_consumo_metrics)

    st.markdown("---")
    st.subheader("KPIs de producción")
    kpi_row = st.columns(4)
    kpi_metrics = [
        ("Producción total", f"{kpis.get('produccion_total_kg', 0):,.0f}", " kg"),
        ("Rendimiento", f"{kpis.get('rendimiento_%', 0):.2f}", "%"),
        ("KG/HH", f"{kpis.get('kg_por_hh', 0):.2f}", ""),
        ("Consumo MP", f"{kpis.get('consumo_mp_kg', 0):,.0f}", " kg"),
    ]
    render_metrics_row(kpi_row, kpi_metrics)

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=kpis.get("rendimiento_%", 0),
        number={"suffix": "%"},
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
    fig_gauge.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=320)
    st.plotly_chart(fig_gauge, use_container_width=True)

    st.markdown("---")
    tab_comp, tab_sub, tab_det, tab_consumo = st.tabs([
        "Componentes",
        "Subproductos",
        "Detenciones",
        "Consumo"
    ])

    with tab_comp:
        render_component_tab(componentes, "componentes")

    with tab_sub:
        render_component_tab(subproductos, "subproductos")

    with tab_det:
        if detenciones:
            df_det = pd.DataFrame([{
                "Responsable": clean_name(det.get("x_studio_responsable")),
                "Motivo": clean_name(det.get("x_motivodetencion")),
                "Hora inicio": det.get("x_horainiciodetencion", "N/A"),
                "Hora fin": det.get("x_horafindetencion", "N/A"),
                "Horas": det.get("x_studio_horas_de_detencin", 0) or 0,
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
                "Hora inicio": item.get("x_studio_hora_inicio", "N/A"),
                "Hora fin": item.get("x_studio_hora_fin", "N/A"),
            } for item in consumo])
            st.dataframe(df_consumo, use_container_width=True, height=360)
        else:
            st.info("No hay registros de consumo")
