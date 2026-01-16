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
        odf_id = odf['id']
        # Keys para datos (diferentes de las keys de widgets)
        preview_data_key = f'preview_data_{odf_id}'
        resultado_data_key = f'resultado_data_{odf_id}'
        
        with st.expander(f"**{i}. {odf['name']}** - SO: {odf.get('x_studio_po_asociada', 'Sin SO')}"):
            col1, col2, col3 = st.columns([2, 2, 1])
            
            with col1:
                st.markdown(f"**ID:** `{odf_id}`")
                product_name = odf.get('product_id', ['N/A'])[1] if isinstance(odf.get('product_id'), list) else 'N/A'
                st.markdown(f"**Producto:** {product_name}")
                st.markdown(f"**Estado:** {odf.get('state', 'N/A')}")
            
            with col2:
                fecha = odf.get('date_planned_start', 'N/A')[:10] if odf.get('date_planned_start') else 'N/A'
                st.markdown(f"**Fecha:** {fecha}")
                st.markdown(f"**PO Cliente:** `{odf.get('x_studio_po_cliente_1', 'N/A')}`")
                st.markdown(f"**SO Asociada:** {odf.get('x_studio_po_asociada', '-')}")
            
            with col3:
                # Botón de preview (key de widget)
                if st.button("👁️ Preview", key=f"btn_preview_{odf_id}", use_container_width=True):
                    with st.spinner("Calculando..."):
                        resultado = shared.preview_reconciliacion_odf(odf_id)
                        
                        if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                            st.session_state[preview_data_key] = resultado
                            st.success("✓ Preview calculado")
                        else:
                            error_msg = resultado.get('error', 'Sin datos') if isinstance(resultado, dict) else 'Respuesta inválida'
                            st.error(f"Error: {error_msg}")
                
                # Botón de reconciliar (key de widget)
                if st.button("✅ Reconciliar", key=f"btn_recon_{odf_id}", type="primary", use_container_width=True):
                    with st.spinner("Reconciliando..."):
                        resultado = shared.reconciliar_odf_kg(odf_id, dry_run=False)
                        
                        if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                            st.session_state[resultado_data_key] = resultado
                            if resultado.get('accion') == 'limpieza_inconsistencia':
                                st.warning("⚠️ Limpieza de inconsistencia realizada")
                            else:
                                st.success("✓ Reconciliado correctamente")
                        else:
                            error_msg = resultado.get('error', 'Error desconocido') if isinstance(resultado, dict) else 'Respuesta inválida'
                            st.error(f"Error: {error_msg}")
            
            # Mostrar preview si existe
            if preview_data_key in st.session_state:
                prev = st.session_state[preview_data_key]
                
                # Validar que prev sea un diccionario válido
                if not isinstance(prev, dict):
                    st.warning("⚠️ Datos de preview inválidos. Haz clic en Preview nuevamente.")
                    del st.session_state[preview_data_key]
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
                    
                    # Desglose por producto
                    if prev.get('desglose_productos'):
                        st.markdown("**Desglose por Producto:**")
                        
                        desglose_data = []
                        for prod in prev['desglose_productos']:
                            desglose_data.append({
                                'Producto': prod.get('producto_nombre', 'N/A'),
                                'KG en SOs': f"{prod.get('kg_en_so', 0):,.2f}",
                                'KG Producidos': f"{prod.get('kg_producidos', 0):,.2f}",
                                'Match': '✅' if prod.get('kg_producidos', 0) > 0 else '❌'
                            })
                        
                        df = pd.DataFrame(desglose_data)
                        st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Mostrar resultado si existe
            if resultado_data_key in st.session_state:
                res = st.session_state[resultado_data_key]
                if isinstance(res, dict):
                    # Verificar si fue limpieza de inconsistencia
                    if res.get('accion') == 'limpieza_inconsistencia':
                        st.warning(f"""
                        🧹 **Inconsistencia Limpiada**
                        {res.get('mensaje', 'ODF sin SO tenía valores incorrectos')}
                        - KG Totales: 0 kg (antes: {res.get('kg_totales_anterior', 'N/A')})
                        - KG Consumidos: 0 kg (antes: {res.get('kg_consumidos_anterior', 'N/A')})
                        - KG Disponibles: 0 kg (antes: {res.get('kg_disponibles_anterior', 'N/A')})
                        """)
                    else:
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
        if st.button("🔄 Reconciliar Todas (Preview)", use_container_width=True, key="btn_mass_preview"):
            # Inicializar log
            log_entries = []
            progress_bar = st.progress(0)
            status = st.empty()
            
            exitosos = 0
            fallidos = 0
            
            for idx, odf in enumerate(odfs, 1):
                progress_bar.progress(idx / len(odfs))
                status.info(f"Calculando preview {idx}/{len(odfs)}: {odf['name']}")
                
                resultado = shared.preview_reconciliacion_odf(odf['id'])
                
                if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                    st.session_state[f'preview_data_{odf["id"]}'] = resultado
                    exitosos += 1
                    log_entries.append({
                        'tipo': 'success',
                        'odf': odf['name'],
                        'mensaje': f"KG: {resultado.get('kg_totales_po', 0):,.0f} total / {resultado.get('kg_consumidos_po', 0):,.0f} consumido"
                    })
                else:
                    fallidos += 1
                    error_msg = resultado.get('error', 'Error desconocido') if isinstance(resultado, dict) else 'Sin respuesta'
                    log_entries.append({
                        'tipo': 'error',
                        'odf': odf['name'],
                        'mensaje': error_msg
                    })
            
            progress_bar.progress(1.0)
            status.success(f"✓ Completado: {exitosos} exitosos, {fallidos} fallidos")
            st.session_state['log_preview_masivo'] = log_entries
            st.rerun()
    
    with col2:
        if st.button("✅ Reconciliar Todas (Escribir)", type="primary", use_container_width=True, key="btn_mass_recon"):
            if st.session_state.get('confirm_mass_recon'):
                # Inicializar log
                log_entries = []
                progress_bar = st.progress(0)
                status = st.empty()
                
                exitosos = 0
                fallidos = 0
                limpiezas = 0
                
                for idx, odf in enumerate(odfs, 1):
                    progress_bar.progress(idx / len(odfs))
                    status.info(f"Reconciliando {idx}/{len(odfs)}: {odf['name']}")
                    
                    resultado = shared.reconciliar_odf_kg(odf['id'], dry_run=False)
                    
                    if isinstance(resultado, dict) and resultado.get('kg_totales_po') is not None:
                        st.session_state[f'resultado_data_{odf["id"]}'] = resultado
                        exitosos += 1
                        
                        # Contar y registrar limpiezas de inconsistencias
                        if resultado.get('accion') == 'limpieza_inconsistencia':
                            limpiezas += 1
                            log_entries.append({
                                'tipo': 'warning',
                                'odf': odf['name'],
                                'mensaje': f"🧹 Inconsistencia limpiada: {resultado.get('mensaje', 'Sin SO pero tenía KG')}"
                            })
                        else:
                            log_entries.append({
                                'tipo': 'success',
                                'odf': odf['name'],
                                'mensaje': f"KG: {resultado.get('kg_totales_po', 0):,.0f} / {resultado.get('kg_consumidos_po', 0):,.0f} / {resultado.get('kg_disponibles_po', 0):,.0f}"
                            })
                    else:
                        fallidos += 1
                        error_msg = resultado.get('error', 'Error desconocido') if isinstance(resultado, dict) else 'Sin respuesta'
                        log_entries.append({
                            'tipo': 'error',
                            'odf': odf['name'],
                            'mensaje': error_msg
                        })
                
                progress_bar.progress(1.0)
                mensaje_final = f"✓ Completado: {exitosos} exitosos, {fallidos} fallidos"
                if limpiezas > 0:
                    mensaje_final += f" ({limpiezas} inconsistencias limpiadas)"
                status.success(mensaje_final)
                st.session_state['log_reconciliacion_masiva'] = log_entries
                st.session_state['confirm_mass_recon'] = False
                st.balloons()
                st.rerun()
            else:
                st.session_state['confirm_mass_recon'] = True
                st.warning("⚠️ Haz clic nuevamente para confirmar la reconciliación masiva")
    
    # =========================================================================
    # LOG DE EJECUCIÓN
    # =========================================================================
    st.divider()
    st.markdown("### 📋 Log de Ejecución")
    
    # Mostrar log de preview masivo
    log_preview = st.session_state.get('log_preview_masivo', [])
    log_recon = st.session_state.get('log_reconciliacion_masiva', [])
    
    if not log_preview and not log_recon:
        st.info("Ejecuta una acción masiva para ver el log de ejecución aquí.")
    else:
        # Tabs para separar logs
        if log_preview and log_recon:
            tab_log_prev, tab_log_recon = st.tabs(["📊 Preview Masivo", "✅ Reconciliación Masiva"])
        elif log_preview:
            tab_log_prev = st.container()
            tab_log_recon = None
        else:
            tab_log_prev = None
            tab_log_recon = st.container()
        
        # Log de Preview
        if tab_log_prev and log_preview:
            with tab_log_prev:
                # Resumen
                n_ok = len([e for e in log_preview if e['tipo'] == 'success'])
                n_err = len([e for e in log_preview if e['tipo'] == 'error'])
                st.caption(f"✅ {n_ok} exitosos | ❌ {n_err} fallidos")
                
                # Botón para limpiar
                if st.button("🗑️ Limpiar Log Preview", key="clear_log_preview"):
                    st.session_state['log_preview_masivo'] = []
                    st.rerun()
                
                # Mostrar entradas
                with st.expander("Ver detalle", expanded=False):
                    for entry in log_preview:
                        if entry['tipo'] == 'success':
                            st.markdown(f"✅ **{entry['odf']}**: {entry['mensaje']}")
                        elif entry['tipo'] == 'warning':
                            st.markdown(f"⚠️ **{entry['odf']}**: {entry['mensaje']}")
                        else:
                            st.markdown(f"❌ **{entry['odf']}**: {entry['mensaje']}")
        
        # Log de Reconciliación
        if tab_log_recon and log_recon:
            with tab_log_recon:
                # Resumen
                n_ok = len([e for e in log_recon if e['tipo'] == 'success'])
                n_warn = len([e for e in log_recon if e['tipo'] == 'warning'])
                n_err = len([e for e in log_recon if e['tipo'] == 'error'])
                st.caption(f"✅ {n_ok} exitosos | ⚠️ {n_warn} inconsistencias | ❌ {n_err} fallidos")
                
                # Botón para limpiar
                if st.button("🗑️ Limpiar Log Reconciliación", key="clear_log_recon"):
                    st.session_state['log_reconciliacion_masiva'] = []
                    st.rerun()
                
                # Mostrar solo inconsistencias por defecto
                inconsistencias = [e for e in log_recon if e['tipo'] == 'warning']
                if inconsistencias:
                    st.markdown("#### ⚠️ Inconsistencias Detectadas")
                    for entry in inconsistencias:
                        st.warning(f"**{entry['odf']}**: {entry['mensaje']}")
                
                # Mostrar errores
                errores = [e for e in log_recon if e['tipo'] == 'error']
                if errores:
                    st.markdown("#### ❌ Errores")
                    for entry in errores:
                        st.error(f"**{entry['odf']}**: {entry['mensaje']}")
                
                # Mostrar todos en expander
                with st.expander("Ver todo el log", expanded=False):
                    for entry in log_recon:
                        if entry['tipo'] == 'success':
                            st.markdown(f"✅ **{entry['odf']}**: {entry['mensaje']}")
                        elif entry['tipo'] == 'warning':
                            st.markdown(f"⚠️ **{entry['odf']}**: {entry['mensaje']}")
                        else:
                            st.markdown(f"❌ **{entry['odf']}**: {entry['mensaje']}")

