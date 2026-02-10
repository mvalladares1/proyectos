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
                            fecha_fin: str = None, producto: str = None):
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
    if producto and producto != "Todos":
        params["producto"] = producto
    
    response = httpx.get(f"{API_URL}/api/v1/produccion/monitor/cerrados",
                         params=params, timeout=60.0)
    response.raise_for_status()
    return response.json()


@st.cache_data(ttl=120, show_spinner=False)
def fetch_evolucion(username: str, password: str, fecha_inicio: str, 
                    fecha_fin: str, planta: str = None, sala: str = None,
                    producto: str = None):
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
    if producto and producto != "Todos":
        params["producto"] = producto
    
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
        st.info("🔍 No hay datos de procesos cerrados para mostrar")
        return
    
    fechas_display = [e['fecha_display'] for e in evolucion]
    cantidades = [e['procesos_cerrados'] for e in evolucion]
    kilos = [round(e['kg_producidos'], 0) for e in evolucion]
    
    if sum(cantidades) == 0:
        st.info("📭 No hay procesos cerrados en el período seleccionado")
        return
    
    # Totales para mostrar en leyenda
    total_procesos = sum(cantidades)
    total_kg = sum(kilos)
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(50,50,50,0.95)",
            "borderColor": "#666",
            "textStyle": {"color": "#fff"}
        },
        "legend": {
            "data": [f"✅ Procesos Cerrados ({total_procesos})", f"📦 KG Producidos ({total_kg:,.0f})"],
            "top": 5,
            "textStyle": {"color": label_color, "fontSize": 12}
        },
        "xAxis": {
            "type": "category",
            "data": fechas_display,
            "axisLabel": {"color": label_color, "rotate": 0, "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#666"}}
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Procesos",
                "nameTextStyle": {"color": "#00E676", "fontSize": 11},
                "position": "left",
                "axisLabel": {"color": "#00E676", "fontSize": 11},
                "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.1)"}}
            },
            {
                "type": "value",
                "name": "Kilos",
                "nameTextStyle": {"color": "#64B5F6", "fontSize": 11},
                "position": "right",
                "axisLabel": {"color": "#64B5F6", "fontSize": 11},
                "splitLine": {"show": False}
            }
        ],
        "series": [
            {
                "name": f"✅ Procesos Cerrados ({total_procesos})",
                "type": "bar",
                "data": cantidades,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#00E676"},
                            {"offset": 1, "color": "#00C853"}
                        ]
                    },
                    "borderRadius": [6, 6, 0, 0]
                },
                "emphasis": {"focus": "series"},
                "label": {
                    "show": True,
                    "position": "top",
                    "color": label_color,
                    "fontSize": 12,
                    "fontWeight": "bold"
                }
            },
            {
                "name": f"📦 KG Producidos ({total_kg:,.0f})",
                "type": "line",
                "yAxisIndex": 1,
                "data": kilos,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 10,
                "itemStyle": {"color": "#64B5F6", "borderWidth": 2, "borderColor": "#fff"},
                "lineStyle": {"width": 3, "color": "#64B5F6"},
                "areaStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "rgba(100,181,246,0.3)"},
                            {"offset": 1, "color": "rgba(100,181,246,0.05)"}
                        ]
                    }
                }
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "10%", "right": "10%", "bottom": "12%", "top": "55px", "containLabel": True}
    }
    
    st_echarts(options=options, height="320px", theme=theme_echarts)


