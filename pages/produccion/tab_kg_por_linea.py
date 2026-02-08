"""
Tab KG por Línea: Productividad por sala de proceso.
Muestra cada orden de fabricación individual con sus KPIs de Odoo.
Diseño visual y explicativo.
"""
import streamlit as st
import httpx
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from streamlit_echarts import st_echarts
from .shared import API_URL


def fetch_datos_salas(username: str, password: str, fecha_inicio: str, 
                      fecha_fin: str, solo_terminadas: bool = False) -> Dict[str, Any]:
    """Obtiene datos de productividad por sala."""
    params = {
        "username": username,
        "password": password,
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "solo_terminadas": solo_terminadas
    }
    
    response = httpx.get(f"{API_URL}/api/v1/rendimiento/dashboard",
                         params=params, timeout=120.0)
    response.raise_for_status()
    return response.json()


def render_kpis_principales(mos: List[Dict]) -> None:
    """Muestra KPIs principales con diseño atractivo."""
    
    # Calcular totales
    total_ordenes = len(mos)
    total_kg = sum(mo.get('kg_pt', 0) or 0 for mo in mos)
    
    # Promedios de campos de Odoo
    kg_hora_values = [mo.get('kg_hora_efectiva', 0) or 0 for mo in mos if mo.get('kg_hora_efectiva', 0) > 0]
    kg_hh_values = [mo.get('kg_hh_efectiva', 0) or 0 for mo in mos if mo.get('kg_hh_efectiva', 0) > 0]
    
    prom_kg_hora = sum(kg_hora_values) / len(kg_hora_values) if kg_hora_values else 0
    prom_kg_hh = sum(kg_hh_values) / len(kg_hh_values) if kg_hh_values else 0
    
    # Salas únicas
    salas_unicas = len(set(mo.get('sala', 'Sin Sala') for mo in mos))
    
    st.markdown("""
    <style>
    .kpi-card-kg {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        border: 1px solid #0f3460;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: transform 0.3s ease;
    }
    .kpi-card-kg:hover { transform: translateY(-5px); }
    .kpi-icon-kg { font-size: 2.5rem; margin-bottom: 8px; }
    .kpi-value-kg { font-size: 2rem; font-weight: bold; margin: 8px 0; }
    .kpi-label-kg { font-size: 0.9rem; color: #aaa; text-transform: uppercase; }
    .kpi-blue .kpi-value-kg { color: #00d4ff; }
    .kpi-green .kpi-value-kg { color: #00ff88; }
    .kpi-orange .kpi-value-kg { color: #ff9f43; }
    .kpi-purple .kpi-value-kg { color: #a855f7; }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="kpi-card-kg kpi-blue">
            <div class="kpi-icon-kg">📋</div>
            <div class="kpi-value-kg">{total_ordenes:,}</div>
            <div class="kpi-label-kg">Órdenes de Producción</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="kpi-card-kg kpi-green">
            <div class="kpi-icon-kg">📦</div>
            <div class="kpi-value-kg">{total_kg:,.0f}</div>
            <div class="kpi-label-kg">KG Producidos</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="kpi-card-kg kpi-orange">
            <div class="kpi-icon-kg">⚡</div>
            <div class="kpi-value-kg">{prom_kg_hora:,.1f}</div>
            <div class="kpi-label-kg">KG/Hora Promedio</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="kpi-card-kg kpi-purple">
            <div class="kpi-icon-kg">🏭</div>
            <div class="kpi-value-kg">{salas_unicas}</div>
            <div class="kpi-label-kg">Líneas Activas</div>
        </div>
        """, unsafe_allow_html=True)


