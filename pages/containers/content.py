"""
Contenido principal del dashboard de Pedidos de Venta.
"""
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta

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
    
    # === FILTROS EN ÁREA PRINCIPAL ===
    st.markdown("### ⚙️ Filtros de Consulta")
    
    col_f1, col_f2, col_f3, col_f4 = st.columns([2, 2, 2, 1])
    
    with col_f1:
        # Fecha inicio
        hoy = datetime.now().date()
        fecha_default_inicio = hoy - timedelta(days=30)
        fecha_inicio = st.date_input(
            "📅 Fecha Inicio",
            value=fecha_default_inicio,
            format="DD/MM/YYYY",
            key="pedidos_venta_fecha_inicio"
        )
    
    with col_f2:
        # Fecha fin
        fecha_fin = st.date_input(
            "📅 Fecha Fin",
            value=hoy,
            format="DD/MM/YYYY",
            key="pedidos_venta_fecha_fin"
        )
    
    with col_f3:
        # Estado
        selected_state = st.selectbox(
            "📋 Estado del Pedido",
            options=list(STATE_OPTIONS.keys()),
            key="pedidos_venta_state_filter"
        )
    
    with col_f4:
        st.markdown("<br>", unsafe_allow_html=True)
        cargar = st.button("🔍 Consultar", type="primary", use_container_width=True)
    
    # Validar fechas
    if fecha_inicio > fecha_fin:
        st.error("❌ La fecha de inicio no puede ser mayor a la fecha fin")
        return
    
    st.caption(f"📅 Período: {fecha_inicio.strftime('%d/%m/%Y')} → {fecha_fin.strftime('%d/%m/%Y')} ({(fecha_fin - fecha_inicio).days + 1} días)")
    
    st.divider()
    
    # Cargar datos SOLO al hacer click en el botón
    if cargar:
        with st.spinner("🔄 Cargando containers..."):
            containers = fetch_containers(
                username, 
                password, 
                start_date=fecha_inicio.strftime("%Y-%m-%d"),
                end_date=fecha_fin.strftime("%Y-%m-%d"),
                state=STATE_OPTIONS[selected_state]
            )
            st.session_state["containers_data"] = containers
            st.rerun()
    
    containers = st.session_state.get("containers_data", [])
    
    if not containers:
        st.info("📦 No hay pedidos de venta con fabricaciones vinculadas en el período seleccionado.")
        return
    
    # === 1. KPIs ===
    _render_kpis(containers)
    
    st.divider()
    
    # === 2. GRÁFICOS ===
    _render_charts(containers)
    
    st.divider()
    
    # === 3. TOP 5 PEDIDOS (DETALLE) ===
    _render_top5(containers)
    
    st.divider()
    
    # === 4. VISTA DE TABLA COMPLETA ===
    _render_table_view(containers)
    
    st.divider()
    
    # === 5. DETALLE INDIVIDUAL ===
    _render_detail(containers, username, password)
    
    # Footer
    st.divider()
    st.caption("Rio Futuro - Sistema de Gestión de Pedidos de Venta y Producción")


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
    
    # Métricas de pedidos
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Pedidos", total_containers, help="Pedidos con fabricaciones")
    col2.metric("En Producción", en_progreso, help="Avance entre 0% y 100%")
    col3.metric("Completados", completados, help="Avance >= 100%")
    col4.metric("Sin Iniciar", sin_iniciar, help="Avance = 0%")
    
    # Métricas de producción
    col5, col6, col7, col8 = st.columns(4)
    col5.metric("Avance Global", f"{avance_global:.1f}%", help="% de producción completado")
    col6.metric("KG Totales", f"{total_kg:,.0f}", help="Total de kg pedidos")
    col7.metric("KG Producidos", f"{total_producidos:,.0f}", help="KG ya fabricados")
    col8.metric("KG Pendientes", f"{pendientes:,.0f}", help="KG por producir", delta_color="inverse")
    
    # Métricas adicionales
    st.markdown("---")
    col9, col10, col11, col12 = st.columns(4)
    
    # Número de clientes únicos
    clientes_unicos = len(set([c.get('partner_name', 'N/A') for c in containers]))
    col9.metric("Clientes Activos", clientes_unicos, help="Clientes con pedidos en período")
    
    # Monto total
    monto_total = sum([c.get("amount_total", 0) for c in containers])
    col10.metric("Monto Total", f"${monto_total:,.0f}", help="Suma de todos los pedidos")
    
    # Promedio de ODFs por pedido
    total_odfs = sum([c.get("num_fabricaciones", 0) for c in containers])
    avg_odfs = total_odfs / total_containers if total_containers > 0 else 0
    col11.metric("Total ODFs", total_odfs, help=f"Promedio: {avg_odfs:.1f} ODFs/pedido")
    
    # Pedidos urgentes (menos de 7 días)
    urgentes = 0
    for c in containers:
        date_order = c.get('date_order', '')
        if date_order:
            try:
                fecha_limite = datetime.strptime(date_order[:10], '%Y-%m-%d').date()
                dias = (fecha_limite - datetime.now().date()).days
                if dias < 7 and c.get('avance_pct', 0) < 100:
                    urgentes += 1
            except:
                pass
    col12.metric("⚠️ Urgentes", urgentes, help="Pedidos con menos de 7 días y no completados")


