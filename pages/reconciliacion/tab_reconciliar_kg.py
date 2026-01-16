"""
Tab para reconciliación de KG en ODFs.
"""
import streamlit as st
from . import shared
import pandas as pd


def render(wait_seconds: float):
    """
    Renderiza el tab de reconciliación de KG.
    
    Args:
        wait_seconds: Configuración (no se usa aquí pero mantiene consistencia)
    """
    odfs = st.session_state.get('trigger_odfs_kg', [])
    
    if not odfs:
        st.info("👈 Usa el filtro de fechas y haz clic en **'Buscar ODFs'** para comenzar")
        return
    
    st.subheader("🔢 Reconciliación de Campos KG")
    st.caption("Calcula y actualiza x_studio_kg_totales_po, x_studio_kg_consumidos_po, x_studio_kg_disponibles_po")
    
    # Tabla de ODFs
    st.markdown("### ODFs para Reconciliar")
    
    for i, odf in enumerate(odfs, 1):
        with st.expander(f"**{i}. {odf['name']}** - SO: {odf.get('x_studio_po_asociada', 'Sin SO')}"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**ID:** `{odf['id']}`")
                product_name = odf.get('product_id', ['N/A'])[1] if isinstance(odf.get('product_id'), list) else 'N/A'
                st.markdown(f"**Producto:** {product_name}")
                st.markdown(f"**Estado:** {odf.get('state', 'N/A')}")
            
            with col2:
                fecha = odf.get('date_planned_start', 'N/A')[:10] if odf.get('date_planned_start') else 'N/A'
                st.markdown(f"**Fecha:** {fecha}")
                st.markdown(f"**PO Cliente:** `{odf.get('x_studio_po_cliente_1', 'N/A')}`")
                st.markdown(f"**SO Asociada:** {odf.get('x_studio_po_asociada', '-')}")
            
            with col3:
                # Botón de preview
                if st.button("👁️ Preview", key=f"preview_{odf['id']}", use_container_width=True):
                    with st.spinner("Calculando..."):
                        resultado = shared.preview_reconciliacion_odf(odf['id'])
                        
                        if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                            st.session_state[f'preview_{odf["id"]}'] = resultado
                        else:
                            error_msg = resultado.get('error', 'Sin datos') if isinstance(resultado, dict) else 'Respuesta inválida'
                            st.error(f"Error: {error_msg}")
                
                # Botón de reconciliar
                if st.button("✅ Reconciliar", key=f"recon_{odf['id']}", type="primary", use_container_width=True):
                    with st.spinner("Reconciliando..."):
                        resultado = shared.reconciliar_odf_kg(odf['id'], dry_run=False)
                        
                        if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                            st.success("✓ Reconciliado")
                            st.session_state[f'resultado_{odf["id"]}'] = resultado
                        else:
                            error_msg = resultado.get('error', 'Error desconocido') if isinstance(resultado, dict) else 'Respuesta inválida'
                            st.error(f"Error: {error_msg}")
            
            # Mostrar preview si existe
            if f'preview_{odf["id"]}' in st.session_state:
                prev = st.session_state[f'preview_{odf["id"]}']
                
                # Validar que prev sea un diccionario válido
                if not isinstance(prev, dict):
                    st.warning("⚠️ Datos de preview inválidos. Haz clic en Preview nuevamente.")
                    del st.session_state[f'preview_{odf["id"]}']
                else:
                    st.divider()
                    st.markdown("**📊 Preview de Cálculos:**")
                    
                    col_a, col_b, col_c = st.columns(3)
                    with col_a:
                        st.metric("KG Totales PO", f"{prev.get('kg_totales_po', 0):,.0f} kg")
                    with col_b:
                        st.metric("KG Consumidos PO", f"{prev.get('kg_consumidos_po', 0):,.0f} kg")
                    with col_c:
                        kg_disp = prev.get('kg_disponibles_po', 0)
                        st.metric("KG Disponibles PO", f"{kg_disp:,.0f} kg")
                    
                    # Desglose por producto (dentro del else para validación)
                    if prev.get('desglose_productos'):
                        st.markdown("**Desglose por Producto:**")
                        
                        desglose_data = []
                        for prod in prev['desglose_productos']:
                            desglose_data.append({
                                'Producto': prod['producto_nombre'],
                                'KG en SOs': f"{prod['kg_en_so']:,.2f}",
                                'KG Producidos': f"{prod['kg_producidos']:,.2f}",
                                'Match': '✅' if prod['kg_producidos'] > 0 else '❌'
                            })
                        
                        df = pd.DataFrame(desglose_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Mostrar resultado si existe
            if f'resultado_{odf["id"]}' in st.session_state:
                res = st.session_state[f'resultado_{odf["id"]}']
                if isinstance(res, dict):
                    st.success(f"""
                    ✅ **Reconciliado Exitosamente**
                    - KG Totales: {res.get('kg_totales_po', 0):,.0f} kg
                    - KG Consumidos: {res.get('kg_consumidos_po', 0):,.0f} kg  
                    - KG Disponibles: {res.get('kg_disponibles_po', 0):,.0f} kg
                    """)
    
    # Botón de reconciliar todas
    st.divider()
    st.markdown("### ⚡ Acciones Masivas")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🔄 Reconciliar Todas (Preview)", use_container_width=True):
            progress_bar = st.progress(0)
            status = st.empty()
            
            exitosos = 0
            fallidos = 0
            
            for idx, odf in enumerate(odfs, 1):
                progress_bar.progress(idx / len(odfs))
                status.info(f"Calculando preview {idx}/{len(odfs)}: {odf['name']}")
                
                resultado = shared.preview_reconciliacion_odf(odf['id'])
                
                if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                    st.session_state[f'preview_{odf["id"]}'] = resultado
                    exitosos += 1
                else:
                    fallidos += 1
            
            progress_bar.progress(1.0)
            status.success(f"✓ Completado: {exitosos} exitosos, {fallidos} fallidos")
            st.rerun()
    
    with col2:
        if st.button("✅ Reconciliar Todas (Escribir)", type="primary", use_container_width=True):
            if st.session_state.get('confirm_mass_recon'):
                progress_bar = st.progress(0)
                status = st.empty()
                
                exitosos = 0
                fallidos = 0
                
                for idx, odf in enumerate(odfs, 1):
                    progress_bar.progress(idx / len(odfs))
                    status.info(f"Reconciliando {idx}/{len(odfs)}: {odf['name']}")
                    
                    resultado = shared.reconciliar_odf_kg(odf['id'], dry_run=False)
                    
                    if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                        st.session_state[f'resultado_{odf["id"]}'] = resultado
                        exitosos += 1
                    else:
                        fallidos += 1
                
                progress_bar.progress(1.0)
                status.success(f"✓ Completado: {exitosos} exitosos, {fallidos} fallidos")
                st.session_state['confirm_mass_recon'] = False
                st.balloons()
                st.rerun()
            else:
                st.session_state['confirm_mass_recon'] = True
                st.warning("⚠️ Haz clic nuevamente para confirmar la reconciliación masiva")