def render_grafico_barras_salas(mos: List[Dict]) -> None:
    """Gráfico de barras por sala con diseño 3D."""
    if not mos:
        st.info("No hay datos para el gráfico")
        return
    
    # Agrupar por sala para el gráfico principal
    salas_data = {}
    for mo in mos:
        sala = mo.get('sala', 'Sin Sala') or 'Sin Sala'
        if sala not in salas_data:
            salas_data[sala] = {'kg_hora_sum': 0, 'count': 0, 'kg_total': 0}
        kg_hora = mo.get('kg_hora_efectiva', 0) or 0
        if kg_hora > 0:
            salas_data[sala]['kg_hora_sum'] += kg_hora
            salas_data[sala]['count'] += 1
        salas_data[sala]['kg_total'] += mo.get('kg_pt', 0) or 0
    
    # Calcular promedios y ordenar
    datos_grafico = []
    for sala, data in salas_data.items():
        prom = data['kg_hora_sum'] / data['count'] if data['count'] > 0 else 0
        if prom > 0:
            datos_grafico.append({
                'sala': sala[:20],
                'kg_hora': round(prom, 1),
                'kg_total': data['kg_total'],
                'ordenes': data['count']
            })
    
    if not datos_grafico:
        st.info("No hay datos con KG/Hora para mostrar")
        return
    
    # Ordenar por KG/Hora
    datos_grafico.sort(key=lambda x: x['kg_hora'], reverse=True)
    datos_grafico = datos_grafico[:15]
    
    salas = [d['sala'] for d in datos_grafico]
    valores = [d['kg_hora'] for d in datos_grafico]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
            "backgroundColor": "rgba(20,20,40,0.95)",
            "borderColor": "#0f3460",
            "textStyle": {"color": "#fff"},
            "formatter": "{b}<br/>⚡ <b>{c} KG/Hora</b>"
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
                "fontSize": 11,
                "rotate": 35,
                "interval": 0
            },
            "axisLine": {"lineStyle": {"color": "#444"}}
        },
        "yAxis": {
            "type": "value",
            "name": "KG/Hora",
            "nameTextStyle": {"color": "#aaa", "fontSize": 12},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333", "type": "dashed"}}
        },
        "series": [{
            "name": "KG/Hora",
            "type": "bar",
            "data": valores,
            "barWidth": "60%",
            "itemStyle": {
                "borderRadius": [8, 8, 0, 0],
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 0, "y2": 1,
                    "colorStops": [
                        {"offset": 0, "color": "#00d4ff"},
                        {"offset": 0.5, "color": "#0099cc"},
                        {"offset": 1, "color": "#006688"}
                    ]
                }
            },
            "emphasis": {
                "itemStyle": {
                    "color": {
                        "type": "linear",
                        "x": 0, "y": 0, "x2": 0, "y2": 1,
                        "colorStops": [
                            {"offset": 0, "color": "#00ff88"},
                            {"offset": 1, "color": "#00aa55"}
                        ]
                    }
                }
            },
            "label": {
                "show": True,
                "position": "top",
                "color": "#00d4ff",
                "fontSize": 12,
                "fontWeight": "bold",
                "formatter": "{c}"
            }
        }]
    }
    
    st_echarts(options=options, height="400px")


def render_grafico_pie_kg(mos: List[Dict]) -> None:
    """Gráfico circular mostrando distribución de KG por sala."""
    if not mos:
        return
    
    # Agrupar KG por sala
    salas_kg = {}
    for mo in mos:
        sala = mo.get('sala', 'Sin Sala') or 'Sin Sala'
        salas_kg[sala] = salas_kg.get(sala, 0) + (mo.get('kg_pt', 0) or 0)
    
    # Convertir a lista y ordenar
    datos = [{"name": k[:18], "value": round(v, 0)} for k, v in salas_kg.items() if v > 0]
    datos.sort(key=lambda x: x['value'], reverse=True)
    datos = datos[:10]
    
    if not datos:
        return
    
    options = {
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}<br/>📦 <b>{c:,} KG</b><br/>({d}%)"
        },
        "legend": {
            "orient": "vertical",
            "right": "5%",
            "top": "center",
            "textStyle": {"color": "#ccc", "fontSize": 11}
        },
        "series": [{
            "name": "KG por Sala",
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["40%", "50%"],
            "avoidLabelOverlap": True,
            "itemStyle": {
                "borderRadius": 10,
                "borderColor": "#1a1a2e",
                "borderWidth": 2
            },
            "label": {
                "show": True,
                "color": "#fff",
                "formatter": "{b}\n{d}%"
            },
            "emphasis": {
                "label": {"show": True, "fontSize": 14, "fontWeight": "bold"}
            },
            "data": datos
        }]
    }
    
    st_echarts(options=options, height="350px")