def _render_charts(containers):
    """Renderiza el gráfico de barras (Top 20) con mejoras visuales."""
    st.subheader("📈 Avance Producción (Top 20)")
    
    containers_sorted = sorted(containers, key=lambda x: x.get("avance_pct", 0), reverse=True)[:20]
    
    if not containers_sorted:
        st.info("No hay datos para mostrar el gráfico.")
        return

    names = [c['name'] for c in containers_sorted]
    avances = [c.get("avance_pct", 0) for c in containers_sorted]
    colors = [get_state_color(a) for a in avances]
    clientes = [c.get("partner_name", "N/A") for c in containers_sorted]
    kg_prod = [c.get("kg_producidos", 0) for c in containers_sorted]
    kg_total_list = [c.get("kg_total", 0) for c in containers_sorted]
    
    # Preparar etiquetas Y con emoji de urgencia y fechas formateadas
    y_labels = []
    fechas_display = []
    
    for c in containers_sorted:
        date_order = c.get("date_order", "")
        _, emoji, _ = get_date_urgency_color(date_order)
        date_fmt = format_date_with_urgency(date_order)
        
        y_labels.append(f"{emoji} {c['name']}")
        fechas_display.append(date_fmt)

    fig = go.Figure()
    
    # 1. Ghost Bars (Fondo de meta 100%)
    fig.add_trace(go.Bar(
        y=y_labels,
        x=[100] * len(names),
        orientation='h',
        marker_color='rgba(255, 255, 255, 0.05)',
        hoverinfo='skip',
        showlegend=False,
        width=0.6  # Un poco más delgadas para elegancia
    ))
    
    # 2. Barras principales
    fig.add_trace(go.Bar(
        y=y_labels,
        x=avances,
        orientation='h',
        marker_color=colors,
        text=[f"<b>{a:.1f}%</b>" for a in avances],
        textposition='outside',
        width=0.6,
        # 3. Tooltip Estilizado (HTML)
        hovertemplate=(
            '<b style="font-size: 14px">📦 %{customdata[4]}</b><br>'
            '<span style="color: #aaaaaa">👤 %{customdata[0]}</span><br>'
            '<hr>'
            '📈 Avance: <b>%{x:.1f}%</b><br>'
            '⚖️ Producción: <b>%{customdata[1]:,.0f}</b> / %{customdata[2]:,.0f} kg<br>'
            '📅 Límite: %{customdata[3]}<extra></extra>'
        ),
        # Pasamos names original en customdata[4] para mostrar nombre limpio en tooltip
        customdata=list(zip(clientes, kg_prod, kg_total_list, fechas_display, names))
    ))
    
    # 4. Línea de Meta Estilizada
    fig.add_vline(
        x=100, 
        line_dash="dot", 
        line_color="rgba(255, 255, 255, 0.5)",
        annotation_text="🏁 Meta 100%", 
        annotation_position="top right",
        annotation_font_color="rgba(255, 255, 255, 0.7)"
    )
    
    # 5. Ajustes de Layout "Pro"
    fig.update_layout(
        height=max(450, len(containers_sorted) * 35), # Un poco más de altura por barra
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": "white", "family": "Arial"},
        title_font_size=16,
        xaxis=dict(
            title="Porcentaje de Avance (%)",
            title_font=dict(size=12, color="#aaaaaa"),
            gridcolor="rgba(255,255,255,0.08)", # Grid muy sutil
            zeroline=False,
            showticklabels=True,
            range=[0, max(115, max(avances) + 20)] # Espacio extra para etiquetas
        ),
        yaxis=dict(
            gridcolor="rgba(0,0,0,0)", # Sin grid en Y
            autorange="reversed",
            tickfont=dict(size=13) # Texto un poco más grande
        ),
        margin=dict(l=10, r=60, t=30, b=50),
        showlegend=False,
        bargap=0.3 # Espacio entre barras
    )
    
    st.plotly_chart(fig, use_container_width=True)


