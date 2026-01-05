"""
Contenido principal del dashboard de Bandejas.
Recepción de bandejas desde procesos externos. Control de cantidades y trazabilidad por proveedor.
"""
import streamlit as st
import pandas as pd
import altair as alt
import io
from datetime import datetime

from .shared import fmt_fecha, fmt_numero, load_in_data, load_out_data, load_stock_data

# Importar servicio de reportes
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from backend.services.report_service import generate_bandejas_report_pdf


def render(username: str, password: str):
    """Renderiza el contenido principal del dashboard de Bandejas."""
    
    # ==================== CARGAR DATOS ====================
    try:
        with st.spinner("Cargando datos de Odoo..."):
            df_in = load_in_data(username, password)
            df_out = load_out_data(username, password)
    except Exception as e:
        st.error(f"Error al conectar con Odoo: {e}")
        st.stop()

    if df_in.empty and df_out.empty:
        st.warning("No se encontraron movimientos para 'Bandeja'.")
        return
    
    st.success(f"✅ Datos cargados correctamente.")
    
    # ==================== PREPARAR DATOS ====================
    if not df_in.empty:
        df_in['date_order'] = pd.to_datetime(df_in['date_order'])
    if not df_out.empty:
        df_out['date'] = pd.to_datetime(df_out['date'])
    
    # Determinar rango de años
    dates = pd.Series(dtype='datetime64[ns]')
    if not df_in.empty:
        dates = pd.concat([dates, df_in['date_order']])
    if not df_out.empty:
        dates = pd.concat([dates, df_out['date']])
    
    if not dates.empty:
        data_min_year = dates.dt.year.min()
        data_max_year = dates.dt.year.max()
        current_year = pd.Timestamp.now().year
        max_year = max(data_max_year, current_year, 2026)
        years = ['Todos'] + list(range(data_min_year, max_year + 1))
    else:
        years = ['Todos', 2025]
    
    months_map = {1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril', 5: 'Mayo', 6: 'Junio',
                  7: 'Julio', 8: 'Agosto', 9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'}
    
    # ==================== FILTROS ====================
    with st.expander("📅 Filtros de Fecha", expanded=True):
        filter_type = st.radio("Tipo de Filtro", ["Por Mes/Año", "Por Temporada"], horizontal=True, key="filter_type_bandejas")
        
        selected_year = 'Todos'
        selected_month_name = 'Todos'
        selected_months_names = []
        selected_season = None
        
        if filter_type == "Por Mes/Año":
            col1, col2 = st.columns(2)
            with col1:
                selected_year = st.selectbox("Año", years, index=0, key="year_bandejas")
            with col2:
                month_options = [months_map[m] for m in range(1, 13)]
                selected_months_names = st.multiselect("Mes(es)", month_options, default=[], placeholder="Todos los meses", key="month_bandejas")
        else:
            season_options = []
            for y in range(2024, max_year + 1):
                season_options.append(f"Temporada {str(y)[-2:]}-{str(y+1)[-2:]}")
            
            today = pd.Timestamp.now()
            current_season_start = today.year if today.month >= 11 else today.year - 1
            current_season_label = f"Temporada {str(current_season_start)[-2:]}-{str(current_season_start+1)[-2:]}"
            
            default_idx = len(season_options) - 1
            if current_season_label in season_options:
                default_idx = season_options.index(current_season_label)
            
            selected_season = st.selectbox("Temporada", season_options, index=default_idx, key="season_bandejas")
        
        # Convertir meses a números
        selected_months = []
        if selected_months_names:
            for name in selected_months_names:
                selected_months.append([k for k, v in months_map.items() if v == name][0])
        
        # Verificar si HOY está en el rango seleccionado (para mostrar stock)
        is_today_in_range = False
        today = pd.Timestamp.now().normalize()
        
        if filter_type == "Por Mes/Año":
            year_match = (selected_year == 'Todos') or (selected_year == today.year)
            month_match = (len(selected_months) == 0) or (today.month in selected_months)
            if year_match and month_match:
                is_today_in_range = True
        else:
            if selected_season:
                parts = selected_season.replace("Temporada ", "").split("-")
                start_yy = int(parts[0])
                start_year = 2000 + start_yy
                end_year = start_year + 1
                start_date = pd.Timestamp(f"{start_year}-11-01")
                end_date = pd.Timestamp(f"{end_year}-10-31")
                if start_date <= today <= end_date:
                    is_today_in_range = True
    
    # ==================== FILTRAR DATOS ====================
    df_in_grouped, df_out_grouped, df_out_projected = _filtrar_datos(
        df_in, df_out, filter_type, selected_year, selected_months, selected_season, today
    )
    
    # ==================== MERGE DATOS ====================
    df_merged = pd.merge(df_in_grouped, df_out_grouped, on='partner_name', how='outer').fillna(0)
    df_merged = df_merged.rename(columns={'partner_name': 'Productor'})
    df_merged['Bandejas en Productor'] = df_merged['Despachadas'] - df_merged['Recepcionadas']
    
    # ==================== CARGAR STOCK ====================
    with st.spinner("Cargando niveles de stock..."):
        df_stock = load_stock_data(username, password)
        
        if not is_today_in_range and not df_stock.empty:
            df_stock['qty_available'] = 0
    
    if not df_stock.empty:
        def classify_stock(row):
            code = str(row.get('default_code', '')).strip().upper()
            return 'Limpia' if code.endswith('L') else 'Sucia'
        
        df_stock['Tipo'] = df_stock.apply(classify_stock, axis=1)
    
    # ==================== KPIs CONSOLIDADOS ====================
    total_recepcionadas = df_merged['Recepcionadas'].sum() if 'Recepcionadas' in df_merged.columns else 0
    total_despachadas = df_merged['Despachadas'].sum() if 'Despachadas' in df_merged.columns else 0
    total_en_productores = df_merged['Bandejas en Productor'].sum() if 'Bandejas en Productor' in df_merged.columns else 0
    
    total_stock_sucias = 0
    total_stock_limpias = 0
    if not df_stock.empty:
        total_stock_sucias = abs(df_stock[df_stock['Tipo'] == 'Sucia']['qty_available'].sum())
        total_stock_limpias = abs(df_stock[df_stock['Tipo'] == 'Limpia']['qty_available'].sum())
    total_stock = total_stock_sucias + total_stock_limpias
    
    st.markdown("---")
    st.subheader("📊 KPIs Consolidados")
    
    kpi_row1 = st.columns(3)
    with kpi_row1[0]:
        st.metric("📤 Despachadas", fmt_numero(total_despachadas))
    with kpi_row1[1]:
        st.metric("📥 Recepcionadas", fmt_numero(total_recepcionadas))
    with kpi_row1[2]:
        st.metric("🏠 En Productores", fmt_numero(total_en_productores))
    
    kpi_row2 = st.columns(3)
    with kpi_row2[0]:
        st.metric("📦 Stock Total", fmt_numero(total_stock))
    with kpi_row2[1]:
        st.metric("✨ Limpias", fmt_numero(total_stock_limpias))
    with kpi_row2[2]:
        st.metric("🧹 Sucias", fmt_numero(total_stock_sucias))
    
    # ==================== TABLA GESTIÓN BANDEJAS ====================
    if not df_stock.empty:
        _render_gestion_bandejas(df_stock, df_out_projected, total_despachadas, total_recepcionadas, 
                                 total_en_productores, total_stock, total_stock_limpias, total_stock_sucias,
                                 filter_type, selected_season, selected_year, selected_months_names)
    
    st.markdown("---")
    
    # ==================== TABLA DETALLE POR PRODUCTOR ====================
    _render_detalle_productores(df_merged, total_despachadas, total_recepcionadas, total_en_productores,
                                total_stock, total_stock_limpias, total_stock_sucias,
                                filter_type, selected_season, selected_year, selected_months_names)


def _filtrar_datos(df_in, df_out, filter_type, selected_year, selected_months, selected_season, today):
    """Filtra datos de entrada y salida según los filtros seleccionados."""
    df_in_grouped = pd.DataFrame(columns=['partner_name', 'Recepcionadas'])
    if not df_in.empty:
        mask_in = pd.Series(True, index=df_in.index)
        
        if filter_type == "Por Mes/Año":
            if selected_year != 'Todos':
                mask_in &= (df_in['date_order'].dt.year == selected_year)
            if selected_months:
                mask_in &= (df_in['date_order'].dt.month.isin(selected_months))
        else:
            if selected_season:
                parts = selected_season.replace("Temporada ", "").split("-")
                start_yy = int(parts[0])
                start_year = 2000 + start_yy
                end_year = start_year + 1
                start_date = pd.Timestamp(f"{start_year}-11-01")
                end_date = pd.Timestamp(f"{end_year}-10-31")
                mask_in &= (df_in['date_order'] >= start_date) & (df_in['date_order'] <= end_date)
        
        df_in_filtered = df_in.loc[mask_in]
        if not df_in_filtered.empty:
            df_in_grouped = df_in_filtered.groupby('partner_name')['qty_received'].sum().reset_index()
            df_in_grouped = df_in_grouped.rename(columns={'qty_received': 'Recepcionadas'})
    
    df_out_grouped = pd.DataFrame(columns=['partner_name', 'Despachadas'])
    df_out_projected = pd.DataFrame()
    
    if not df_out.empty:
        mask_out = pd.Series(True, index=df_out.index)
        
        if filter_type == "Por Mes/Año":
            if selected_year != 'Todos':
                mask_out &= (df_out['date'].dt.year == selected_year)
            if selected_months:
                mask_out &= (df_out['date'].dt.month.isin(selected_months))
        else:
            if selected_season:
                parts = selected_season.replace("Temporada ", "").split("-")
                start_yy = int(parts[0])
                start_year = 2000 + start_yy
                end_year = start_year + 1
                start_date = pd.Timestamp(f"{start_year}-11-01")
                end_date = pd.Timestamp(f"{end_year}-10-31")
                mask_out &= (df_out['date'] >= start_date) & (df_out['date'] <= end_date)
        
        df_out_filtered = df_out.loc[mask_out]
        
        # Proyectados
        assigned_mask = (df_out['state'] == 'assigned')
        date_mask = (df_out['date'] >= today)
        df_out_projected = df_out[assigned_mask & date_mask & mask_out]
        
        if not df_out_filtered.empty:
            df_out_done = df_out_filtered[df_out_filtered['state'] == 'done']
            if not df_out_done.empty:
                df_out_grouped = df_out_done.groupby('partner_name')['qty_sent'].sum().reset_index()
                df_out_grouped = df_out_grouped.rename(columns={'qty_sent': 'Despachadas'})
    
    return df_in_grouped, df_out_grouped, df_out_projected


def _render_gestion_bandejas(df_stock, df_out_projected, total_despachadas, total_recepcionadas, 
                             total_en_productores, total_stock, total_stock_limpias, total_stock_sucias,
                             filter_type, selected_season, selected_year, selected_months_names):
    """Renderiza la sección de Gestión de Bandejas."""
    st.markdown("---")
    st.subheader("Gestión Bandejas")
    
    df_stock['BaseCode'] = df_stock['default_code'].apply(lambda x: str(x).strip().upper().rstrip('L'))
    df_grouped_stock = df_stock.groupby(['BaseCode', 'Tipo'])['qty_available'].sum().unstack(fill_value=0)
    
    if 'Sucia' not in df_grouped_stock.columns:
        df_grouped_stock['Sucia'] = 0
    if 'Limpia' not in df_grouped_stock.columns:
        df_grouped_stock['Limpia'] = 0
    
    df_grouped_stock = df_grouped_stock.reset_index()
    
    name_map = df_stock.sort_values('Tipo', ascending=False).drop_duplicates('BaseCode')[['BaseCode', 'display_name']]
    df_gestion = pd.merge(df_grouped_stock, name_map, on='BaseCode', how='left')
    
    def clean_name(name):
        name = str(name)
        name = name.replace("(copia)", "").replace("- Sucia", "").replace("Limpia", "").strip()
        return name
    
    df_gestion['display_name'] = df_gestion['display_name'].apply(clean_name)
    df_gestion = df_gestion.rename(columns={
        'BaseCode': 'Código',
        'display_name': 'Nombre',
        'Sucia': 'Bandejas Sucias',
        'Limpia': 'Bandejas Limpias'
    })
    
    # Agregar Proyectados
    if not df_out_projected.empty:
        df_out_projected = df_out_projected.copy()
        df_out_projected['BaseCode'] = df_out_projected['default_code'].apply(lambda x: str(x).strip().upper().rstrip('L'))
        df_proj_grouped = df_out_projected.groupby('BaseCode')['qty_sent'].sum().reset_index()
        df_proj_grouped = df_proj_grouped.rename(columns={'qty_sent': 'Proyectados'})
        df_gestion = pd.merge(df_gestion, df_proj_grouped, left_on='Código', right_on='BaseCode', how='left').fillna(0)
        if 'BaseCode' in df_gestion.columns:
            df_gestion = df_gestion.drop(columns=['BaseCode'])
    else:
        df_gestion['Proyectados'] = 0
    
    if 'Proyectados' not in df_gestion.columns:
        df_gestion['Proyectados'] = 0
    
    # Aplicar valor absoluto
    df_gestion['Bandejas Sucias'] = df_gestion['Bandejas Sucias'].abs()
    df_gestion['Bandejas Limpias'] = df_gestion['Bandejas Limpias'].abs()
    df_gestion['Proyectados'] = df_gestion['Proyectados'].abs()
    df_gestion['Stock Total'] = df_gestion['Bandejas Sucias'] + df_gestion['Bandejas Limpias']
    
    # Guardar datos para gráfico
    df_gestion_chart = df_gestion.copy()
    df_gestion_chart = df_gestion_chart.melt(
        id_vars=['Nombre'], 
        value_vars=['Bandejas Sucias', 'Bandejas Limpias', 'Proyectados'], 
        var_name='Tipo', 
        value_name='Cantidad'
    )
    df_gestion_chart['Tipo'] = df_gestion_chart['Tipo'].replace({
        'Bandejas Sucias': 'Sucia', 
        'Bandejas Limpias': 'Limpia', 
        'Proyectados': 'Proyectada'
    })
    
    # Calcular totales
    total_sucias = df_gestion['Bandejas Sucias'].sum()
    total_limpias = df_gestion['Bandejas Limpias'].sum()
    total_proyectados = df_gestion['Proyectados'].sum()
    total_stock_gestion = df_gestion['Stock Total'].sum()
    
    # Agregar fila TOTAL
    total_row = pd.DataFrame([{
        'Código': '',
        'Nombre': 'TOTAL',
        'Bandejas Sucias': total_sucias,
        'Bandejas Limpias': total_limpias,
        'Proyectados': total_proyectados,
        'Stock Total': total_stock_gestion
    }])
    df_gestion = pd.concat([df_gestion, total_row], ignore_index=True)
    
    # Formatear números
    df_gestion['Bandejas Sucias'] = df_gestion['Bandejas Sucias'].apply(lambda x: fmt_numero(x))
    df_gestion['Bandejas Limpias'] = df_gestion['Bandejas Limpias'].apply(lambda x: fmt_numero(x))
    df_gestion['Proyectados'] = df_gestion['Proyectados'].apply(lambda x: fmt_numero(x))
    df_gestion['Stock Total'] = df_gestion['Stock Total'].apply(lambda x: fmt_numero(x))
    
    def highlight_total_gestion(row):
        if row['Nombre'] == 'TOTAL':
            return ['background-color: #ffc107; color: black; font-weight: bold'] * len(row)
        return [''] * len(row)
    
    st.dataframe(
        df_gestion[['Nombre', 'Bandejas Sucias', 'Bandejas Limpias', 'Proyectados', 'Stock Total']].style.apply(highlight_total_gestion, axis=1),
        hide_index=True,
        use_container_width=True
    )
    
    # Gráfico
    st.markdown("##### Stock por Producto (Sucia vs Limpia)")
    
    stock_base = alt.Chart(df_gestion_chart).encode(
        x=alt.X('Nombre', axis=alt.Axis(title=None, labelAngle=0)),
        y=alt.Y('Cantidad', axis=alt.Axis(title='Cantidad')),
        color=alt.Color('Tipo', scale=alt.Scale(domain=['Sucia', 'Limpia', 'Proyectada'], range=['#dc3545', '#28a745', '#ff7f0e']), legend=alt.Legend(title="Tipo de Bandeja", orient='top')),
        tooltip=['Nombre', 'Tipo', alt.Tooltip('Cantidad', format=',.0f')]
    )
    
    stock_bars = stock_base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(xOffset='Tipo:N')
    stock_text = stock_base.mark_text(align='center', baseline='bottom', dy=-5, fontSize=10).encode(
        xOffset='Tipo:N',
        text=alt.Text('Cantidad:Q', format=',.0f')
    )
    
    final_stock_chart = (stock_bars + stock_text).properties(
        height=400,
        title="Detalle de Stock por Producto"
    ).configure_axis(labelFontSize=12, titleFontSize=14, grid=False).configure_legend(titleFontSize=12, labelFontSize=11)
    
    st.altair_chart(final_stock_chart, use_container_width=True)
    
    # Exportar
    st.markdown("##### 📥 Exportar Datos de Gestión")
    export_gestion_cols = st.columns(2)
    
    df_gestion_export = df_gestion_chart.pivot(index='Nombre', columns='Tipo', values='Cantidad').reset_index()
    df_gestion_export.columns.name = None
    if 'Sucia' not in df_gestion_export.columns:
        df_gestion_export['Sucia'] = 0
    if 'Limpia' not in df_gestion_export.columns:
        df_gestion_export['Limpia'] = 0
    if 'Proyectada' not in df_gestion_export.columns:
        df_gestion_export['Proyectada'] = 0
    df_gestion_export['Sucia'] = df_gestion_export['Sucia'].abs()
    df_gestion_export['Limpia'] = df_gestion_export['Limpia'].abs()
    df_gestion_export['Proyectada'] = df_gestion_export['Proyectada'].abs()
    df_gestion_export['Stock Total'] = df_gestion_export['Sucia'] + df_gestion_export['Limpia']
    df_gestion_export = df_gestion_export.rename(columns={'Sucia': 'Bandejas Sucias', 'Limpia': 'Bandejas Limpias', 'Proyectada': 'Proyectados'})
    
    with export_gestion_cols[0]:
        try:
            buffer_gestion = io.BytesIO()
            with pd.ExcelWriter(buffer_gestion, engine='xlsxwriter') as writer:
                df_gestion_export.to_excel(writer, sheet_name='Gestión Bandejas', index=False)
            st.download_button(
                "📥 Descargar Excel (Gestión)",
                buffer_gestion.getvalue(),
                "bandejas_gestion.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_gestion_excel"
            )
        except Exception:
            csv_gestion = df_gestion_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV (Gestión)", csv_gestion, "bandejas_gestion.csv", "text/csv", key="download_gestion_csv")
    
    with export_gestion_cols[1]:
        if st.button("📄 Generar PDF Informe", key="generate_pdf_btn"):
            try:
                kpis_pdf = {
                    'despachadas': total_despachadas,
                    'recepcionadas': total_recepcionadas,
                    'en_productores': total_en_productores,
                    'stock_total': total_stock,
                    'limpias': total_stock_limpias,
                    'sucias': total_stock_sucias
                }
                
                gestion_records = df_gestion_export.to_dict(orient='records')
                
                filtros_pdf = {}
                if filter_type == "Por Temporada" and selected_season:
                    filtros_pdf['temporada'] = selected_season
                elif filter_type == "Por Mes/Año":
                    if selected_year != 'Todos':
                        filtros_pdf['año'] = str(selected_year)
                    if selected_months_names:
                        filtros_pdf['mes'] = ', '.join(selected_months_names)
                
                pdf_bytes = generate_bandejas_report_pdf(
                    kpis=kpis_pdf,
                    df_gestion=gestion_records,
                    df_productores=[],
                    filtros=filtros_pdf
                )
                st.download_button(
                    "⬇️ Descargar PDF",
                    pdf_bytes,
                    "informe_bandejas.pdf",
                    "application/pdf",
                    key="download_pdf"
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")


def _render_detalle_productores(df_merged, total_despachadas, total_recepcionadas, total_en_productores,
                                total_stock, total_stock_limpias, total_stock_sucias,
                                filter_type, selected_season, selected_year, selected_months_names):
    """Renderiza la sección de Detalle por Productor."""
    st.subheader("Detalle por Productor")
    
    all_producers = sorted(df_merged['Productor'].unique())
    
    with st.expander("🔍 Filtrar por Productor", expanded=False):
        selected_producers = st.multiselect("Seleccionar Productores", all_producers, key="producers_bandejas")
    
    if selected_producers:
        df_merged = df_merged[df_merged['Productor'].isin(selected_producers)]
    
    # Calcular totales
    total_in = df_merged['Recepcionadas'].sum()
    total_out = df_merged['Despachadas'].sum()
    total_diff = total_out - total_in
    
    # Mostrar totales
    tot_cols = st.columns(3)
    with tot_cols[0]:
        st.metric("📥 Total Recepcionadas", fmt_numero(total_in))
    with tot_cols[1]:
        st.metric("📤 Total Despachadas", fmt_numero(total_out))
    with tot_cols[2]:
        st.metric("🏠 Total en Productores", fmt_numero(total_diff))
    
    # Guardar para gráfico ANTES de formatear
    df_chart_prod = df_merged.copy()
    
    # Ordenar por Bandejas en Productor descendente
    df_merged_sorted = df_merged.sort_values('Bandejas en Productor', ascending=False)
    df_display = df_merged_sorted.copy()
    df_display['Recepcionadas'] = df_display['Recepcionadas'].apply(lambda x: fmt_numero(x))
    df_display['Despachadas'] = df_display['Despachadas'].apply(lambda x: fmt_numero(x))
    df_display['Bandejas en Productor'] = df_display['Bandejas en Productor'].apply(lambda x: fmt_numero(x))
    df_display = df_display[['Productor', 'Recepcionadas', 'Despachadas', 'Bandejas en Productor']]
    
    st.dataframe(df_display, hide_index=True, use_container_width=True)
    
    # Gráfico
    st.markdown("##### Recepción vs Despacho por Productor")
    
    df_chart = df_chart_prod.melt(
        id_vars=['Productor'], 
        value_vars=['Recepcionadas', 'Despachadas', 'Bandejas en Productor'], 
        var_name='Tipo', 
        value_name='Cantidad'
    )
    
    df_chart_prod['Total_Vol'] = df_chart_prod['Recepcionadas'] + df_chart_prod['Despachadas']
    sort_order = df_chart_prod.sort_values('Total_Vol', ascending=False)['Productor'].tolist()
    
    domain = ['Recepcionadas', 'Despachadas', 'Bandejas en Productor']
    range_ = ['#28a745', '#dc3545', '#1f77b4']
    
    base = alt.Chart(df_chart).encode(
        x=alt.X('Productor', axis=alt.Axis(title=None, labelAngle=-90), sort=sort_order),
        y=alt.Y('Cantidad', axis=alt.Axis(title='Cantidad')),
        color=alt.Color('Tipo', scale=alt.Scale(domain=domain, range=range_), legend=alt.Legend(title="Tipo de Movimiento", orient='top')),
        tooltip=['Productor', 'Tipo', alt.Tooltip('Cantidad', format=',.0f')]
    )
    
    bars = base.mark_bar(cornerRadiusTopLeft=5, cornerRadiusTopRight=5).encode(xOffset='Tipo:N')
    text = base.mark_text(align='center', baseline='bottom', dy=-5, fontSize=10).encode(
        xOffset='Tipo:N',
        text=alt.Text('Cantidad:Q', format=',.0f')
    )
    
    chart = (bars + text).properties(
        height=400,
        title="Detalle de Movimientos por Productor"
    ).configure_axis(labelFontSize=12, titleFontSize=14, grid=False).configure_legend(titleFontSize=12, labelFontSize=11)
    
    st.altair_chart(chart, use_container_width=True)
    
    # Exportar
    st.markdown("##### 📥 Exportar Datos por Productor")
    export_prod_cols = st.columns(2)
    
    df_prod_export = df_merged_sorted[['Productor', 'Recepcionadas', 'Despachadas', 'Bandejas en Productor']].copy()
    
    with export_prod_cols[0]:
        try:
            buffer_prod = io.BytesIO()
            with pd.ExcelWriter(buffer_prod, engine='xlsxwriter') as writer:
                df_prod_export.to_excel(writer, sheet_name='Por Productor', index=False)
            st.download_button(
                "📥 Descargar Excel (Por Productor)",
                buffer_prod.getvalue(),
                "bandejas_productores.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_prod_excel"
            )
        except Exception:
            csv_prod = df_prod_export.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV (Por Productor)", csv_prod, "bandejas_productores.csv", "text/csv", key="download_prod_csv")
    
    with export_prod_cols[1]:
        if st.button("📄 Generar PDF (Por Productor)", key="generate_pdf_prod_btn"):
            try:
                kpis_pdf = {
                    'despachadas': total_despachadas,
                    'recepcionadas': total_recepcionadas,
                    'en_productores': total_en_productores,
                    'stock_total': total_stock,
                    'limpias': total_stock_limpias,
                    'sucias': total_stock_sucias
                }
                
                prod_records = df_prod_export.to_dict(orient='records')
                
                filtros_pdf = {}
                if filter_type == "Por Temporada" and selected_season:
                    filtros_pdf['temporada'] = selected_season
                elif filter_type == "Por Mes/Año":
                    if selected_year != 'Todos':
                        filtros_pdf['año'] = str(selected_year)
                    if selected_months_names:
                        filtros_pdf['mes'] = ', '.join(selected_months_names)
                
                pdf_bytes = generate_bandejas_report_pdf(
                    kpis=kpis_pdf,
                    df_gestion=[],
                    df_productores=prod_records,
                    filtros=filtros_pdf
                )
                st.download_button(
                    "⬇️ Descargar PDF",
                    pdf_bytes,
                    "bandejas_por_productor.pdf",
                    "application/pdf",
                    key="download_pdf_prod"
                )
            except Exception as e:
                st.error(f"Error al generar PDF: {e}")