def render_tabla_ordenes(mos: List[Dict], sala_filtro: str = None) -> None:
    """Tabla detallada de cada orden individual."""
    if not mos:
        st.info("No hay órdenes para mostrar")
        return
    
    # Filtrar por sala si se especifica
    if sala_filtro and sala_filtro != "Todas":
        mos = [mo for mo in mos if (mo.get('sala', '') or '').upper() == sala_filtro.upper()]
    
    # Preparar datos para la tabla
    datos = []
    for mo in mos:
        # Extraer fecha de inicio
        inicio = mo.get('inicio_proceso') or mo.get('date_planned_start') or ''
        fecha_str = ''
        hora_str = ''
        if inicio:
            try:
                if 'T' in str(inicio):
                    dt = datetime.fromisoformat(str(inicio).replace('Z', ''))
                else:
                    dt = datetime.strptime(str(inicio)[:19], '%Y-%m-%d %H:%M:%S')
                fecha_str = dt.strftime('%d/%m/%Y')
                hora_str = dt.strftime('%H:%M')
            except:
                fecha_str = str(inicio)[:10] if inicio else ''
        
        kg_hora = mo.get('kg_hora_efectiva', 0) or 0
        kg_hh = mo.get('kg_hh_efectiva', 0) or 0
        
        # Determinar estado con emoji
        estado = mo.get('state', '')
        estado_emoji = {
            'done': '✅ Terminado',
            'progress': '🔄 En Proceso',
            'confirmed': '📋 Confirmado',
            'to_close': '⏳ Por Cerrar',
            'draft': '📝 Borrador'
        }.get(estado, estado)
        
        datos.append({
            '📅 Fecha': fecha_str,
            '🕐 Hora Inicio': hora_str,
            '🏭 Línea': (mo.get('sala', 'Sin Sala') or 'Sin Sala')[:25],
            '📋 Orden': mo.get('name', ''),
            '📦 KG': f"{round(mo.get('kg_pt', 0) or 0, 0):,.0f}",
            '⚡ KG/Hora': f"{kg_hora:,.1f}" if kg_hora > 0 else '-',
            '👷 KG/HH': f"{kg_hh:,.2f}" if kg_hh > 0 else '-',
            '👥 Personas': mo.get('dotacion', '-') or '-',
            '📊 Estado': estado_emoji
        })
    
    if not datos:
        st.info("No hay datos para mostrar con los filtros seleccionados")
        return
    
    df = pd.DataFrame(datos)
    
    # Ordenar por fecha y hora descendente
    df = df.sort_values(['📅 Fecha', '🕐 Hora Inicio'], ascending=[False, False])
    
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=450
    )
    
    # Resumen
    st.markdown(f"""
    <div style="text-align: center; padding: 10px; background: linear-gradient(90deg, #1a1a2e, #16213e); 
                border-radius: 8px; margin-top: 10px; border: 1px solid #0f3460;">
        📊 Mostrando <b style="color: #00d4ff;">{len(datos)}</b> órdenes de producción
    </div>
    """, unsafe_allow_html=True)