def _render_top5(containers):
    """Renderiza el detalle Top 5 Pedidos (con opción de ver diferentes rankings)."""
    st.subheader("🏆 Top 5 Pedidos")
    
    # Selector de criterio de ranking
    col_rank1, col_rank2 = st.columns([3, 3])
    with col_rank1:
        ranking_criterio = st.selectbox(
            "Criterio de ranking:",
            options=["Mayor Avance", "Mayor KG Total", "Más Urgentes", "Mayor Monto", "Menor Avance"],
            index=0
        )
    
    # Ordenar según criterio
    if ranking_criterio == "Mayor Avance":
        containers_top5 = sorted(containers, key=lambda x: x.get("avance_pct", 0), reverse=True)[:5]
    elif ranking_criterio == "Mayor KG Total":
        containers_top5 = sorted(containers, key=lambda x: x.get("kg_total", 0), reverse=True)[:5]
    elif ranking_criterio == "Mayor Monto":
        containers_top5 = sorted(containers, key=lambda x: x.get("amount_total", 0), reverse=True)[:5]
    elif ranking_criterio == "Menor Avance":
        containers_top5 = sorted(containers, key=lambda x: x.get("avance_pct", 0))[:5]
    else:  # Más Urgentes
        # Calcular urgencia (días restantes)
        containers_with_urgency = []
        for c in containers:
            date_order = c.get('date_order', '')
            dias = 999
            if date_order:
                try:
                    fecha_limite = datetime.strptime(date_order[:10], '%Y-%m-%d').date()
                    dias = (fecha_limite - datetime.now().date()).days
                except:
                    pass
            containers_with_urgency.append((c, dias))
        containers_top5 = [c for c, dias in sorted(containers_with_urgency, key=lambda x: x[1])[:5]]
    
    for i, c in enumerate(containers_top5, 1):
        avance = c.get("avance_pct", 0)
        container_id = c.get("id")
        container_name = c.get("name", "N/A")
        kg_prod = c.get("kg_producidos", 0)
        kg_total = c.get("kg_total", 0)
        date_order = c.get("date_order", "")
        productions = c.get("productions", [])
        monto = c.get("amount_total", 0)
        estado = c.get("state", "")
        
        # Color de fecha
        date_color, date_emoji, _ = get_date_urgency_color(date_order)
        date_display = format_date_with_urgency(date_order)
        
        with st.container(border=True):
            # Header con link a Odoo
            col_num, col_info, col_monto = st.columns([1, 4, 2])
            with col_num:
                st.markdown(f"### #{i}")
            with col_info:
                odoo_link = get_odoo_link("sale.order", container_id)
                st.markdown(f"**[🔗 {container_name}]({odoo_link})**")
                st.caption(f"👥 {c.get('partner_name', 'N/A')} | 📋 {get_sale_state_display(estado)}")
            with col_monto:
                st.metric("💰 Monto", f"${monto:,.0f}")
            
            # Info adicional en columnas
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.markdown(f"📅 **Fecha Límite:** <span style='color:{date_color}'>{date_display}</span>", unsafe_allow_html=True)
            with col_b:
                st.markdown(f"⚖️ **Producción:** {kg_prod:,.0f} / {kg_total:,.0f} kg ({avance:.1f}%)")
            with col_c:
                st.markdown(f"🏭 **ODFs:** {len(productions)} fabricaciones")
            
            # PO Cliente si existe
            if c.get('origin'):
                st.caption(f"📄 PO Cliente: {c.get('origin', 'N/A')}")
            
            # KG por producto
            kg_por_producto = c.get('kg_por_producto', {})
            if kg_por_producto:
                st.caption("📊 **KG por Producto:**")
                productos_str = " | ".join([f"{prod[:25]}: {kg:,.0f} kg" for prod, kg in sorted(kg_por_producto.items(), key=lambda x: x[1], reverse=True)])
                st.caption(productos_str)
            
            st.markdown("---")
            
            # Barra de progreso con ODFs apiladas
            if productions and kg_total > 0:
                # Crear barra apilada por ODF
                fig_bar = go.Figure()
                
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



