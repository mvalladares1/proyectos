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


@st.cache_data(ttl=60, show_spinner=False)
def fetch_procesos_cerrados(username: str, password: str, fecha: str,
                            planta: str = None, sala: str = None,
                            fecha_fin: str = None):
    """Obtiene procesos cerrados para un rango de fechas."""
    params = {
        "username": username,
        "password": password,
        "fecha": fecha
    }
    if fecha_fin:
        params["fecha_fin"] = fecha_fin
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
    cols = st.columns(4)
    
    with cols[0]:
        st.metric(
            "📋 Procesos Pendientes",
            stats_activos.get('total_procesos', 0),
            help="Procesos ni cerrados ni cancelados"
        )
    
    with cols[1]:
        st.metric(
            "⏳ KG Pendientes",
            f"{stats_activos.get('kg_pendientes', 0):,.0f}",
            help="Kilos que faltan por producir"
        )
    
    with cols[2]:
        st.metric(
            "✅ Cerrados",
            stats_cerrados.get('total_procesos', 0),
            help="Procesos cerrados en el período"
        )
    
    with cols[3]:
        st.metric(
            "📦 KG Cerrados",
            f"{stats_cerrados.get('kg_producidos', 0):,.0f}",
            help="Kilos de procesos cerrados en el período"
        )