def render_grafico_pendientes_por_planta(procesos: list):
    """Renderiza gráfico de barras con procesos pendientes agrupados por planta."""
    if not procesos:
        st.info("🔍 No hay procesos pendientes para mostrar")
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
        
        texto_busqueda = f"{sala} {name} {origin} {workcenter}"
        
        if 'VILKUN' in texto_busqueda or 'VLK' in texto_busqueda or '/VLK/' in name:
            planta = 'VILKUN'
        else:
            planta = 'RIO FUTURO'
        
        conteo_planta[planta] += 1
        kg_prog = p.get('product_qty', 0) or 0
        kg_prod = p.get('qty_produced', 0) or 0
        kg_planta[planta] += max(0, kg_prog - kg_prod)
    
    plantas = [p for p in conteo_planta.keys() if conteo_planta[p] > 0]
    cantidades = [conteo_planta[p] for p in plantas]
    kilos = [round(kg_planta[p], 0) for p in plantas]
    
    if not plantas:
        st.info("🔍 No hay procesos pendientes")
        return
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    # Colores más vivos
    colores = {
        "RIO FUTURO": "#00D4FF",  # Cyan brillante
        "VILKUN": "#FF6B9D"       # Rosa vibrante
    }
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(50,50,50,0.95)",
            "borderColor": "#666",
            "textStyle": {"color": "#fff"},
            "formatter": "{b}<br/>📦 <b>{c0}</b> procesos<br/>⚖️ <b>{c1}</b> kg pendientes"
        },
        "legend": {
            "data": ["📦 Procesos Pendientes", "⚖️ KG por Producir"],
            "top": 5,
            "textStyle": {"color": label_color, "fontSize": 12}
        },
        "xAxis": {
            "type": "category",
            "data": plantas,
            "axisLabel": {"color": label_color, "fontSize": 14, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#666"}}
        },
        "yAxis": [
            {
                "type": "value",
                "name": "Procesos",
                "nameTextStyle": {"color": "#00D4FF", "fontSize": 11},
                "position": "left",
                "axisLabel": {"color": "#00D4FF", "fontSize": 11},
                "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.1)"}}
            },
            {
                "type": "value",
                "name": "Kilos",
                "nameTextStyle": {"color": "#FFB347", "fontSize": 11},
                "position": "right",
                "axisLabel": {"color": "#FFB347", "fontSize": 11},
                "splitLine": {"show": False}
            }
        ],
        "series": [
            {
                "name": "📦 Procesos Pendientes",
                "type": "bar",
                "data": [{"value": cantidades[i], "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": colores.get(plantas[i], "#95a5a6")},
                            {"offset": 1, "color": colores.get(plantas[i], "#95a5a6").replace("FF", "99")}
                        ]
                    },
                    "borderRadius": [8, 8, 0, 0]
                }} for i in range(len(plantas))],
                "barWidth": "45%",
                "label": {
                    "show": True,
                    "position": "top",
                    "color": label_color,
                    "fontSize": 18,
                    "fontWeight": "bold",
                    "formatter": "{c}"
                }
            },
            {
                "name": "⚖️ KG por Producir",
                "type": "line",
                "yAxisIndex": 1,
                "data": kilos,
                "smooth": True,
                "symbol": "circle",
                "symbolSize": 12,
                "itemStyle": {"color": "#FFB347", "borderWidth": 2, "borderColor": "#fff"},
                "lineStyle": {"width": 3, "color": "#FFB347"},
                "label": {
                    "show": True,
                    "position": "top",
                    "color": "#FFB347",
                    "fontSize": 11,
                    "fontWeight": "bold",
                    "formatter": "{c} kg"
                }
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "12%", "right": "12%", "bottom": "10%", "top": "60px", "containLabel": True}
    }
    
    st_echarts(options=options, height="320px", theme=theme_echarts)


