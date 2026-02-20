"""
Contenido principal del dashboard de Relación Comercial.
KPIs, gráficos de barras, tabla dinámica y gráficos de pie.
"""
import streamlit as st
import pandas as pd
import plotly.express as px

from .shared import (
    COLOR_NAVY, COLOR_PINK, 
    BAR_COLORS_PROGRAMA, BAR_COLORS_MANEJO, PIE_COLORS,
    MONTH_MAP, MONTH_MAP_REV, MONTH_MAP_SHORT,
    fmt_moneda, fmt_kilos, fmt_val
)


def render(comercial_service, username: str, password: str):
    """Renderiza el contenido principal del dashboard."""
    
    # Obtener opciones de filtros
    filter_options = comercial_service.get_filter_values()
    
    # Selectores de vista
    col_met, col_cur, _ = st.columns([1.5, 1, 2])
    with col_met:
        metric_type = st.radio("Ver Datos por:", ["Kilos", "Ventas ($)"], horizontal=True)
    with col_cur:
        currency = st.radio("Moneda:", ["CLP", "USD"], horizontal=True)
    
    metric_key = 'kilos' if metric_type == "Kilos" else 'monto'
    metric_label = "Kilos" if metric_type == "Kilos" else currency
    val_format = ",.0f" if metric_type == "Kilos" else (",.2f" if currency == "USD" else ",.0f")
    prefix = "" if metric_type == "Kilos" else "$"
    
    # Filtros de datos
    with st.form("filtros_form"):
        f1, f2, f3, f4, f5 = st.columns(5)
        with f1:
            s_anio = st.multiselect("Año", options=filter_options.get('anio', []), placeholder="ELEGIR")
        with f2:
            s_mes_names = st.multiselect("Mes", options=list(MONTH_MAP.values()), placeholder="ELEGIR")
        with f3:
            s_trim = st.multiselect("Trimestre", options=["Q1", "Q2", "Q3", "Q4"], placeholder="ELEGIR")
        with f4:
            s_cliente = st.multiselect("Cliente", options=filter_options.get('cliente', []), placeholder="ELEGIR")
        with f5:
            s_especie = st.multiselect("Tipo Fruta", options=filter_options.get('especie', []), placeholder="ELEGIR")
        
        st.write(" ")
        submitted = st.form_submit_button("APLICAR FILTROS DE DATOS", use_container_width=True)
    
    if 'applied_filters' not in st.session_state:
        st.session_state.applied_filters = {}
    
    if submitted:
        new_f = {}
        if s_anio:
            new_f['anio'] = s_anio
        if s_mes_names:
            new_f['mes'] = [MONTH_MAP_REV[m] for m in s_mes_names]
        if s_trim:
            new_f['trimestre'] = s_trim
        if s_cliente:
            new_f['cliente'] = s_cliente
        if s_especie:
            new_f['especie'] = s_especie
        st.session_state.applied_filters = new_f
    
    # Obtener datos
    data = comercial_service.get_relacion_comercial_data(filters=st.session_state.applied_filters)
    df_raw = pd.DataFrame(data.get('raw_data', []))
    usd_rate = data.get('usd_rate', 1.0)
    kpis_data = data.get('kpis', {
        "total_ventas": 0,
        "total_kilos": 0,
        "total_comprometido": 0,
        "kpi_label": "Total Ventas",
        "has_filters": False
    })
    
    # Conversión de moneda
    if currency == "USD" and not df_raw.empty:
        df_raw['monto'] = df_raw['monto'] * usd_rate
        kpis_data['total_ventas'] *= usd_rate
        kpis_data['total_comprometido'] *= usd_rate
    
    # Header con botón de descarga
    _render_header(df_raw, kpis_data, currency, metric_type)
    
    # KPIs
    _render_kpis(kpis_data, currency)
    
    # Gráficos de barras - Vendido
    _render_bar_charts(df_raw, metric_key, metric_label, val_format, prefix)
    
    # Gráficos de barras - Comprometido
    _render_bar_charts_comprometido(df_raw, metric_key, metric_label, val_format, prefix)
    
    # Tabla
    _render_table(df_raw, metric_key, metric_label, val_format, prefix)
    
    # Gráficos de pie
    _render_pie_charts(df_raw, metric_key, metric_label, val_format, prefix)


