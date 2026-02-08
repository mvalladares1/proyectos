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
        st.session_state['kg_linea_fecha_ini'] = fecha_inicio.isoformat()
        st.session_state['kg_linea_fecha_fin'] = fecha_fin.isoformat()
    
    if not st.session_state.get('kg_linea_data_loaded'):
        st.info("👆 Selecciona el rango de fechas y presiona **Buscar**")
        return
    
    # Cargar datos
    try:
        with st.spinner("Cargando datos de producción..."):
            data = fetch_datos_produccion(
                username, password,
                st.session_state['kg_linea_fecha_ini'],
                st.session_state['kg_linea_fecha_fin']
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
    
    # === RENDERIZAR POR DÍA ===
    dias_ordenados = sorted(procesos_por_dia.keys(), reverse=True)
    
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
        
        # Expander por cada sala
        for sala, procesos in sorted(procesos_dia.items(), key=lambda x: -sum(p['kg_hora'] for p in x[1])):
            kg_promedio = sum(p['kg_hora'] for p in procesos if p['kg_hora'] > 0)
            if procesos:
                kg_promedio = kg_promedio / len([p for p in procesos if p['kg_hora'] > 0]) if any(p['kg_hora'] > 0 for p in procesos) else 0
            
            total_kg_sala = sum(p['kg_producidos'] for p in procesos)
            
            # Emoji según rendimiento
            if kg_promedio >= 1500:
                emoji = "🟢"
            elif kg_promedio >= 1000:
                emoji = "🟡"
            elif kg_promedio > 0:
                emoji = "🔴"
            else:
                emoji = "⚫"
            
            with st.expander(
                f"{emoji} **{sala}** — Promedio: **{kg_promedio:,.0f} KG/Hora** — {len(procesos)} proceso(s) — {total_kg_sala:,.0f} KG",
                expanded=False
            ):
                # Ordenar procesos por hora de inicio
                procesos_ordenados = sorted(procesos, key=lambda x: x['inicio_dt'] or datetime.min)
                
                for idx, p in enumerate(procesos_ordenados):
                    render_proceso_card(p, idx)
        
        st.markdown("---")