def render_grafico_pendientes_por_dia(procesos_pendientes: list):
    """Renderiza gráfico de procesos pendientes agrupados por fecha de proceso."""
    if not procesos_pendientes:
        st.info("No hay procesos pendientes para mostrar")
        return
    
    from collections import defaultdict
    from datetime import datetime
    
    # Agrupar procesos pendientes por fecha de PROCESO (no de creación)
    pendientes_por_fecha = defaultdict(lambda: {"RIO FUTURO": 0, "VILKUN": 0})
    
    for p in procesos_pendientes:
        # Usar fecha de inicio de proceso real, fallback a date_planned_start
        fecha_str = (p.get('x_studio_inicio_de_proceso', '') or 
                     p.get('date_planned_start', '') or 
                     p.get('date_start', ''))
        if not fecha_str:
            continue
        
        # Extraer solo la fecha (sin hora)
        try:
            if isinstance(fecha_str, str):
                fecha = fecha_str.split('T')[0] if 'T' in fecha_str else fecha_str.split(' ')[0]
            else:
                fecha = str(fecha_str)[:10]
        except:
            continue
        
        # Detectar planta
        sala = (p.get('x_studio_sala_de_proceso', '') or '').upper()
        name = (p.get('name', '') or '').upper()
        origin = (p.get('origin', '') or '').upper()
        texto_busqueda = f"{sala} {name} {origin}"
        
        if 'VILKUN' in texto_busqueda or 'VLK' in texto_busqueda or '/VLK/' in name:
            planta = 'VILKUN'
        else:
            planta = 'RIO FUTURO'
        
        pendientes_por_fecha[fecha][planta] += 1
    
    if not pendientes_por_fecha:
        st.info("No hay procesos pendientes con fecha válida")
        return
    
    # Ordenar por fecha
    fechas_ordenadas = sorted(pendientes_por_fecha.keys())
    
    # Preparar datos para el gráfico
    fechas_display = []
    datos_rio = []
    datos_vlk = []
    
    for fecha in fechas_ordenadas:
        # Formatear fecha para mostrar (dd/mm)
        try:
            fecha_obj = datetime.strptime(fecha, '%Y-%m-%d')
            fecha_display = fecha_obj.strftime('%d/%m')
        except:
            fecha_display = fecha
        
        fechas_display.append(fecha_display)
        datos_rio.append(pendientes_por_fecha[fecha]["RIO FUTURO"])
        datos_vlk.append(pendientes_por_fecha[fecha]["VILKUN"])
    
    theme_echarts = st.session_state.get('theme_mode', 'Dark').lower()
    label_color = "#ffffff" if theme_echarts == "dark" else "#1a1a1a"
    
    # Totales para mostrar
    total_rio = sum(datos_rio)
    total_vlk = sum(datos_vlk)
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(50,50,50,0.95)",
            "borderColor": "#666",
            "textStyle": {"color": "#fff"}
        },
        "xAxis": {
            "type": "category",
            "data": fechas_display,
            "axisLabel": {"color": label_color, "rotate": 0, "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#666"}}
        },
        "yAxis": {
            "type": "value",
            "name": "Cantidad",
            "nameTextStyle": {"color": label_color, "fontSize": 11},
            "axisLabel": {"color": label_color, "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "rgba(255,255,255,0.1)"}},
            "min": 0
        },
        "legend": {
            "data": [f"🔵 RIO FUTURO ({total_rio})", f"🟣 VILKUN ({total_vlk})"],
            "top": 5,
            "textStyle": {"color": label_color, "fontSize": 12}
        },
        "series": [
            {
                "name": f"🔵 RIO FUTURO ({total_rio})",
                "type": "bar",
                "stack": "total",
                "data": datos_rio,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#00D4FF"},
                            {"offset": 1, "color": "#0099CC"}
                        ]
                    },
                    "borderRadius": [0, 0, 0, 0]
                },
                "label": {
                    "show": True,
                    "position": "inside",
                    "color": "#ffffff",
                    "fontSize": 10,
                    "fontWeight": "bold",
                    "formatter": "{c}"
                }
            },
            {
                "name": f"🟣 VILKUN ({total_vlk})",
                "type": "bar",
                "stack": "total",
                "data": datos_vlk,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#FF6B9D"},
                            {"offset": 1, "color": "#CC5580"}
                        ]
                    },
                    "borderRadius": [4, 4, 0, 0]
                },
                "label": {
                    "show": True,
                    "position": "inside",
                    "color": "#ffffff",
                    "fontSize": 10,
                    "fontWeight": "bold",
                    "formatter": "{c}"
                }
            }
        ],
        "backgroundColor": "rgba(0,0,0,0)",
        "grid": {"left": "8%", "right": "5%", "bottom": "15%", "top": "55px", "containLabel": True}
    }
    
    st_echarts(options=options, height="320px", theme=theme_echarts)


