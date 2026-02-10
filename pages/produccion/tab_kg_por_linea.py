"""
Tab Rendimiento en Salas: Productividad por sala de proceso.
Muestra KG/Hora, órdenes, KG totales desglosado por sala con filtros de especie y planta.
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
    """Parsea fecha y ajusta de UTC a hora Chile (UTC-3)."""
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
        if dt:
            dt = dt - timedelta(hours=3)
        return dt
    except Exception:
        pass
    return None


def detectar_planta(mo: Dict) -> str:
    """Detecta la planta a partir del nombre de la MO o sala."""
    mo_name = (mo.get('mo_name') or mo.get('name') or '').upper()
    sala = (mo.get('sala') or mo.get('sala_original') or '').lower()

    if 'VLK' in mo_name or 'vilkun' in sala:
        return 'Vilkun'
    if 'RF' in mo_name:
        return 'Rio Futuro'
    return 'Rio Futuro'


def emoji_kg_hora(kg: float) -> str:
    if kg >= 2000: return '🟢'
    if kg >= 1500: return '🟡'
    if kg >= 1000: return '🟠'
    return '🔴'


def color_kg_hora(kg: float) -> str:
    if kg >= 2000: return '#4caf50'
    if kg >= 1500: return '#8bc34a'
    if kg >= 1000: return '#ffc107'
    if kg >= 500: return '#ff9800'
    return '#f44336'


def estado_label(state: str) -> str:
    estados = {
        'draft': 'Borrador',
        'confirmed': 'Confirmada',
        'progress': 'En Proceso',
        'done': 'Terminada',
        'cancel': 'Cancelada',
    }
    return estados.get(state, state)


def _render_grafico_salas(mos_filtradas: List[Dict], salas_data: Dict[str, Dict]):
    """Gráfico de KG desglosado por día y sala."""
    if not mos_filtradas:
        return

    # --- Paleta de colores por sala ---
    colores_paleta = [
        '#00d4ff', '#e040fb', '#4caf50', '#ff9800', '#FF3366',
        '#33FF99', '#FFCC00', '#3399FF', '#FF6633', '#66FFCC',
        '#CC33FF', '#99FF33', '#6633FF', '#FF66CC', '#00FF66',
    ]

    # Agrupar KG por fecha y sala
    dia_sala_kg: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    todas_salas_set = set()

    for mo in mos_filtradas:
        sala = mo.get('sala') or 'Sin Sala'
        todas_salas_set.add(sala)
        # Usar fecha de inicio para determinar el día
        dt = mo.get('_inicio_dt')
        if not dt:
            continue
        dia_key = dt.strftime('%d/%m')
        kg = mo.get('kg_pt', 0) or 0
        dia_sala_kg[dia_key][sala] += kg

    if not dia_sala_kg:
        return

    # Ordenar días cronológicamente
    dias_sorted = sorted(dia_sala_kg.keys(), key=lambda d: datetime.strptime(d, '%d/%m'))
    salas_sorted = sorted(todas_salas_set)
    color_map = {sala: colores_paleta[i % len(colores_paleta)] for i, sala in enumerate(salas_sorted)}

    # Construir series por sala
    series = []
    for sala in salas_sorted:
        data_vals = [round(dia_sala_kg[dia].get(sala, 0)) for dia in dias_sorted]
        c = color_map[sala]
        series.append({
            "name": sala,
            "type": "bar",
            "stack": "total",
            "data": data_vals,
            "barMaxWidth": 50,
            "itemStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": c},
                        {"offset": 1, "color": c + "88"}
                    ]
                },
                "borderRadius": [0, 0, 0, 0]
            },
            "emphasis": {
                "itemStyle": {"shadowBlur": 10, "shadowColor": "rgba(0,0,0,0.4)"}
            }
        })
    # Redondear bordes de la última serie (top del stack)
    if series:
        series[-1]["itemStyle"]["borderRadius"] = [8, 8, 0, 0]

    options = {
        "title": {
            "text": "⚖️ KG Producidos por Día / Sala",
            "subtext": "Kilogramos de producto terminado desglosados por día y sala",
            "left": "center",
            "textStyle": {"color": "#fff", "fontSize": 16, "fontWeight": "bold"},
            "subtextStyle": {"color": "#999", "fontSize": 12}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(10, 10, 30, 0.95)",
            "borderColor": "#555",
            "borderWidth": 1,
            "borderRadius": 10,
            "textStyle": {"color": "#fff", "fontSize": 13},
            "extraCssText": "box-shadow: 0 4px 20px rgba(0,0,0,0.5);"
        },
        "legend": {
            "data": salas_sorted,
            "bottom": 0,
            "textStyle": {"color": "#ccc", "fontSize": 12},
            "itemGap": 15,
            "icon": "roundRect",
            "type": "scroll"
        },
        "grid": {
            "left": "3%", "right": "4%",
            "bottom": "15%", "top": "18%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": dias_sorted,
            "axisLabel": {
                "color": "#fff", "fontSize": 12, "fontWeight": "bold",
                "interval": 0
            },
            "axisLine": {"lineStyle": {"color": "#444", "width": 2}},
            "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value",
            "name": "⚖️ KG",
            "nameTextStyle": {"color": "#aaa", "fontSize": 13, "fontWeight": "bold"},
            "axisLabel": {"color": "#ccc", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}},
            "axisLine": {"show": False}
        },
        "series": series,
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0, "start": 0, "end": 100}
        ] if len(dias_sorted) > 14 else []
    }

    altura = max(450, 380 + len(salas_sorted) * 8)
    st_echarts(options=options, height=f"{altura}px")


def render(username: str = None, password: str = None):
    """Render principal del tab Rendimiento en Salas."""

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
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                border-left: 5px solid #00d4ff;">
        <h2 style="margin:0; color:#00d4ff;">🏭 Rendimiento en Salas</h2>
        <p style="margin:5px 0 0 0; color:#aaa;">
            Rendimiento, KG/Hora y detalle de órdenes por sala de proceso
        </p>
    </div>
    """, unsafe_allow_html=True)

    # === FILTROS ===
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col1:
        fecha_inicio = st.date_input("📅 Desde",
                                     value=datetime.now().date() - timedelta(days=7),
                                     key="rend_sala_fecha_inicio")
    with col2:
        fecha_fin = st.date_input("📅 Hasta",
                                  value=datetime.now().date(),
                                  key="rend_sala_fecha_fin")
    with col3:
        planta_opciones = ["Todos", "Rio Futuro", "Vilkun"]
        planta_sel = st.selectbox("🏭 Planta", planta_opciones, key="rend_sala_planta")
    with col4:
        st.markdown("<br>", unsafe_allow_html=True)
        btn = st.button("🔍 Buscar", type="primary", use_container_width=True,
                         key="rend_sala_buscar")

    st.markdown("---")

    if btn:
        st.session_state['rend_sala_loaded'] = True

    if not st.session_state.get('rend_sala_loaded'):
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

    if not mos_raw:
        st.warning("No hay órdenes de producción en el período seleccionado")
        return

    # === ENRIQUECER MOs ===
    for mo in mos_raw:
        mo['_planta'] = detectar_planta(mo)
        # Determinar estado: si no viene explícito, inferir
        if not mo.get('_estado'):
            mo['_estado'] = 'done' if mo.get('fecha_termino') else 'progress'

        mo['_inicio_dt'] = parsear_fecha(mo.get('fecha_inicio'))
        mo['_fin_dt'] = parsear_fecha(mo.get('fecha_termino'))

    # Excluir canceladas
    mos_all = [mo for mo in mos_raw if mo.get('_estado') != 'cancel']

    # === FILTRO PLANTA ===
    if planta_sel != "Todos":
        mos_all = [mo for mo in mos_all if mo['_planta'] == planta_sel]

    if not mos_all:
        st.warning("No hay órdenes con los filtros seleccionados")
        return

    # Excluir túneles estáticos (no son líneas de proceso)
    mos_all = [mo for mo in mos_all
               if not any(t in (mo.get('sala') or '').lower()
                          for t in ['estatico', 'estático'])]

    if not mos_all:
        st.warning("No hay órdenes de líneas de proceso en el período")
        return

    # === EXTRAER ESPECIES Y SALAS DISPONIBLES ===
    especies_set = set()
    salas_set = set()
    for mo in mos_all:
        esp = mo.get('especie', '') or 'Otro'
        if esp and esp != 'Otro':
            especies_set.add(esp)
        sala = mo.get('sala') or 'Sin Sala'
        salas_set.add(sala)

    especies_list = sorted(especies_set)
    salas_list = sorted(salas_set)

    # === FILTROS SECUNDARIOS (especie + sala) ===
    col_e, col_s = st.columns(2)
    with col_e:
        especie_opciones = ["Todos"] + especies_list
        especie_sel = st.selectbox("🍓 Especie", especie_opciones, key="rend_sala_especie")
    with col_s:
        sala_opciones = ["Todos"] + salas_list
        sala_sel = st.selectbox("🏠 Sala", sala_opciones, key="rend_sala_sala")

    st.markdown("---")

    # === APLICAR FILTROS SECUNDARIOS ===
    mos_filtradas = mos_all
    if especie_sel != "Todos":
        mos_filtradas = [mo for mo in mos_filtradas if mo.get('especie') == especie_sel]
    if sala_sel != "Todos":
        mos_filtradas = [mo for mo in mos_filtradas
                         if (mo.get('sala') or 'Sin Sala') == sala_sel]

    if not mos_filtradas:
        st.warning("No hay órdenes con los filtros seleccionados")
        return

    # === AGRUPAR POR SALA ===
    salas_data: Dict[str, Dict] = {}
    for mo in mos_filtradas:
        sala = mo.get('sala') or 'Sin Sala'
        if sala not in salas_data:
            salas_data[sala] = {
                'ordenes': [],
                'total_kg': 0.0,
                'kg_hora_sum': 0.0,
                'kg_hora_count': 0,
                'hechas': 0,
                'no_hechas': 0,
            }

        sd = salas_data[sala]
        sd['ordenes'].append(mo)
        sd['total_kg'] += mo.get('kg_pt', 0) or 0

        kg_hora = mo.get('kg_hora_efectiva', 0) or mo.get('kg_por_hora', 0) or 0
        if kg_hora > 0:
            sd['kg_hora_sum'] += kg_hora
            sd['kg_hora_count'] += 1

        fecha_termino = mo.get('fecha_termino')
        if fecha_termino:
            sd['hechas'] += 1
        else:
            sd['no_hechas'] += 1

    # === KPIs GENERALES ===
    total_ordenes = len(mos_filtradas)
    total_kg = sum(s['total_kg'] for s in salas_data.values())
    all_kg_hrs = []
    for mo in mos_filtradas:
        kh = mo.get('kg_hora_efectiva', 0) or mo.get('kg_por_hora', 0) or 0
        if kh > 0:
            all_kg_hrs.append(kh)
    prom_kg_hora = sum(all_kg_hrs) / len(all_kg_hrs) if all_kg_hrs else 0
    hechas_total = sum(s['hechas'] for s in salas_data.values())
    no_hechas_total = sum(s['no_hechas'] for s in salas_data.values())

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📋 Órdenes", f"{total_ordenes:,}",
                   help=f"✅ {hechas_total} hechas | 🔄 {no_hechas_total} en proceso")
    with k2:
        st.metric("⚖️ KG Procesados", f"{total_kg:,.0f}")
    with k3:
        st.metric("⚡ KG/Hora Prom", f"{prom_kg_hora:,.0f}")
    with k4:
        st.metric("🏭 Salas Activas", f"{len(salas_data)}")

    st.markdown("---")

    # === GRÁFICO KG POR DÍA/SALA ===
    _render_grafico_salas(mos_filtradas, salas_data)

    st.markdown("---")

    # === TARJETAS POR SALA ===
    colores_sala = [
        '#FF3366', '#00CCFF', '#33FF99', '#FFCC00', '#FF6633',
        '#CC33FF', '#00FF66', '#FF3399', '#3399FF', '#FFFF33',
        '#FF9933', '#66FFCC', '#FF66CC', '#99FF33', '#6633FF',
    ]

    # Ordenar salas por KG/Hora promedio descendente
    salas_ordenadas = sorted(
        salas_data.items(),
        key=lambda x: (x[1]['kg_hora_sum'] / x[1]['kg_hora_count'])
        if x[1]['kg_hora_count'] > 0 else 0,
        reverse=True
    )

    for idx, (sala, sd) in enumerate(salas_ordenadas):
        prom = sd['kg_hora_sum'] / sd['kg_hora_count'] if sd['kg_hora_count'] > 0 else 0
        em = emoji_kg_hora(prom)
        c = colores_sala[idx % len(colores_sala)]
        total = sd['hechas'] + sd['no_hechas']

        # Tarjeta de sala
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, {c}15, {c}08);
                    border: 2px solid {c}55; border-radius: 14px; padding: 18px;
                    margin-bottom: 6px;">
            <div style="display: flex; justify-content: space-between;
                        align-items: center; flex-wrap: wrap;">
                <div style="color: {c}; font-weight: bold; font-size: 18px;">
                    {em} 🏭 {sala}
                </div>
                <div style="color: #aaa; font-size: 13px;">
                    {total} órdenes
                    ({sd['hechas']} ✅ hechas | {sd['no_hechas']} 🔄 en proceso)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Métricas de la sala
        mc1, mc2, mc3, mc4 = st.columns(4)
        with mc1:
            st.metric("📋 Órdenes", f"{total}")
        with mc2:
            st.metric("⚖️ KG Procesados", f"{sd['total_kg']:,.0f}")
        with mc3:
            st.metric("⚡ KG/Hora Prom", f"{prom:,.0f}")
        with mc4:
            pct_hechas = (sd['hechas'] / total * 100) if total > 0 else 0
            st.metric("✅ % Completadas", f"{pct_hechas:.0f}%")

        # Desplegable con detalle de órdenes
        with st.expander(f"📋 Ver {total} órdenes de {sala}", expanded=False):
            ordenes_sorted = sorted(
                sd['ordenes'],
                key=lambda o: o.get('_inicio_dt') or datetime.min,
                reverse=True
            )

            for oi, orden in enumerate(ordenes_sorted):
                kg_h = orden.get('kg_hora_efectiva', 0) or orden.get('kg_por_hora', 0) or 0
                kg_total_o = orden.get('kg_pt', 0) or 0
                dot = orden.get('dotacion', 0) or 0
                rend = orden.get('rendimiento', 0) or 0
                especie_o = orden.get('especie', '-')
                mo_name = orden.get('mo_name', 'N/A')
                estado = 'Terminada' if orden.get('fecha_termino') else 'En Proceso'

                inicio_dt = orden.get('_inicio_dt')
                fin_dt = orden.get('_fin_dt')
                hora_ini = inicio_dt.strftime("%d/%m %H:%M") if inicio_dt else '-'
                hora_fin = fin_dt.strftime("%d/%m %H:%M") if fin_dt else '-'

                em_o = emoji_kg_hora(kg_h)

                st.markdown(f"**{em_o} {mo_name}** — {estado} — 🍓 {especie_o}")

                oc1, oc2, oc3, oc4, oc5, oc6 = st.columns(6)
                with oc1:
                    st.metric("⚡ KG/Hora", f"{kg_h:,.0f}")
                with oc2:
                    st.metric("⚖️ KG Total", f"{kg_total_o:,.0f}")
                with oc3:
                    st.metric("👷 Dotación", f"{int(dot)}")
                with oc4:
                    st.metric("🕐 Inicio", hora_ini)
                with oc5:
                    st.metric("🕑 Fin", hora_fin)
                with oc6:
                    st.metric("📈 Rend.", f"{rend:.1f}%")

                if oi < len(ordenes_sorted) - 1:
                    st.divider()

        st.markdown("---")

    # === SECCIÓN COMPARACIÓN ===
    _render_comparacion(
        username, password,
        fecha_inicio, fecha_fin,
        planta_sel, especie_sel, sala_sel,
        salas_data, mos_filtradas
    )


