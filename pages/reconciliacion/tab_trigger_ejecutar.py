"""
Tab de Ejecución del Trigger.
"""
import streamlit as st
from . import shared


def render(wait_seconds: float):
    """
    Renderiza el tab de ejecución.
    
    Args:
        wait_seconds: Segundos a esperar entre operaciones
    """
    odfs = st.session_state.get('trigger_odfs_pendientes', [])
    
    if not odfs:
        st.info("👈 Primero busca ODFs pendientes usando el sidebar")
        return
    
    st.subheader("🚀 Ejecutar Trigger Masivo")
    
    # Información del proceso
    tiempo_estimado = len(odfs) * wait_seconds * 2 / 60
    
    st.warning(f"""
    **⚠️ Proceso Masivo**
    
    Se procesarán **{len(odfs)} ODFs** con la siguiente secuencia:
    
    1. Borrar campo **PO Cliente**
    2. Esperar **{wait_seconds}** segundos
    3. Reescribir campo **PO Cliente**
    4. Esperar **{wait_seconds}** segundos
    5. La automatización de Odoo carga **SO Asociada** (si existe)
    
    ⏱️ **Tiempo estimado:** {tiempo_estimado:.1f} minutos
    """)
    
    # Botón de ejecución
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        ejecutar = st.button(
            "▶️ EJECUTAR TRIGGER",
            type="primary",
            use_container_width=True,
            key="trigger_ejecutar_btn"
        )
    
    with col2:
        if st.button("🗑️ Limpiar Log", use_container_width=True):
            shared.clear_log()
            st.rerun()
    
    # Contenedores para log y progreso
    if ejecutar:
        ejecutar_trigger_masivo(odfs, wait_seconds)
    
    # Mostrar log actual si existe
    if st.session_state.get('trigger_log_lines'):
        st.divider()
        st.subheader("📜 Log de Ejecución")
        st.code(shared.get_log_text(40), language="log")


def ejecutar_trigger_masivo(odfs: list, wait_seconds: float):
    """
    Ejecuta el trigger para múltiples ODFs.
    
    Args:
        odfs: Lista de ODFs a procesar
        wait_seconds: Segundos a esperar
    """
    # Limpiar log anterior
    shared.clear_log()
    
    # Contenedores
    progress_bar = st.progress(0)
    status_container = st.empty()
    log_container = st.empty()
    
    # Iniciar log
    shared.add_log(f"Iniciando procesamiento de {len(odfs)} ODFs...")
    log_container.code(shared.get_log_text(30), language="log")
    
    exitosos = 0
    fallidos = 0
    resultados = []
    
    # Procesar cada ODF
    for idx, odf in enumerate(odfs, 1):
        # Actualizar progreso
        progress = idx / len(odfs)
        progress_bar.progress(progress)
        status_container.info(f"⏳ Procesando ODF {idx}/{len(odfs)}: **{odf['name']}**")
        
        po_cliente = odf.get('x_studio_po_cliente_1', 'N/A')
        shared.add_log(f"Procesando [{idx}/{len(odfs)}] {odf['name']} - PO: {po_cliente}")
        log_container.code(shared.get_log_text(30), language="log")
        
        # Ejecutar trigger
        resultado = shared.trigger_odf_individual(odf['id'], wait_seconds)
        
        if resultado.get('success'):
            so_asociada = resultado.get('so_asociada', 'N/A')
            shared.add_log(f"  ✓ {odf['name']}: SO Asociada → {so_asociada}", "success")
            exitosos += 1
        else:
            error = resultado.get('error', 'Error desconocido')
            shared.add_log(f"  ✗ {odf['name']}: {error}", "error")
            fallidos += 1
        
        resultados.append({
            'odf': odf['name'],
            'success': resultado.get('success', False),
            'so_asociada': resultado.get('so_asociada', '-'),
            'error': resultado.get('error', '')
        })
        
        log_container.code(shared.get_log_text(30), language="log")
    
    # Finalizar
    progress_bar.progress(1.0)
    status_container.success("✅ Procesamiento completado")
    
    # Resumen final
    shared.add_log("=" * 60)
    shared.add_log(f"RESUMEN FINAL:")
    shared.add_log(f"  Total procesados: {len(odfs)}")
    shared.add_log(f"  Exitosos: {exitosos}", "success")
    shared.add_log(f"  Fallidos: {fallidos}", "error")
    shared.add_log("=" * 60)
    log_container.code(shared.get_log_text(40), language="log")
    
    # Métricas finales
    st.divider()
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("📊 Total Procesados", len(odfs))
    with col2:
        st.metric("✅ Exitosos", exitosos, delta=f"{exitosos/len(odfs)*100:.1f}%")
    with col3:
        st.metric("❌ Fallidos", fallidos, delta=f"{fallidos/len(odfs)*100:.1f}%", delta_color="inverse")
    
    # Mostrar tabla de resultados
    st.divider()
    st.subheader("📊 Detalle de Resultados")
    
    import pandas as pd
    df_resultados = pd.DataFrame(resultados)
    df_resultados['Estado'] = df_resultados['success'].apply(lambda x: '✅ Exitoso' if x else '❌ Fallido')
    df_resultados = df_resultados[['odf', 'Estado', 'so_asociada', 'error']]
    df_resultados.columns = ['ODF', 'Estado', 'SO Asociada', 'Error']
    
    st.dataframe(
        df_resultados,
        use_container_width=True,
        hide_index=True
    )
    
    # Celebración si hay exitosos
    if exitosos > 0:
        st.balloons()
