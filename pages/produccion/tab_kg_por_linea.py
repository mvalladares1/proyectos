"""
Tab KG por Línea: Rendimiento por sala de proceso.
Muestra cada proceso individual con métricas detalladas usando componentes nativos.
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
        fecha_str = str(fecha_str).strip()
        if 'T' in fecha_str:
            return datetime.fromisoformat(fecha_str.replace('Z', ''))
        elif len(fecha_str) >= 19:
            return datetime.strptime(fecha_str[:19], '%Y-%m-%d %H:%M:%S')
        elif len(fecha_str) >= 16:
            return datetime.strptime(fecha_str[:16], '%Y-%m-%d %H:%M')
        elif len(fecha_str) >= 10:
            return datetime.strptime(fecha_str[:10], '%Y-%m-%d')
        return None
    except:
        return None


def formatear_hora(dt: Optional[datetime]) -> str:
    """Formatea datetime a HH:MM."""
    if not dt:
        return "-"
    return dt.strftime("%H:%M")


def render_linea_proceso_sala(sala: str, procesos: List[Dict]):
    """
    Renderiza una línea de proceso visual para una sala.
    Muestra cada proceso como un bloque en una línea de tiempo.
    """
    if not procesos:
        return
    
    # Ordenar procesos por hora de inicio
    procesos_ordenados = sorted(procesos, key=lambda x: x.get('inicio_dt') or datetime.min)
    
    # Calcular totales de la sala
    total_kg = sum(p.get('kg_producidos', 0) for p in procesos)
    total_dotacion = sum(p.get('dotacion', 0) for p in procesos)
    kg_horas = [p.get('kg_hora', 0) for p in procesos if p.get('kg_hora', 0) > 0]
    promedio_kg_hora = sum(kg_horas) / len(kg_horas) if kg_horas else 0
    total_detenciones = sum(p.get('detenciones', 0) for p in procesos)
    
    # CSS para la línea de proceso
    st.markdown("""
    <style>
    .linea-proceso-container {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        border-left: 5px solid #00d4ff;
    }
    .linea-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
        gap: 10px;
    }
    .linea-title {
        font-size: 1.4em;
        font-weight: bold;
        color: #00d4ff;
    }
    .linea-stats {
        display: flex;
        gap: 20px;
        flex-wrap: wrap;
    }
    .linea-stat {
        background: rgba(255,255,255,0.1);
        padding: 8px 15px;
        border-radius: 20px;
        font-size: 0.9em;
    }
    .linea-stat-value {
        font-weight: bold;
        color: #fff;
    }
    .proceso-timeline {
        position: relative;
        padding: 20px 0;
    }
    .proceso-timeline::before {
        content: '';
        position: absolute;
        left: 20px;
        top: 0;
        bottom: 0;
        width: 4px;
        background: linear-gradient(180deg, #00d4ff, #0099cc);
        border-radius: 2px;
    }
    .proceso-item {
        position: relative;
        margin-left: 50px;
        margin-bottom: 20px;
        background: rgba(255,255,255,0.05);
        border-radius: 12px;
        padding: 15px;
        border: 1px solid rgba(255,255,255,0.1);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .proceso-item:hover {
        transform: translateX(5px);
        box-shadow: 0 5px 20px rgba(0,212,255,0.2);
    }
    .proceso-item::before {
        content: '';
        position: absolute;
        left: -38px;
        top: 20px;
        width: 16px;
        height: 16px;
        border-radius: 50%;
        border: 3px solid #00d4ff;
        background: #1a1a2e;
    }
    .proceso-item.excelente::before { background: #4caf50; border-color: #4caf50; }
    .proceso-item.bueno::before { background: #8bc34a; border-color: #8bc34a; }
    .proceso-item.regular::before { background: #ffc107; border-color: #ffc107; }
    .proceso-item.bajo::before { background: #f44336; border-color: #f44336; }
    
    .proceso-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 12px;
        flex-wrap: wrap;
        gap: 10px;
    }
    .proceso-nombre {
        font-weight: bold;
        color: #00d4ff;
        font-size: 1.1em;
    }
    .proceso-horario {
        background: rgba(0,212,255,0.2);
        padding: 5px 12px;
        border-radius: 15px;
        font-size: 0.9em;
        color: #00d4ff;
    }
    .proceso-producto {
        color: #aaa;
        font-size: 0.9em;
        margin-bottom: 10px;
    }
    .proceso-metricas {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(100px, 1fr));
        gap: 10px;
    }
    .metrica {
        background: rgba(255,255,255,0.05);
        padding: 10px;
        border-radius: 8px;
        text-align: center;
    }
    .metrica-valor {
        font-size: 1.3em;
        font-weight: bold;
        color: #fff;
    }
    .metrica-label {
        font-size: 0.75em;
        color: #888;
        margin-top: 3px;
    }
    .metrica.destacado {
        background: linear-gradient(135deg, rgba(0,212,255,0.3), rgba(0,153,204,0.2));
        border: 1px solid rgba(0,212,255,0.5);
    }
    .metrica.destacado .metrica-valor {
        color: #00d4ff;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Construir HTML de la línea de proceso
    html = f"""
    <div class="linea-proceso-container">
        <div class="linea-header">
            <div class="linea-title">🏭 {sala}</div>
            <div class="linea-stats">
                <div class="linea-stat">📋 <span class="linea-stat-value">{len(procesos)}</span> procesos</div>
                <div class="linea-stat">⚖️ <span class="linea-stat-value">{total_kg:,.0f}</span> KG</div>
                <div class="linea-stat">⚡ <span class="linea-stat-value">{promedio_kg_hora:,.0f}</span> KG/Hora prom</div>
                <div class="linea-stat">👷 <span class="linea-stat-value">{total_dotacion}</span> personas total</div>
            </div>
        </div>
        
        <div class="proceso-timeline">
    """
    
    for p in procesos_ordenados:
        kg_hora = p.get('kg_hora', 0)
        
        # Clase de rendimiento
        if kg_hora >= 2000:
            clase = "excelente"
        elif kg_hora >= 1500:
            clase = "bueno"
        elif kg_hora >= 1000:
            clase = "regular"
        else:
            clase = "bajo"
        
        nombre = p.get('nombre', 'N/A')
        producto = p.get('producto', '-')
        if len(str(producto)) > 50:
            producto = str(producto)[:47] + "..."
        
        hora_inicio = p.get('hora_inicio', '-')
        hora_fin = p.get('hora_fin', '-')
        duracion = p.get('duracion', '-')
        dotacion = int(p.get('dotacion', 0))
        kg_producidos = p.get('kg_producidos', 0)
        hh_efectiva = p.get('hh_efectiva', 0)
        kg_hh = p.get('kg_hh', 0)
        detenciones = p.get('detenciones', 0)
        rendimiento = p.get('rendimiento', 0)
        
        # Formatear detenciones
        det_h = int(detenciones)
        det_m = int((detenciones - det_h) * 60) if detenciones > 0 else 0
        det_str = f"{det_h}:{det_m:02d}" if detenciones > 0 else "0:00"
        
        html += f"""
            <div class="proceso-item {clase}">
                <div class="proceso-header">
                    <div class="proceso-nombre">📋 {nombre}</div>
                    <div class="proceso-horario">🕐 {hora_inicio} → {hora_fin} ({duracion}h)</div>
                </div>
                <div class="proceso-producto">📦 {producto}</div>
                <div class="proceso-metricas">
                    <div class="metrica destacado">
                        <div class="metrica-valor">{kg_hora:,.0f}</div>
                        <div class="metrica-label">⚡ KG/HORA</div>
                    </div>
                    <div class="metrica">
                        <div class="metrica-valor">{kg_producidos:,.0f}</div>
                        <div class="metrica-label">⚖️ KG TOTAL</div>
                    </div>
                    <div class="metrica">
                        <div class="metrica-valor">{dotacion}</div>
                        <div class="metrica-label">👷 DOTACIÓN</div>
                    </div>
                    <div class="metrica">
                        <div class="metrica-valor">{hh_efectiva:.1f}</div>
                        <div class="metrica-label">⏱️ HH EFECT</div>
                    </div>
                    <div class="metrica">
                        <div class="metrica-valor">{kg_hh:,.0f}</div>
                        <div class="metrica-label">📊 KG/HH</div>
                    </div>
                    <div class="metrica">
                        <div class="metrica-valor">{det_str}</div>
                        <div class="metrica-label">⏸️ DETENC.</div>
                    </div>
                    <div class="metrica">
                        <div class="metrica-valor">{rendimiento:.1f}%</div>
                        <div class="metrica-label">📈 REND.</div>
                    </div>
                </div>
            </div>
        """
    
    html += """
        </div>
    </div>
    """
    
    st.markdown(html, unsafe_allow_html=True)


def render_proceso_card(p: Dict, idx: int):
    """Renderiza una tarjeta de proceso con componentes nativos de Streamlit."""
    
    kg = p.get('kg_hora', 0)
    
    # Determinar color y emoji según rendimiento
    if kg >= 2000:
        color = "🟢"
        status = "Excelente"
    elif kg >= 1500:
        color = "🟡"
        status = "Bueno"
    elif kg >= 1000:
        color = "🟠"
        status = "Regular"
    elif kg > 0:
        color = "🔴"
        status = "Bajo"
    else:
        color = "⚫"
        status = "Sin datos"
    
    # Header con nombre de orden
    st.markdown(f"### 📋 {p.get('nombre', 'N/A')}")
    
    # Fila 1: KG/Hora destacado + Horario + Producto
    c1, c2, c3 = st.columns([1.5, 1.5, 2])
    
    with c1:
        st.metric(
            label=f"{color} KG/Hora",
            value=f"{kg:,.0f}",
            delta=status
        )
    
    with c2:
        hora_inicio = p.get('hora_inicio', '-')
        hora_fin = p.get('hora_fin', '-')
        duracion = p.get('duracion', '-')
        st.metric(
            label="🕐 Horario",
            value=f"{hora_inicio} → {hora_fin}",
            delta=f"{duracion} hrs"
        )
    
    with c3:
        producto = p.get('producto', '-')
        if len(str(producto)) > 40:
            producto = str(producto)[:37] + "..."
        st.metric(
            label="📦 Producto",
            value=str(producto)
        )
    
    # Fila 2: Métricas detalladas
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    
    with m1:
        st.metric("👷 Dotación", f"{int(p.get('dotacion', 0))}")
    
    with m2:
        st.metric("⚖️ KG Total", f"{p.get('kg_producidos', 0):,.0f}")
    
    with m3:
        hh_efectiva = p.get('hh_efectiva', 0)
        st.metric("⏱️ HH Efectiva", f"{hh_efectiva:.1f}")
    
    with m4:
        kg_hh = p.get('kg_hh', 0)
        st.metric("📊 KG/HH", f"{kg_hh:,.0f}")
    
    with m5:
        detenciones = p.get('detenciones', 0)
        det_h = int(detenciones)
        det_m = int((detenciones - det_h) * 60)
        det_str = f"{det_h}:{det_m:02d}" if detenciones > 0 else "0:00"
        st.metric("⏸️ Detenciones", det_str)
    
    with m6:
        rend = p.get('rendimiento', 0)
        st.metric("📈 Rendimiento", f"{rend:.1f}%")
    
    st.divider()


def render_grafico_comparativo_dia(procesos_por_sala: Dict[str, List[Dict]], fecha_str: str):
    """Renderiza gráfico comparativo de todas las salas del día."""
    
    # Calcular promedio por sala
    datos_salas = []
    for sala, procesos in procesos_por_sala.items():
        kg_horas = [p['kg_hora'] for p in procesos if p['kg_hora'] > 0]
        if kg_horas:
            promedio = sum(kg_horas) / len(kg_horas)
            total_kg = sum(p['kg_producidos'] for p in procesos)
            datos_salas.append({
                'sala': sala,
                'promedio': promedio,
                'total_kg': total_kg,
                'procesos': len(procesos)
            })
    
    if not datos_salas:
        return
    
    # Ordenar por promedio
    datos_salas.sort(key=lambda x: x['promedio'], reverse=True)
    
    # Preparar datos para el gráfico
    salas = [d['sala'][:25] for d in datos_salas]
    promedios = [round(d['promedio'], 0) for d in datos_salas]
    
    # Colores según rendimiento
    colores = []
    for p in promedios:
        if p >= 2000:
            colores.append('#4caf50')
        elif p >= 1500:
            colores.append('#8bc34a')
        elif p >= 1000:
            colores.append('#ffc107')
        elif p >= 500:
            colores.append('#ff9800')
        else:
            colores.append('#f44336')
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "formatter": "{b}<br/>⚡ KG/Hora: <b>{c}</b>"
        },
        "grid": {
            "left": "3%",
            "right": "4%",
            "bottom": "15%",
            "top": "10%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": salas,
            "axisLabel": {
                "color": "#ccc",
                "rotate": 30,
                "fontSize": 10
            }
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [{
            "name": "KG/Hora Promedio",
            "type": "bar",
            "data": [
                {"value": v, "itemStyle": {"color": c}} 
                for v, c in zip(promedios, colores)
            ],
            "label": {
                "show": True,
                "position": "top",
                "color": "#fff",
                "fontSize": 11,
                "formatter": "{c}"
            },
            "barMaxWidth": 60
        }]
    }
    
    st_echarts(options=options, height="300px")


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
            Visualiza el KG/Hora de cada sala, desglosado por día y por orden de producción
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
        btn_buscar = st.button("🔍 Buscar", type="primary", use_container_width=True, key="kg_linea_buscar")
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    if btn_buscar:
        st.session_state['kg_linea_data_loaded'] = True
    
    if not st.session_state.get('kg_linea_data_loaded'):
        st.info("👆 Selecciona el rango de fechas y presiona **Buscar**")
        return
    
    # Cargar datos usando las fechas actuales de los widgets
    try:
        with st.spinner("Cargando datos de producción..."):
            data = fetch_datos_produccion(
                username, password,
                fecha_inicio.isoformat(),
                fecha_fin.isoformat()
            )
    except Exception as e:
        st.error(f"Error al cargar datos: {str(e)}")
        return
    
    mos = data.get('mos', [])
    
    if not mos:
        st.warning("No hay órdenes de producción en el período seleccionado")
        return
    
    # === PROCESAR Y AGRUPAR POR DÍA ===
    procesos_por_dia = defaultdict(lambda: defaultdict(list))
    
    for mo in mos:
        # Obtener fecha de inicio
        fecha_str = mo.get('fecha_inicio') or mo.get('fecha_termino')
        if not fecha_str:
            continue
        
        fecha_dt = parsear_fecha_hora(fecha_str)
        if not fecha_dt:
            continue
        
        dia_key = fecha_dt.strftime('%Y-%m-%d')
        
        # Obtener sala
        sala = mo.get('sala') or 'Sin Sala'
        
        # Obtener fecha fin
        fecha_fin_str = mo.get('fecha_termino')
        fin_dt = parsear_fecha_hora(fecha_fin_str)
        
        # Calcular duración
        duracion = 0
        if fecha_dt and fin_dt:
            duracion = (fin_dt - fecha_dt).total_seconds() / 3600
        
        # Obtener producto
        producto = mo.get('producto', '-')
        if isinstance(producto, (list, tuple)) and len(producto) > 1:
            producto = producto[1]
        
        # Crear info del proceso
        proceso_info = {
            'nombre': mo.get('name', 'N/A'),
            'producto': producto,
            'hora_inicio': formatear_hora(fecha_dt),
            'hora_fin': formatear_hora(fin_dt),
            'inicio_dt': fecha_dt,
            'fin_dt': fin_dt,
            'duracion': f"{duracion:.1f}" if duracion > 0 else "-",
            'dotacion': mo.get('dotacion', 0) or 0,
            'kg_producidos': mo.get('kg_pt', 0) or 0,
            'kg_hora': mo.get('kg_por_hora', 0) or 0,
            'kg_hh': mo.get('kg_hh_efectiva', 0) or mo.get('kg_por_hh', 0) or 0,
            'hh': mo.get('hh', 0) or 0,
            'hh_efectiva': mo.get('hh_efectiva', 0) or 0,
            'detenciones': mo.get('detenciones', 0) or 0,
            'rendimiento': mo.get('rendimiento', 0) or 0
        }
        
        procesos_por_dia[dia_key][sala].append(proceso_info)
    
    if not procesos_por_dia:
        st.warning("No se encontraron procesos con fechas válidas")
        return
    
    # === KPIs GENERALES ===
    total_ordenes = len(mos)
    total_kg = sum(mo.get('kg_pt', 0) or 0 for mo in mos)
    kg_horas = [mo.get('kg_por_hora', 0) or 0 for mo in mos if mo.get('kg_por_hora', 0) > 0]
    promedio_kg_hora = sum(kg_horas) / len(kg_horas) if kg_horas else 0
    salas_unicas = set(mo.get('sala', 'Sin Sala') for mo in mos if mo.get('sala'))
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📋 Órdenes", f"{total_ordenes:,}")
    with k2:
        st.metric("⚖️ KG Total", f"{total_kg:,.0f}")
    with k3:
        st.metric("⚡ KG/Hora Prom", f"{promedio_kg_hora:,.0f}")
    with k4:
        st.metric("🏭 Líneas", f"{len(salas_unicas)}")
    
    st.markdown("---")
    
    # === GRÁFICO EVOLUTIVO POR LÍNEA ===
    st.markdown("### 📈 Evolución de KG/Hora por Línea de Proceso")
    st.caption("Comparativa del rendimiento diario de cada línea. Cada punto representa el promedio de KG/Hora del día.")
    
    # Preparar datos para el gráfico evolutivo
    dias_ordenados = sorted(procesos_por_dia.keys())
    todas_salas = sorted(salas_unicas)
    
    # Colores distintivos para cada sala
    colores = [
        '#00D4FF', '#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', 
        '#F38181', '#AA96DA', '#FCBAD3', '#A8D8EA', '#FF9F43',
        '#6C5CE7', '#00B894', '#E17055', '#0984E3', '#FDCB6E'
    ]
    
    series = []
    for idx, sala in enumerate(todas_salas):
        datos_sala = []
        for dia in dias_ordenados:
            procesos_sala_dia = procesos_por_dia[dia].get(sala, [])
            if procesos_sala_dia:
                # Promedio de KG/Hora del día para esta sala
                kg_horas_dia = [p['kg_hora'] for p in procesos_sala_dia if p['kg_hora'] > 0]
                promedio = sum(kg_horas_dia) / len(kg_horas_dia) if kg_horas_dia else 0
                datos_sala.append(round(promedio, 0))
            else:
                datos_sala.append(None)  # Sin datos ese día
        
        series.append({
            "name": sala[:25],
            "type": "line",
            "data": datos_sala,
            "smooth": True,
            "symbol": "circle",
            "symbolSize": 8,
            "lineStyle": {"width": 3},
            "itemStyle": {"color": colores[idx % len(colores)]},
            "connectNulls": False
        })
    
    # Formatear fechas para el eje X
    fechas_formato = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in dias_ordenados]
    
    options_evolucion = {
        "tooltip": {
            "trigger": "axis",
            "backgroundColor": "rgba(30, 30, 50, 0.95)",
            "borderColor": "#555",
            "textStyle": {"color": "#fff"},
            "formatter": """function(params) {
                let result = '<b>' + params[0].axisValue + '</b><br/>';
                params.forEach(function(item) {
                    if (item.value !== null && item.value !== undefined) {
                        result += item.marker + ' ' + item.seriesName + ': <b>' + item.value.toLocaleString() + '</b> kg/h<br/>';
                    }
                });
                return result;
            }"""
        },
        "legend": {
            "data": [s[:25] for s in todas_salas],
            "bottom": 0,
            "textStyle": {"color": "#ccc", "fontSize": 11},
            "type": "scroll"
        },
        "grid": {
            "left": "5%",
            "right": "5%",
            "bottom": "15%",
            "top": "10%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": fechas_formato,
            "axisLabel": {"color": "#ccc", "fontSize": 11},
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {"color": "#ccc", "formatter": "{value}"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": series
    }
    
    st_echarts(options=options_evolucion, height="400px")
    
    st.markdown("---")
    
    # === RENDERIZAR POR DÍA ===
    dias_ordenados = sorted(procesos_por_dia.keys(), reverse=True)  # Ahora sí en orden descendente
    
    for dia_key in dias_ordenados:
        fecha_dt = datetime.strptime(dia_key, '%Y-%m-%d')
        dia_nombre = fecha_dt.strftime('%A %d de %B, %Y').title()
        
        # Traducir día
        traducciones = {
            'Monday': 'Lunes', 'Tuesday': 'Martes', 'Wednesday': 'Miércoles',
            'Thursday': 'Jueves', 'Friday': 'Viernes', 'Saturday': 'Sábado', 'Sunday': 'Domingo',
            'January': 'Enero', 'February': 'Febrero', 'March': 'Marzo', 'April': 'Abril',
            'May': 'Mayo', 'June': 'Junio', 'July': 'Julio', 'August': 'Agosto',
            'September': 'Septiembre', 'October': 'Octubre', 'November': 'Noviembre', 'December': 'Diciembre'
        }
        for en, es in traducciones.items():
            dia_nombre = dia_nombre.replace(en, es)
        
        procesos_dia = procesos_por_dia[dia_key]
        total_procesos_dia = sum(len(p) for p in procesos_dia.values())
        total_kg_dia = sum(
            sum(proc['kg_producidos'] for proc in procs)
            for procs in procesos_dia.values()
        )
        
        # Header del día
        st.markdown(f"## 📅 {dia_nombre}")
        st.markdown(f"**{total_procesos_dia} órdenes** | **{total_kg_dia:,.0f} KG producidos**")
        
        # Gráfico comparativo del día
        st.markdown("#### 📊 Comparativa KG/Hora por Sala")
        render_grafico_comparativo_dia(procesos_dia, dia_key)
        
        # Línea de proceso por cada sala
        st.markdown("#### 🏭 Detalle por Línea de Proceso")
        
        for sala, procesos in sorted(procesos_dia.items(), key=lambda x: -sum(p['kg_hora'] for p in x[1])):
            render_linea_proceso_sala(sala, procesos)
        
        st.markdown("---")
