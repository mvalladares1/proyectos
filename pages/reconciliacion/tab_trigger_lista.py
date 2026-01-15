"""
Tab de Lista de ODFs Pendientes.
"""
import streamlit as st
from . import shared_reconciliacion as shared


def render():
    """Renderiza el tab de lista de ODFs."""
    total = st.session_state.get('trigger_total_pendientes', 0)
    odfs = st.session_state.get('trigger_odfs_pendientes', [])
    
    if not odfs:
        st.info("👈 Usa el botón **'Buscar ODFs Pendientes'** en el sidebar para comenzar")
        return
    
    st.subheader(f"📋 ODFs Pendientes ({total})")
    st.caption("ODFs que tienen PO Cliente pero no SO Asociada cargada")
    
    # Mostrar ODFs en expandibles
    for i, odf in enumerate(odfs, 1):
        po_cliente = odf.get('x_studio_po_cliente_1', 'N/A')
        
        with st.expander(f"**{i}. {odf['name']}** - PO: {po_cliente}"):
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
