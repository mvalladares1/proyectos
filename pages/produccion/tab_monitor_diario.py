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
    """Renderiza KPIs de resumen con diseño mejorado."""
    
    # Estilos CSS para las tarjetas
    st.markdown("""
    <style>
    .kpi-card {
        background: linear-gradient(135deg, #1e3a5f 0%, #0d1b2a 100%);
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        border-left: 4px solid;
        margin-bottom: 10px;
    }
    .kpi-card.pendientes { border-color: #e74c3c; }
    .kpi-card.kg-pend { border-color: #f39c12; }
    .kpi-card.cerrados { border-color: #2ecc71; }
    .kpi-card.kg-cerr { border-color: #3498db; }
    .kpi-value {
        font-size: 2.2em;
        font-weight: bold;
        color: #fff;
        margin: 5px 0;
    }
    .kpi-label {
        font-size: 0.9em;
        color: #8892b0;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    cols = st.columns(4)
    
    total_pendientes = stats_activos.get('total_procesos', 0)
    kg_pendientes = stats_activos.get('kg_pendientes', 0)
    total_cerrados = stats_cerrados.get('total_procesos', 0)
    kg_cerrados = stats_cerrados.get('kg_producidos', 0)
    
    with cols[0]:
        st.markdown(f"""
        <div class="kpi-card pendientes">
            <div class="kpi-label">📋 Procesos Pendientes</div>
            <div class="kpi-value">{total_pendientes}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[1]:
        st.markdown(f"""
        <div class="kpi-card kg-pend">
            <div class="kpi-label">⏳ KG Pendientes</div>
            <div class="kpi-value">{kg_pendientes:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[2]:
        st.markdown(f"""
        <div class="kpi-card cerrados">
            <div class="kpi-label">✅ Procesos Cerrados</div>
            <div class="kpi-value">{total_cerrados}</div>
        </div>
        """, unsafe_allow_html=True)
    
    with cols[3]:
        st.markdown(f"""
        <div class="kpi-card kg-cerr">
            <div class="kpi-label">📦 KG Producidos</div>
            <div class="kpi-value">{kg_cerrados:,.0f}</div>
        </div>
        """, unsafe_allow_html=True)


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


def render_grafico_cerrados_por_dia(evolucion: list):
    """Renderiza gráfico de barras con procesos cerrados por día usando datos de evolución."""
    if not evolucion:
        st.info("No hay datos de procesos cerrados para mostrar")
        return
    
    # Usar directamente los datos de evolución para mantener consistencia
    fechas_display = [e['fecha_display'] for e in evolucion]
    cantidades = [e['procesos_cerrados'] for e in evolucion]
    kilos = [e['kg_producidos'] for e in evolucion]
    
    # Verificar que hay al menos un cierre
    if sum(cantidades) == 0:
        st.info("No hay procesos cerrados en el período seleccionado")
        return
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    options = {
        "title": {
            "text": "✅ Procesos Cerrados por Día",
            "textStyle": {"color": label_color, "fontSize": 14}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
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


def render_grafico_pendientes_por_planta(procesos: list):
    """Renderiza gráfico de barras con procesos pendientes agrupados por planta."""
    if not procesos:
        st.info("No hay datos de procesos pendientes para mostrar")
        return
    
    # Contar por planta - mejorar detección
    conteo_planta = {"RIO FUTURO": 0, "VILKUN": 0}
    kg_planta = {"RIO FUTURO": 0, "VILKUN": 0}
    
    for p in procesos:
        sala = (p.get('x_studio_sala_de_proceso', '') or '').upper()
        name = (p.get('name', '') or '').upper()
        origin = (p.get('origin', '') or '').upper()
        workcenter = (p.get('workcenter_id', '') or '')
        if isinstance(workcenter, (list, tuple)):
            workcenter = str(workcenter[1] if len(workcenter) > 1 else workcenter[0]).upper()
        else:
            workcenter = str(workcenter).upper()
        
        # Combinar todos los campos para búsqueda
        texto_busqueda = f"{sala} {name} {origin} {workcenter}"
        
        # Detectar planta - priorizar VILKUN porque tiene menos procesos
        if 'VILKUN' in texto_busqueda or 'VLK' in texto_busqueda or '/VLK/' in name:
            planta = 'VILKUN'
        else:
            # Por defecto es RIO FUTURO (la planta principal)
            planta = 'RIO FUTURO'
        
        conteo_planta[planta] += 1
        kg_prog = p.get('product_qty', 0) or 0
        kg_prod = p.get('qty_produced', 0) or 0
        kg_planta[planta] += max(0, kg_prog - kg_prod)
    
    # Filtrar plantas con datos
    plantas = [p for p in conteo_planta.keys() if conteo_planta[p] > 0]
    cantidades = [conteo_planta[p] for p in plantas]
    kilos = [kg_planta[p] for p in plantas]
    
    if not plantas:
        st.info("No hay procesos pendientes")
        return
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    # Colores por planta
    colores = {
        "RIO FUTURO": "#3498db",
        "VILKUN": "#9b59b6"
    }
    
    options = {
        "title": {
            "text": "📊 Procesos Pendientes por Planta",
            "textStyle": {"color": label_color, "fontSize": 16, "fontWeight": "bold"},
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "legend": {
            "data": ["Procesos", "KG Pendientes"],
            "top": 35,
            "textStyle": {"color": label_color}
        },
        "xAxis": {
            "type": "category",
            "data": plantas,
            "axisLabel": {"color": label_color, "fontSize": 12, "fontWeight": "bold"}
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
                "axisLabel": {"color": "#8892b0"}
            }
        ],
        "series": [
            {
                "name": "Procesos",
                "type": "bar",
                "data": [{"value": cantidades[i], "itemStyle": {"color": colores.get(plantas[i], "#95a5a6")}} for i in range(len(plantas))],
                "barWidth": "50%",
                "label": {
                    "show": True,
                    "position": "top",
                    "color": label_color,
                    "fontSize": 14,
                    "fontWeight": "bold"
                }
            },
            {
                "name": "KG Pendientes",
                "type": "line",
                "yAxisIndex": 1,
                "data": kilos,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 10,
                "itemStyle": {"color": "#f39c12"},
                "lineStyle": {"width": 3}
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "10%", "right": "12%", "bottom": "15%", "top": "80px", "containLabel": True}
    }
    
    st_echarts(options=options, height="320px", theme=theme_echarts)


def render_grafico_pendientes_por_dia(evolucion: list):
    """Renderiza gráfico de procesos pendientes acumulados por día."""
    if not evolucion:
        st.info("No hay datos de evolución para mostrar")
        return
    
    fechas_display = [e['fecha_display'] for e in evolucion]
    
    # Calcular pendientes acumulados: creados - cerrados (acumulado)
    pendientes_acumulados = []
    acumulado = 0
    for e in evolucion:
        creados = e.get('procesos_creados', 0)
        cerrados = e.get('procesos_cerrados', 0)
        # Pendientes del día = lo que se creó y no se cerró
        pendientes_dia = max(0, creados - cerrados)
        pendientes_acumulados.append(pendientes_dia)
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    options = {
        "title": {
            "text": "⏳ Procesos Pendientes por Día",
            "textStyle": {"color": label_color, "fontSize": 16, "fontWeight": "bold"},
            "left": "center"
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "xAxis": {
            "type": "category",
            "data": fechas_display,
            "axisLabel": {"color": "#8892b0", "rotate": 45}
        },
        "yAxis": {
            "type": "value",
            "name": "Procesos",
            "axisLabel": {"color": "#8892b0"},
            "min": 0
        },
        "series": [
            {
                "name": "Pendientes",
                "type": "bar",
                "data": pendientes_acumulados,
                "itemStyle": {"color": "#e74c3c"},
                "label": {
                    "show": True,
                    "position": "top",
                    "color": label_color,
                    "fontSize": 12,
                    "fontWeight": "bold"
                }
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "10%", "right": "5%", "bottom": "20%", "top": "70px", "containLabel": True}
    }
    
    st_echarts(options=options, height="320px", theme=theme_echarts)


def render_tabla_pendientes_por_proceso_planta(procesos: list):
    """Renderiza tabla de procesos pendientes agrupados por tipo de proceso y planta."""
    if not procesos:
        st.info("No hay procesos pendientes para mostrar")
        return
    
    # Agrupar por tipo de proceso y planta
    resumen = {}
    for p in procesos:
        producto = p.get('product_id', {})
        if isinstance(producto, dict):
            tipo_proceso = producto.get('name', 'Sin Producto')
        else:
            tipo_proceso = str(producto) if producto else 'Sin Producto'
        
        # Extraer solo el nombre del proceso (sin código)
        if ']' in tipo_proceso:
            tipo_proceso = tipo_proceso.split(']')[-1].strip()
        
        # Detectar planta - mejorado
        sala = (p.get('x_studio_sala_de_proceso', '') or '').upper()
        name = (p.get('name', '') or '').upper()
        origin = (p.get('origin', '') or '').upper()
        texto_busqueda = f"{sala} {name} {origin}"
        
        if 'VILKUN' in texto_busqueda or 'VLK' in texto_busqueda or '/VLK/' in name:
            planta = 'VILKUN'
        else:
            planta = 'RIO FUTURO'
        
        key = (tipo_proceso, planta)
        if key not in resumen:
            resumen[key] = {'cantidad': 0, 'kg_pendientes': 0}
        
        resumen[key]['cantidad'] += 1
        kg_prog = p.get('product_qty', 0) or 0
        kg_prod = p.get('qty_produced', 0) or 0
        resumen[key]['kg_pendientes'] += (kg_prog - kg_prod)
    
    # Convertir a lista para DataFrame
    data = []
    for (tipo, planta), stats in sorted(resumen.items(), key=lambda x: -x[1]['cantidad']):
        data.append({
            "Tipo de Proceso": tipo[:50],
            "Planta": planta,
            "Cant. Pendientes": stats['cantidad'],
            "KG Pendientes": f"{stats['kg_pendientes']:,.0f}"
        })
    
    if not data:
        st.info("No hay datos para mostrar")
        return
    
    df = pd.DataFrame(data)
    
    st.dataframe(
        df,
        use_container_width=True,
        height=min(400, 50 + len(data) * 35),
        hide_index=True,
        column_config={
            "Tipo de Proceso": st.column_config.TextColumn("Tipo de Proceso", width="large"),
            "Planta": st.column_config.TextColumn("Planta", width="medium"),
            "Cant. Pendientes": st.column_config.NumberColumn("Cant. Pendientes", width="small"),
            "KG Pendientes": st.column_config.TextColumn("KG Pendientes", width="small"),
        }
    )


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
            "Tipo Proceso",
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
    
    # === SECCIÓN 1: GRÁFICOS PRINCIPALES EN 2 COLUMNAS ===
    col_graf1, col_graf2 = st.columns(2)
    
    with col_graf1:
        # Gráfico de procesos pendientes por planta
        render_grafico_pendientes_por_planta(activos.get("procesos", []))
    
    with col_graf2:
        # Gráfico de procesos cerrados por día
        render_grafico_cerrados_por_dia(evolucion.get("evolucion", []))
    
    st.markdown("---")
    
    # === SECCIÓN 2: GRÁFICO DE PENDIENTES POR DÍA ===
    render_grafico_pendientes_por_dia(evolucion.get("evolucion", []))
    
    st.markdown("---")
    
    # === SECCIÓN 3: TABLA RESUMEN ===
    st.markdown("### 📋 Detalle de Procesos Pendientes por Tipo y Planta")
    render_tabla_pendientes_por_proceso_planta(activos.get("procesos", []))
    
    st.markdown("---")
    
    # === SECCIÓN 4: TABLAS DETALLADAS (colapsables) ===
    with st.expander("📊 Ver Evolución de Procesos", expanded=False):
        render_grafico_evolucion(evolucion.get("evolucion", []))
    
    with st.expander(f"📋 Ver Lista de Procesos Pendientes ({activos.get('estadisticas', {}).get('total_procesos', 0)})", expanded=False):
        render_tabla_compacta(activos.get("procesos", []), "pendientes")
    
    with st.expander(f"✅ Ver Lista de Procesos Cerrados ({cerrados.get('estadisticas', {}).get('total_procesos', 0)})", expanded=False):
        render_tabla_compacta(cerrados.get("procesos", []), "cerrados")
