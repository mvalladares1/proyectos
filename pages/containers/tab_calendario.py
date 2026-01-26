"""
Tab de Calendario de Pedidos - Vista Timeline/Gantt
Visualización tipo calendario de todos los pedidos con su avance, cliente, fruta y manejo.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Dict
import calendar

from .shared import (
    fetch_containers, STATE_OPTIONS, API_URL,
    get_state_color, get_sale_state_display,
    get_date_urgency_color, get_odoo_link, format_date_with_urgency
)
import httpx


def fetch_all_pedidos(username: str, password: str, start_date: str, end_date: str) -> List[Dict]:
    """
    Obtiene todos los pedidos (progreso + proyecciones) para vista calendario.
    """
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": start_date,
            "end_date": end_date
        }
        
        # Llamar al endpoint de proyecciones que trae todos los pedidos
        response = httpx.get(
            f"{API_URL}/api/v1/containers/proyecciones",
            params=params,
            timeout=60.0
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al obtener pedidos: {str(e)}")
        return []


def get_color_by_avance(avance: float) -> str:
    """Retorna color según porcentaje de avance."""
    if avance >= 100:
        return "#2ecc71"  # Verde - Completado
    elif avance >= 75:
        return "#3498db"  # Azul - Alto avance
    elif avance >= 50:
        return "#f39c12"  # Naranja - Medio avance
    elif avance >= 25:
        return "#e67e22"  # Naranja oscuro - Bajo avance
    else:
        return "#e74c3c"  # Rojo - Sin avance o muy bajo


def get_producto_principal_nombre(lineas: List[Dict]) -> str:
    """Extrae el nombre del producto principal de las líneas."""
    if not lineas:
        return "Sin producto"
    
    # Buscar la línea con mayor cantidad
    linea_principal = max(lineas, key=lambda x: x.get("product_uom_qty", 0))
    prod = linea_principal.get("product_id", {})
    
    if isinstance(prod, dict):
        return prod.get("name", "N/A")
    elif isinstance(prod, (list, tuple)) and len(prod) > 1:
        return prod[1]
    return "N/A"


def get_sala_proceso(productions: List[Dict]) -> str:
    """Extrae la sala de proceso de las fabricaciones."""
    if not productions:
        return "—"
    
    salas = set()
    for prod in productions:
        sala = prod.get("sala_proceso", "")
        if sala and sala != "N/A":
            salas.add(sala)
    
    return ", ".join(sorted(salas)) if salas else "—"


def render_gantt_chart(pedidos: List[Dict]):
    """Renderiza un Gantt Chart de los pedidos."""
    
    if not pedidos:
        st.info("No hay pedidos para mostrar en el Gantt")
        return
    
    # Preparar datos para Gantt
    gantt_data = []
    
    for p in pedidos:
        # Fechas
        commitment = p.get("commitment_date") or p.get("date_order")
        if not commitment:
            continue
        
        try:
            if 'T' in str(commitment):
                fecha_entrega = datetime.fromisoformat(str(commitment).replace('Z', '+00:00'))
            else:
                fecha_entrega = datetime.strptime(str(commitment)[:10], '%Y-%m-%d')
        except:
            continue
        
        # Calcular fecha inicio (fecha_entrega - días según kg)
        kg_total = p.get("kg_total", 0)
        dias_estimados = max(1, int(kg_total / 5000))  # Estimar 5000 kg/día
        fecha_inicio = fecha_entrega - timedelta(days=dias_estimados)
        
        avance = p.get("avance_pct", 0)
        producto = get_producto_principal_nombre(p.get("lineas", []))
        sala = get_sala_proceso(p.get("productions", []))
        
        gantt_data.append({
            "Pedido": p.get("name", "N/A"),
            "Cliente": p.get("partner_name", "N/A")[:30],  # Truncar para legibilidad
            "Inicio": fecha_inicio,
            "Fin": fecha_entrega,
            "Avance": avance,
            "KG Total": kg_total,
            "Producto": producto[:40],
            "Sala": sala,
            "Estado": get_sale_state_display(p.get("state", "")),
            "Color": get_color_by_avance(avance)
        })
    
    if not gantt_data:
        st.info("No hay pedidos con fechas válidas para mostrar")
        return
    
    df_gantt = pd.DataFrame(gantt_data)
    
    # Crear Gantt Chart usando plotly
    fig = go.Figure()
    
    # Ordenar por fecha de fin
    df_gantt = df_gantt.sort_values("Fin")
    
    for idx, row in df_gantt.iterrows():
        # Barra de tiempo total (gris claro)
        fig.add_trace(go.Bar(
            name="",
            x=[row["Fin"] - row["Inicio"]],
            y=[f"{row['Pedido']} - {row['Cliente']}"],
            base=row["Inicio"],
            orientation='h',
            marker=dict(color='rgba(200, 200, 200, 0.3)'),
            showlegend=False,
            hovertemplate=(
                f"<b>{row['Pedido']}</b><br>"
                f"Cliente: {row['Cliente']}<br>"
                f"Producto: {row['Producto']}<br>"
                f"Sala: {row['Sala']}<br>"
                f"KG: {row['KG Total']:,.0f}<br>"
                f"Estado: {row['Estado']}<br>"
                f"Avance: {row['Avance']:.1f}%<br>"
                f"Inicio estimado: {row['Inicio'].strftime('%Y-%m-%d')}<br>"
                f"Entrega: {row['Fin'].strftime('%Y-%m-%d')}<br>"
                "<extra></extra>"
            )
        ))
        
        # Barra de avance (color según progreso)
        if row["Avance"] > 0:
            duracion_total = (row["Fin"] - row["Inicio"]).total_seconds()
            duracion_avance = duracion_total * (row["Avance"] / 100)
            
            fig.add_trace(go.Bar(
                name="",
                x=[timedelta(seconds=duracion_avance)],
                y=[f"{row['Pedido']} - {row['Cliente']}"],
                base=row["Inicio"],
                orientation='h',
                marker=dict(color=row["Color"]),
                showlegend=False,
                hovertemplate=(
                    f"<b>{row['Pedido']}</b><br>"
                    f"Avance: {row['Avance']:.1f}%<br>"
                    "<extra></extra>"
                )
            ))
    
    # Agregar línea vertical para "hoy"
    fig.add_vline(
        x=datetime.now().timestamp() * 1000,
        line_dash="dash",
        line_color="red",
        annotation_text="Hoy",
        annotation_position="top"
    )
    
    fig.update_layout(
        title="Timeline de Pedidos de Venta",
        xaxis_title="Fecha",
        yaxis_title="Pedido - Cliente",
        height=max(600, len(df_gantt) * 40),
        barmode='overlay',
        showlegend=False,
        hovermode='closest',
        xaxis=dict(
            type='date',
            tickformat='%Y-%m-%d'
        )
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_calendario_mensual(pedidos: List[Dict], fecha_vista: datetime):
    """Renderiza un calendario mensual con los pedidos."""
    
    # Filtrar pedidos del mes seleccionado
    pedidos_mes = []
    for p in pedidos:
        commitment = p.get("commitment_date") or p.get("date_order")
        if not commitment:
            continue
        
        try:
            if 'T' in str(commitment):
                fecha = datetime.fromisoformat(str(commitment).replace('Z', '+00:00'))
            else:
                fecha = datetime.strptime(str(commitment)[:10], '%Y-%m-%d')
            
            if fecha.year == fecha_vista.year and fecha.month == fecha_vista.month:
                pedidos_mes.append({**p, "_fecha_parsed": fecha})
        except:
            continue
    
    # Crear calendario
    cal = calendar.monthcalendar(fecha_vista.year, fecha_vista.month)
    
    st.markdown(f"### 📅 {calendar.month_name[fecha_vista.month]} {fecha_vista.year}")
    
    # Crear tabla de calendario
    dias_semana = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    
    # Header
    cols = st.columns(7)
    for i, dia in enumerate(dias_semana):
        with cols[i]:
            st.markdown(f"**{dia}**")
    
    # Semanas
    for semana in cal:
        cols = st.columns(7)
        for i, dia in enumerate(semana):
            with cols[i]:
                if dia == 0:
                    st.markdown("&nbsp;")
                else:
                    # Buscar pedidos de este día
                    pedidos_dia = [
                        p for p in pedidos_mes 
                        if p["_fecha_parsed"].day == dia
                    ]
                    
                    # Color de fondo según si hay pedidos
                    if pedidos_dia:
                        total_kg = sum(p.get("kg_total", 0) for p in pedidos_dia)
                        avance_promedio = sum(p.get("avance_pct", 0) for p in pedidos_dia) / len(pedidos_dia)
                        
                        color = get_color_by_avance(avance_promedio)
                        
                        st.markdown(
                            f"""
                            <div style="
                                background-color: {color}22;
                                border-left: 4px solid {color};
                                padding: 8px;
                                border-radius: 4px;
                                margin-bottom: 4px;
                            ">
                                <div style="font-weight: bold; font-size: 18px;">{dia}</div>
                                <div style="font-size: 11px;">📦 {len(pedidos_dia)} pedido(s)</div>
                                <div style="font-size: 11px;">📊 {total_kg:,.0f} kg</div>
                                <div style="font-size: 11px;">⚡ {avance_promedio:.0f}%</div>
                            </div>
                            """,
                            unsafe_allow_html=True
                        )
                        
                        # Detalle en expander
                        with st.expander(f"Ver pedidos del {dia}"):
                            for p in pedidos_dia:
                                st.markdown(
                                    f"""
                                    **{p.get('name')}** - {p.get('partner_name', 'N/A')[:30]}  
                                    🍇 {get_producto_principal_nombre(p.get('lineas', []))}  
                                    📊 {p.get('kg_total', 0):,.0f} kg | {p.get('avance_pct', 0):.1f}% avance  
                                    🏭 {get_sala_proceso(p.get('productions', []))}
                                    """
                                )
                                st.divider()
                    else:
                        st.markdown(
                            f"""
                            <div style="
                                padding: 8px;
                                color: #888;
                            ">
                                {dia}
                            </div>
                            """,
                            unsafe_allow_html=True
                        )


def render(username: str, password: str):
    """Renderiza el tab de Calendario de Pedidos."""
    
    st.markdown("### 📅 Vista de Calendario")
    st.markdown("Visualización temporal de todos los pedidos con su estado, avance y detalles")
    
    # =========================================================================
    # FILTROS Y CONTROLES
    # =========================================================================
    col_control1, col_control2, col_control3 = st.columns([2, 2, 1])
    
    with col_control1:
        fecha_inicio = st.date_input(
            "Fecha Inicio",
            value=(datetime.now() - timedelta(days=30)).date(),
            key="cal_fecha_inicio"
        )
    
    with col_control2:
        fecha_fin = st.date_input(
            "Fecha Fin",
            value=(datetime.now() + timedelta(days=90)).date(),
            key="cal_fecha_fin"
        )
    
    with col_control3:
        buscar = st.button("🔄 Actualizar", type="primary", use_container_width=True, key="btn_actualizar_cal")
    
    # =========================================================================
    # CARGAR DATOS
    # =========================================================================
    if buscar or "calendario_data" not in st.session_state:
        with st.spinner("📊 Cargando pedidos..."):
            pedidos = fetch_all_pedidos(
                username, password,
                start_date=fecha_inicio.isoformat(),
                end_date=fecha_fin.isoformat()
            )
            st.session_state["calendario_data"] = pedidos
            
            if pedidos:
                st.success(f"✓ {len(pedidos)} pedidos cargados")
            else:
                st.warning("No se encontraron pedidos en el período")
    
    pedidos = st.session_state.get("calendario_data", [])
    
    if not pedidos:
        st.info("👆 Haz clic en 'Actualizar' para cargar los pedidos")
        return
    
    st.divider()
    
    # =========================================================================
    # KPIs RÁPIDOS
    # =========================================================================
    col_kpi1, col_kpi2, col_kpi3, col_kpi4, col_kpi5 = st.columns(5)
    
    total_pedidos = len(pedidos)
    total_kg = sum(p.get("kg_total", 0) for p in pedidos)
    kg_producidos = sum(p.get("kg_producidos", 0) for p in pedidos)
    avance_global = (kg_producidos / total_kg * 100) if total_kg > 0 else 0
    clientes_unicos = len(set(p.get("partner_name", "N/A") for p in pedidos))
    
    with col_kpi1:
        st.metric("📋 Total Pedidos", f"{total_pedidos:,}")
    
    with col_kpi2:
        st.metric("📦 KG Totales", f"{total_kg:,.0f}")
    
    with col_kpi3:
        st.metric("✅ KG Producidos", f"{kg_producidos:,.0f}")
    
    with col_kpi4:
        st.metric("📊 Avance Global", f"{avance_global:.1f}%")
    
    with col_kpi5:
        st.metric("👥 Clientes", clientes_unicos)
    
    st.divider()
    
    # =========================================================================
    # SELECCIÓN DE VISTA
    # =========================================================================
    vista_tab1, vista_tab2, vista_tab3 = st.tabs([
        "📊 Timeline / Gantt",
        "📅 Calendario Mensual",
        "📋 Tabla Detallada"
    ])
    
    # --- Vista 1: Timeline/Gantt ---
    with vista_tab1:
        render_gantt_chart(pedidos)
    
    # --- Vista 2: Calendario Mensual ---
    with vista_tab2:
        col_mes1, col_mes2 = st.columns([1, 4])
        
        with col_mes1:
            mes_vista = st.date_input(
                "Mes a visualizar",
                value=datetime.now().date(),
                key="mes_calendario"
            )
        
        render_calendario_mensual(pedidos, datetime.combine(mes_vista, datetime.min.time()))
    
    # --- Vista 3: Tabla Detallada ---
    with vista_tab3:
        st.markdown("#### 📋 Todos los Pedidos - Vista Detallada")
        
        # Preparar datos para tabla
        tabla_data = []
        for p in pedidos:
            commitment = p.get("commitment_date") or p.get("date_order") or "—"
            
            tabla_data.append({
                "SO": p.get("name", "N/A"),
                "Cliente": p.get("partner_name", "N/A"),
                "Producto": get_producto_principal_nombre(p.get("lineas", [])),
                "Sala": get_sala_proceso(p.get("productions", [])),
                "Fecha Entrega": format_date_with_urgency(commitment),
                "KG Total": p.get("kg_total", 0),
                "KG Producidos": p.get("kg_producidos", 0),
                "Avance %": p.get("avance_pct", 0),
                "Estado": get_sale_state_display(p.get("state", "")),
                "# Fabricaciones": p.get("num_fabricaciones", 0)
            })
        
        df_tabla = pd.DataFrame(tabla_data)
        
        # Filtros rápidos
        col_filtro1, col_filtro2, col_filtro3 = st.columns(3)
        
        with col_filtro1:
            filtro_cliente = st.multiselect(
                "Filtrar por Cliente",
                options=sorted(df_tabla["Cliente"].unique()),
                key="filtro_cliente_tabla"
            )
        
        with col_filtro2:
            filtro_sala = st.multiselect(
                "Filtrar por Sala",
                options=sorted(df_tabla["Sala"].unique()),
                key="filtro_sala_tabla"
            )
        
        with col_filtro3:
            filtro_avance = st.select_slider(
                "Avance mínimo",
                options=[0, 25, 50, 75, 100],
                value=0,
                key="filtro_avance_tabla"
            )
        
        # Aplicar filtros
        df_filtrado = df_tabla.copy()
        if filtro_cliente:
            df_filtrado = df_filtrado[df_filtrado["Cliente"].isin(filtro_cliente)]
        if filtro_sala:
            df_filtrado = df_filtrado[df_filtrado["Sala"].isin(filtro_sala)]
        df_filtrado = df_filtrado[df_filtrado["Avance %"] >= filtro_avance]
        
        st.markdown(f"**Mostrando {len(df_filtrado)} de {len(df_tabla)} pedidos**")
        
        # Mostrar tabla con estilos
        st.dataframe(
            df_filtrado.style.format({
                "KG Total": "{:,.0f}",
                "KG Producidos": "{:,.0f}",
                "Avance %": "{:.1f}%"
            }).background_gradient(subset=["Avance %"], cmap="RdYlGn", vmin=0, vmax=100),
            use_container_width=True,
            hide_index=True,
            height=600
        )