def _render_table_view(containers):
    """Renderiza vista de tabla completa con todos los pedidos de venta."""
    st.subheader("📋 Vista de Tabla - Todos los Pedidos")
    
    # Preparar datos para tabla
    table_data = []
    for c in containers:
        # Calcular días hasta fecha límite
        date_order = c.get('date_order', '')
        dias_restantes = "N/A"
        if date_order:
            try:
                fecha_limite = datetime.strptime(date_order[:10], '%Y-%m-%d').date()
                dias = (fecha_limite - datetime.now().date()).days
                dias_restantes = dias
            except:
                pass
        
        # Formatear KG por producto para mostrar en tabla
        kg_productos_str = ""
        kg_por_producto = c.get('kg_por_producto', {})
        if kg_por_producto:
            productos_list = [f"{prod[:20]}: {kg:,.0f}" for prod, kg in sorted(kg_por_producto.items(), key=lambda x: x[1], reverse=True)]
            kg_productos_str = " | ".join(productos_list[:3])  # Mostrar solo los 3 principales
        
        table_data.append({
            "Pedido": c.get('name', 'N/A'),
            "Cliente": c.get('partner_name', 'N/A'),
            "PO Cliente": c.get('origin', 'N/A')[:20],
            "Estado": get_sale_state_display(c.get('state', '')),
            "Fecha Límite": date_order[:10] if date_order else "N/A",
            "Días Restantes": dias_restantes,
            "KG Total": c.get('kg_total', 0),
            "KG Producido": c.get('kg_producidos', 0),
            "KG Pendiente": c.get('kg_disponibles', 0),
            "Avance %": c.get('avance_pct', 0),
            "# ODFs": c.get('num_fabricaciones', 0),
            "Monto Total": c.get('amount_total', 0),
            "Producto Principal": c.get('producto_principal', 'N/A')[:30],
            "KG por Producto": kg_productos_str
        })
    
    df = pd.DataFrame(table_data)
    
    # Configurar display
    if not df.empty:
        # Formatear columnas numéricas
        df_display = df.copy()
        df_display['KG Total'] = df_display['KG Total'].apply(lambda x: f"{x:,.0f}")
        df_display['KG Producido'] = df_display['KG Producido'].apply(lambda x: f"{x:,.0f}")
        df_display['KG Pendiente'] = df_display['KG Pendiente'].apply(lambda x: f"{x:,.0f}")
        df_display['Avance %'] = df_display['Avance %'].apply(lambda x: f"{x:.1f}%")
        df_display['Monto Total'] = df_display['Monto Total'].apply(lambda x: f"${x:,.0f}")
        
        # Mostrar tabla con estilo
        st.dataframe(
            df_display,
            use_container_width=True,
            height=400,
            hide_index=True,
            column_config={
                "Pedido": st.column_config.TextColumn("Pedido", width="small"),
                "Cliente": st.column_config.TextColumn("Cliente", width="medium"),
                "PO Cliente": st.column_config.TextColumn("PO Cliente", width="small"),
                "Estado": st.column_config.TextColumn("Estado", width="small"),
                "Fecha Límite": st.column_config.TextColumn("Fecha Límite", width="small"),
                "Días Restantes": st.column_config.NumberColumn("Días", width="small"),
                "Avance %": st.column_config.TextColumn("Avance %", width="small"),
                "# ODFs": st.column_config.NumberColumn("ODFs", width="small"),
                "KG por Producto": st.column_config.TextColumn("KG por Producto", width="large"),
            }
        )
        
        # Opciones de descarga y análisis
        col_d1, col_d2, col_d3 = st.columns([2, 2, 2])
        
        with col_d1:
            # Descarga CSV
            csv = df.to_csv(index=False)
            st.download_button(
                "📥 Descargar CSV",
                csv,
                f"pedidos_venta_{datetime.now().strftime('%Y%m%d')}.csv",
                "text/csv",
                use_container_width=True
            )
        
        with col_d2:
            # Estadísticas rápidas
            st.metric("Total Registros", len(df))
        
        with col_d3:
            # Promedio de avance
            avg_avance = df['Avance %'].mean() if 'Avance %' in df.columns else 0
            st.metric("Avance Promedio", f"{avg_avance:.1f}%")
        
        # Análisis por cliente
        with st.expander("📊 Análisis por Cliente", expanded=False):
            cliente_stats = df.groupby('Cliente').agg({
                'Pedido': 'count',
                'KG Total': 'sum',
                'KG Producido': 'sum',
                'Avance %': 'mean',
                'Monto Total': 'sum'
            }).reset_index()
            
            cliente_stats.columns = ['Cliente', 'Cant. Pedidos', 'KG Total', 'KG Producido', 'Avance Prom %', 'Monto Total']
            cliente_stats = cliente_stats.sort_values('KG Total', ascending=False)
            
            # Formatear
            cliente_stats['KG Total'] = cliente_stats['KG Total'].apply(lambda x: f"{x:,.0f}")
            cliente_stats['KG Producido'] = cliente_stats['KG Producido'].apply(lambda x: f"{x:,.0f}")
            cliente_stats['Avance Prom %'] = cliente_stats['Avance Prom %'].apply(lambda x: f"{x:.1f}%")
            cliente_stats['Monto Total'] = cliente_stats['Monto Total'].apply(lambda x: f"${x:,.0f}")
            
            st.dataframe(cliente_stats, use_container_width=True, hide_index=True)
    else:
        st.info("No hay datos para mostrar")


