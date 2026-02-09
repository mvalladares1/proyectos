"""
Tab Pallets Disponibles: Muestra pallets con stock que NO están en ninguna fabricación.
Excluye ubicaciones de stock final y cámaras de congelado.
"""
import streamlit as st
import httpx
import pandas as pd
from typing import Dict, List, Any
from streamlit_echarts import st_echarts
from .shared import API_URL


def fetch_pallets_disponibles(username: str, password: str, 
                               planta: str = None) -> Dict[str, Any]:
    """Obtiene pallets disponibles del backend."""
    params = {
        "username": username,
        "password": password,
    }
    if planta and planta != "Todas":
        params["planta"] = planta
    
    response = httpx.get(f"{API_URL}/api/v1/produccion/pallets-disponibles",
                         params=params, timeout=120.0)
    response.raise_for_status()
    return response.json()


def render(username: str = None, password: str = None):
    """Renderiza el tab de Pallets Disponibles."""
    
    if not username or not password:
        username = st.session_state.get("username", "")
        password = st.session_state.get("password", "")
    
    # === HEADER ===
    st.markdown("""
    <div style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); 
                padding: 20px; border-radius: 12px; border-left: 4px solid #e94560;
                margin-bottom: 20px;">
        <h2 style="color: #e94560; margin: 0;">📦 Pallets Disponibles</h2>
        <p style="color: #aaa; margin: 5px 0 0 0;">
            Pallets con stock que <b>NO están asignados</b> a ninguna orden de fabricación
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # === FILTROS ===
    col1, col2 = st.columns([2, 1])
    with col1:
        planta_sel = st.selectbox(
            "🏭 Planta",
            ["Todas", "RIO FUTURO", "VILKUN"],
            key="pallets_disp_planta"
        )
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        btn_buscar = st.button("🔍 Buscar Pallets", type="primary", 
                                use_container_width=True, key="pallets_disp_buscar")
    
    st.markdown("---")
    
    # === CARGAR DATOS ===
    if btn_buscar:
        st.cache_data.clear()
        try:
            with st.spinner("Buscando pallets disponibles..."):
                data = fetch_pallets_disponibles(username, password, planta_sel)
                st.session_state['pallets_disp_data'] = data
                st.session_state['pallets_disp_loaded'] = True
        except Exception as e:
            st.error(f"Error al cargar datos: {str(e)}")
            return
    
    if not st.session_state.get('pallets_disp_loaded', False):
        st.info("👆 Selecciona la planta y presiona **'🔍 Buscar Pallets'** para ver los pallets disponibles")
        return
    
    data = st.session_state.get('pallets_disp_data', {})
    pallets = data.get('pallets', [])
    stats = data.get('estadisticas', {})
    
    if not pallets:
        st.warning("No se encontraron pallets disponibles con los filtros seleccionados")
        return
    
    # === KPIs ===
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.metric("📦 Total Pallets", f"{stats.get('total_pallets', 0):,}")
    with k2:
        st.metric("⚖️ KG Totales", f"{stats.get('total_kg', 0):,.0f}")
    with k3:
        st.metric("❄️ Congelados", f"{stats.get('congelados', 0):,}")
    with k4:
        st.metric("🌿 Frescos", f"{stats.get('frescos', 0):,}")
    
    st.markdown("---")
    
    # === GRÁFICOS ===
    col_g1, col_g2 = st.columns(2)
    
    with col_g1:
        # Gráfico tipo (Congelado vs Fresco)
        render_grafico_tipo(stats)
    
    with col_g2:
        # Gráfico por planta
        render_grafico_planta(data.get('por_planta', {}))
    
    st.markdown("---")
    
    # === GRÁFICO POR UBICACIÓN ===
    render_grafico_ubicacion(pallets)
    
    st.markdown("---")
    
    # === BUSCAR PAQUETE EN ODOO ===
    st.markdown("### 🔗 Buscar Paquete en Odoo")
    
    ODOO_BASE = "https://riofuturo.server98c6e.oerpondemand.net"
    
    col_odoo1, col_odoo2 = st.columns([3, 1])
    with col_odoo1:
        buscar_paquete = st.text_input(
            "📦 Ingresa el nombre del pallet/paquete",
            placeholder="Ej: PACK0012345",
            key="pallets_buscar_odoo"
        )
    with col_odoo2:
        st.markdown("<br>", unsafe_allow_html=True)
        if buscar_paquete:
            # Buscar el pallet en los datos cargados
            pallet_encontrado = None
            for p in pallets:
                if buscar_paquete.upper() in p.get('pallet', '').upper():
                    pallet_encontrado = p
                    break
            
            if pallet_encontrado:
                pallet_id = pallet_encontrado.get('pallet_id', 0)
                odoo_url = f"{ODOO_BASE}/web#id={pallet_id}&model=stock.quant.package&view_type=form"
                st.link_button("🔗 Abrir en Odoo", odoo_url, use_container_width=True)
            else:
                st.warning("No encontrado")
    
    st.markdown("---")
    
    # === TABLA DE PALLETS ===
    st.markdown("### 📋 Detalle de Pallets Disponibles")
    
    # Filtros de tabla
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        tipo_filtro = st.selectbox("Filtrar por tipo", ["Todos", "Congelado", "Fresco"],
                                    key="pallets_tipo_filtro")
    with col_f2:
        buscar_texto = st.text_input("🔎 Buscar pallet/producto/lote", 
                                      key="pallets_buscar_texto")
    
    # Aplicar filtros
    pallets_filtrados = pallets
    if tipo_filtro != "Todos":
        pallets_filtrados = [p for p in pallets_filtrados if p['tipo'] == tipo_filtro]
    if buscar_texto:
        texto = buscar_texto.upper()
        pallets_filtrados = [p for p in pallets_filtrados 
                             if texto in p.get('pallet', '').upper()
                             or texto in p.get('producto', '').upper()
                             or texto in p.get('lote', '').upper()
                             or texto in p.get('ubicacion', '').upper()]
    
    # Crear DataFrame con link a Odoo
    if pallets_filtrados:
        df_data = []
        for p in pallets_filtrados:
            pid = p.get('pallet_id', 0)
            odoo_link = f"{ODOO_BASE}/web#id={pid}&model=stock.quant.package&view_type=form"
            df_data.append({
                'Pallet': p.get('pallet', ''),
                'Lote': p.get('lote', ''),
                'Producto': p.get('producto', ''),
                'KG': p.get('cantidad_kg', 0),
                'Ubicación': p.get('ubicacion', ''),
                'Tipo': p.get('tipo', ''),
                'Planta': p.get('planta', ''),
                'Fecha Ingreso': p.get('fecha_ingreso', ''),
                'Ver en Odoo': odoo_link
            })
        
        df = pd.DataFrame(df_data)
        df['KG'] = df['KG'].apply(lambda x: f"{x:,.1f}")
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            height=500,
            column_config={
                "Pallet": st.column_config.TextColumn("📦 Pallet", width="medium"),
                "Lote": st.column_config.TextColumn("🏷️ Lote", width="medium"),
                "Producto": st.column_config.TextColumn("📋 Producto", width="large"),
                "KG": st.column_config.TextColumn("⚖️ KG", width="small"),
                "Ubicación": st.column_config.TextColumn("📍 Ubicación", width="medium"),
                "Tipo": st.column_config.TextColumn("🔄 Tipo", width="small"),
                "Planta": st.column_config.TextColumn("🏭 Planta", width="small"),
                "Fecha Ingreso": st.column_config.TextColumn("📅 Ingreso", width="small"),
                "Ver en Odoo": st.column_config.LinkColumn("🔗 Odoo", width="small", display_text="Abrir"),
            }
        )
        
        st.caption(f"Mostrando **{len(pallets_filtrados)}** pallets de {len(pallets)} totales")
    else:
        st.info("No hay pallets que coincidan con los filtros")


def render_grafico_tipo(stats: Dict):
    """Gráfico de dona: Congelado vs Fresco."""
    st.markdown("#### ❄️🌿 Tipo de Pallet")
    
    congelados = stats.get('congelados', 0)
    frescos = stats.get('frescos', 0)
    
    if congelados == 0 and frescos == 0:
        st.info("Sin datos")
        return
    
    options = {
        "tooltip": {
            "trigger": "item",
            "formatter": "{b}: {c} pallets ({d}%)"
        },
        "legend": {
            "bottom": "0%",
            "textStyle": {"color": "#ddd"}
        },
        "series": [{
            "type": "pie",
            "radius": ["40%", "70%"],
            "center": ["50%", "45%"],
            "avoidLabelOverlap": True,
            "itemStyle": {"borderRadius": 8, "borderColor": "#1a1a2e", "borderWidth": 2},
            "label": {
                "show": True,
                "formatter": "{b}\n{c} pallets",
                "color": "#ddd"
            },
            "data": [
                {"value": congelados, "name": "❄️ Congelado", 
                 "itemStyle": {"color": "#4fc3f7"}},
                {"value": frescos, "name": "🌿 Fresco", 
                 "itemStyle": {"color": "#81c784"}},
            ]
        }]
    }
    
    st_echarts(options=options, height="280px")


def render_grafico_planta(por_planta: Dict):
    """Gráfico de barras: Pallets por planta."""
    st.markdown("#### 🏭 Pallets por Planta")
    
    if not por_planta:
        st.info("Sin datos")
        return
    
    plantas = list(por_planta.keys())
    cantidades = [len(v) for v in por_planta.values()]
    kg_totales = [sum(p['cantidad_kg'] for p in v) for v in por_planta.values()]
    
    colores = {
        'RIO FUTURO': '#4ecdc4',
        'VILKUN': '#ff6b6b',
    }
    
    colors = [colores.get(p, '#ffd93d') for p in plantas]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"}
        },
        "grid": {"left": "5%", "right": "5%", "bottom": "15%", "top": "10%", "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": plantas,
            "axisLabel": {"color": "#ddd", "fontSize": 12}
        },
        "yAxis": {
            "type": "value",
            "name": "Cantidad",
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "series": [
            {
                "name": "Pallets",
                "type": "bar",
                "data": [{"value": c, "itemStyle": {"color": colors[i]}} 
                         for i, c in enumerate(cantidades)],
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": "{c} pallets",
                    "color": "#fff",
                    "fontSize": 12
                },
                "barWidth": "50%"
            }
        ]
    }
    
    st_echarts(options=options, height="280px")


def render_grafico_ubicacion(pallets: List[Dict]):
    """Gráfico de barras horizontales: Top ubicaciones con más pallets."""
    st.markdown("### 📍 Pallets por Ubicación")
    st.caption("Top ubicaciones con más pallets disponibles")
    
    # Agrupar por ubicación
    ubicaciones = {}
    for p in pallets:
        ub = p.get('ubicacion', 'Sin ubicación')
        if ub not in ubicaciones:
            ubicaciones[ub] = {'pallets': 0, 'kg': 0}
        ubicaciones[ub]['pallets'] += 1
        ubicaciones[ub]['kg'] += p.get('cantidad_kg', 0)
    
    # Ordenar por cantidad de pallets y tomar top 15
    top_ub = sorted(ubicaciones.items(), key=lambda x: x[1]['pallets'], reverse=True)[:15]
    top_ub.reverse()  # Para que el más grande quede arriba en barras horizontales
    
    nombres = [u[0][-35:] for u in top_ub]  # Truncar nombres largos
    cantidades = [u[1]['pallets'] for u in top_ub]
    kg_list = [round(u[1]['kg'], 0) for u in top_ub]
    
    options = {
        "tooltip": {
            "trigger": "axis",
            "axisPointer": {"type": "shadow"},
        },
        "grid": {"left": "30%", "right": "10%", "bottom": "5%", "top": "5%", "containLabel": False},
        "xAxis": {
            "type": "value",
            "name": "Pallets",
            "nameLocation": "middle",
            "nameGap": 30,
            "nameTextStyle": {"color": "#aaa"},
            "axisLabel": {"color": "#ccc"},
            "splitLine": {"lineStyle": {"color": "#333"}}
        },
        "yAxis": {
            "type": "category",
            "data": nombres,
            "axisLabel": {"color": "#ddd", "fontSize": 10},
        },
        "series": [{
            "name": "Pallets",
            "type": "bar",
            "data": cantidades,
            "label": {
                "show": True,
                "position": "right",
                "formatter": "{c}",
                "color": "#fff",
                "fontSize": 11
            },
            "itemStyle": {
                "color": {
                    "type": "linear",
                    "x": 0, "y": 0, "x2": 1, "y2": 0,
                    "colorStops": [
                        {"offset": 0, "color": "#e94560"},
                        {"offset": 1, "color": "#f39c12"}
                    ]
                },
                "borderRadius": [0, 4, 4, 0]
            }
        }]
    }
    
    st_echarts(options=options, height=f"{max(300, len(top_ub) * 30)}px")