def render_grafico_evolucion(evolucion: list):
    """Renderiza gráfico de evolución: barras apiladas con líneas conectoras."""
    if not evolucion:
        st.info("No hay datos de evolución para mostrar")
        return
    
    fechas = [e['fecha_display'] for e in evolucion]
    creados = [e['procesos_creados'] for e in evolucion]
    cerrados = [e['procesos_cerrados'] for e in evolucion]
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    options = {
        "title": {
            "text": "📊 Evolución de Procesos por Día",
            "textStyle": {"color": label_color, "fontSize": 14}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "legend": {
            "data": ["Creados (barra)", "Cerrados (barra)", "Creados (línea)", "Cerrados (línea)"],
            "top": 30,
            "textStyle": {"color": label_color}
        },
        "xAxis": {
            "type": "category",
            "data": fechas,
            "axisLabel": {"color": "#8892b0", "rotate": 45}
        },
        "yAxis": {
            "type": "value",
            "name": "Procesos",
            "axisLabel": {"color": "#8892b0"}
        },
        "series": [
            {
                "name": "Creados (barra)",
                "type": "bar",
                "stack": "total",
                "data": creados,
                "itemStyle": {"color": "#3498db"},
                "emphasis": {"focus": "series"}
            },
            {
                "name": "Cerrados (barra)",
                "type": "bar",
                "stack": "total",
                "data": cerrados,
                "itemStyle": {"color": "#2ecc71"},
                "emphasis": {"focus": "series"}
            },
            {
                "name": "Creados (línea)",
                "type": "line",
                "data": creados,
                "smooth": False,
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": "#2980b9"},
                "lineStyle": {"width": 2, "type": "solid"}
            },
            {
                "name": "Cerrados (línea)",
                "type": "line",
                "data": cerrados,
                "smooth": False,
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": "#27ae60"},
                "lineStyle": {"width": 2, "type": "solid"}
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "8%", "right": "5%", "bottom": "20%", "containLabel": True}
    }
    
    st_echarts(options=options, height="400px", theme=theme_echarts)


def render_grafico_cerrados_por_dia(procesos_cerrados: list):
    """Renderiza gráfico de barras con procesos cerrados por día."""
    if not procesos_cerrados:
        st.info("No hay procesos cerrados para mostrar")
        return
    
    # Agrupar procesos por fecha de cierre (date_finished)
    cerrados_por_dia = {}
    for p in procesos_cerrados:
        fecha_cierre = p.get('date_finished')
        if fecha_cierre:
            # Extraer solo la fecha (sin hora)
            if 'T' in str(fecha_cierre):
                fecha_dia = str(fecha_cierre).split('T')[0]
            else:
                fecha_dia = str(fecha_cierre)[:10]
            
            if fecha_dia not in cerrados_por_dia:
                cerrados_por_dia[fecha_dia] = {'cantidad': 0, 'kg': 0}
            cerrados_por_dia[fecha_dia]['cantidad'] += 1
            cerrados_por_dia[fecha_dia]['kg'] += p.get('qty_produced', 0) or 0
    
    if not cerrados_por_dia:
        st.info("No hay fechas de cierre disponibles")
        return
    
    # Ordenar por fecha
    fechas_ordenadas = sorted(cerrados_por_dia.keys())
    fechas_display = [f"{f[8:10]}/{f[5:7]}" for f in fechas_ordenadas]  # DD/MM
    cantidades = [cerrados_por_dia[f]['cantidad'] for f in fechas_ordenadas]
    kilos = [cerrados_por_dia[f]['kg'] for f in fechas_ordenadas]
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    options = {
        "title": {
            "text": "✅ Procesos Cerrados por Día",
            "textStyle": {"color": label_color, "fontSize": 14}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>Procesos: {c0}<br/>KG: {c1}"
        },
        "legend": {
            "data": ["Cantidad Procesos", "KG Producidos"],
            "top": 30,
            "textStyle": {"color": label_color}
        },
        "xAxis": {
            "type": "category",
            "data": fechas_display,
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
                "axisLabel": {"color": "#8892b0", "formatter": "{value}"}
            }
        ],
        "series": [
            {
                "name": "Cantidad Procesos",
                "type": "bar",
                "data": cantidades,
                "itemStyle": {"color": "#2ecc71"},
                "emphasis": {"focus": "series"},
                "label": {
                    "show": True,
                    "position": "top",
                    "color": label_color,
                    "fontSize": 11
                }
            },
            {
                "name": "KG Producidos",
                "type": "line",
                "yAxisIndex": 1,
                "data": kilos,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 8,
                "itemStyle": {"color": "#3498db"},
                "lineStyle": {"width": 2}
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "10%", "right": "10%", "bottom": "20%", "containLabel": True}
    }
    
    st_echarts(options=options, height="350px", theme=theme_echarts)


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
            options=["Todas", "RIO FUTURO", "VILKUN", "SAN JOSE"],
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
        # Limpiar datos cargados para forzar recarga
        if "monitor_data_loaded" in st.session_state:
            del st.session_state["monitor_data_loaded"]
        if "monitor_activos" in st.session_state:
            del st.session_state["monitor_activos"]
        if "monitor_cerrados" in st.session_state:
            del st.session_state["monitor_cerrados"]
        if "monitor_evolucion" in st.session_state:
            del st.session_state["monitor_evolucion"]
        st.cache_data.clear()
        st.rerun()
    
    st.markdown("---")
    
    # === CARGAR DATOS (solo cuando se presiona Buscar) ===
    if btn_buscar:
        # Limpiar cache para obtener datos frescos
        st.cache_data.clear()
        
        try:
            with st.spinner("Cargando datos del monitor..."):
                # Procesos activos: TODOS los que no son done ni cancel
                activos_data = fetch_procesos_activos(
                    username, password, 
                    fecha_fin.isoformat(),
                    planta_sel, sala_sel, producto_sel
                )
                
                # Procesos cerrados en el rango de fechas seleccionado
                cerrados_data = fetch_procesos_cerrados(
                    username, password,
                    fecha_inicio.isoformat(),
                    planta_sel, sala_sel,
                    fecha_fin.isoformat()
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
        if not st.session_state.get("monitor_data_loaded", False):
            st.warning("⚠️ Primero debes cargar los datos con el botón 'Buscar'")
        else:
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
    
    # Si no hay datos, mostrar mensaje de instrucciones
    if not st.session_state.get("monitor_data_loaded", False):
        st.info("👆 Selecciona las fechas y filtros, luego presiona **'🔍 Buscar'** para cargar los datos del monitor")
        return
    
    if not activos:
        st.warning("No se encontraron datos para los filtros seleccionados")
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
    
    # Gráfico de procesos cerrados por día
    render_grafico_cerrados_por_dia(cerrados.get("procesos", []))
    
    st.markdown("---")
    
    # === TABLAS DE PROCESOS ===
    sub_tabs = st.tabs(["📋 Procesos Pendientes", "✅ Cerrados"])
    
    with sub_tabs[0]:
        st.markdown(f"**{activos.get('estadisticas', {}).get('total_procesos', 0)} procesos pendientes**")
        render_tabla_compacta(activos.get("procesos", []), "pendientes")
    
    with sub_tabs[1]:
        st.markdown(f"**{cerrados.get('estadisticas', {}).get('total_procesos', 0)} procesos cerrados en el período**")
        render_tabla_compacta(cerrados.get("procesos", []), "cerrados")
