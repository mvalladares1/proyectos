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


def _render_grafico_salas(salas_data: Dict[str, Dict]):
    """Gráfico de barras comparativo: KG/Hora, KG Totales y Órdenes por sala."""
    if not salas_data:
        return

    # Ordenar salas por KG/Hora promedio descendente
    salas_sorted = sorted(
        salas_data.items(),
        key=lambda x: (x[1]['kg_hora_sum'] / x[1]['kg_hora_count'])
        if x[1]['kg_hora_count'] > 0 else 0,
        reverse=True
    )

    nombres = []
    kg_hora_vals = []
    kg_total_vals = []
    ordenes_vals = []
    hechas_vals = []
    no_hechas_vals = []

    for sala, sd in salas_sorted:
        nombres.append(sala)
        prom = sd['kg_hora_sum'] / sd['kg_hora_count'] if sd['kg_hora_count'] > 0 else 0
        kg_hora_vals.append(round(prom))
        kg_total_vals.append(round(sd['total_kg']))
        ordenes_vals.append(sd['hechas'] + sd['no_hechas'])
        hechas_vals.append(sd['hechas'])
        no_hechas_vals.append(sd['no_hechas'])

    # Colores por rendimiento
    colores_barra = [color_kg_hora(v) for v in kg_hora_vals]
    data_kg_hora = []
    for i, v in enumerate(kg_hora_vals):
        data_kg_hora.append({
            "value": v,
            "itemStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": colores_barra[i]},
                        {"offset": 1, "color": colores_barra[i] + "66"}
                    ]
                },
                "borderRadius": [8, 8, 0, 0]
            }
        })

    options = {
        "title": {
            "text": "⚡ Comparativa de Rendimiento por Sala",
            "subtext": "KG/Hora promedio · KG totales procesados · Órdenes completadas vs en proceso",
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
            "extraCssText": "box-shadow: 0 4px 20px rgba(0,0,0,0.5);",
            "formatter": None  # will use default multi-series
        },
        "legend": {
            "data": ["⚡ KG/Hora Prom", "✅ Órdenes Hechas", "🔄 En Proceso"],
            "bottom": 0,
            "textStyle": {"color": "#ccc", "fontSize": 12},
            "itemGap": 25,
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
        "yAxis": [
            {
                "type": "value",
                "name": "⚡ KG / Hora",
                "nameTextStyle": {"color": "#aaa", "fontSize": 13, "fontWeight": "bold"},
                "axisLabel": {"color": "#ccc", "fontSize": 11,
                              "formatter": "{value}"},
                "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}},
                "axisLine": {"show": False}
            },
            {
                "type": "value",
                "name": "📋 Órdenes",
                "nameTextStyle": {"color": "#aaa", "fontSize": 13, "fontWeight": "bold"},
                "axisLabel": {"color": "#ccc", "fontSize": 11},
                "splitLine": {"show": False},
                "axisLine": {"show": False}
            }
        ],
        "series": [
            {
                "name": "⚡ KG/Hora Prom",
                "type": "bar",
                "data": data_kg_hora,
                "barMaxWidth": 50,
                "yAxisIndex": 0,
                "label": {
                    "show": True,
                    "position": "top",
                    "fontSize": 13,
                    "fontWeight": "bold",
                    "color": "#fff",
                    "formatter": "{c} kg/h"
                },
                "emphasis": {
                    "itemStyle": {"shadowBlur": 15, "shadowColor": "rgba(0,200,255,0.4)"}
                }
            },
            {
                "name": "✅ Órdenes Hechas",
                "type": "bar",
                "data": hechas_vals,
                "yAxisIndex": 1,
                "barMaxWidth": 30,
                "itemStyle": {
                    "color": "#4caf50",
                    "borderRadius": [6, 6, 0, 0]
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "fontSize": 11,
                    "fontWeight": "bold",
                    "color": "#4caf50"
                }
            },
            {
                "name": "🔄 En Proceso",
                "type": "bar",
                "data": no_hechas_vals,
                "yAxisIndex": 1,
                "barMaxWidth": 30,
                "itemStyle": {
                    "color": "#ff9800",
                    "borderRadius": [6, 6, 0, 0]
                },
                "label": {
                    "show": True,
                    "position": "top",
                    "fontSize": 11,
                    "fontWeight": "bold",
                    "color": "#ff9800"
                }
            }
        ],
        "dataZoom": [
            {"type": "inside", "xAxisIndex": 0, "start": 0, "end": 100}
        ] if len(nombres) > 8 else []
    }

    # KG Totales como gráfico separado debajo para que no sature el principal
    altura = max(420, 350 + len(nombres) * 15)
    st_echarts(options=options, height=f"{altura}px")

    # === GRÁFICO 2: KG TOTALES POR SALA ===
    data_kg_total = []
    for i, v in enumerate(kg_total_vals):
        c = colores_barra[i]
        data_kg_total.append({
            "value": v,
            "itemStyle": {
                "color": {
                    "type": "linear", "x": 0, "y": 0, "x2": 1, "y2": 0,
                    "colorStops": [
                        {"offset": 0, "color": c + "66"},
                        {"offset": 1, "color": c}
                    ]
                },
                "borderRadius": [0, 8, 8, 0]
            }
        })

    options_kg = {
        "title": {
            "text": "⚖️ KG Totales Procesados por Sala",
            "subtext": "Kilogramos de producto terminado producidos en el período",
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
            "extraCssText": "box-shadow: 0 4px 20px rgba(0,0,0,0.5);",
            "formatter": "{b}: {c} KG"
        },
        "grid": {
            "left": "3%", "right": "12%",
            "bottom": "5%", "top": "18%",
            "containLabel": True
        },
        "xAxis": {
            "type": "value",
            "name": "⚖️ KG Totales",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": "#aaa", "fontSize": 13, "fontWeight": "bold"},
            "axisLabel": {"color": "#ccc", "fontSize": 11,
                          "formatter": "{value}"},
            "splitLine": {"lineStyle": {"color": "#2a2a4a", "type": "dashed"}}
        },
        "yAxis": {
            "type": "category",
            "data": list(reversed(nombres)),
            "axisLabel": {"color": "#eee", "fontSize": 12, "fontWeight": "bold"},
            "axisLine": {"lineStyle": {"color": "#444"}},
            "axisTick": {"show": False}
        },
        "series": [{
            "type": "bar",
            "data": list(reversed(data_kg_total)),
            "barMaxWidth": 32,
            "label": {
                "show": True,
                "position": "right",
                "color": "#fff",
                "fontSize": 13,
                "fontWeight": "bold",
                "formatter": "{c} kg"
            }
        }]
    }

    altura_kg = max(250, 50 + len(nombres) * 40)
    st_echarts(options=options_kg, height=f"{altura_kg}px")


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

    # === GRÁFICO COMPARATIVO POR SALA ===
    _render_grafico_salas(salas_data)

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
