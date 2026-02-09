"""
Tab KG por Línea: Productividad por sala de proceso.
Muestra KG/Hora desglosado por día y por orden individual.
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
    """Obtiene datos de producción."""
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


def parsear_fecha(fecha_str: str) -> Optional[datetime]:
    """Parsea fecha de diferentes formatos y ajusta de UTC a hora Chile (UTC-3)."""
    if not fecha_str:
        return None
    try:
        s = str(fecha_str).strip()
        dt = None
        if 'T' in s:
            dt = datetime.fromisoformat(s.replace('Z', ''))
        elif len(s) >= 19:
            dt = datetime.strptime(s[:19], '%Y-%m-%d %H:%M:%S')
        elif len(s) >= 16:
            dt = datetime.strptime(s[:16], '%Y-%m-%d %H:%M')
        elif len(s) >= 10:
            dt = datetime.strptime(s[:10], '%Y-%m-%d')
        
        # Ajustar UTC → Chile (UTC-3)
        if dt:
            dt = dt - timedelta(hours=3)
        return dt
    except:
        pass
    return None


def color_kg_hora(kg: float) -> str:
    """Retorna color según KG/Hora."""
    if kg >= 2000: return '#4caf50'
    if kg >= 1500: return '#8bc34a'
    if kg >= 1000: return '#ffc107'
    if kg >= 500: return '#ff9800'
    return '#f44336'


def emoji_kg_hora(kg: float) -> str:
    """Retorna emoji según KG/Hora."""
    if kg >= 2000: return '🟢'
    if kg >= 1500: return '🟡'
    if kg >= 1000: return '🟠'
    return '🔴'


def traducir_fecha(dia_key: str) -> str:
    """Convierte YYYY-MM-DD a nombre legible en español."""
    dt = datetime.strptime(dia_key, '%Y-%m-%d')
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    meses = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    return f"{dias[dt.weekday()]} {dt.day} de {meses[dt.month - 1]}, {dt.year}"


def render_evolucion(procesos_por_dia: Dict, todas_salas: set):
    """Gráfico de barras agrupadas: KG/Hora promedio por sala por día."""
    dias = sorted(procesos_por_dia.keys())
    
    if not dias:
        return
    
    # Solo mostrar salas que tengan al menos un dato con KG/Hora > 0
    salas_con_datos = set()
    for dia in dias:
        for sala, procs in procesos_por_dia[dia].items():
            if any(p['kg_hora'] > 0 for p in procs):
                salas_con_datos.add(sala)
    
    salas_activas = sorted(salas_con_datos)
    if not salas_activas:
        return
    
    colores = [
        '#00D4FF', '#FF6B6B', '#4ECDC4', '#FFE66D', '#95E1D3', 
        '#F38181', '#AA96DA', '#FCBAD3', '#A8D8EA', '#FF9F43',
        '#6C5CE7', '#00B894', '#E17055', '#0984E3', '#FDCB6E'
    ]
    
    fechas_fmt = [datetime.strptime(d, '%Y-%m-%d').strftime('%d/%m') for d in dias]
    
    series = []
    for idx, sala in enumerate(salas_activas):
        datos = []
        for dia in dias:
            procs = procesos_por_dia[dia].get(sala, [])
            if procs:
                vals = [p['kg_hora'] for p in procs if p['kg_hora'] > 0]
                datos.append(round(sum(vals) / len(vals), 0) if vals else 0)
            else:
                datos.append(0)
        
        series.append({
            "name": sala[:30],
            "type": "bar",
            "data": datos,
            "itemStyle": {"color": colores[idx % len(colores)]},
            "barMaxWidth": 30,
            "label": {
                "show": False
            }
        })
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(20, 20, 40, 0.95)",
            "borderColor": "#444",
            "textStyle": {"color": "#fff", "fontSize": 12}
        },
        "legend": {
            "data": [s[:30] for s in salas_activas],
            "bottom": 0,
            "textStyle": {"color": "#ccc", "fontSize": 10},
            "type": "scroll"
        },
        "grid": {
            "left": "3%", "right": "4%",
            "bottom": "18%", "top": "8%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": fechas_fmt,
            "axisLabel": {"color": "#ccc", "fontSize": 12, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#555"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": series
    }
    
    st_echarts(options=options, height="420px")


def render_barras_dia(procesos_por_sala: Dict[str, List[Dict]]):
    """Gráfico de barras con KG/Hora promedio por sala para un día."""
    datos = []
    for sala, procs in procesos_por_sala.items():
        vals = [p['kg_hora'] for p in procs if p['kg_hora'] > 0]
        if vals:
            datos.append({
                'sala': sala[:25],
                'promedio': round(sum(vals) / len(vals), 0),
                'total_kg': sum(p['kg_producidos'] for p in procs),
                'n': len(procs)
            })
    
    if not datos:
        return
    
    datos.sort(key=lambda x: x['promedio'], reverse=True)
    
    salas = [d['sala'] for d in datos]
    valores = [d['promedio'] for d in datos]
    colores = [color_kg_hora(v) for v in valores]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "grid": {
            "left": "3%", "right": "8%",
            "bottom": "5%", "top": "8%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": salas,
            "axisLabel": {"color": "#ccc", "fontSize": 10, "rotate": 20}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [{
            "type": "bar",
            "data": [{"value": v, "itemStyle": {"color": c}} for v, c in zip(valores, colores)],
            "label": {
                "show": True,
                "position": "top",
                "color": "#fff",
                "fontSize": 12,
                "fontWeight": "bold"
            },
            "barMaxWidth": 55
        }]
    }
    
    st_echarts(options=options, height="280px")


def render_detalle_sala(sala: str, procesos: List[Dict]):
    """Renderiza el detalle de una sala usando componentes nativos de Streamlit."""
    procesos_ord = sorted(procesos, key=lambda x: x.get('inicio_dt') or datetime.min)
    
    for p in procesos_ord:
        kg = p.get('kg_hora', 0)
        em = emoji_kg_hora(kg)
        nombre = p.get('nombre', 'N/A')
        producto = str(p.get('producto', '-'))
        if len(producto) > 45:
            producto = producto[:42] + "..."
        
        hora_i = p.get('hora_inicio', '-')
        hora_f = p.get('hora_fin', '-')
        dur = p.get('duracion', '-')
        
        st.markdown(f"**{em} {nombre}** — `{hora_i} → {hora_f}` ({dur}h) — 📦 {producto}")
        
        c1, c2, c3, c4, c5, c6 = st.columns(6)
        with c1:
            st.metric("⚡ KG/Hora", f"{kg:,.0f}")
        with c2:
            st.metric("⚖️ KG Total", f"{p.get('kg_producidos', 0):,.0f}")
        with c3:
            st.metric("👷 Dotación", f"{int(p.get('dotacion', 0))}")
        with c4:
            st.metric("⏱️ HH Efect.", f"{p.get('hh_efectiva', 0):.1f}")
        with c5:
            det = p.get('detenciones', 0)
            det_h = int(det)
            det_m = int((det - det_h) * 60) if det > 0 else 0
            st.metric("⏸️ Detenc.", f"{det_h}:{det_m:02d}")
        with c6:
            st.metric("📈 Rend.", f"{p.get('rendimiento', 0):.1f}%")
        
        st.divider()


def render(username: str = None, password: str = None):
    """Render principal del tab KG por Línea."""
    
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
        <p style="margin:5px 0 0 0; color:#aaa;">
            KG/Hora de cada sala, desglosado por día y por orden de producción
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        fecha_inicio = st.date_input("📅 Desde",
            value=datetime.now().date() - timedelta(days=7),
            key="kg_linea_fecha_inicio")
    with col2:
        fecha_fin = st.date_input("📅 Hasta",
            value=datetime.now().date(),
            key="kg_linea_fecha_fin")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn = st.button("🔍 Buscar", type="primary", use_container_width=True, key="kg_linea_buscar")
    
    st.markdown("---")
    
    if btn:
        st.session_state['kg_linea_loaded'] = True
    
    if not st.session_state.get('kg_linea_loaded'):
        st.info("👆 Selecciona el rango de fechas y presiona **Buscar**")
        return
    
    # === CARGAR DATOS ===
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
    
    mos_raw = data.get('mos', [])
    
    # Filtrar: excluir túneles estáticos (no son líneas de proceso)
    SALAS_EXCLUIR = ['tunel', 'túnel', 'estatico', 'estático', 'congelado']
    mos = []
    for mo in mos_raw:
        sala = (mo.get('sala') or mo.get('sala_original') or '').lower()
        sala_tipo = (mo.get('sala_tipo') or '').upper()
        # Excluir si es tipo CONGELADO o si contiene tunel/estatico
        if sala_tipo == 'CONGELADO':
            continue
        if any(excl in sala for excl in SALAS_EXCLUIR):
            continue
        mos.append(mo)
    
    if not mos:
        st.warning("No hay órdenes de producción (líneas de proceso) en el período seleccionado")
        return
    
    # === PROCESAR Y AGRUPAR POR DÍA ===
    procesos_por_dia = defaultdict(lambda: defaultdict(list))
    todas_salas = set()
    
    for mo in mos:
        fecha_str = mo.get('fecha_inicio') or mo.get('fecha_termino')
        if not fecha_str:
            continue
        
        fecha_dt = parsear_fecha(fecha_str)
        if not fecha_dt:
            continue
        
        dia_key = fecha_dt.strftime('%Y-%m-%d')
        sala = mo.get('sala') or 'Sin Sala'
        todas_salas.add(sala)
        
        fin_dt = parsear_fecha(mo.get('fecha_termino'))
        
        duracion = 0
        if fecha_dt and fin_dt:
            duracion = (fin_dt - fecha_dt).total_seconds() / 3600
        
        producto = mo.get('product_name', '') or mo.get('producto', '-')
        if isinstance(producto, (list, tuple)) and len(producto) > 1:
            producto = producto[1]
        
        procesos_por_dia[dia_key][sala].append({
            'nombre': mo.get('mo_name', '') or mo.get('name', 'N/A'),
            'producto': producto,
            'hora_inicio': fecha_dt.strftime("%H:%M") if fecha_dt else "-",
            'hora_fin': fin_dt.strftime("%H:%M") if fin_dt else "-",
            'inicio_dt': fecha_dt,
            'fin_dt': fin_dt,
            'duracion': f"{duracion:.1f}" if duracion > 0 else "-",
            'dotacion': mo.get('dotacion', 0) or 0,
            'kg_producidos': mo.get('kg_pt', 0) or 0,
            'kg_hora': mo.get('kg_por_hora', 0) or mo.get('kg_hora_efectiva', 0) or 0,
            'kg_hh': mo.get('kg_hh_efectiva', 0) or 0,
            'hh': mo.get('hh', 0) or 0,
            'hh_efectiva': mo.get('hh_efectiva', 0) or 0,
            'detenciones': mo.get('detenciones', 0) or 0,
            'rendimiento': mo.get('rendimiento', 0) or 0
        })
    
    if not procesos_por_dia:
        st.warning("No se encontraron procesos con fechas válidas")
        return
    
    # === KPIs GENERALES ===
    total_ordenes = sum(len(procs) for dia in procesos_por_dia.values() for procs in dia.values())
    total_kg = sum(p['kg_producidos'] for dia in procesos_por_dia.values() for procs in dia.values() for p in procs)
    kg_hrs = [p['kg_hora'] for dia in procesos_por_dia.values() for procs in dia.values() for p in procs if p['kg_hora'] > 0]
    prom_kg = sum(kg_hrs) / len(kg_hrs) if kg_hrs else 0
    
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📋 Órdenes", f"{total_ordenes:,}")
    with k2:
        st.metric("⚖️ KG Total", f"{total_kg:,.0f}")
    with k3:
        st.metric("⚡ KG/Hora Prom", f"{prom_kg:,.0f}")
    with k4:
        st.metric("🏭 Líneas Activas", f"{len(todas_salas)}")
    
    st.markdown("---")
    
    # === GRÁFICO EVOLUTIVO ===
    if len(procesos_por_dia) > 1:
        st.markdown("### � KG/Hora por Línea y por Día")
        st.caption("Cada barra muestra el KG/Hora promedio de cada sala en ese día. Compara fácilmente el rendimiento entre líneas.")
        render_evolucion(procesos_por_dia, todas_salas)
        st.markdown("---")
    
    # === DESGLOSE POR DÍA ===
    for dia_key in sorted(procesos_por_dia.keys(), reverse=True):
        dia_nombre = traducir_fecha(dia_key)
        salas_dia = procesos_por_dia[dia_key]
        
        total_procs = sum(len(p) for p in salas_dia.values())
        total_kg_dia = sum(p['kg_producidos'] for procs in salas_dia.values() for p in procs)
        
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1e3a5f 0%, #0d2137 100%); 
                    padding: 15px 25px; border-radius: 15px; margin: 15px 0;
                    border-left: 5px solid #00d4ff;">
            <h3 style="margin:0; color:#00d4ff;">📅 {dia_nombre}</h3>
            <p style="margin:5px 0 0 0; color:#aaa;">
                <b style="color:#fff;">{total_procs}</b> órdenes &nbsp;|&nbsp;
                <b style="color:#4caf50;">{total_kg_dia:,.0f}</b> KG producidos &nbsp;|&nbsp;
                <b style="color:#FFE66D;">{len(salas_dia)}</b> líneas activas
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Gráfico de barras comparativo del día
        render_barras_dia(salas_dia)
        
        # Detalle por sala (colapsable)
        for sala in sorted(salas_dia.keys(), 
                          key=lambda s: -sum(p['kg_hora'] for p in salas_dia[s])):
            procesos = salas_dia[sala]
            kg_vals = [p['kg_hora'] for p in procesos if p['kg_hora'] > 0]
            prom_sala = sum(kg_vals) / len(kg_vals) if kg_vals else 0
            total_kg_sala = sum(p['kg_producidos'] for p in procesos)
            em = emoji_kg_hora(prom_sala)
            
            with st.expander(
                f"{em} {sala} — {prom_sala:,.0f} KG/Hora prom — {len(procesos)} procesos — {total_kg_sala:,.0f} KG",
                expanded=False
            ):
                render_detalle_sala(sala, procesos)
        
        st.markdown("---")
