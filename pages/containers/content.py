"""
Contenido principal del dashboard de Containers.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime

from .shared import (
    fetch_containers, STATE_OPTIONS,
    get_state_color, get_sale_state_display,
    get_date_urgency_color, get_odoo_link, format_date_with_urgency
)

# Colores para ODFs
ODF_COLORS = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf'
]


def render(username: str, password: str):
    """Renderiza el contenido principal del dashboard."""
    
    # Sidebar - Filtros
    with st.sidebar:
        st.header("⚙️ Filtros")
        
        # Estado (con callback para auto-refresh)
        def on_state_change():
            st.session_state["load_containers"] = True
            st.session_state.pop("containers_data", None)

        selected_state = st.selectbox(
            "Estado del Pedido",
            options=list(STATE_OPTIONS.keys()),
            on_change=on_state_change,
            key="containers_state_filter"
        )
        
        st.divider()
        st.caption("💡 Los cambios se aplican automáticamente.")
    
    # Cargar datos
    if st.session_state.get("load_containers", False) or "containers_data" not in st.session_state:
        # SKELETON LOADER
        skeleton = st.empty()
        with skeleton.container():
            st.markdown("""
            <div style="animation: pulse 2s infinite;">
                <div style="height: 200px; background-color: #f0f2f6; border-radius: 10px; margin-bottom: 20px;"></div>
                <div style="display: flex; gap: 20px;">
                    <div style="flex: 2; height: 300px; background-color: #f0f2f6; border-radius: 10px;"></div>
                    <div style="flex: 1; height: 300px; background-color: #f0f2f6; border-radius: 10px;"></div>
                </div>
            </div>
            <style>
                @keyframes pulse {
                    0% { opacity: 0.6; }
                    50% { opacity: 0.3; }
                    100% { opacity: 0.6; }
                }
            </style>
            """, unsafe_allow_html=True)
        
        # Carga real
        containers = fetch_containers(username, password, state=STATE_OPTIONS[selected_state])
        st.session_state["containers_data"] = containers
        st.session_state["load_containers"] = False
        
        # LIMPIAR SKELETON antes de mostrar contenido
        skeleton.empty()
    
    # PLACEHOLDER PARA CONTENIDO - evita que se muestre debajo del skeleton
    content_placeholder = st.container()
    
    with content_placeholder:
        containers = st.session_state.get("containers_data", [])
        
        if not containers:
            st.info("📦 No hay containers con fabricaciones vinculadas. Haz clic en 'Cargar Containers' para buscar.")
            return
        
        # KPIs
        _render_kpis(containers)
        
        st.divider()
        
        # Gráfico y Top 5
        _render_charts(containers)
    
    st.divider()
    
    # Detalle
    _render_detail(containers, username, password)
    
    # Footer
    st.divider()
    st.caption("Rio Futuro - Sistema de Gestión de Containers y Producción")


def _render_kpis(containers):
    """Renderiza los KPIs principales."""
    st.subheader("📊 Resumen General")
    
    total_containers = len(containers)
    total_kg = sum([c.get("kg_total", 0) for c in containers])
    total_producidos = sum([c.get("kg_producidos", 0) for c in containers])
    avance_global = (total_producidos / total_kg * 100) if total_kg > 0 else 0
    pendientes = total_kg - total_producidos
    
    en_progreso = len([c for c in containers if 0 < c.get("avance_pct", 0) < 100])
    completados = len([c for c in containers if c.get("avance_pct", 0) >= 100])
    sin_iniciar = len([c for c in containers if c.get("avance_pct", 0) == 0])
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Containers", total_containers, help="Pedidos con fabricaciones")
    col2.metric("En Producción", en_progreso, help="Avance entre 0% y 100%")
    col3.metric("Completados", completados, help="Avance >= 100%")
    col4.metric("Sin Iniciar", sin_iniciar, help="Avance = 0%")
    
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Avance Global", f"{avance_global:.1f}%", help="% de producción completado")
    col6.metric("KG Totales", f"{total_kg:,.0f}", help="Total de kg pedidos")
    col7.metric("KG Producidos", f"{total_producidos:,.0f}", help="KG ya fabricados")
    col8.metric("KG Pendientes", f"{pendientes:,.0f}", help="KG por producir", delta_color="inverse")


def _render_charts(containers):
    """Renderiza el gráfico de barras y top 5."""
    col_chart, col_stats = st.columns([2, 1])
    
    with col_chart:
        st.subheader("📈 Avance por Container")
        
        containers_sorted = sorted(containers, key=lambda x: x.get("avance_pct", 0), reverse=True)[:20]
        
        names = [f"{c['name']}" for c in containers_sorted]
        avances = [c.get("avance_pct", 0) for c in containers_sorted]
        colors = [get_state_color(a) for a in avances]
        clientes = [c.get("partner_name", "N/A") for c in containers_sorted]
        kg_prod = [c.get("kg_producidos", 0) for c in containers_sorted]
        kg_total_list = [c.get("kg_total", 0) for c in containers_sorted]
        fechas = [format_date_with_urgency(c.get("date_order", "")) for c in containers_sorted]
        
        fig = go.Figure()
        
        fig.add_trace(go.Bar(
            y=names,
            x=avances,
            orientation='h',
            marker_color=colors,
            text=[f"{a:.1f}%" for a in avances],
            textposition='outside',
            hovertemplate=(
                '<b>%{y}</b><br>'
                'Cliente: %{customdata[0]}<br>'
                'Avance: %{x:.1f}%<br>'
                'Producido: %{customdata[1]:,.0f} kg<br>'
                'Total: %{customdata[2]:,.0f} kg<br>'
                'Fecha Límite: %{customdata[3]}<extra></extra>'
            ),
            customdata=list(zip(clientes, kg_prod, kg_total_list, fechas))
        ))
        
        fig.add_vline(x=100, line_dash="dash", line_color="rgba(255,255,255,0.3)",
                      annotation_text="Meta 100%")
        
        fig.update_layout(
            height=max(400, len(containers_sorted) * 30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font={"color": "white"},
            xaxis=dict(
                title="Avance (%)",
                gridcolor="rgba(255,255,255,0.1)",
                range=[0, max(110, max(avances) + 15)]
            ),
            yaxis=dict(
                gridcolor="rgba(255,255,255,0.05)",
                autorange="reversed"
            ),
            margin=dict(l=10, r=50, t=20, b=40),
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
    
    with col_stats:
        st.subheader("🏆 Top 5 Containers")
        
        containers_top5 = sorted(containers, key=lambda x: x.get("avance_pct", 0), reverse=True)[:5]
        for i, c in enumerate(containers_top5, 1):
            avance = c.get("avance_pct", 0)
            container_id = c.get("id")
            container_name = c.get("name", "N/A")
            kg_prod = c.get("kg_producidos", 0)
            kg_total = c.get("kg_total", 0)
            date_order = c.get("date_order", "")
            productions = c.get("productions", [])
            
            # Color de fecha
            date_color, date_emoji, _ = get_date_urgency_color(date_order)
            date_display = format_date_with_urgency(date_order)
            
            with st.container(border=True):
                # Header con link a Odoo
                col_num, col_info = st.columns([1, 5])
                with col_num:
                    st.markdown(f"### #{i}")
                with col_info:
                    odoo_link = get_odoo_link("sale.order", container_id)
                    st.markdown(f"**[🔗 {container_name}]({odoo_link})**")
                    st.caption(f"{c.get('partner_name', 'N/A')}")
                
                # Fecha límite con color
                st.markdown(f"📅 **Fecha Límite:** <span style='color:{date_color}'>{date_display}</span>", unsafe_allow_html=True)
                
                # KG breakdown
                st.markdown(f"⚖️ **{kg_prod:,.0f}** / {kg_total:,.0f} kg ({avance:.1f}%)")
                
                # Barra de progreso con ODFs apiladas
                if productions and kg_total > 0:
                    # Crear barra apilada por ODF
                    fig_bar = go.Figure()
                    
                    cumulative = 0
                    for idx, prod in enumerate(productions):
                        prod_kg = prod.get("qty_produced", 0) or 0
                        prod_pct = (prod_kg / kg_total * 100) if kg_total > 0 else 0
                        prod_name = prod.get("name", f"ODF {idx+1}")
                        prod_id = prod.get("id")
                        color = ODF_COLORS[idx % len(ODF_COLORS)]
                        
                        fig_bar.add_trace(go.Bar(
                            x=[prod_pct],
                            y=["Avance"],
                            orientation='h',
                            name=prod_name,
                            marker_color=color,
                            text=f"{prod_name[:12]}" if prod_pct > 8 else "",
                            textposition='inside',
                            hovertemplate=f"<b>{prod_name}</b><br>{prod_kg:,.0f} kg ({prod_pct:.1f}%)<extra></extra>"
                        ))
                    
                    # Espacio restante (pendiente)
                    pending_pct = max(0, 100 - avance)
                    if pending_pct > 0:
                        fig_bar.add_trace(go.Bar(
                            x=[pending_pct],
                            y=["Avance"],
                            orientation='h',
                            name="Pendiente",
                            marker_color="rgba(100,100,100,0.3)",
                            hovertemplate=f"<b>Pendiente</b><br>{kg_total - kg_prod:,.0f} kg ({pending_pct:.1f}%)<extra></extra>"
                        ))
                    
                    fig_bar.update_layout(
                        barmode='stack',
                        height=40,
                        margin=dict(l=0, r=0, t=0, b=0),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        xaxis=dict(visible=False, range=[0, 100]),
                        yaxis=dict(visible=False)
                    )
                    
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
                    
                    # Desglose de ODFs
                    with st.expander(f"🏭 Ver {len(productions)} ODF(s)", expanded=False):
                        for idx, prod in enumerate(productions):
                            prod_name = prod.get("name", "N/A")
                            prod_id = prod.get("id")
                            prod_kg = prod.get("qty_produced", 0) or 0
                            prod_state = prod.get("state_display", prod.get("state", ""))
                            color = ODF_COLORS[idx % len(ODF_COLORS)]
                            odoo_link = get_odoo_link("mrp.production", prod_id)
                            st.markdown(
                                f"<span style='color:{color}'>●</span> [🔗 {prod_name}]({odoo_link}) - {prod_kg:,.0f} kg - {prod_state}",
                                unsafe_allow_html=True
                            )
                else:
                    st.progress(min(avance / 100, 1.0))



def _render_detail(containers, username, password):
    """Renderiza el detalle del container seleccionado."""
    st.subheader("🔍 Detalle de Containers")
    
    container_options = {
        f"{c['name']} - {c['partner_name']} ({c['avance_pct']:.1f}%)": c
        for c in sorted(containers, key=lambda x: x.get("name", ""))
    }
    
    selected_key = st.selectbox(
        "Seleccionar container:",
        options=list(container_options.keys())
    )
    
    if not selected_key:
        return
    
    selected = container_options[selected_key]
    container_id = selected.get("id")
    
    # Link a Odoo
    odoo_link = get_odoo_link("sale.order", container_id)
    st.markdown(f"[🔗 **Abrir en Odoo**]({odoo_link})")
    
    # Información general
    col_info1, col_info2, col_info3, col_info4 = st.columns(4)
    
    with col_info1:
        st.markdown("**📋 Información General**")
        st.write(f"**Container:** {selected.get('name', 'N/A')}")
        st.write(f"**Cliente:** {selected.get('partner_name', 'N/A')}")
        st.write(f"**Estado:** {get_sale_state_display(selected.get('state', ''))}")
        st.write(f"**PO Cliente:** {selected.get('origin', 'N/A')}")
    
    with col_info2:
        st.markdown("**📅 Fechas**")
        # Fecha límite con color
        date_order = selected.get('date_order', '')
        date_color, date_emoji, _ = get_date_urgency_color(date_order)
        date_display = format_date_with_urgency(date_order)
        st.markdown(f"**Fecha Límite:**")
        st.markdown(f"<span style='color:{date_color}; font-size: 1.2em;'>{date_display}</span>", unsafe_allow_html=True)
    
    with col_info3:
        st.markdown("**📦 Producción**")
        st.write(f"**Producto Principal:** {selected.get('producto_principal', 'N/A')}")
        st.write(f"**Fabricaciones:** {selected.get('num_fabricaciones', 0)}")
        avance = selected.get('avance_pct', 0)
        st.write(f"**Avance:** :{'green' if avance >= 75 else 'orange' if avance >= 40 else 'red'}[{avance:.1f}%]")
    
    with col_info4:
        st.markdown("**💰 Cantidades**")
        st.write(f"**Total Pedido:** {selected.get('kg_total', 0):,.2f} kg")
        st.write(f"**Producido:** {selected.get('kg_producidos', 0):,.2f} kg")
        st.write(f"**Pendiente:** {selected.get('kg_disponibles', 0):,.2f} kg")
        st.write(f"**Monto:** ${selected.get('amount_total', 0):,.2f}")
    
    st.divider()
    
    # Gauge de avance
    st.markdown("**📊 Avance de Producción**")
    
    avance_val = selected.get("avance_pct", 0)
    color = get_state_color(avance_val)
    
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=avance_val,
        number={"suffix": "%", "font": {"size": 40}},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "bgcolor": "rgba(255,255,255,0.1)",
            "steps": [
                {"range": [0, 25], "color": "rgba(255, 68, 68, 0.2)"},
                {"range": [25, 50], "color": "rgba(255, 136, 0, 0.2)"},
                {"range": [50, 75], "color": "rgba(255, 170, 0, 0.2)"},
                {"range": [75, 100], "color": "rgba(0, 204, 102, 0.2)"}
            ],
        }
    ))
    
    fig_gauge.update_layout(
        height=200,
        margin=dict(l=20, r=20, t=20, b=10)
    )
    
    st.plotly_chart(fig_gauge, use_container_width=True)
    
    st.divider()
    
    # Tabla de fabricaciones con links
    productions = selected.get("productions", [])
    st.markdown(f"**🏭 Fabricaciones Vinculadas ({len(productions)})**")
    
    if productions:
        # Mostrar cada fabricación con link
        for idx, p in enumerate(productions):
            prod_id = p.get("id")
            prod_name = p.get("name", "N/A")
            prod_product = p.get("product_name", "N/A")
            prod_state = p.get("state_display", p.get("state", ""))
            prod_kg_plan = p.get("product_qty", 0)
            prod_kg_prod = p.get("qty_produced", 0)
            prod_sala = p.get("sala_proceso", "N/A")
            prod_fecha = p.get("date_planned_start", "")[:10] if p.get("date_planned_start") else "N/A"
            
            color = ODF_COLORS[idx % len(ODF_COLORS)]
            odoo_link = get_odoo_link("mrp.production", prod_id)
            
            with st.container(border=True):
                col1, col2, col3, col4, col5 = st.columns([2, 3, 2, 2, 2])
                with col1:
                    st.markdown(f"<span style='color:{color}'>●</span> [🔗 **{prod_name}**]({odoo_link})", unsafe_allow_html=True)
                with col2:
                    st.write(f"📦 {prod_product[:30]}...")
                with col3:
                    st.write(f"📊 {prod_state}")
                with col4:
                    st.write(f"⚖️ {prod_kg_prod:,.0f} / {prod_kg_plan:,.0f} kg")
                with col5:
                    st.write(f"🏭 {prod_sala}")
        
        # Tabla descargable
        with st.expander("📥 Descargar datos", expanded=False):
            df_prod = pd.DataFrame([{
                "OF": p.get("name", ""),
                "Producto": p.get("product_name", "N/A"),
                "Estado": p.get("state_display", ""),
                "KG Plan": p.get("product_qty", 0),
                "KG Prod": p.get("qty_produced", 0),
                "Responsable": p.get("user_name", "N/A"),
                "Sala": p.get("sala_proceso", "N/A"),
                "Fecha": p.get("date_planned_start", "")[:10] if p.get("date_planned_start") else "N/A"
            } for p in productions])
            
            csv = df_prod.to_csv(index=False)
            st.download_button(
                "📥 Descargar Fabricaciones",
                csv,
                f"fabricaciones_{selected.get('name', 'container')}_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv"
            )
    else:
        st.info("No hay fabricaciones vinculadas")
