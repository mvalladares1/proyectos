"""
Tab de Lista de ODFs Pendientes.
"""
import streamlit as st
import pandas as pd
from . import shared

ODOO_BASE_URL = "https://riofuturo.server98c6e.oerpondemand.net/web"


def render():
    """Renderiza el tab de lista de ODFs."""
    total = st.session_state.get('trigger_total_pendientes', 0)
    odfs = st.session_state.get('trigger_odfs_pendientes', [])
    
    if not odfs:
        st.info("👈 Usa el botón **'Buscar ODFs Pendientes'** en el sidebar para comenzar")
        return
    
    st.subheader(f"📋 ODFs Pendientes ({total})")
    st.caption("ODFs que tienen PO Cliente pero no SO Asociada cargada")
    
    # Tabla filtrable con TODOS los ODFs
    st.divider()
    st.subheader("📊 Lista Completa de ODFs Pendientes")
    
    # Preparar datos para la tabla
    tabla_data = []
    for odf in odfs:
        product_name = odf.get('product_id', ['', 'N/A'])[1] if isinstance(odf.get('product_id'), list) else 'N/A'
        fecha = odf.get('date_planned_start', '')[:10] if odf.get('date_planned_start') else 'N/A'
        po_cliente = odf.get('x_studio_po_cliente_1', '') or '(Sin PO)'
        
        tabla_data.append({
            'ODF': odf['name'],
            'ID': odf['id'],
            'Producto': product_name,
            'Fecha': fecha,
            'PO Cliente': po_cliente,
            'Estado': odf.get('state', 'N/A')
        })
    
    df = pd.DataFrame(tabla_data)
    
    # Filtros interactivos
    col_f1, col_f2, col_f3 = st.columns(3)
    
    with col_f1:
        search_odf = st.text_input("🔍 Buscar ODF", "", key="filter_odf")
    with col_f2:
        search_producto = st.text_input("🔍 Buscar Producto", "", key="filter_producto")  
    with col_f3:
        estados_unicos = ['Todos'] + sorted(df['Estado'].unique().tolist())
        filtro_estado = st.selectbox("Estado", estados_unicos, key="filter_estado")
    
    # Aplicar filtros
    df_filtrado = df.copy()
    if search_odf:
        df_filtrado = df_filtrado[df_filtrado['ODF'].str.contains(search_odf, case=False, na=False)]
    if search_producto:
        df_filtrado = df_filtrado[df_filtrado['Producto'].str.contains(search_producto, case=False, na=False)]
    if filtro_estado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Estado'] == filtro_estado]
    
    st.caption(f"Mostrando {len(df_filtrado)} de {len(df)} ODFs")
    
    st.dataframe(
        df_filtrado,
        use_container_width=True,
        hide_index=True,
        height=500
    )
    
    # Expandibles con detalle
    st.divider()
    st.subheader("📋 Detalle de ODFs")
    
    # Mostrar ODFs en expandibles
    for i, odf in enumerate(odfs, 1):
        po_cliente = odf.get('x_studio_po_cliente_1', 'N/A')
        odf_id = odf['id']
        odf_name = odf['name']
        
        # Construir URL a Odoo
        odoo_url = f"{ODOO_BASE_URL}#id={odf_id}&menu_id=390&cids=1&action=604&model=mrp.production&view_type=form"
        
        with st.expander(f"**{i}. {odf_name}** - PO: {po_cliente}"):
            # Link a Odoo
            st.markdown(f"🔗 [Abrir en Odoo]({odoo_url})")
            st.divider()
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"**ID Odoo:** `{odf['id']}`")
                product_name = odf.get('product_id', ['N/A'])[1] if isinstance(odf.get('product_id'), list) else 'N/A'
                st.markdown(f"**Producto:** {product_name}")
                st.markdown(f"**Estado:** {odf.get('state', 'N/A')}")
            
            with col2:
                fecha = odf.get('date_planned_start', 'N/A')[:10] if odf.get('date_planned_start') else 'N/A'
                st.markdown(f"**Fecha Planificada:** {fecha}")
                st.markdown(f"**PO Cliente:** `{po_cliente}`")
                so_asociada = odf.get('x_studio_po_asociada', '-')
                st.markdown(f"**SO Asociada:** {so_asociada if so_asociada else '*(Vacío)*'}")
    
    # Información adicional
    st.divider()
    st.info(f"""
    💡 **Información:**
    - Se encontraron **{total}** ODFs que tienen PO Cliente pero no SO Asociada
    - Estos ODFs necesitan que se triggee la automatización de Odoo
    - Ve al tab **"Ejecutar Trigger"** para procesarlos
    """)
