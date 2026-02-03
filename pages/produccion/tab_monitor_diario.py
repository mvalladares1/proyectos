"""
Tab: Monitor Diario de Producción
Vista compacta para monitorear procesos activos, tracking de cierres y evolución.
"""
import streamlit as st
import pandas as pd
import httpx
from datetime import date, timedelta
from streamlit_echarts import st_echarts

from .shared import (
    clean_name, get_state_label, format_fecha, format_num, fmt_numero,
    detectar_planta, API_URL, ESTADOS_MAP
)


# ===================== FUNCIONES DE FETCH =====================

@st.cache_data(ttl=120, show_spinner=False)
def fetch_procesos_activos(username: str, password: str, fecha: str,
                           planta: str = None, sala: str = None, 
                           producto: str = None):
    """Obtiene procesos activos para una fecha."""
    params = {
        "username": username,
        "password": password,
        "fecha": fecha
    }
    if planta and planta != "Todas":
        params["planta"] = planta
    if sala and sala != "Todas":
        params["sala"] = sala
    if producto and producto != "Todos":
        params["producto"] = producto
    
    response = httpx.get(f"{API_URL}/api/v1/produccion/monitor/activos", 
                         params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_procesos_cerrados(username: str, password: str, fecha: str,
                            planta: str = None, sala: str = None):
    """Obtiene procesos cerrados para una fecha."""
    params = {
        "username": username,
        "password": password,
        "fecha": fecha
    }
    if planta and planta != "Todas":
        params["planta"] = planta
    if sala and sala != "Todas":
        params["sala"] = sala
    
    response = httpx.get(f"{API_URL}/api/v1/produccion/monitor/cerrados",
                         params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_evolucion(username: str, password: str, fecha_inicio: str, 
                    fecha_fin: str, planta: str = None, sala: str = None):
    """Obtiene evolución de procesos en rango de fechas."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin
    }
    if planta and planta != "Todas":
        params["planta"] = planta
    if sala and sala != "Todas":
        params["sala"] = sala
    
    response = httpx.get(f"{API_URL}/api/v1/produccion/monitor/evolucion",
                         params=params, timeout=90.0)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_salas_disponibles(username: str, password: str):
    """Obtiene lista de salas disponibles."""
    params = {"username": username, "password": password}
    response = httpx.get(f"{API_URL}/api/v1/produccion/monitor/salas",
                         params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=300, show_spinner=False)
def fetch_productos_disponibles(username: str, password: str):
    """Obtiene lista de productos disponibles."""
    params = {"username": username, "password": password}
    response = httpx.get(f"{API_URL}/api/v1/produccion/monitor/productos",
                         params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


def guardar_snapshot(username: str, password: str, fecha: str, planta: str = None):
    """Guarda un snapshot del estado actual."""
    params = {
        "username": username,
        "password": password,
        "fecha": fecha
    }
    if planta and planta != "Todas":
        params["planta"] = planta
    
    response = httpx.post(f"{API_URL}/api/v1/produccion/monitor/snapshot",
                          params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


def descargar_reporte_pdf(data: dict):
    """Descarga el reporte PDF."""
    response = httpx.post(f"{API_URL}/api/v1/produccion/monitor/report_pdf",
                          json=data, timeout=120.0)
    response.raise_for_status()
    return response.content


# ===================== COMPONENTES DE VISUALIZACIÓN =====================

def render_kpis_resumen(stats_activos: dict, stats_cerrados: dict):
    """Renderiza KPIs de resumen."""
    cols = st.columns(5)
    
    with cols[0]:
        st.metric(
            "🔄 Procesos Activos",
            stats_activos.get('total_procesos', 0),
            help="Procesos ni cerrados ni cancelados"
        )
    
    with cols[1]:
        st.metric(
            "⏳ KG Pendientes",
            f"{stats_activos.get('kg_pendientes', 0):,.0f}",
            help="Kilos por producir"
        )
    
    with cols[2]:
        st.metric(
            "✅ Cerrados Hoy",
            stats_cerrados.get('total_procesos', 0),
            help="Procesos cerrados en la fecha"
        )
    
    with cols[3]:
        st.metric(
            "📦 KG Producidos",
            f"{stats_cerrados.get('kg_producidos', 0):,.0f}",
            help="Kilos producidos hoy"
        )
    
    with cols[4]:
        avance = stats_activos.get('avance_porcentaje', 0)
        st.metric(
            "📈 % Avance",
            f"{avance:.1f}%",
            help="Avance general de producción"
        )


def render_grafico_evolucion(evolucion: list):
    """Renderiza gráfico de evolución creados vs cerrados."""
    if not evolucion:
        st.info("No hay datos de evolución para mostrar")
        return
    
    fechas = [e['fecha_display'] for e in evolucion]
    creados = [e['procesos_creados'] for e in evolucion]
    cerrados = [e['procesos_cerrados'] for e in evolucion]
    kg_producidos = [e['kg_producidos'] for e in evolucion]
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    options = {
        "title": {
            "text": "📊 Evolución de Procesos (Creados vs Cerrados)",
            "textStyle": {"color": label_color, "fontSize": 14}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "cross"}
        },
        "legend": {
            "data": ["Creados", "Cerrados", "KG Producidos"],
            "top": 30,
            "textStyle": {"color": label_color}
        },
        "xAxis": {
            "type": "category",
            "data": fechas,
            "axisLabel": {"color": "#8892b0", "rotate": 45}
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Procesos",
                "position": "left",
                "axisLabel": {"color": "#8892b0"}
            },
            {
                "type": "value",
                "name": "KG",
                "position": "right",
                "axisLabel": {"color": "#8892b0", "formatter": "{value} kg"}
            }
        ],
        "series": [
            {
                "name": "Creados",
                "type": "bar",
                "data": creados,
                "itemStyle": {"color": "#3498db"},
                "barGap": "10%"
            },
            {
                "name": "Cerrados",
                "type": "bar",
                "data": cerrados,
                "itemStyle": {"color": "#2ecc71"}
            },
            {
                "name": "KG Producidos",
                "type": "line",
                "yAxisIndex": 1,
                "data": kg_producidos,
                "smooth": True,
                "itemStyle": {"color": "#e67e22"},
                "lineStyle": {"width": 3}
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "8%", "right": "8%", "bottom": "20%", "containLabel": True}
    }
    
    st_echarts(options=options, height="400px", theme=theme_echarts)


def render_tabla_compacta(procesos: list, tipo: str = "activos"):
    """Renderiza tabla compacta de procesos."""
    if not procesos:
        st.info(f"No hay procesos {tipo} para mostrar")
        return
    
    # Preparar datos para DataFrame
    data = []
    for p in procesos:
        producto = p.get('product_id', {})
        if isinstance(producto, dict):
            prod_name = producto.get('name', 'N/A')
        else:
            prod_name = str(producto)
        
        kg_prog = p.get('product_qty', 0) or 0
        kg_prod = p.get('qty_produced', 0) or 0
        pendiente = kg_prog - kg_prod
        avance = (kg_prod / kg_prog * 100) if kg_prog > 0 else 0
        
        data.append({
            "OF": p.get('name', ''),
            "Producto": prod_name[:40],
            "Sala": p.get('x_studio_sala_de_proceso') or 'Sin Sala',
            "Estado": ESTADOS_MAP.get(p.get('state', ''), p.get('state', '')),
            "KG Prog.": f"{kg_prog:,.0f}",
            "KG Prod.": f"{kg_prod:,.0f}",
            "Pendiente": f"{pendiente:,.0f}",
            "% Avance": f"{avance:.1f}%"
        })
    
    df = pd.DataFrame(data)
    
    # Mostrar tabla con configuración
    st.dataframe(
        df,
        use_container_width=True,
        height=min(400, 50 + len(data) * 35),
        hide_index=True,
        column_config={
            "OF": st.column_config.TextColumn("OF", width="small"),
            "Producto": st.column_config.TextColumn("Producto", width="large"),
            "Sala": st.column_config.TextColumn("Sala", width="medium"),
            "Estado": st.column_config.TextColumn("Estado", width="small"),
            "KG Prog.": st.column_config.TextColumn("KG Prog.", width="small"),
            "KG Prod.": st.column_config.TextColumn("KG Prod.", width="small"),
            "Pendiente": st.column_config.TextColumn("Pendiente", width="small"),
            "% Avance": st.column_config.TextColumn("% Avance", width="small"),
        }
    )


def render_kanban_por_sala(procesos: list, stats_por_sala: dict):
    """Renderiza vista kanban agrupada por sala."""
    if not procesos:
        st.info("No hay procesos para mostrar en vista kanban")
        return
    
    # Agrupar por sala
    salas = {}
    for p in procesos:
        sala = p.get('x_studio_sala_de_proceso') or 'Sin Sala'
        if sala not in salas:
            salas[sala] = []
        salas[sala].append(p)
    
    # Renderizar columnas por sala
    cols = st.columns(min(len(salas), 3))
    
    for idx, (sala, procs) in enumerate(sorted(salas.items())):
        col_idx = idx % 3
        
        with cols[col_idx]:
            # Header de la sala
            sala_stats = stats_por_sala.get(sala, {"cantidad": len(procs), "kg": 0})
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #2d3748 0%, #1a202c 100%); 
                        padding: 10px; border-radius: 10px; margin-bottom: 10px;
                        border-left: 4px solid #3498db;">
                <h5 style="margin: 0; color: #fff;">📍 {sala}</h5>
                <small style="color: #8892b0;">{sala_stats['cantidad']} procesos | {sala_stats['kg']:,.0f} kg</small>
            </div>
            """, unsafe_allow_html=True)
            
            # Cards de procesos
            for p in procs[:5]:  # Limitar a 5 por sala
                producto = p.get('product_id', {})
                if isinstance(producto, dict):
                    prod_name = producto.get('name', 'N/A')[:25]
                else:
                    prod_name = str(producto)[:25]
                
                kg_prog = p.get('product_qty', 0) or 0
                kg_prod = p.get('qty_produced', 0) or 0
                avance = (kg_prod / kg_prog * 100) if kg_prog > 0 else 0
                
                estado_color = "#3498db" if p.get('state') == 'progress' else "#f1c40f"
                
                st.markdown(f"""
                <div style="background: rgba(255,255,255,0.03); padding: 8px; 
                            border-radius: 8px; margin-bottom: 6px;
                            border-left: 3px solid {estado_color};">
                    <div style="font-weight: bold; color: #fff; font-size: 0.9em;">
                        {p.get('name', '')}
                    </div>
                    <div style="color: #8892b0; font-size: 0.8em;">{prod_name}</div>
                    <div style="display: flex; justify-content: space-between; 
                                font-size: 0.75em; color: #a0aec0; margin-top: 4px;">
                        <span>{kg_prod:,.0f}/{kg_prog:,.0f} kg</span>
                        <span style="color: {'#2ecc71' if avance > 80 else '#e74c3c'};">
                            {avance:.0f}%
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            if len(procs) > 5:
                st.caption(f"... y {len(procs) - 5} más")


# ===================== RENDER PRINCIPAL =====================

@st.fragment
def render(username: str, password: str):
    """Renderiza el contenido del sub-tab Monitor Diario."""
    
    st.markdown("### 📊 Monitor Diario de Producción")
    st.caption("Seguimiento en tiempo real de procesos activos, cierres y evolución")
    
    # === FILTROS ===
    st.markdown("##### 🔍 Filtros")
    
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])
    
    with col1:
        fecha_inicio = st.date_input(
            "Desde", 
            value=date.today() - timedelta(days=7),
            key="monitor_fecha_inicio",
            format="DD/MM/YYYY"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "Hasta",
            value=date.today(),
            key="monitor_fecha_fin",
            format="DD/MM/YYYY"
        )
    
    with col3:
        planta_sel = st.selectbox(
            "Planta",
            options=["Todas", "RIO FUTURO", "VILKUN"],
            index=0,
            key="monitor_planta"
        )
    
    with col4:
        # Cargar salas disponibles
        try:
            salas_list = fetch_salas_disponibles(username, password)
            salas_options = ["Todas"] + salas_list
        except:
            salas_options = ["Todas"]
        
        sala_sel = st.selectbox(
            "Sala",
            options=salas_options,
            index=0,
            key="monitor_sala"
        )
    
    with col5:
        # Cargar productos disponibles
        try:
            productos_list = fetch_productos_disponibles(username, password)
            productos_options = ["Todos"] + productos_list[:50]  # Limitar
        except:
            productos_options = ["Todos"]
        
        producto_sel = st.selectbox(
            "Producto",
            options=productos_options,
            index=0,
            key="monitor_producto"
        )
    
    # Botones de acción
    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
    
    with btn_col1:
        btn_buscar = st.button("🔍 Buscar", type="primary", key="btn_monitor_buscar")
    
    with btn_col2:
        btn_snapshot = st.button("📸 Guardar Snapshot", key="btn_monitor_snapshot")
    
    with btn_col3:
        btn_refresh = st.button("🔄 Refrescar", key="btn_monitor_refresh")
    
    with btn_col4:
        btn_pdf = st.button("📄 Descargar PDF", key="btn_monitor_pdf")
    
    if btn_refresh:
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    if btn_buscar or "monitor_data_loaded" not in st.session_state:
        try:
            with st.spinner("Cargando datos del monitor..."):
                # Procesos activos (del día de hoy)
                activos_data = fetch_procesos_activos(
                    username, password, 
                    fecha_fin.isoformat(),
                    planta_sel, sala_sel, producto_sel
                )
                
                # Procesos cerrados del día
                cerrados_data = fetch_procesos_cerrados(
                    username, password,
                    fecha_fin.isoformat(),
                    planta_sel, sala_sel
                )
                
                # Evolución en el rango
                evolucion_data = fetch_evolucion(
                    username, password,
                    fecha_inicio.isoformat(),
                    fecha_fin.isoformat(),
                    planta_sel, sala_sel
                )
                
                st.session_state["monitor_activos"] = activos_data
                st.session_state["monitor_cerrados"] = cerrados_data
                st.session_state["monitor_evolucion"] = evolucion_data
                st.session_state["monitor_data_loaded"] = True
                
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")
            return
    
    # === GUARDAR SNAPSHOT ===
    if btn_snapshot:
        try:
            result = guardar_snapshot(
                username, password,
                fecha_fin.isoformat(),
                planta_sel
            )
            st.success(f"✅ Snapshot guardado: {result.get('filename', '')}")
        except Exception as e:
            st.error(f"Error al guardar snapshot: {str(e)}")
    
    # === DESCARGAR PDF ===
    if btn_pdf:
        try:
            activos = st.session_state.get("monitor_activos", {})
            cerrados = st.session_state.get("monitor_cerrados", {})
            evolucion = st.session_state.get("monitor_evolucion", {})
            
            pdf_data = {
                "fecha_inicio": fecha_inicio.isoformat(),
                "fecha_fin": fecha_fin.isoformat(),
                "planta": planta_sel,
                "sala": sala_sel,
                "procesos_pendientes": activos.get("procesos", []),
                "procesos_cerrados": cerrados.get("procesos", []),
                "evolucion": evolucion.get("evolucion", []),
                "totales": evolucion.get("totales", {})
            }
            
            pdf_bytes = descargar_reporte_pdf(pdf_data)
            
            st.download_button(
                label="⬇️ Descargar Reporte PDF",
                data=pdf_bytes,
                file_name=f"Monitor_Produccion_{fecha_fin.isoformat()}.pdf",
                mime="application/pdf"
            )
        except Exception as e:
            st.error(f"Error al generar PDF: {str(e)}")
    
    # === MOSTRAR DATOS ===
    activos = st.session_state.get("monitor_activos", {})
    cerrados = st.session_state.get("monitor_cerrados", {})
    evolucion = st.session_state.get("monitor_evolucion", {})
    
    if not activos:
        st.info("Presiona 'Buscar' para cargar los datos del monitor")
        return
    
    # KPIs de resumen
    render_kpis_resumen(
        activos.get("estadisticas", {}),
        cerrados.get("estadisticas", {})
    )
    
    st.markdown("---")
    
    # Gráfico de evolución
    render_grafico_evolucion(evolucion.get("evolucion", []))
    
    st.markdown("---")
    
    # === VISTAS DE PROCESOS ===
    vista_tabs = st.tabs(["📋 Vista Tabla", "📊 Vista Kanban"])
    
    with vista_tabs[0]:
        # Tabs internos para activos/cerrados
        sub_tabs = st.tabs(["🔄 Procesos Activos", "✅ Cerrados Hoy"])
        
        with sub_tabs[0]:
            st.markdown(f"**{activos.get('estadisticas', {}).get('total_procesos', 0)} procesos activos**")
            render_tabla_compacta(activos.get("procesos", []), "activos")
        
        with sub_tabs[1]:
            st.markdown(f"**{cerrados.get('estadisticas', {}).get('total_procesos', 0)} procesos cerrados hoy**")
            render_tabla_compacta(cerrados.get("procesos", []), "cerrados")
    
    with vista_tabs[1]:
        st.markdown("##### Procesos Activos por Sala")
        render_kanban_por_sala(
            activos.get("procesos", []),
            activos.get("estadisticas", {}).get("por_sala", {})
        )
    
    # === TOTALES DEL PERÍODO ===
    st.markdown("---")
    st.markdown("##### 📊 Totales del Período")
    
    totales = evolucion.get("totales", {})
    tot_cols = st.columns(4)
    
    with tot_cols[0]:
        st.metric("Total Creados", totales.get("total_creados", 0))
    with tot_cols[1]:
        st.metric("Total Cerrados", totales.get("total_cerrados", 0))
    with tot_cols[2]:
        st.metric("KG Programados", f"{totales.get('total_kg_programados', 0):,.0f}")
    with tot_cols[3]:
        st.metric("KG Producidos", f"{totales.get('total_kg_producidos', 0):,.0f}")
