"""
Recepción de bandejas desde procesos externos. Control de cantidades y trazabilidad por proveedor.
"""
import streamlit as st
import pandas as pd
import altair as alt
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.auth import verificar_autenticacion, proteger_pagina, get_credenciales
from shared.odoo_client import OdooClient


# --- Funciones de formateo chileno ---
def fmt_fecha(fecha_str):
    """Convierte fecha ISO a formato DD/MM/AAAA"""
    if not fecha_str:
        return ""
    try:
        if isinstance(fecha_str, (pd.Timestamp, datetime)):
            return fecha_str.strftime("%d/%m/%Y")
        if isinstance(fecha_str, str):
            if " " in fecha_str:
                fecha_str = fecha_str.split(" ")[0]
            elif "T" in fecha_str:
                fecha_str = fecha_str.split("T")[0]
            dt = datetime.strptime(fecha_str, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
    except:
        pass
    return str(fecha_str)

def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal"""
    if valor is None:
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)

st.set_page_config(page_title="Recepción Bandejas Río Futuro Procesos", layout="wide")

# Verificar autenticación
if not proteger_pagina():
    st.stop()

st.title("Recepción Bandejas Río Futuro Procesos")

# Obtener credenciales
username, password = get_credenciales()

if not username or not password:
    st.error("No se encontraron credenciales. Por favor inicie sesión nuevamente.")
    st.stop()


# ==================== FUNCIONES DE CARGA DE DATOS ====================
@st.cache_data(ttl=300)
def load_in_data(_username, _password):
    client = OdooClient(username=_username, password=_password)
    return get_tray_in_movements(client)

@st.cache_data(ttl=300)
def load_out_data(_username, _password):
    client = OdooClient(username=_username, password=_password)
    return get_tray_out_movements(client)

@st.cache_data(ttl=300)
def load_stock_data(_username, _password):
    client = OdooClient(username=_username, password=_password)
    return get_tray_stock_levels(client)


def get_tray_in_movements(client):
    """Movimientos de entrada de bandejas (recepción de productores)"""
    CATEG_ID = 107  # BANDEJAS A PRODUCTOR
    
    product_ids = client.search('product.product', [['categ_id', '=', CATEG_ID]])
    if not product_ids:
        return pd.DataFrame()
    
    domain = [
        ['product_id', 'in', product_ids],
        ['state', 'in', ['done', 'assigned']]
    ]
    
    move_ids = client.search('stock.move', domain, limit=20000, order='date desc')
    moves = client.read('stock.move', move_ids, 
                       ['date', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'state'])
    
    if not moves:
        return pd.DataFrame()
    
    picking_ids = list(set([m['picking_id'][0] for m in moves if m.get('picking_id')]))
    product_ids_in_moves = list(set([m['product_id'][0] for m in moves if m.get('product_id')]))
    
    picking_map = {}
    if picking_ids:
        pickings = client.read('stock.picking', picking_ids, ['origin', 'partner_id'])
        for p in pickings:
            p_data = {'origin': p['origin'] or '', 'partner_name': 'Unknown'}
            if p.get('partner_id'):
                p_data['partner_name'] = p['partner_id'][1]
            picking_map[p['id']] = p_data
    
    product_code_map = {}
    if product_ids_in_moves:
        products = client.read('product.product', product_ids_in_moves, ['default_code'])
        for p in products:
            product_code_map[p['id']] = p.get('default_code', '')
    
    final_moves = []
    for move in moves:
        picking_id = move['picking_id'][0] if move.get('picking_id') else None
        p_data = picking_map.get(picking_id, {'origin': '', 'partner_name': 'Unknown'})
        origin = p_data['origin']
        
        is_valid = origin.startswith('P') or origin.startswith('OC')
        if not is_valid:
            if move['date'] < '2025-01-01' and origin.startswith('Retorno'):
                is_valid = True
        
        if not is_valid:
            continue
        
        qty = move['quantity_done']
        if qty == 0 and move['state'] == 'done':
            qty = move['product_uom_qty']
        
        if qty > 0:
            final_moves.append({
                'date_order': move['date'],
                'product_name': move['product_id'][1] if move.get('product_id') else '',
                'default_code': product_code_map.get(move['product_id'][0], '') if move.get('product_id') else '',
                'order_name': origin,
                'partner_name': p_data['partner_name'],
                'qty_received': qty
            })
    
    return pd.DataFrame(final_moves)


def get_tray_out_movements(client):
    """Movimientos de salida de bandejas (despacho a productores)"""
    CATEG_ID = 107
    
    product_ids = client.search('product.product', [['categ_id', '=', CATEG_ID]])
    if not product_ids:
        return pd.DataFrame()
    
    domain = [
        ['picking_type_id', '=', 2],  # Expediciones
        ['product_id', 'in', product_ids],
        ['state', 'in', ['done', 'assigned']]
    ]
    
    move_ids = client.search('stock.move', domain, limit=20000, order='date desc')
    moves = client.read('stock.move', move_ids,
                       ['date', 'picking_id', 'product_id', 'product_uom_qty', 'quantity_done', 'state'])
    
    if not moves:
        return pd.DataFrame()
    
    picking_ids = list(set([m['picking_id'][0] for m in moves if m.get('picking_id')]))
    product_ids_in_moves = list(set([m['product_id'][0] for m in moves if m.get('product_id')]))
    
    picking_map = {}
    if picking_ids:
        pickings = client.read('stock.picking', picking_ids, ['partner_id', 'name'])
        for p in pickings:
            p_name = p['partner_id'][1] if p.get('partner_id') else 'Unknown'
            picking_map[p['id']] = {'partner_name': p_name, 'picking_name': p['name']}
    
    product_code_map = {}
    if product_ids_in_moves:
        products = client.read('product.product', product_ids_in_moves, ['default_code'])
        for p in products:
            product_code_map[p['id']] = p.get('default_code', '')
    
    final_moves = []
    for move in moves:
        picking_id = move['picking_id'][0] if move.get('picking_id') else None
        p_data = picking_map.get(picking_id, {'partner_name': 'Unknown', 'picking_name': ''})
        
        qty = move['quantity_done']
        if qty == 0 and move['state'] == 'done':
            qty = move['product_uom_qty']
        
        if qty > 0:
            final_moves.append({
                'date': move['date'],
                'product_name': move['product_id'][1] if move.get('product_id') else '',
                'default_code': product_code_map.get(move['product_id'][0], '') if move.get('product_id') else '',
                'picking_name': p_data['picking_name'],
                'partner_name': p_data['partner_name'],
                'state': move['state'],
                'qty_sent': qty
            })
    
    return pd.DataFrame(final_moves)


def get_tray_stock_levels(client):
    """Stock actual de bandejas"""
    CATEG_ID = 107
    
    product_ids = client.search('product.product', [['categ_id', '=', CATEG_ID]])
    if not product_ids:
        return pd.DataFrame()
    
    domain = [
        ['product_id', 'in', product_ids],
        ['location_id.usage', '=', 'internal']
    ]
    
    quant_ids = client.search('stock.quant', domain)
    quants = client.read('stock.quant', quant_ids, ['product_id', 'quantity', 'location_id'])
    
    product_qty_map = {}
    for q in quants:
        pid = q['product_id'][0]
        product_qty_map[pid] = product_qty_map.get(pid, 0) + q['quantity']
    
    products = client.read('product.product', product_ids, ['display_name', 'default_code'])
    
    data = []
    for p in products:
        pid = p['id']
        data.append({
            'display_name': p['display_name'],
            'default_code': p.get('default_code', ''),
            'qty_available': product_qty_map.get(pid, 0)
        })
    
    return pd.DataFrame(data)


# ==================== CARGAR DATOS ====================
try:
    with st.spinner("Cargando datos de Odoo..."):
        df_in = load_in_data(username, password)
        df_out = load_out_data(username, password)
except Exception as e:
    st.error(f"Error al conectar con Odoo: {e}")
    st.stop()

if not df_in.empty or not df_out.empty:
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
        selected_season = None
        
        if filter_type == "Por Mes/Año":
            col1, col2 = st.columns(2)
            with col1:
                selected_year = st.selectbox("Año", years, index=0, key="year_bandejas")
            with col2:
                month_options = ['Todos'] + [months_map[m] for m in range(1, 13)]
                selected_month_name = st.selectbox("Mes", month_options, index=0, key="month_bandejas")
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
        
        # Convertir mes a número
        selected_month = None
        if selected_month_name != 'Todos':
            selected_month = [k for k, v in months_map.items() if v == selected_month_name][0]
        
        # Verificar si HOY está en el rango seleccionado (para mostrar stock)
        is_today_in_range = False
        today = pd.Timestamp.now().normalize()
        
        if filter_type == "Por Mes/Año":
            year_match = (selected_year == 'Todos') or (selected_year == today.year)
            month_match = (selected_month_name == 'Todos') or (selected_month == today.month)
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
        
        # ==================== FILTRAR DATOS DE ENTRADA ====================
        df_in_grouped = pd.DataFrame(columns=['partner_name', 'Recepcionadas'])
        if not df_in.empty:
            mask_in = pd.Series(True, index=df_in.index)
            
            if filter_type == "Por Mes/Año":
                if selected_year != 'Todos':
                    mask_in &= (df_in['date_order'].dt.year == selected_year)
                if selected_month_name != 'Todos':
                    mask_in &= (df_in['date_order'].dt.month == selected_month)
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
        
        # ==================== FILTRAR DATOS DE SALIDA ====================
        df_out_grouped = pd.DataFrame(columns=['partner_name', 'Despachadas'])
        df_out_projected = pd.DataFrame()
        
        if not df_out.empty:
            mask_out = pd.Series(True, index=df_out.index)
            
            if filter_type == "Por Mes/Año":
                if selected_year != 'Todos':
                    mask_out &= (df_out['date'].dt.year == selected_year)
                if selected_month_name != 'Todos':
                    mask_out &= (df_out['date'].dt.month == selected_month)
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
            
            # Proyectados: Assigned + Fechas futuras + Rango seleccionado
            assigned_mask = (df_out['state'] == 'assigned')
            date_mask = (df_out['date'] >= today)
            df_out_projected = df_out[assigned_mask & date_mask & mask_out]
            
            if not df_out_filtered.empty:
                df_out_done = df_out_filtered[df_out_filtered['state'] == 'done']
                if not df_out_done.empty:
                    df_out_grouped = df_out_done.groupby('partner_name')['qty_sent'].sum().reset_index()
                    df_out_grouped = df_out_grouped.rename(columns={'qty_sent': 'Despachadas'})
    
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
    st.markdown("---")
    st.subheader("📊 KPIs Consolidados")
    
    # Calcular métricas
    total_recepcionadas = df_merged['Recepcionadas'].sum() if 'Recepcionadas' in df_merged.columns else 0
    total_despachadas = df_merged['Despachadas'].sum() if 'Despachadas' in df_merged.columns else 0
    total_en_productores = df_merged['Bandejas en Productor'].sum() if 'Bandejas en Productor' in df_merged.columns else 0
    
    total_stock_sucias = 0
    total_stock_limpias = 0
    if not df_stock.empty:
        total_stock_sucias = df_stock[df_stock['Tipo'] == 'Sucia']['qty_available'].sum()
        total_stock_limpias = df_stock[df_stock['Tipo'] == 'Limpia']['qty_available'].sum()
    total_stock = total_stock_sucias + total_stock_limpias
    
    # Mostrar KPIs en 5 columnas
    kpi_cols = st.columns(5)
    with kpi_cols[0]:
        st.metric("📤 Despachadas", fmt_numero(total_despachadas))
    with kpi_cols[1]:
        st.metric("📥 Recepcionadas", fmt_numero(total_recepcionadas))
    with kpi_cols[2]:
        st.metric("🏠 En Productores", fmt_numero(total_en_productores))
    with kpi_cols[3]:
        st.metric("📦 Stock Total", fmt_numero(total_stock))
    with kpi_cols[4]:
        st.metric("✨ Limpias / 🧹 Sucias", f"{fmt_numero(total_stock_limpias)} / {fmt_numero(total_stock_sucias)}")
    
    # ==================== TABLA GESTIÓN BANDEJAS ====================
    if not df_stock.empty:
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
        
        df_gestion['Diferencia'] = df_gestion['Proyectados'] - df_gestion['Bandejas Limpias']
        
        # Guardar datos para gráfico ANTES de agregar total y formatear
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
        total_diferencia = df_gestion['Diferencia'].sum()
        
        # Agregar fila TOTAL
        total_row = pd.DataFrame([{
            'Código': '',
            'Nombre': 'TOTAL',
            'Bandejas Sucias': total_sucias,
            'Bandejas Limpias': total_limpias,
            'Proyectados': total_proyectados,
            'Diferencia': total_diferencia
        }])
        df_gestion = pd.concat([df_gestion, total_row], ignore_index=True)
        
        # Formatear números (formato chileno)
        df_gestion['Bandejas Sucias'] = df_gestion['Bandejas Sucias'].apply(lambda x: fmt_numero(x))
        df_gestion['Bandejas Limpias'] = df_gestion['Bandejas Limpias'].apply(lambda x: fmt_numero(x))
        df_gestion['Proyectados'] = df_gestion['Proyectados'].apply(lambda x: fmt_numero(x))
        df_gestion['Diferencia'] = df_gestion['Diferencia'].apply(lambda x: fmt_numero(x))
        
        # Estilo para fila TOTAL (amarilla)
        def highlight_total_gestion(row):
            if row['Nombre'] == 'TOTAL':
                return ['background-color: #ffc107; color: black; font-weight: bold'] * len(row)
            return [''] * len(row)
        
        st.dataframe(
            df_gestion[['Nombre', 'Bandejas Sucias', 'Bandejas Limpias', 'Proyectados', 'Diferencia']].style.apply(highlight_total_gestion, axis=1),
            hide_index=True,
            use_container_width=True
        )
        
        # ==================== GRÁFICO STOCK ====================
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
    
    st.markdown("---")
    
    # ==================== TABLA DETALLE POR PRODUCTOR ====================
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
    
    # Mostrar totales como métricas fijas (no se mueven al ordenar)
    tot_cols = st.columns(3)
    with tot_cols[0]:
        st.metric("📥 Total Recepcionadas", fmt_numero(total_in))
    with tot_cols[1]:
        st.metric("📤 Total Despachadas", fmt_numero(total_out))
    with tot_cols[2]:
        st.metric("🏠 Total en Productores", fmt_numero(total_diff))
    
    # Solo datos de productores (sin fila TOTAL)
    df_display = df_merged.copy()
    
    # Guardar datos para gráfico ANTES de formatear
    df_chart_prod = df_merged.copy()
    
    # Formatear números (formato chileno)
    df_display['Recepcionadas'] = df_display['Recepcionadas'].apply(lambda x: fmt_numero(x))
    df_display['Despachadas'] = df_display['Despachadas'].apply(lambda x: fmt_numero(x))
    df_display['Bandejas en Productor'] = df_display['Bandejas en Productor'].apply(lambda x: fmt_numero(x))
    
    df_display = df_display[['Productor', 'Recepcionadas', 'Despachadas', 'Bandejas en Productor']]
    
    # Ordenar por Bandejas en Productor descendente (mayor deuda primero)
    df_merged_sorted = df_merged.sort_values('Bandejas en Productor', ascending=False)
    df_display = df_merged_sorted.copy()
    df_display['Recepcionadas'] = df_display['Recepcionadas'].apply(lambda x: fmt_numero(x))
    df_display['Despachadas'] = df_display['Despachadas'].apply(lambda x: fmt_numero(x))
    df_display['Bandejas en Productor'] = df_display['Bandejas en Productor'].apply(lambda x: fmt_numero(x))
    df_display = df_display[['Productor', 'Recepcionadas', 'Despachadas', 'Bandejas en Productor']]
    
    st.dataframe(df_display, hide_index=True, use_container_width=True)
    
    # ==================== GRÁFICO POR PRODUCTOR ====================
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

else:
    st.warning("No se encontraron movimientos para 'Bandeja'.")