def render(username: str = None, password: str = None) -> None:
    """Renderiza el tab de KG por Línea."""
    
    # Header con explicación
    st.markdown("""
    ## 📊 Productividad por Línea de Proceso
    
    <div style="background: linear-gradient(90deg, #1a1a2e, #16213e); padding: 15px; border-radius: 10px; 
                margin-bottom: 20px; border-left: 4px solid #00d4ff;">
        <p style="margin: 0; color: #ccc; line-height: 1.6;">
            📌 <b style="color: #00d4ff;">¿Qué muestra este dashboard?</b><br>
            El rendimiento de cada <b>línea/sala de proceso</b>. Los valores de <b>KG/Hora</b> y <b>KG/Hora-Hombre</b> 
            vienen directamente de Odoo.<br><br>
            🔍 <b style="color: #00ff88;">Cada orden se muestra por separado</b> - Si hay 2 procesos en la misma sala el mismo día, 
            verás cada uno en su propia fila.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Credenciales - usar parámetros o session_state
    if not username:
        username = st.session_state.get("username", "")
    if not password:
        password = st.session_state.get("password", "")
    
    if not username or not password:
        st.warning("⚠️ Debes iniciar sesión para ver este dashboard")
        return
    
    # === FILTROS ===
    st.markdown("### 🔍 Filtros")
    
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
        st.session_state["kg_linea_data"] = None
        
        try:
            with st.spinner("🔄 Cargando datos de productividad..."):
                data = fetch_datos_salas(
                    username, password,
                    fecha_inicio.isoformat(),
                    fecha_fin.isoformat(),
                    solo_terminadas=False
                )
                st.session_state["kg_linea_data"] = data
                st.session_state["kg_linea_loaded"] = True
        except Exception as e:
            st.error(f"❌ Error al cargar datos: {str(e)}")
            return
    
    # === MOSTRAR DATOS ===
    data = st.session_state.get("kg_linea_data")
    
    if not data:
        st.info("👆 Selecciona un rango de fechas y presiona **Buscar** para cargar los datos")
        return
    
    mos = data.get('mos', [])
    
    if not mos:
        st.warning("⚠️ No se encontraron órdenes de producción en el período seleccionado")
        return
    
    # === KPIs PRINCIPALES ===
    render_kpis_principales(mos)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # === GRÁFICOS ===
    col_graf1, col_graf2 = st.columns([3, 2])
    
    with col_graf1:
        st.markdown("""
        ### 📊 KG/Hora Promedio por Línea
        <p style="color: #888; font-size: 0.9rem; margin-bottom: 10px;">
            ⬆️ Barras más altas = Mayor productividad. Este es el <b>promedio</b> de todas las órdenes de cada sala.
        </p>
        """, unsafe_allow_html=True)
        render_grafico_barras_salas(mos)
    
    with col_graf2:
        st.markdown("""
        ### 🥧 Distribución de KG Producidos
        <p style="color: #888; font-size: 0.9rem; margin-bottom: 10px;">
            Proporción de KG que produjo cada línea del total.
        </p>
        """, unsafe_allow_html=True)
        render_grafico_pie_kg(mos)
    
    st.markdown("---")
    
    # === TABLA DETALLADA ===
    st.markdown("""
    ### 📋 Detalle por Orden de Producción
    <p style="color: #888; font-size: 0.9rem;">
        👇 <b>Cada fila = Una orden de fabricación</b>. Si hay varios procesos el mismo día en la misma sala, 
        aparecen por separado. Puedes filtrar por línea específica.
    </p>
    """, unsafe_allow_html=True)
    
    # Filtro de sala
    salas_disponibles = sorted(set(mo.get('sala', 'Sin Sala') or 'Sin Sala' for mo in mos))
    salas_opciones = ["Todas"] + salas_disponibles
    
    col_filtro, col_espacio = st.columns([1, 3])
    with col_filtro:
        sala_sel = st.selectbox(
            "🏭 Filtrar por Línea",
            salas_opciones,
            key="kg_linea_sala_filtro"
        )
    
    render_tabla_ordenes(mos, sala_sel)