def _procesar_mos_a_salas(mos_list: List[Dict]) -> Dict[str, Dict]:
    """Agrupa MOs en datos por sala (reutilizable para principal y comparación)."""
    salas: Dict[str, Dict] = {}
    for mo in mos_list:
        sala = mo.get('sala') or 'Sin Sala'
        if sala not in salas:
            salas[sala] = {
                'ordenes': [],
                'total_kg': 0.0,
                'kg_hora_sum': 0.0,
                'kg_hora_count': 0,
                'hechas': 0,
                'no_hechas': 0,
            }
        sd = salas[sala]
        sd['ordenes'].append(mo)
        sd['total_kg'] += mo.get('kg_pt', 0) or 0
        kg_hora = mo.get('kg_hora_efectiva', 0) or mo.get('kg_por_hora', 0) or 0
        if kg_hora > 0:
            sd['kg_hora_sum'] += kg_hora
            sd['kg_hora_count'] += 1
        if mo.get('fecha_termino'):
            sd['hechas'] += 1
        else:
            sd['no_hechas'] += 1
    return salas


def _render_comparacion(
    username, password,
    fecha_inicio_principal, fecha_fin_principal,
    planta_sel, especie_sel, sala_sel,
    salas_principal, mos_principal
):
    """Sección de Comparación: permite comparar rendimiento con otro período."""

    st.markdown("""
    <div style="background: linear-gradient(135deg, #2d1b4e 0%, #1a1a2e 100%);
                padding: 25px; border-radius: 15px; margin-bottom: 20px;
                border-left: 5px solid #e040fb;">
        <h2 style="margin:0; color:#e040fb;">📊 Comparación de Períodos</h2>
        <p style="margin:5px 0 0 0; color:#aaa;">
            Compara el rendimiento del período actual con otro rango de fechas
            (mismos filtros de Planta, Especie y Sala)
        </p>
    </div>
    """, unsafe_allow_html=True)

    filtros_activos = []
    if planta_sel != "Todos":
        filtros_activos.append(f"🏭 {planta_sel}")
    if especie_sel != "Todos":
        filtros_activos.append(f"🍓 {especie_sel}")
    if sala_sel != "Todos":
        filtros_activos.append(f"🏠 {sala_sel}")
    if filtros_activos:
        st.caption(f"Filtros aplicados: {' · '.join(filtros_activos)}")

    cc1, cc2, cc3 = st.columns([1, 1, 1])
    with cc1:
        comp_inicio = st.date_input("📅 Comparar Desde",
                                     value=fecha_inicio_principal - timedelta(days=7),
                                     key="rend_comp_fecha_inicio")
    with cc2:
        comp_fin = st.date_input("📅 Comparar Hasta",
                                  value=fecha_inicio_principal - timedelta(days=1),
                                  key="rend_comp_fecha_fin")
    with cc3:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_comp = st.button("🔍 Comparar", type="primary", use_container_width=True,
                              key="rend_comp_buscar")

    if btn_comp:
        st.session_state['rend_comp_loaded'] = True

    if not st.session_state.get('rend_comp_loaded'):
        st.info("👆 Selecciona el rango de fechas a comparar y presiona **Comparar**")
        return

    # Cargar datos del período comparación
    try:
        with st.spinner("Cargando datos del período de comparación..."):
            data_comp = fetch_datos_produccion(
                username, password,
                comp_inicio.isoformat(),
                comp_fin.isoformat()
            )
    except Exception as e:
        st.error(f"Error al cargar datos de comparación: {str(e)}")
        return

    mos_comp_raw = data_comp.get('mos', [])
    if not mos_comp_raw:
        st.warning("No hay órdenes en el período de comparación")
        return

    # Enriquecer y filtrar igual que el principal
    for mo in mos_comp_raw:
        mo['_planta'] = detectar_planta(mo)
        if not mo.get('_estado'):
            mo['_estado'] = 'done' if mo.get('fecha_termino') else 'progress'
        mo['_inicio_dt'] = parsear_fecha(mo.get('fecha_inicio'))
        mo['_fin_dt'] = parsear_fecha(mo.get('fecha_termino'))

    mos_comp = [mo for mo in mos_comp_raw if mo.get('_estado') != 'cancel']
    mos_comp = [mo for mo in mos_comp
                if not any(t in (mo.get('sala') or '').lower()
                           for t in ['estatico', 'estático'])]

    if planta_sel != "Todos":
        mos_comp = [mo for mo in mos_comp if mo['_planta'] == planta_sel]
    if especie_sel != "Todos":
        mos_comp = [mo for mo in mos_comp if mo.get('especie') == especie_sel]
    if sala_sel != "Todos":
        mos_comp = [mo for mo in mos_comp
                     if (mo.get('sala') or 'Sin Sala') == sala_sel]

    if not mos_comp:
        st.warning("No hay órdenes con los mismos filtros en el período de comparación")
        return

    salas_comp = _procesar_mos_a_salas(mos_comp)

    # === CALCULAR TOTALES DE AMBOS PERÍODOS ===
    def _totales(mos_list, salas_dict):
        total_ordenes = len(mos_list)
        total_kg = sum(s['total_kg'] for s in salas_dict.values())
        khs = [
            (mo.get('kg_hora_efectiva', 0) or mo.get('kg_por_hora', 0) or 0)
            for mo in mos_list
            if (mo.get('kg_hora_efectiva', 0) or mo.get('kg_por_hora', 0) or 0) > 0
        ]
        prom_kh = sum(khs) / len(khs) if khs else 0
        hechas = sum(s['hechas'] for s in salas_dict.values())
        return total_ordenes, total_kg, prom_kh, hechas

    ord_a, kg_a, kh_a, hech_a = _totales(mos_principal, salas_principal)
    ord_b, kg_b, kh_b, hech_b = _totales(mos_comp, salas_comp)

    # Labels de período
    lbl_a = f"{fecha_inicio_principal.strftime('%d/%m')} - {fecha_fin_principal.strftime('%d/%m')}"
    lbl_b = f"{comp_inicio.strftime('%d/%m')} - {comp_fin.strftime('%d/%m')}"

    # === KPIs V/S ===
    st.markdown(f"""
    <div style="text-align: center; margin: 15px 0;">
        <span style="color: #00d4ff; font-size: 16px; font-weight: bold;">📅 {lbl_a}</span>
        <span style="color: #888; font-size: 20px; margin: 0 15px;">VS</span>
        <span style="color: #e040fb; font-size: 16px; font-weight: bold;">📅 {lbl_b}</span>
    </div>
    """, unsafe_allow_html=True)

    def _delta(actual, anterior):
        if anterior == 0:
            return None
        diff = actual - anterior
        pct = (diff / anterior) * 100
        return f"{pct:+.1f}%"

    v1, v2, v3, v4 = st.columns(4)
    with v1:
        st.metric("📋 Órdenes", f"{ord_a}", delta=_delta(ord_a, ord_b),
                   help=f"Actual: {ord_a} | Comparación: {ord_b}")
    with v2:
        st.metric("⚖️ KG Totales", f"{kg_a:,.0f}", delta=_delta(kg_a, kg_b),
                   help=f"Actual: {kg_a:,.0f} | Comparación: {kg_b:,.0f}")
    with v3:
        st.metric("⚡ KG/Hora", f"{kh_a:,.0f}", delta=_delta(kh_a, kh_b),
                   help=f"Actual: {kh_a:,.0f} | Comparación: {kh_b:,.0f}")
    with v4:
        st.metric("✅ Completadas", f"{hech_a}", delta=_delta(hech_a, hech_b),
                   help=f"Actual: {hech_a} | Comparación: {hech_b}")

    st.markdown("---")

    # === GRÁFICO V/S POR SALA ===
    todas_salas = sorted(set(list(salas_principal.keys()) + list(salas_comp.keys())))

    if not todas_salas:
        return

    nombres = []
    kh_actual = []
    kh_comp_vals = []
    kg_actual = []
    kg_comp_list = []

    for sala in todas_salas:
        nombres.append(sala)
        # Período actual
        sa = salas_principal.get(sala)
        if sa and sa['kg_hora_count'] > 0:
            kh_actual.append(round(sa['kg_hora_sum'] / sa['kg_hora_count']))
        else:
            kh_actual.append(0)
        kg_actual.append(round(sa['total_kg']) if sa else 0)

        # Período comparación
        sc = salas_comp.get(sala)
        if sc and sc['kg_hora_count'] > 0:
            kh_comp_vals.append(round(sc['kg_hora_sum'] / sc['kg_hora_count']))
        else:
            kh_comp_vals.append(0)
        kg_comp_list.append(round(sc['total_kg']) if sc else 0)

    options_vs = {
        "title": {
            "text": f"⚡ KG/Hora por Sala — {lbl_a} vs {lbl_b}",
            "subtext": "Barras azules = período actual · Barras moradas = período comparación",
            "left": "center",
            "textStyle": {"color": "#fff", "fontSize": 15, "fontWeight": "bold"},
            "subtextStyle": {"color": "#999", "fontSize": 11}
        },
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(10, 10, 30, 0.95)",
            "borderColor": "#555",
            "borderRadius": 10,
            "textStyle": {"color": "#fff", "fontSize": 13},
            "extraCssText": "box-shadow: 0 4px 20px rgba(0,0,0,0.5);"
        },
        "legend": {
            "data": [f"📅 {lbl_a}", f"📅 {lbl_b}"],
            "bottom": 0,
            "textStyle": {"color": "#ccc", "fontSize": 12},
            "itemGap": 30,
            "icon": "roundRect"
        },
        "grid": {
            "left": "3%", "right": "4%",
            "bottom": "15%", "top": "20%",
            "containLabel": True
        },
        "xAxis": {
            "type": "category",
            "data": nombres,
            "axisLabel": {
                "color": "#fff", "fontSize": 12, "fontWeight": "bold",
                "rotate": 25 if len(nombres) > 5 else 0,
                "interval": 0
            },
            "axisLine": {"lineStyle": {"color": "#444", "width": 2}},
            "axisTick": {"show": False}
        },
        "yAxis": {
            "type": "value",
            "name": "⚡ KG / Hora",
            "nameTextStyle": {"color": "#aaa", "fontSize": 13, "fontWeight": "bold"},
            "axisLabel": {"color": "#ccc", "fontSize": 11},
            "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}},
            "axisLine": {"show": False}
        },
        "series": [
            {
                "name": f"📅 {lbl_a}",
                "type": "bar",
                "data": kh_actual,
                "barMaxWidth": 40,
                "barGap": "30%",
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#00d4ff"},
                            {"offset": 1, "color": "#00d4ff55"}
                        ]
                    },
                    "borderRadius": [8, 8, 0, 0]
                },
                "label": {
                    "show": True, "position": "top",
                    "fontSize": 12, "fontWeight": "bold", "color": "#00d4ff",
                    "formatter": "{c}"
                }
            },
            {
                "name": f"📅 {lbl_b}",
                "type": "bar",
                "data": kh_comp_vals,
                "barMaxWidth": 40,
                "itemStyle": {
                    "color": {
                        "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#e040fb"},
                            {"offset": 1, "color": "#e040fb55"}
                        ]
                    },
                    "borderRadius": [8, 8, 0, 0]
                },
                "label": {
                    "show": True, "position": "top",
                    "fontSize": 12, "fontWeight": "bold", "color": "#e040fb",
                    "formatter": "{c}"
                }
            }
        ]
    }

    altura_vs = max(420, 350 + len(nombres) * 15)
    st_echarts(options=options_vs, height=f"{altura_vs}px")

    # === TABLA DETALLE V/S POR SALA ===
    st.markdown("##### 📋 Detalle Comparativo por Sala")

    for sala in todas_salas:
        sa = salas_principal.get(sala)
        sc = salas_comp.get(sala)

        prom_a = (sa['kg_hora_sum'] / sa['kg_hora_count']) if sa and sa['kg_hora_count'] > 0 else 0
        prom_b = (sc['kg_hora_sum'] / sc['kg_hora_count']) if sc and sc['kg_hora_count'] > 0 else 0
        kg_a_s = sa['total_kg'] if sa else 0
        kg_b_s = sc['total_kg'] if sc else 0
        ord_a_s = len(sa['ordenes']) if sa else 0
        ord_b_s = len(sc['ordenes']) if sc else 0

        diff_kh = prom_a - prom_b
        diff_color = "#4caf50" if diff_kh >= 0 else "#f44336"
        diff_icon = "▲" if diff_kh >= 0 else "▼"

        with st.container(border=True):
            tc1, tc2, tc3, tc4, tc5 = st.columns([2, 1.5, 1.5, 1.5, 1])
            with tc1:
                st.markdown(f"**🏭 {sala}**")
            with tc2:
                st.metric(f"⚡ {lbl_a}", f"{prom_a:,.0f} kg/h")
            with tc3:
                st.metric(f"⚡ {lbl_b}", f"{prom_b:,.0f} kg/h")
            with tc4:
                st.metric("⚖️ KG", f"{kg_a_s:,.0f} vs {kg_b_s:,.0f}")
            with tc5:
                st.markdown(f"""
                <div style="text-align: center; padding-top: 10px;">
                    <span style="color: {diff_color}; font-size: 22px; font-weight: bold;">
                        {diff_icon} {abs(diff_kh):,.0f}
                    </span>
                    <br>
                    <span style="color: #aaa; font-size: 11px;">kg/h dif.</span>
                </div>
                """, unsafe_allow_html=True)