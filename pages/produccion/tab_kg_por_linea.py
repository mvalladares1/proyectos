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
    """Renderiza tarjetas visuales detalladas para cada proceso de la sala."""
    
    if not procesos:
        return
    
    # Ordenar por hora de inicio
    procesos_ordenados = sorted(procesos, key=lambda x: x['inicio_dt'] or datetime.min)
    
    # Estilos CSS para las tarjetas
    st.markdown("""
    <style>
    .proceso-card {
        background: linear-gradient(145deg, #1e2a3a 0%, #152238 100%);
        border-radius: 12px;
        padding: 20px;
        margin: 15px 0;
        border-left: 5px solid;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    .proceso-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 15px;
        padding-bottom: 12px;
        border-bottom: 1px solid #333;
    }
    .proceso-title {
        font-size: 16px;
        font-weight: bold;
        color: #00d4ff;
    }
    .kg-hora-badge {
        font-size: 28px;
        font-weight: bold;
        padding: 5px 15px;
        border-radius: 8px;
    }
    .proceso-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 15px;
        margin-top: 10px;
    }
    .proceso-stat {
        background: rgba(0,0,0,0.2);
        padding: 12px;
        border-radius: 8px;
        text-align: center;
    }
    .stat-label {
        font-size: 11px;
        color: #888;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .stat-value {
        font-size: 20px;
        font-weight: bold;
        color: #fff;
        margin-top: 4px;
    }
    .stat-unit {
        font-size: 12px;
        color: #666;
    }
    .producto-row {
        background: rgba(0,212,255,0.1);
        padding: 10px 15px;
        border-radius: 8px;
        margin-top: 12px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .horario-badge {
        background: rgba(255,255,255,0.1);
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 13px;
        color: #aaa;
    }
    @media (max-width: 768px) {
        .proceso-grid {
            grid-template-columns: repeat(2, 1fr);
        }
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Renderizar cada proceso como tarjeta detallada
    for i, p in enumerate(procesos_ordenados):
        kg = p['kg_hora']
        
        # Determinar color según rendimiento
        if kg >= 2000:
            border_color = "#4caf50"  # Verde
            bg_badge = "rgba(76, 175, 80, 0.2)"
        elif kg >= 1500:
            border_color = "#8bc34a"  # Verde claro
            bg_badge = "rgba(139, 195, 74, 0.2)"
        elif kg >= 1000:
            border_color = "#ffc107"  # Amarillo
            bg_badge = "rgba(255, 193, 7, 0.2)"
        elif kg >= 500:
            border_color = "#ff9800"  # Naranja
            bg_badge = "rgba(255, 152, 0, 0.2)"
        else:
            border_color = "#f44336"  # Rojo
            bg_badge = "rgba(244, 67, 54, 0.2)"
        
        # Datos del proceso
        producto = p.get('producto', '-')
        if len(producto) > 50:
            producto = producto[:47] + "..."
        
        # Calcular horas efectivas (duración - detenciones)
        duracion_str = p.get('duracion', '0:00')
        detenciones = p.get('detenciones', 0)
        hh = p.get('hh', 0)
        hh_efectiva = p.get('hh_efectiva', 0)
        
        # Formatear detenciones como horas:minutos
        det_horas = int(detenciones)
        det_mins = int((detenciones - det_horas) * 60)
        detenciones_str = f"{det_horas}:{det_mins:02d}" if detenciones > 0 else "0:00"
        
        st.markdown(f"""
        <div class="proceso-card" style="border-left-color: {border_color};">
            <div class="proceso-header">
                <div>
                    <div class="proceso-title">📋 {p['nombre']}</div>
                    <div class="horario-badge">
                        🕐 {p['hora_inicio']} → {p['hora_fin']} 
                        <span style="color: #00d4ff; margin-left: 8px;">({p['duracion']} hrs)</span>
                    </div>
                </div>
                <div class="kg-hora-badge" style="background: {bg_badge}; color: {border_color};">
                    ⚡ {kg:,.0f} <span style="font-size: 14px;">kg/h</span>
                </div>
            </div>
            
            <div class="producto-row">
                <span style="color: #00d4ff;">📦</span>
                <span style="color: #ddd; font-weight: 500;">{producto}</span>
            </div>
            
            <div class="proceso-grid">
                <div class="proceso-stat">
                    <div class="stat-label">👷 Dotación</div>
                    <div class="stat-value">{int(p['dotacion'])}</div>
                    <div class="stat-unit">personas</div>
                </div>
                <div class="proceso-stat">
                    <div class="stat-label">⚖️ KG Producidos</div>
                    <div class="stat-value">{p['kg_producidos']:,.0f}</div>
                    <div class="stat-unit">kilogramos</div>
                </div>
                <div class="proceso-stat">
                    <div class="stat-label">⏱️ HH Efectiva</div>
                    <div class="stat-value">{hh_efectiva:.1f}</div>
                    <div class="stat-unit">horas-hombre</div>
                </div>
                <div class="proceso-stat">
                    <div class="stat-label">📊 KG/HH</div>
                    <div class="stat-value">{p['kg_hh']:,.0f}</div>
                    <div class="stat-unit">kg por hora-hombre</div>
                </div>
            </div>
            
            <div class="proceso-grid" style="margin-top: 10px;">
                <div class="proceso-stat" style="background: rgba(244,67,54,0.1);">
                    <div class="stat-label">⏸️ Detenciones</div>
                    <div class="stat-value" style="color: {'#f44336' if detenciones > 0 else '#4caf50'};">{detenciones_str}</div>
                    <div class="stat-unit">horas</div>
                </div>
                <div class="proceso-stat" style="background: rgba(33,150,243,0.1);">
                    <div class="stat-label">🕐 HH Total</div>
                    <div class="stat-value" style="color: #2196f3;">{hh:.1f}</div>
                    <div class="stat-unit">horas-hombre</div>
                </div>
                <div class="proceso-stat" style="background: rgba(156,39,176,0.1);">
                    <div class="stat-label">📈 Rendimiento</div>
                    <div class="stat-value" style="color: #9c27b0;">{p.get('rendimiento', 0):.1f}%</div>
                    <div class="stat-unit">producción</div>
                </div>
                <div class="proceso-stat" style="background: rgba(0,150,136,0.1);">
                    <div class="stat-label">🏭 Sala</div>
                    <div class="stat-value" style="color: #009688; font-size: 14px;">{sala[:15]}</div>
                    <div class="stat-unit">línea</div>
                </div>
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
                'hh': mo.get('hh', 0) or 0,
                'hh_efectiva': mo.get('hh_efectiva', 0) or 0,
                'detenciones': mo.get('detenciones', 0) or 0,
                'rendimiento': mo.get('rendimiento', 0) or 0,
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