def _render_detail(containers, username, password):
    """Renderiza el detalle del pedido de venta seleccionado con filtros mejorados."""
    st.subheader("🔍 Detalle de Pedidos de Venta")
    
    # FILTROS INTELIGENTES
    col_f1, col_f2, col_f3 = st.columns([2, 2, 2])
    
    with col_f1:
        # Filtro por cliente
        clientes = sorted(set([c['partner_name'] for c in containers]))
        cliente_filter = st.multiselect(
            "👥 Filtrar por Cliente",
            options=clientes,
            default=None,
            placeholder="Todos los clientes"
        )
    
    with col_f2:
        # Filtro por estado de avance
        avance_filter = st.selectbox(
            "📊 Estado de Avance",
            options=["Todos", "Sin Iniciar (0%)", "En Proceso (1-99%)", "Completados (100%)"],
            index=0
        )
    
    with col_f3:
        # Búsqueda por texto
        search_text = st.text_input(
            "🔍 Buscar por Nombre/PO",
            placeholder="Ej: S00687, PO N°2574..."
        )
    
    # Aplicar filtros
    containers_filtered = containers.copy()
    
    if cliente_filter:
        containers_filtered = [c for c in containers_filtered if c['partner_name'] in cliente_filter]
    
    if avance_filter == "Sin Iniciar (0%)":
        containers_filtered = [c for c in containers_filtered if c.get('avance_pct', 0) == 0]
    elif avance_filter == "En Proceso (1-99%)":
        containers_filtered = [c for c in containers_filtered if 0 < c.get('avance_pct', 0) < 100]
    elif avance_filter == "Completados (100%)":
        containers_filtered = [c for c in containers_filtered if c.get('avance_pct', 0) >= 100]
    
    if search_text:
        search_lower = search_text.lower()
        containers_filtered = [
            c for c in containers_filtered 
            if search_lower in c.get('name', '').lower() 
            or search_lower in c.get('origin', '').lower()
        ]
    
    st.caption(f"📦 Mostrando {len(containers_filtered)} de {len(containers)} pedidos")
    
    if not containers_filtered:
        st.warning("No hay pedidos que coincidan con los filtros seleccionados")
        return
    
    # Selector mejorado con opciones limitadas
    container_options = {
        f"{c['name']} - {c['partner_name']} ({c['avance_pct']:.1f}%)": c
        for c in sorted(containers_filtered, key=lambda x: x.get("name", ""))
    }
    
    selected_key = st.selectbox(
        "Seleccionar pedido de venta:",
        options=list(container_options.keys()),
        help=f"Mostrando {len(container_options)} pedidos filtrados"
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
    
    # Mostrar KG por producto
    kg_por_producto = selected.get('kg_por_producto', {})
    if kg_por_producto:
        st.markdown("**📊 KG por Producto**")
        cols_productos = st.columns(min(len(kg_por_producto), 4))
        for idx, (producto, kg) in enumerate(sorted(kg_por_producto.items(), key=lambda x: x[1], reverse=True)):
            with cols_productos[idx % 4]:
                st.metric(producto[:30], f"{kg:,.2f} kg", help=producto)
    
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