def render_tabla_pendientes_por_proceso_planta(procesos: list):
    """Renderiza tablas de procesos pendientes separadas por planta."""
    if not procesos:
        st.info("No hay procesos pendientes para mostrar")
        return
    
    # Clasificar por planta
    vlk_procesos = []
    rf_procesos = []
    
    for p in procesos:
        sala = (p.get('x_studio_sala_de_proceso', '') or '').upper()
        name = (p.get('name', '') or '').upper()
        origin = (p.get('origin', '') or '').upper()
        texto = f"{sala} {name} {origin}"
        
        if 'VILKUN' in texto or 'VLK' in texto or '/VLK/' in name:
            vlk_procesos.append(p)
        else:
            rf_procesos.append(p)
    
    def _crear_tabla_planta(procs, nombre_planta, emoji):
        """Crea tabla para una planta."""
        resumen = {}
        for p in procs:
            producto = p.get('product_id', {})
            if isinstance(producto, dict):
                tipo_proceso = producto.get('name', 'Sin Producto')
            else:
                tipo_proceso = str(producto) if producto else 'Sin Producto'
            
            # Quitar código [X.X] y mostrar nombre descriptivo
            if ']' in tipo_proceso:
                tipo_proceso = tipo_proceso.split(']')[-1].strip()
            
            if tipo_proceso not in resumen:
                resumen[tipo_proceso] = 0
            resumen[tipo_proceso] += 1
        
        data = []
        for tipo, cant in sorted(resumen.items(), key=lambda x: -x[1]):
            data.append({
                "Proceso": tipo[:60],
                "Cantidad Pendiente": cant
            })
        
        if not data:
            return
        
        st.markdown(f"#### {emoji} {nombre_planta} — {len(procs)} procesos pendientes")
        df = pd.DataFrame(data)
        st.dataframe(
            df,
            use_container_width=True,
            height=min(350, 50 + len(data) * 35),
            hide_index=True,
            column_config={
                "Proceso": st.column_config.TextColumn("Proceso", width="large"),
                "Cantidad Pendiente": st.column_config.NumberColumn("Cantidad Pendiente", width="small"),
            }
        )
    
    # Dos columnas: VILKUN | RIO FUTURO
    col1, col2 = st.columns(2)
    
    with col1:
        _crear_tabla_planta(vlk_procesos, "VILKUN", "🟢")
    
    with col2:
        _crear_tabla_planta(rf_procesos, "RIO FUTURO", "🔵")


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
                    fecha_fin.isoformat(),
                    producto_sel
                )
                
                # Evolución en el rango
                evolucion_data = fetch_evolucion(
                    username, password,
                    fecha_inicio.isoformat(),
                    fecha_fin.isoformat(),
                    planta_sel, sala_sel,
                    producto_sel
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
    
    # === GRÁFICO 1: PROCESOS PENDIENTES POR PLANTA ===
    st.markdown("### 🏭 ¿Cuántos procesos están pendientes en cada planta?")
    st.caption("Compara la cantidad de procesos y kilos pendientes entre **RIO FUTURO** y **VILKUN**")
    render_grafico_pendientes_por_planta(activos.get("procesos", []))
    
    st.markdown("---")
    
    # === GRÁFICO 2: PROCESOS PENDIENTES POR DÍA ===
    st.markdown("### 📅 Procesos Pendientes por Fecha de Proceso")
    st.caption("Muestra cuántos procesos pendientes hay en cada fecha, separados por planta")
    render_grafico_pendientes_por_dia(activos.get("procesos", []))
    
    st.markdown("---")
    
    # === GRÁFICO 3: PROCESOS CERRADOS POR DÍA ===
    st.markdown("### 🎉 ¿Cuántos procesos se completaron por día?")
    st.caption("Cantidad de procesos cerrados y kilos producidos cada día del período seleccionado")
    render_grafico_cerrados_por_dia(evolucion.get("evolucion", []))
    
    st.markdown("---")
    
    # === TABLA RESUMEN ===
    st.markdown("### 📋 Detalle de Procesos Pendientes por Tipo y Planta")
    render_tabla_pendientes_por_proceso_planta(activos.get("procesos", []))
    
    st.markdown("---")
    
    # === TABLAS DETALLADAS (colapsables) ===
    with st.expander(f"📋 Ver Lista de Procesos Pendientes ({activos.get('estadisticas', {}).get('total_procesos', 0)})", expanded=False):
        render_tabla_compacta(activos.get("procesos", []), "pendientes")
    
    with st.expander(f"✅ Ver Lista de Procesos Cerrados ({cerrados.get('estadisticas', {}).get('total_procesos', 0)})", expanded=False):
        render_tabla_compacta(cerrados.get("procesos", []), "cerrados")
