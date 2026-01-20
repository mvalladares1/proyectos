"""
Tab de Trazabilidad de Inventario: Compras, Ventas y Merma
Análisis de facturas de clientes y proveedores por categoría de producto
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from shared.odoo_client import get_odoo_client

def render(username: str, password: str):
    """Renderiza el tab de trazabilidad de inventario."""
    
    st.subheader("📊 Trazabilidad de Inventario: Compras, Ventas y Merma")
    st.markdown("Análisis de facturas por tipo de fruta y categoría de manejo")
    
    # Filtros
    col1, col2, col3 = st.columns(3)
    
    with col1:
        anio = st.selectbox(
            "Año",
            options=[2026, 2025, 2024, 2023],
            index=1  # Default 2025
        )
    
    with col2:
        mes_hasta = st.selectbox(
            "Hasta mes",
            options=list(range(1, 13)),
            format_func=lambda x: datetime(2000, x, 1).strftime('%B'),
            index=9  # Default octubre (índice 9 = mes 10)
        )
    
    with col3:
        if st.button("🔄 Actualizar Datos", type="primary", use_container_width=True):
            st.session_state.pop('inventario_data', None)
    
    # Obtener datos
    if 'inventario_data' not in st.session_state:
        with st.spinner("🔎 Cargando datos de facturas..."):
            st.session_state.inventario_data = _get_inventario_data(
                username, password, anio, mes_hasta
            )
    
    data = st.session_state.inventario_data
    
    if data.get('error'):
        st.error(f"❌ {data['error']}")
        return
    
    # Mostrar métricas principales
    st.markdown("### 📈 Resumen General")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Comprado",
            f"{data['total_comprado']:,.0f} kg",
            help="Suma de todas las facturas de proveedor"
        )
    
    with col2:
        st.metric(
            "Total Vendido",
            f"{data['total_vendido']:,.0f} kg",
            help="Suma de todas las facturas de cliente"
        )
    
    with col3:
        merma = data['total_comprado'] - data['total_vendido']
        merma_pct = (merma / data['total_comprado'] * 100) if data['total_comprado'] > 0 else 0
        st.metric(
            "Merma Estimada",
            f"{merma:,.0f} kg",
            f"{merma_pct:.1f}%",
            help="Diferencia entre comprado y vendido"
        )
    
    with col4:
        st.metric(
            "Inventario Teórico",
            f"{merma:,.0f} kg",
            help="Stock que debería quedar al final del periodo"
        )
    
    # Mostrar tabla detallada
    st.markdown("### 📋 Detalle por Tipo de Fruta y Manejo")
    
    if data['detalle']:
        df = pd.DataFrame(data['detalle'])
        
        # Formatear columnas
        df_display = df.copy()
        df_display['Comprado'] = df_display['comprado'].apply(lambda x: f"{x:,.2f}")
        df_display['Vendido'] = df_display['vendido'].apply(lambda x: f"{x:,.2f}")
        df_display['Merma'] = df_display['merma'].apply(lambda x: f"{x:,.2f}")
        df_display['% Merma'] = df_display['merma_pct'].apply(lambda x: f"{x:.1f}%")
        
        st.dataframe(
            df_display[['tipo_fruta', 'manejo', 'Comprado', 'Vendido', 'Merma', '% Merma']],
            use_container_width=True,
            hide_index=True
        )
        
        # Gráfico de barras
        st.markdown("### 📊 Visualización")
        
        tab_viz1, tab_viz2, tab_viz3 = st.tabs(["Por Tipo de Fruta", "Por Manejo", "Comparativo"])
        
        with tab_viz1:
            # Agrupar por tipo de fruta
            df_fruta = df.groupby('tipo_fruta').agg({
                'comprado': 'sum',
                'vendido': 'sum',
                'merma': 'sum'
            }).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Comprado',
                x=df_fruta['tipo_fruta'],
                y=df_fruta['comprado'],
                marker_color='#4CAF50'
            ))
            fig.add_trace(go.Bar(
                name='Vendido',
                x=df_fruta['tipo_fruta'],
                y=df_fruta['vendido'],
                marker_color='#2196F3'
            ))
            fig.add_trace(go.Bar(
                name='Merma',
                x=df_fruta['tipo_fruta'],
                y=df_fruta['merma'],
                marker_color='#FF9800'
            ))
            
            fig.update_layout(
                title="Compras, Ventas y Merma por Tipo de Fruta",
                xaxis_title="Tipo de Fruta",
                yaxis_title="Kilogramos",
                barmode='group',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab_viz2:
            # Agrupar por manejo
            df_manejo = df.groupby('manejo').agg({
                'comprado': 'sum',
                'vendido': 'sum',
                'merma': 'sum'
            }).reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                name='Comprado',
                x=df_manejo['manejo'],
                y=df_manejo['comprado'],
                marker_color='#4CAF50'
            ))
            fig.add_trace(go.Bar(
                name='Vendido',
                x=df_manejo['manejo'],
                y=df_manejo['vendido'],
                marker_color='#2196F3'
            ))
            fig.add_trace(go.Bar(
                name='Merma',
                x=df_manejo['manejo'],
                y=df_manejo['merma'],
                marker_color='#FF9800'
            ))
            
            fig.update_layout(
                title="Compras, Ventas y Merma por Categoría de Manejo",
                xaxis_title="Categoría de Manejo",
                yaxis_title="Kilogramos",
                barmode='group',
                height=500
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with tab_viz3:
            # Sunburst: Tipo Fruta > Manejo > Movimiento
            df_sunburst = []
            for _, row in df.iterrows():
                # Compras
                df_sunburst.append({
                    'tipo_fruta': row['tipo_fruta'],
                    'manejo': row['manejo'],
                    'movimiento': 'Comprado',
                    'valor': row['comprado']
                })
                # Ventas
                df_sunburst.append({
                    'tipo_fruta': row['tipo_fruta'],
                    'manejo': row['manejo'],
                    'movimiento': 'Vendido',
                    'valor': row['vendido']
                })
            
            df_sun = pd.DataFrame(df_sunburst)
            
            fig = px.sunburst(
                df_sun,
                path=['movimiento', 'tipo_fruta', 'manejo'],
                values='valor',
                title="Distribución de Compras y Ventas",
                height=600
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    else:
        st.info("ℹ️ No se encontraron datos para el periodo seleccionado")


def _get_inventario_data(username: str, password: str, anio: int, mes_hasta: int):
    """
    Obtiene datos de compras y ventas desde facturas.
    
    Returns:
        dict con total_comprado, total_vendido, y detalle por tipo_fruta/manejo
    """
    try:
        odoo = get_odoo_client()
        
        fecha_inicio = f"{anio}-01-01"
        fecha_fin = f"{anio}-{mes_hasta:02d}-31"
        
        # 1. Obtener líneas de facturas de proveedor (COMPRAS)
        lineas_compra = odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'in_invoice'],
                ['move_id.state', '=', 'posted'],
                ['product_id', '!=', False],
                ['date', '>=', fecha_inicio],
                ['date', '<=', fecha_fin]
            ],
            ['product_id', 'quantity', 'product_uom_id'],
            limit=10000
        )
        
        # 2. Obtener líneas de facturas de cliente (VENTAS)
        lineas_venta = odoo.search_read(
            'account.move.line',
            [
                ['move_id.move_type', '=', 'out_invoice'],
                ['move_id.state', '=', 'posted'],
                ['product_id', '!=', False],
                ['date', '>=', fecha_inicio],
                ['date', '<=', fecha_fin]
            ],
            ['product_id', 'quantity', 'product_uom_id'],
            limit=10000
        )
        
        # 3. Obtener productos únicos
        prod_ids = set()
        for linea in lineas_compra + lineas_venta:
            prod_id = linea.get('product_id', [None])[0]
            if prod_id:
                prod_ids.add(prod_id)
        
        # 4. Obtener información de productos (tipo fruta y manejo)
        productos = odoo.search_read(
            'product.product',
            [['id', 'in', list(prod_ids)]],
            ['id', 'name', 'x_studio_sub_categora', 'x_studio_categora_tipo_de_manejo'],
            limit=10000
        )
        
        # Mapear productos
        productos_map = {}
        for prod in productos:
            prod_id = prod['id']
            
            # Tipo de fruta (x_studio_sub_categora)
            tipo_fruta = prod.get('x_studio_sub_categora')
            if isinstance(tipo_fruta, (list, tuple)):
                tipo_fruta = tipo_fruta[1] if len(tipo_fruta) > 1 else str(tipo_fruta[0])
            elif not tipo_fruta:
                tipo_fruta = "Sin clasificar"
            
            # Manejo (x_studio_categora_tipo_de_manejo)
            manejo = prod.get('x_studio_categora_tipo_de_manejo')
            if isinstance(manejo, (list, tuple)):
                manejo = manejo[1] if len(manejo) > 1 else str(manejo[0])
            elif not manejo:
                manejo = "Sin clasificar"
            
            productos_map[prod_id] = {
                'nombre': prod.get('name', ''),
                'tipo_fruta': str(tipo_fruta),
                'manejo': str(manejo)
            }
        
        # 5. Procesar compras
        compras = {}  # {(tipo_fruta, manejo): cantidad}
        for linea in lineas_compra:
            prod_id = linea.get('product_id', [None])[0]
            cantidad = linea.get('quantity', 0)
            
            if prod_id and prod_id in productos_map:
                info = productos_map[prod_id]
                key = (info['tipo_fruta'], info['manejo'])
                compras[key] = compras.get(key, 0) + cantidad
        
        # 6. Procesar ventas
        ventas = {}  # {(tipo_fruta, manejo): cantidad}
        for linea in lineas_venta:
            prod_id = linea.get('product_id', [None])[0]
            cantidad = linea.get('quantity', 0)
            
            if prod_id and prod_id in productos_map:
                info = productos_map[prod_id]
                key = (info['tipo_fruta'], info['manejo'])
                ventas[key] = ventas.get(key, 0) + cantidad
        
        # 7. Combinar y calcular merma
        todas_keys = set(compras.keys()) | set(ventas.keys())
        
        detalle = []
        total_comprado = 0
        total_vendido = 0
        
        for key in todas_keys:
            tipo_fruta, manejo = key
            comprado = compras.get(key, 0)
            vendido = ventas.get(key, 0)
            merma = comprado - vendido
            merma_pct = (merma / comprado * 100) if comprado > 0 else 0
            
            detalle.append({
                'tipo_fruta': tipo_fruta,
                'manejo': manejo,
                'comprado': comprado,
                'vendido': vendido,
                'merma': merma,
                'merma_pct': merma_pct
            })
            
            total_comprado += comprado
            total_vendido += vendido
        
        # Ordenar por tipo de fruta
        detalle = sorted(detalle, key=lambda x: (x['tipo_fruta'], x['manejo']))
        
        return {
            'total_comprado': total_comprado,
            'total_vendido': total_vendido,
            'detalle': detalle,
            'error': None
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'total_comprado': 0,
            'total_vendido': 0,
            'detalle': [],
            'error': f"Error obteniendo datos: {str(e)}"
        }
