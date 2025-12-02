"""
Dashboard de Producción - Órdenes de Fabricación detalladas
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
    if not state:
        return "N/A"
    return state_map.get(state, state.title())


def clean_name(value) -> str:
    if isinstance(value, dict):
        return value.get("name", "N/A")
    if isinstance(value, (list, tuple)) and len(value) == 2:
        return value[1]
    return "N/A"


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
        text = f"{value}{suffix if suffix else ''}"
        col.metric(label, text)


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


@st.cache_data(ttl=300)
def fetch_kpis(username: str, password: str) -> Dict:
    response = httpx.get(
        f"{API_URL}/api/v1/produccion/kpis",
        params={"username": username, "password": password},
        timeout=30.0
    )
    response.raise_for_status()
    return response.json()


st.title("📦 Dashboard de Producción")
st.markdown("---")

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

if "production_ofs" not in st.session_state:
    st.session_state["production_ofs"] = []
if "production_current_of" not in st.session_state:
    st.session_state["production_current_of"] = None

with st.expander("🔍 Filtros de búsqueda", expanded=True):
    col1, col2, col3 = st.columns([1, 1, 1])
    start_date = col1.date_input("Desde", value=date.today() - timedelta(days=30), key="prod_filter_start")
    end_date = col2.date_input("Hasta", value=date.today(), key="prod_filter_end")
    state_label = col3.selectbox("Estado", options=list(STATE_OPTIONS.keys()), index=0, key="prod_filter_state")
    state_filter = STATE_OPTIONS[state_label]

    btn_col1, btn_col2 = st.columns(2)
    if btn_col1.button("Buscar órdenes", type="primary"):
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
    if btn_col2.button("Limpiar resultados", type="secondary"):
        st.session_state["production_ofs"] = []
        st.session_state["production_current_of"] = None
        st.cache_data.clear()
        st.experimental_rerun()

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
    if st.button("Cargar detalle", type="primary"):
        with st.spinner("Cargando la orden..."):
            try:
                detail = fetch_of_detail(selected_id, username, password)
                st.session_state["production_current_of"] = detail
                st.success("Detalle cargado correctamente")
            except Exception as error:
                st.error(f"No se pudo cargar la orden: {error}")
else:
    st.info("Busca una orden para comenzar")

if not st.session_state["production_current_of"]:
    st.stop()

st.markdown("---")
data = st.session_state["production_current_of"]
of = data.get("of", {})
componentes = data.get("componentes", [])
subproductos = data.get("subproductos", [])
detenciones = data.get("detenciones", [])
consumo = data.get("consumo", [])
kpis_detail = data.get("kpis", {})

st.subheader("Detalle de la orden")
row1 = st.columns(4)
render_metrics_row(row1, [
    ("Responsable", clean_name(of.get("user_id")), ""),
    ("Cliente", clean_name(of.get("x_studio_clientes")), ""),
    ("Producto", clean_name(of.get("product_id")), ""),
    ("Estado", get_state_label(of.get("state")), ""),
])

st.markdown("---")
row2 = st.columns(4)
render_metrics_row(row2, [
    ("Para PO", "Sí" if of.get("x_studio_odf_es_para_una_po_en_particular") else "No", ""),
    ("PO asociada", clean_name(of.get("x_studio_po_asociada")), ""),
    ("KG totales PO", f"{of.get('x_studio_kg_totales_po', 0):,.0f}", " kg"),
    ("Sala", clean_name(of.get("x_studio_sala_de_proceso")), ""),
])

row3 = st.columns(4)
render_metrics_row(row3, [
    ("KG consumidos", f"{of.get('x_studio_kg_consumidos_po', 0):,.0f}", " kg"),
    ("KG disponibles", f"{of.get('x_studio_kg_disponibles_po', 0):,.0f}", " kg"),
    ("Dotación", str(of.get("x_studio_dotacin", "N/A")), ""),
    ("Usuario", clean_name(of.get("user_id")), ""),
])

st.markdown("---")
st.subheader("KPIs de producción")
kpi_cols = st.columns(4)
render_metrics_row(kpi_cols, [
    ("Producción total", f"{kpis_detail.get('produccion_total_kg', 0):,.0f}", " kg"),
    ("Rendimiento", f"{kpis_detail.get('rendimiento_%', 0):.2f}", "%"),
    ("KG/HH", f"{kpis_detail.get('kg_por_hh', 0):.2f}", ""),
    ("Consumo MP", f"{kpis_detail.get('consumo_mp_kg', 0):,.0f}", " kg"),
])

fig_gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=kpis_detail.get("rendimiento_%", 0),
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
