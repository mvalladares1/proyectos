"""
Tab KG por Línea: Rendimiento por sala de proceso con gráficos.
Muestra cada proceso individual con gráficos de barras por sala.
"""
import streamlit as st
import httpx
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict
from streamlit_echarts import st_echarts
from .shared import API_URL


def fetch_datos_produccion(username: str, password: str, fecha_inicio: str, 
                           fecha_fin: str) -> Dict[str, Any]:
    """Obtiene datos de productividad."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "solo_terminadas": False
    }
    
    response = httpx.get(f"{API_URL}/api/v1/rendimiento/dashboard",
                         params=params, timeout=120.0)
    response.raise_for_status()
    return response.json()


def parsear_fecha_hora(fecha_str: str) -> Optional[datetime]:
    """Parsea fecha/hora de diferentes formatos."""
    if not fecha_str:
        return None
    try:
        if 'T' in str(fecha_str):
            return datetime.fromisoformat(str(fecha_str).replace('Z', ''))
        else:
            return datetime.strptime(str(fecha_str)[:19], '%Y-%m-%d %H:%M:%S')
    except:
        return None


def formatear_hora(dt: Optional[datetime]) -> str:
    """Formatea datetime a HH:MM."""
    if not dt:
        return "-"
    return dt.strftime("%H:%M")


def render_grafico_sala(sala: str, procesos: List[Dict], key_suffix: str):
    """Renderiza gráfico de barras horizontales para una sala con detalle de cada proceso."""
    
    if not procesos:
        return
    
    # Ordenar por hora de inicio
    procesos_ordenados = sorted(procesos, key=lambda x: x['inicio_dt'] or datetime.min)
    
    # Preparar datos para el gráfico
    nombres = []
    kg_hora_valores = []
    colores = []
    tooltips_data = []
    
    for p in procesos_ordenados:
        # Etiqueta: Orden + horario
        nombre_orden = p['nombre'][-10:] if len(p['nombre']) > 10 else p['nombre']
        etiqueta = f"{p['hora_inicio']}-{p['hora_fin']} | {nombre_orden}"
        nombres.append(etiqueta)
        kg_hora_valores.append(p['kg_hora'])
        
        # Datos para tooltip
        tooltips_data.append({
            'orden': p['nombre'],
            'producto': p['producto'],
            'inicio': p['hora_inicio'],
            'fin': p['hora_fin'],
            'duracion': p['duracion'],
            'dotacion': p['dotacion'],
            'kg_producidos': p['kg_producidos'],
            'kg_hora': p['kg_hora'],
            'kg_hh': p['kg_hh']
        })
        
        # Color según rendimiento
        kg = p['kg_hora']
        if kg >= 2000:
            colores.append("#4caf50")  # Verde
        elif kg >= 1500:
            colores.append("#8bc34a")  # Verde claro
        elif kg >= 1000:
            colores.append("#ffc107")  # Amarillo
        elif kg >= 500:
            colores.append("#ff9800")  # Naranja
        else:
            colores.append("#f44336")  # Rojo
    
    # Crear datos de serie con colores individuales
    data_series = []
    for i, kg in enumerate(kg_hora_valores):
        data_series.append({
            "value": kg,
            "itemStyle": {"color": colores[i]}
        })
    
    # Calcular altura dinámica
    altura = max(250, len(procesos_ordenados) * 55)
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(30, 40, 60, 0.95)",
            "borderColor": "#555",
            "textStyle": {"color": "#fff"}
        },
        "grid": {
            "left": "3%",
            "right": "18%",
            "top": "10px",
            "bottom": "3%",
            "containLabel": True
        },
        "xAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#aaa", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}},
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "category",
            "data": nombres[::-1],
            "axisLabel": {
                "color": "#ddd", 
                "fontSize": 12,
                "width": 200,
                "overflow": "truncate"
            },
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "series": [{
            "name": "KG/Hora",
            "type": "bar",
            "data": data_series[::-1],
            "barWidth": "65%",
            "label": {
                "show": True,
                "position": "right",
                "formatter": "{c} kg/h",
                "color": "#fff",
                "fontSize": 13,
                "fontWeight": "bold"
            },
            "emphasis": {
                "itemStyle": {
                    "shadowBlur": 10,
                    "shadowColor": "rgba(0, 0, 0, 0.5)"
                }
            }
        }]
    }
    
    st_echarts(options=options, height=f"{altura}px", key=f"grafico_sala_{key_suffix}")
    
    # Mostrar tabla con detalles debajo del gráfico
    st.markdown("##### 📋 Detalle de procesos:")
    
    for i, p in enumerate(procesos_ordenados):
        # Color de fondo según rendimiento
        kg = p['kg_hora']
        if kg >= 2000:
            bg_color = "rgba(76, 175, 80, 0.15)"
            border_color = "#4caf50"
        elif kg >= 1500:
            bg_color = "rgba(139, 195, 74, 0.15)"
            border_color = "#8bc34a"
        elif kg >= 1000:
            bg_color = "rgba(255, 193, 7, 0.15)"
            border_color = "#ffc107"
        elif kg >= 500:
            bg_color = "rgba(255, 152, 0, 0.15)"
            border_color = "#ff9800"
        else:
            bg_color = "rgba(244, 67, 54, 0.15)"
            border_color = "#f44336"
        
        producto_display = p['producto'][:40] + "..." if len(p['producto']) > 40 else p['producto']
        
        st.markdown(f"""
        <div style="background: {bg_color}; border-left: 4px solid {border_color};
                    padding: 12px 15px; margin: 8px 0; border-radius: 0 8px 8px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
                <div>
                    <span style="font-weight: bold; color: #00d4ff; font-size: 14px;">{p['nombre']}</span>
                    <span style="color: #888; margin-left: 10px;">🕐 {p['hora_inicio']} → {p['hora_fin']}</span>
                    <span style="color: #aaa; margin-left: 10px;">({p['duracion']})</span>
                </div>
                <div style="font-size: 20px; font-weight: bold; color: {border_color};">
                    ⚡ {p['kg_hora']:,.0f} kg/h
                </div>
            </div>
            <div style="margin-top: 8px; display: flex; gap: 25px; flex-wrap: wrap; color: #ccc; font-size: 13px;">
                <span>📦 <b>{producto_display}</b></span>
                <span>👷 Dotación: <b>{p['dotacion']}</b></span>
                <span>⚖️ KG Producidos: <b>{p['kg_producidos']:,.0f}</b></span>
                <span>📊 KG/HH: <b>{p['kg_hh']:,.0f}</b></span>
            </div>
        </div>
        """, unsafe_allow_html=True)


def render(username: str = None, password: str = None):
    """Render principal del tab KG por Línea."""
    
    # Obtener credenciales
    if not username:
        username = st.session_state.get("odoo_username", "")
    if not password:
        password = st.session_state.get("odoo_api_key", "")
    
    if not username or not password:
        st.warning("⚠️ Debes iniciar sesión para ver este módulo")
        return
    
    # === HEADER ===
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 25px; border-radius: 15px; margin-bottom: 25px;
                border-left: 5px solid #00d4ff;">
        <h2 style="margin:0; color:#00d4ff;">📊 Rendimiento por Línea de Proceso</h2>
        <p style="margin:5px 0 0 0; color:#aaa; font-size:14px;">
            Visualiza el KG/Hora de cada sala con gráficos por día y orden de producción
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
    col1, col2, col3 = st.columns([1, 1, 1])
    
    with col1:
        fecha_inicio = st.date_input(
            "📅 Desde",
            value=datetime.now().date() - timedelta(days=7),
            key="kg_linea_fecha_inicio"
        )
    
    with col2:
        fecha_fin = st.date_input(
            "📅 Hasta",
            value=datetime.now().date(),
            key="kg_linea_fecha_fin"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_buscar = st.button("🔍 Buscar", type="primary", use_container_width=True)
    
    # === CARGAR DATOS ===
    if btn_buscar or st.session_state.get("kg_linea_data"):
        if btn_buscar:
            with st.spinner("Cargando datos de producción..."):
                try:
                    data = fetch_datos_produccion(
                        username, password,
                        fecha_inicio.isoformat(),
                        fecha_fin.isoformat()
                    )
                    st.session_state["kg_linea_data"] = data
                except Exception as e:
                    st.error(f"Error al cargar datos: {e}")
                    return
        
        data = st.session_state.get("kg_linea_data", {})
        mos = data.get("mos", [])
        
        if not mos:
            st.info("📭 No hay órdenes de producción en el rango seleccionado")
            return
        
        # === PROCESAR Y AGRUPAR POR DÍA Y SALA ===
        por_dia_sala = defaultdict(lambda: defaultdict(list))
        
        for mo in mos:
            inicio_str = mo.get('fecha_inicio') or mo.get('inicio_proceso')
            inicio_dt = parsear_fecha_hora(inicio_str)
            
            if not inicio_dt:
                fecha_str = mo.get('fecha', '')
                if fecha_str:
                    try:
                        inicio_dt = datetime.strptime(fecha_str[:10], '%Y-%m-%d')
                    except:
                        continue
                else:
                    continue
            
            fecha_dia = inicio_dt.strftime("%Y-%m-%d")
            sala = mo.get('sala', '') or mo.get('sala_original', '') or 'Sin Sala'
            
            fin_str = mo.get('fecha_termino') or mo.get('fin_proceso')
            fin_dt = parsear_fecha_hora(fin_str)
            
            kg_hora = mo.get('kg_hora_efectiva') or mo.get('kg_por_hora') or 0
            
            # Calcular duración
            duracion = "-"
            if inicio_dt and fin_dt:
                delta = fin_dt - inicio_dt
                horas = delta.total_seconds() / 3600
                h = int(horas)
                m = int((horas - h) * 60)
                duracion = f"{h}h {m}m"
            
            proceso_info = {
                'nombre': mo.get('mo_name', mo.get('name', '-')),
                'producto': mo.get('product_name', mo.get('producto', '-')),
                'inicio_dt': inicio_dt,
                'fin_dt': fin_dt,
                'hora_inicio': formatear_hora(inicio_dt),
                'hora_fin': formatear_hora(fin_dt),
                'duracion': duracion,
                'kg_hora': round(kg_hora, 0) if kg_hora else 0,
                'kg_hh': round(mo.get('kg_hh_efectiva', 0) or 0, 0),
                'dotacion': mo.get('dotacion', 0) or 0,
                'kg_producidos': round(mo.get('kg_pt', 0) or mo.get('kg_producidos', 0) or 0, 0),
            }
            
            por_dia_sala[fecha_dia][sala].append(proceso_info)
        
        dias_ordenados = sorted(por_dia_sala.keys(), reverse=True)
        
        # === KPIs GENERALES ===
        total_procesos = sum(len(p) for sala in por_dia_sala.values() for p in sala.values())
        total_kg = sum(p['kg_producidos'] for sala in por_dia_sala.values() for procs in sala.values() for p in procs)
        kg_horas_validos = [p['kg_hora'] for sala in por_dia_sala.values() for procs in sala.values() for p in procs if p['kg_hora'] > 0]
        promedio_kg_hora = sum(kg_horas_validos) / len(kg_horas_validos) if kg_horas_validos else 0
        salas_unicas = set(sala for dia in por_dia_sala.values() for sala in dia.keys())
        
        st.markdown("---")
        
        # KPIs en cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{total_procesos}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">ÓRDENES</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{total_kg:,.0f}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">KG PRODUCIDOS</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{promedio_kg_hora:,.0f}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">KG/HORA PROM</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
                        padding: 20px; border-radius: 12px; text-align: center;">
                <div style="font-size: 32px; font-weight: bold; color: white;">{len(salas_unicas)}</div>
                <div style="color: rgba(255,255,255,0.8); font-size: 12px;">LÍNEAS</div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # === LEYENDA DE COLORES ===
        st.markdown("""
        <div style="display: flex; gap: 20px; justify-content: center; margin-bottom: 20px; flex-wrap: wrap;">
            <span style="color: #4caf50;">🟢 Excelente (≥2000)</span>
            <span style="color: #8bc34a;">🟡 Bueno (≥1500)</span>
            <span style="color: #ffc107;">🟠 Regular (≥1000)</span>
            <span style="color: #ff9800;">🟠 Bajo (≥500)</span>
            <span style="color: #f44336;">🔴 Crítico (<500)</span>
        </div>
        """, unsafe_allow_html=True)
        
        # === MOSTRAR POR CADA DÍA ===
        for idx_dia, fecha_dia in enumerate(dias_ordenados):
            salas_del_dia = por_dia_sala[fecha_dia]
            
            # Formatear fecha
            fecha_dt = datetime.strptime(fecha_dia, "%Y-%m-%d")
            dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
            meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 
                     'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
            fecha_display = f"{dias_semana[fecha_dt.weekday()]} {fecha_dt.day} de {meses[fecha_dt.month - 1]}, {fecha_dt.year}"
            
            procesos_dia = sum(len(procs) for procs in salas_del_dia.values())
            kg_dia = sum(p['kg_producidos'] for procs in salas_del_dia.values() for p in procs)
            
            # Header del día
            st.markdown(f"""
            <div style="background: linear-gradient(90deg, #1e3c72 0%, #2a5298 100%);
                        padding: 15px 20px; border-radius: 10px; margin: 25px 0 15px 0;">
                <span style="font-size: 22px; font-weight: bold; color: white;">📅 {fecha_display}</span>
                <span style="float: right; color: #90caf9;">
                    📦 {procesos_dia} órdenes &nbsp;|&nbsp; ⚖️ {kg_dia:,.0f} KG
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Ordenar salas por promedio KG/Hora
            salas_ordenadas = sorted(
                salas_del_dia.items(),
                key=lambda x: sum(p['kg_hora'] for p in x[1]) / len(x[1]) if x[1] else 0,
                reverse=True
            )
            
            # Gráfico comparativo de todas las salas del día
            if len(salas_ordenadas) > 1:
                salas_nombres = []
                salas_promedios = []
                salas_colores = []
                
                for sala_nombre, procs in salas_ordenadas:
                    kg_horas = [p['kg_hora'] for p in procs if p['kg_hora'] > 0]
                    promedio = sum(kg_horas) / len(kg_horas) if kg_horas else 0
                    salas_nombres.append(sala_nombre[:25])
                    salas_promedios.append(round(promedio, 0))
                    
                    if promedio >= 2000:
                        salas_colores.append("#4caf50")
                    elif promedio >= 1500:
                        salas_colores.append("#8bc34a")
                    elif promedio >= 1000:
                        salas_colores.append("#ffc107")
                    else:
                        salas_colores.append("#ff9800")
                
                data_comparativo = [{"value": v, "itemStyle": {"color": c}} for v, c in zip(salas_promedios, salas_colores)]
                
                options_comparativo = {
                    "title": {
                        "text": "📊 Comparativa de Líneas (Promedio KG/Hora)",
                        "left": "center",
                        "textStyle": {"color": "#fff", "fontSize": 14}
                    },
                    "tooltip": {"trigger": "axis"},
                    "grid": {
                        "left": "3%",
                        "right": "10%",
                        "top": "50px",
                        "bottom": "3%",
                        "containLabel": True
                    },
                    "xAxis": {
                        "type": "category",
                        "data": salas_nombres,
                        "axisLabel": {"color": "#aaa", "rotate": 15, "fontSize": 10}
                    },
                    "yAxis": {
                        "type": "value",
                        "name": "KG/Hora",
                        "axisLabel": {"color": "#aaa"},
                        "splitLine": {"lineStyle": {"color": "#333"}}
                    },
                    "series": [{
                        "type": "bar",
                        "data": data_comparativo,
                        "barWidth": "50%",
                        "label": {
                            "show": True,
                            "position": "top",
                            "color": "#fff",
                            "fontSize": 11
                        }
                    }]
                }
                
                st_echarts(options=options_comparativo, height="280px", key=f"comparativo_dia_{idx_dia}")
            
            # === DETALLE POR CADA SALA ===
            for idx_sala, (sala, procesos) in enumerate(salas_ordenadas):
                procesos_ordenados = sorted(procesos, key=lambda x: x['inicio_dt'] or datetime.min)
                
                kg_horas_sala = [p['kg_hora'] for p in procesos_ordenados if p['kg_hora'] > 0]
                promedio_sala = sum(kg_horas_sala) / len(kg_horas_sala) if kg_horas_sala else 0
                total_kg_sala = sum(p['kg_producidos'] for p in procesos_ordenados)
                
                # Emoji según rendimiento
                if promedio_sala >= 2000:
                    emoji = "🟢"
                elif promedio_sala >= 1500:
                    emoji = "🟡"
                elif promedio_sala >= 1000:
                    emoji = "🟠"
                else:
                    emoji = "🔴"
                
                with st.expander(f"{emoji} **{sala}** — Promedio: **{promedio_sala:,.0f} KG/Hora** — {len(procesos_ordenados)} procesos — {total_kg_sala:,.0f} KG", expanded=False):
                    
                    # Gráfico de barras de la sala
                    render_grafico_sala(sala, procesos_ordenados, f"{idx_dia}_{idx_sala}")
                    
                    # Mini resumen
                    st.markdown("---")
                    col_r1, col_r2, col_r3, col_r4 = st.columns(4)
                    with col_r1:
                        st.metric("📦 Procesos", len(procesos_ordenados))
                    with col_r2:
                        st.metric("⚖️ KG Total", f"{total_kg_sala:,.0f}")
                    with col_r3:
                        dotacion_prom = sum(p['dotacion'] for p in procesos_ordenados) / len(procesos_ordenados) if procesos_ordenados else 0
                        st.metric("👷 Dotación Prom", f"{dotacion_prom:.0f}")
                    with col_r4:
                        st.metric("⚡ KG/Hora Prom", f"{promedio_sala:,.0f}")
            
            st.markdown("<br>", unsafe_allow_html=True)