def _render_header(df_raw, kpis_data, currency, metric_type):
    """Renderiza el header con título y botón de descarga."""
    from backend.utils.pdf_generator import generate_commercial_pdf
    
    head_col1, head_col2 = st.columns([3, 1])
    with head_col1:
        st.markdown('<div class="dashboard-title">Data Relación Comercial</div>', unsafe_allow_html=True)
    
    with head_col2:
        st.write("")
        if not df_raw.empty:
            try:
                pdf_bytes = generate_commercial_pdf(
                    df_raw, kpis_data, st.session_state.applied_filters, currency, metric_type
                )
                st.download_button(
                    label="📄 DESCARGAR INFORME PDF",
                    data=pdf_bytes,
                    file_name=f"Informe_Detallado_{st.session_state.applied_filters.get('cliente', ['General'])[0]}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")


def _render_kpis(kpis_data, currency):
    """Renderiza las tarjetas de KPIs."""
    st.markdown(f"""
    <div class="kpi-container">
        <div class="kpi-card">
            <div class="kpi-value">{fmt_moneda(kpis_data['total_ventas'], currency)}</div>
            <div class="kpi-label">Total Ventas ({currency})</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{fmt_kilos(kpis_data['total_kilos'])}</div>
            <div class="kpi-label">Total Ventas (KG)</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{fmt_moneda(kpis_data['total_comprometido'], currency)}</div>
            <div class="kpi-label">Comprometido ({currency})</div>
        </div>
        <div class="kpi-card">
            <div class="kpi-value">{fmt_kilos(kpis_data.get('total_comprometido_kilos', 0))}</div>
            <div class="kpi-label">Comprometido (KG)</div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _render_bar_charts(df_raw, metric_key, metric_label, val_format, prefix):
    """Renderiza los gráficos de barras."""
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">VENDIDO POR PROGRAMA ({metric_label})</p>', unsafe_allow_html=True)
        
        if not df_raw.empty:
            has_time_filter = len(st.session_state.applied_filters.get('mes', [])) > 0 or len(st.session_state.applied_filters.get('trimestre', [])) > 0
            x_axis = 'mes_nombre' if has_time_filter else 'anio'
            
            df_m = df_raw[df_raw['tipo'].isin(['Factura', 'Nota de Crédito'])].copy()
            
            if has_time_filter:
                df_m['mes_nombre'] = df_m['mes'].map(MONTH_MAP_SHORT)
                df_m = df_m.sort_values('mes')
            
            group_cols = [x_axis, 'programa']
            df_m_plot = df_m.groupby(group_cols)[[metric_key]].sum().reset_index()
            if not has_time_filter:
                df_m_plot['anio'] = df_m_plot['anio'].astype(str)
            
            if not df_m_plot.empty:
                fig_m = px.bar(df_m_plot, x=x_axis, y=metric_key, color='programa', barmode='group',
                               color_discrete_map=BAR_COLORS_PROGRAMA, text=metric_key)
                fig_m.update_traces(
                    texttemplate=f'<b>%{{text:{val_format}}}</b>',
                    textposition='outside',
                    textfont=dict(size=11, color="#333", family="Inter"),
                    marker=dict(line=dict(width=0), cornerradius=5),
                    width=0.35
                )
                fig_m.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=40, b=20, l=20, r=20), height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                               title=None, font=dict(color="#333", size=11),
                               bgcolor='rgba(255,255,255,0.8)', bordercolor='#ddd', borderwidth=1),
                    xaxis=dict(title=None, showgrid=False, showline=True, linecolor="#ddd",
                              tickfont=dict(color="#333", size=12, family="Inter"), type='category'),
                    yaxis=dict(title=None, showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                              tickfont=dict(color="#999", size=10), showline=False,
                              range=[0, df_m_plot[metric_key].max() * 1.2]),
                    bargap=0.3, bargroupgap=0.1
                )
                st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False}, key="chart_programa")
    
    with chart_col2:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">VENDIDO POR MANEJO ({metric_label})</p>', unsafe_allow_html=True)
        
        if not df_raw.empty:
            has_time_filter = len(st.session_state.applied_filters.get('mes', [])) > 0 or len(st.session_state.applied_filters.get('trimestre', [])) > 0
            x_axis = 'mes_nombre' if has_time_filter else 'anio'
            
            df_p = df_raw[df_raw['tipo'].isin(['Factura', 'Nota de Crédito'])].copy()
            
            if has_time_filter:
                df_p['mes_nombre'] = df_p['mes'].map(MONTH_MAP_SHORT)
                df_p = df_p.sort_values('mes')
            
            group_cols = [x_axis, 'manejo']
            df_p_plot = df_p.groupby(group_cols)[[metric_key]].sum().reset_index()
            if not has_time_filter:
                df_p_plot['anio'] = df_p_plot['anio'].astype(str)
            
            if not df_p_plot.empty:
                fig_p = px.bar(df_p_plot, x=x_axis, y=metric_key, color='manejo', barmode='group',
                               color_discrete_map=BAR_COLORS_MANEJO, text=metric_key)
                fig_p.update_traces(
                    texttemplate=f'<b>%{{text:{val_format}}}</b>',
                    textposition='outside',
                    textfont=dict(size=11, color="#333", family="Inter"),
                    marker=dict(line=dict(width=0), cornerradius=5),
                    width=0.35
                )
                fig_p.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(t=40, b=20, l=20, r=20), height=380,
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                               title=None, font=dict(color="#333", size=11),
                               bgcolor='rgba(255,255,255,0.8)', bordercolor='#ddd', borderwidth=1),
                    xaxis=dict(title=None, showgrid=False, showline=True, linecolor="#ddd",
                              tickfont=dict(color="#333", size=12, family="Inter"), type='category'),
                    yaxis=dict(title=None, showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                              tickfont=dict(color="#999", size=10), showline=False,
                              range=[0, df_p_plot[metric_key].max() * 1.2]),
                    bargap=0.3, bargroupgap=0.1
                )
                st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False}, key="chart_manejo")


def _render_bar_charts_comprometido(df_raw, metric_key, metric_label, val_format, prefix):
    """Renderiza los gráficos de barras de comprometido."""
    if df_raw.empty:
        return
    
    df_comp = df_raw[df_raw['tipo'] == 'Comprometido'].copy()
    if df_comp.empty:
        return
    
    st.markdown('<div style="margin-top: 30px;"></div>', unsafe_allow_html=True)
    chart_col1, chart_col2 = st.columns(2)
    
    with chart_col1:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">COMPROMETIDO POR PROGRAMA ({metric_label})</p>', unsafe_allow_html=True)
        
        has_time_filter = len(st.session_state.applied_filters.get('mes', [])) > 0 or len(st.session_state.applied_filters.get('trimestre', [])) > 0
        x_axis = 'mes_nombre' if has_time_filter else 'anio'
        
        df_m = df_comp.copy()
        if has_time_filter:
            df_m['mes_nombre'] = df_m['mes'].map(MONTH_MAP_SHORT)
            df_m = df_m.sort_values('mes')
        
        group_cols = [x_axis, 'programa']
        df_m_plot = df_m.groupby(group_cols)[[metric_key]].sum().reset_index()
        if not has_time_filter:
            df_m_plot['anio'] = df_m_plot['anio'].astype(str)
        
        if not df_m_plot.empty:
            fig_m = px.bar(df_m_plot, x=x_axis, y=metric_key, color='programa', barmode='group',
                           color_discrete_map=BAR_COLORS_PROGRAMA, text=metric_key)
            fig_m.update_traces(
                texttemplate=f'<b>%{{text:{val_format}}}</b>',
                textposition='outside',
                textfont=dict(size=11, color="#333", family="Inter"),
                marker=dict(line=dict(width=0), cornerradius=5),
                width=0.35
            )
            fig_m.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=20, l=20, r=20), height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                           title=None, font=dict(color="#333", size=11),
                           bgcolor='rgba(255,255,255,0.8)', bordercolor='#ddd', borderwidth=1),
                xaxis=dict(title=None, showgrid=False, showline=True, linecolor="#ddd",
                          tickfont=dict(color="#333", size=12, family="Inter"), type='category'),
                yaxis=dict(title=None, showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                          tickfont=dict(color="#999", size=10), showline=False,
                          range=[0, df_m_plot[metric_key].max() * 1.2]),
                bargap=0.3, bargroupgap=0.1
            )
            st.plotly_chart(fig_m, use_container_width=True, config={'displayModeBar': False}, key="chart_programa_comp")
        else:
            st.info("No hay datos comprometidos por programa.")
    
    with chart_col2:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">COMPROMETIDO POR MANEJO ({metric_label})</p>', unsafe_allow_html=True)
        
        has_time_filter = len(st.session_state.applied_filters.get('mes', [])) > 0 or len(st.session_state.applied_filters.get('trimestre', [])) > 0
        x_axis = 'mes_nombre' if has_time_filter else 'anio'
        
        df_p = df_comp.copy()
        if has_time_filter:
            df_p['mes_nombre'] = df_p['mes'].map(MONTH_MAP_SHORT)
            df_p = df_p.sort_values('mes')
        
        group_cols = [x_axis, 'manejo']
        df_p_plot = df_p.groupby(group_cols)[[metric_key]].sum().reset_index()
        if not has_time_filter:
            df_p_plot['anio'] = df_p_plot['anio'].astype(str)
        
        if not df_p_plot.empty:
            fig_p = px.bar(df_p_plot, x=x_axis, y=metric_key, color='manejo', barmode='group',
                           color_discrete_map=BAR_COLORS_MANEJO, text=metric_key)
            fig_p.update_traces(
                texttemplate=f'<b>%{{text:{val_format}}}</b>',
                textposition='outside',
                textfont=dict(size=11, color="#333", family="Inter"),
                marker=dict(line=dict(width=0), cornerradius=5),
                width=0.35
            )
            fig_p.update_layout(
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(t=40, b=20, l=20, r=20), height=380,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5,
                           title=None, font=dict(color="#333", size=11),
                           bgcolor='rgba(255,255,255,0.8)', bordercolor='#ddd', borderwidth=1),
                xaxis=dict(title=None, showgrid=False, showline=True, linecolor="#ddd",
                          tickfont=dict(color="#333", size=12, family="Inter"), type='category'),
                yaxis=dict(title=None, showgrid=True, gridcolor="rgba(0,0,0,0.05)",
                          tickfont=dict(color="#999", size=10), showline=False,
                          range=[0, df_p_plot[metric_key].max() * 1.2]),
                bargap=0.3, bargroupgap=0.1
            )
            st.plotly_chart(fig_p, use_container_width=True, config={'displayModeBar': False}, key="chart_manejo_comp")
        else:
            st.info("No hay datos comprometidos por manejo.")


def _render_table(df_raw, metric_key, metric_label, val_format, prefix):
    """Renderiza la tabla de volumen total."""
    st.markdown(f'<p class="section-header">VOLUMEN TOTAL (FACTURADO Y COMPROMETIDO SEPARADOS) ({metric_label.upper()})</p>', unsafe_allow_html=True)
    
    if df_raw.empty:
        return
    
    df_table = df_raw[df_raw['tipo'].isin(['Factura', 'Nota de Crédito', 'Comprometido'])].copy()
    if df_table.empty:
        st.warning("No hay datos para los filtros seleccionados.")
        return
    
    df_table['estado'] = df_table['tipo'].apply(lambda x: 'Facturado' if 'Factura' in x or 'Nota' in x else 'Comprometido')
    
    pivot_base = df_table.pivot_table(index=['programa', 'manejo', 'estado'], columns='especie', values=metric_key, aggfunc='sum', fill_value=0)
    
    final_rows = []
    all_specs = pivot_base.columns.tolist()
    
    programas_orden = ["Granel", "Retail", "Subproducto"]
    available_progs = df_table['programa'].unique()
    programas_final = [p for p in programas_orden if p in available_progs]
    for p in available_progs:
        if p not in programas_final:
            programas_final.append(p)
    
    for prog in programas_final:
        if prog in pivot_base.index.get_level_values(0):
            prog_data = pivot_base.loc[prog]
            prog_sub = prog_data.sum(axis=0)
            
            row_h = {'Etiqueta': f"<b>{prog}</b>", '_row_type': 'subtotal'}
            for s in all_specs:
                row_h[s] = prog_sub[s]
            row_h['Total'] = sum(prog_sub)
            final_rows.append(row_h)
            
            manejos = prog_data.index.get_level_values(0).unique()
            for mane in manejos:
                mane_data = prog_data.loc[mane]
                for estado in ["Facturado", "Comprometido"]:
                    if estado in mane_data.index:
                        row_d = {'Etiqueta': f"{mane} ({estado})", '_row_type': 'detail'}
                        for s in all_specs:
                            row_d[s] = mane_data.loc[estado, s]
                        row_d['Total'] = sum(mane_data.loc[estado])
                        final_rows.append(row_d)
    
    grand_row = {'Etiqueta': '<b>TOTAL</b>', '_row_type': 'total'}
    grand_total_data = pivot_base.sum()
    for s in all_specs:
        grand_row[s] = grand_total_data[s]
    grand_row['Total'] = grand_total_data.sum()
    final_rows.append(grand_row)
    
    columns = ['Etiqueta'] + all_specs + ['Total']
    html_rows = []
    for row in final_rows:
        row_type = row.get('_row_type', '')
        row_class = f'row-{row_type}' if row_type else ''
        cells = ''.join([f'<td>{fmt_val(row.get(c, ""), prefix, val_format)}</td>' for c in columns])
        html_rows.append(f'<tr class="{row_class}">{cells}</tr>')
    
    header_cells = ''.join([f'<th>{c}</th>' for c in columns])
    table_html = f'''
    <table class="custom-table">
        <thead><tr>{header_cells}</tr></thead>
        <tbody>{''.join(html_rows)}</tbody>
    </table>
    '''
    st.write(table_html, unsafe_allow_html=True)


def _render_pie_charts(df_raw, metric_key, metric_label, val_format, prefix):
    """Renderiza los gráficos de pie."""
    st.markdown('<div style="margin-top: 40px;"></div>', unsafe_allow_html=True)
    pie_col1, pie_col2 = st.columns(2)
    
    with pie_col1:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">VENDIDO CONVENCIONAL ({metric_label})</p>', unsafe_allow_html=True)
        _render_single_pie(df_raw, 'Convencional', metric_key, val_format, prefix, "pie_convencional", tipo_filter=['Factura', 'Nota de Crédito'])
    
    with pie_col2:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">VENDIDO ORGÁNICO ({metric_label})</p>', unsafe_allow_html=True)
        _render_single_pie(df_raw, 'Orgánico', metric_key, val_format, prefix, "pie_organico", tipo_filter=['Factura', 'Nota de Crédito'])
    
    # Pie charts - Comprometido
    st.markdown('<div style="margin-top: 30px;"></div>', unsafe_allow_html=True)
    pie_col3, pie_col4 = st.columns(2)
    
    with pie_col3:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">COMPROMETIDO CONVENCIONAL ({metric_label})</p>', unsafe_allow_html=True)
        _render_single_pie(df_raw, 'Convencional', metric_key, val_format, prefix, "pie_conv_comp", tipo_filter=['Comprometido'])
    
    with pie_col4:
        st.markdown(f'<p style="font-weight:800; color:#1b4f72; font-size:1.2rem; margin-bottom:15px;">COMPROMETIDO ORGÁNICO ({metric_label})</p>', unsafe_allow_html=True)
        _render_single_pie(df_raw, 'Orgánico', metric_key, val_format, prefix, "pie_org_comp", tipo_filter=['Comprometido'])


def _render_single_pie(df_raw, manejo, metric_key, val_format, prefix, key, tipo_filter=None):
    """Renderiza un gráfico de pie individual."""
    if df_raw.empty:
        return
    
    if tipo_filter is None:
        tipo_filter = ['Factura', 'Nota de Crédito']
    df_filtered = df_raw[(df_raw['manejo'] == manejo) & (df_raw['tipo'].isin(tipo_filter))]
    if df_filtered.empty:
        st.info("No hay datos.")
        return
    
    df_pie = df_filtered.groupby('especie')[metric_key].sum().reset_index()
    df_pie = df_pie[df_pie[metric_key] > 0].sort_values(metric_key, ascending=False)
    
    if df_pie.empty:
        st.info("No hay datos positivos.")
        return
    
    total_val = df_pie[metric_key].sum()
    
    fig = px.pie(df_pie, values=metric_key, names='especie', color='especie', color_discrete_map=PIE_COLORS, hole=0.45)
    
    center_color = '#1b4f72' if manejo == 'Convencional' else '#155724'
    fig.update_layout(
        showlegend=False,
        margin=dict(t=30, b=30, l=80, r=80),
        height=350,
        paper_bgcolor='rgba(0,0,0,0)',
        annotations=[dict(
            text=f'<b>{prefix}{total_val:{val_format}}</b><br><span style="font-size:10px">Total</span>',
            x=0.5, y=0.5, font_size=14, showarrow=False,
            font=dict(color=center_color)
        )]
    )
    fig.update_traces(
        textposition='outside',
        textinfo='label+percent',
        texttemplate='<b>%{label}</b><br>%{percent:.1%}',
        textfont=dict(color="#333", size=11),
        marker=dict(line=dict(color='#ffffff', width=2)),
        pull=[0.05 if i == 0 else 0 for i in range(len(df_pie))],
        hovertemplate=f'<b>%{{label}}</b><br>Valor: {prefix}%{{value:{val_format}}}<br>Porcentaje: %{{percent:.1%}}<extra></extra>'
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False}, key=key)
    
    # Tabla resumen
    st.markdown('<div style="margin-top:-20px;">', unsafe_allow_html=True)
    for _, row in df_pie.iterrows():
        color = PIE_COLORS.get(row['especie'], '#666')
        st.markdown(f'''
        <div style="display:flex; justify-content:space-between; padding:5px 10px; 
                    border-bottom:1px solid #eee; font-size:0.85rem;">
            <span style="color:{color}; font-weight:600;">● {row['especie']}</span>
            <span style="color:#333;">{prefix}{row[metric_key]:{val_format}}</span>
        </div>
        ''', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
