"""
Tab: Crear Orden
Formulario de creación de órdenes de fabricación para túneles estáticos.
"""
import streamlit as st
import requests

from .shared import (
    API_URL, get_tuneles, validar_pallets, crear_orden, validar_duplicados
)



@st.dialog("⚠️ Advertencia: Pallets en Uso")
def show_duplicate_dialog(duplicados):
    st.write("Los siguientes pallets ya están asignados a otra orden activa:")
    for d in duplicados:
        st.warning(d)
    
    st.markdown("---")
    st.write("¿Desea continuar con la creación de la orden?")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Cancelar", key="btn_cancel_dup"):
            st.rerun()
    with col2:
        if st.button("Confirmar y Crear", type="primary", key="btn_confirm_dup"):
            st.session_state.confirmado_duplicados = True
            st.rerun()

def render(username: str, password: str):
    """Renderiza el contenido del tab Crear Orden."""
    st.header("Crear Orden de Fabricación")
    
    tuneles = get_tuneles(username, password)
    
    if not tuneles:
        st.error("❌ No se pudieron cargar los túneles disponibles")
        return
    
    # Selector de túnel
    st.subheader("1️⃣ Seleccionar Túnel")
    
    tunel_options = {t['codigo']: f"{t['codigo']} - {t['nombre']} ({t['sucursal']})" for t in tuneles}
    selected_tunel = st.radio(
        "Túnel:",
        options=list(tunel_options.keys()),
        format_func=lambda x: tunel_options[x],
        horizontal=False,
        label_visibility="collapsed"
    )
    
    # Opción de búsqueda automática para VLK
    buscar_ubicacion_auto = False
    if selected_tunel == 'VLK':
        buscar_ubicacion_auto = st.checkbox(
            "🔍 Buscar ubicación automáticamente (para pallets mal ubicados)",
            value=True,
            help="Si está activado, busca la ubicación real del pallet aunque no esté en VLK/Camara 0°"
        )
    
    st.divider()
    
    # Input de pallets
    st.subheader("2️⃣ Agregar Pallets")
    
    # Inicializar session state para pallets
    if 'pallets_list' not in st.session_state:
        st.session_state.pallets_list = []
    
    # Función callback para convertir a mayúsculas
    def _convert_to_uppercase():
        if 'pallets_multiple_input' in st.session_state:
            st.session_state.pallets_multiple_input = st.session_state.pallets_multiple_input.upper()
    
    # Ingreso múltiple de pallets
    pallets_textarea = st.text_area(
        "Ingresa los códigos de pallet (uno por línea)",
        placeholder="PAC0002683\nPAC0006041\nPAC0005928",
        height=200,
        key="pallets_multiple_input",
        on_change=_convert_to_uppercase
    )
    
    if st.button("➕ Agregar Todos", use_container_width=True, type="primary"):
        _procesar_pallets(username, password, pallets_textarea.upper(), buscar_ubicacion_auto)
    
    st.divider()
    
    # Lista de pallets agregados
    st.subheader("3️⃣ Pallets a Procesar")
    
    if st.session_state.pallets_list:
        _mostrar_pallets_lista()
        st.divider()
        _botones_accion(username, password, selected_tunel, buscar_ubicacion_auto)
    else:
        st.info("👆 Agrega pallets para comenzar")


def _procesar_pallets(username, password, pallets_textarea, buscar_ubicacion_auto):
    """Procesa el texto de pallets ingresados."""
    if not pallets_textarea:
        st.warning("⚠️ Ingresa al menos un código de pallet")
        return
    
    codigos_raw = [c.strip() for c in pallets_textarea.split('\n') if c.strip()]
    
    # Filtrar duplicados
    codigos_existentes = {p['codigo'] for p in st.session_state.pallets_list}
    codigos = [c for c in codigos_raw if c not in codigos_existentes]
    duplicados_ignorados = len(codigos_raw) - len(codigos)
    
    if not codigos:
        st.warning("⚠️ Todos los pallets ya están en la lista")
        return
    
    with st.spinner(f"Validando {len(codigos)} pallets..."):
        validaciones = validar_pallets(username, password, codigos, buscar_ubicacion_auto)
        
        if not validaciones:
            st.error("Error al validar pallets")
            return
        
        agregados = 0
        en_recepcion = 0
        no_encontrados = []
        
        for val in validaciones:
            if val.get('existe') and val.get('kg', 0) > 0:
                st.session_state.pallets_list.append({
                    'codigo': val['codigo'],
                    'kg': val.get('kg', 0.0),
                    'ubicacion': val.get('ubicacion_nombre', 'N/A'),
                    'advertencia': val.get('advertencia'),
                    'producto_id': val.get('producto_id'),
                    'producto_nombre': val.get('producto_nombre', 'N/A'),
                    'manual': False
                })
                agregados += 1
            elif val.get('reception_info'):
                reception_info = val['reception_info']
                st.session_state.pallets_list.append({
                    'codigo': val['codigo'],
                    'kg': val.get('kg', 0.0),
                    'ubicacion': f"RECEPCIÓN PENDIENTE ({reception_info['state']})",
                    'advertencia': f"Pallet en recepción {reception_info['picking_name']}",
                    'producto_id': reception_info.get('product_id'),
                    'producto_nombre': reception_info.get('product_name', 'N/A'),
                    'lot_name': reception_info.get('lot_name'),
                    'lot_id': reception_info.get('lot_id'),
                    'picking_id': reception_info.get('picking_id'),
                    'manual': False,
                    'pendiente_recepcion': True,
                    'odoo_url': reception_info['odoo_url']
                })
                en_recepcion += 1
            else:
                no_encontrados.append(val['codigo'])
        
        # Mostrar resumen
        msgs = []
        if agregados > 0:
            msgs.append(f"✅ {agregados} en stock")
        if en_recepcion > 0:
            msgs.append(f"⚠️ {en_recepcion} en recepción pendiente")
        if duplicados_ignorados > 0:
            msgs.append(f"🔄 {duplicados_ignorados} duplicados ignorados")
        if no_encontrados:
            msgs.append(f"❌ {len(no_encontrados)} no encontrados")
        
        if agregados + en_recepcion > 0:
            st.success(" | ".join(msgs))
            st.rerun()
        else:
            st.error("❌ Ningún pallet fue encontrado: " + ", ".join(no_encontrados))


def _mostrar_pallets_lista():
    """Muestra la lista de pallets agregados."""
    total_kg = sum(p['kg'] for p in st.session_state.pallets_list if p['kg'] > 0)
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pallets", len(st.session_state.pallets_list))
    col2.metric("Total Kg", f"{total_kg:,.2f}")
    col3.metric("Promedio Kg/Pallet", f"{total_kg/len(st.session_state.pallets_list):,.2f}" if len(st.session_state.pallets_list) > 0 else "0")
    
    st.markdown("---")
    
    for idx, pallet in enumerate(st.session_state.pallets_list):
        is_pending = pallet.get('pendiente_recepcion', False)
        border_color = '#ff9800' if is_pending else '#4caf50'
        
        with st.container():
            col1, col2 = st.columns([5, 1])
            
            with col1:
                kg_display = f"{pallet['kg']:,.2f} Kg" if pallet.get('kg', 0) > 0 else "⚠️ Sin Kg"
                producto_display = pallet.get('producto_nombre', 'N/A')
                
                lines = [f"<strong>{producto_display}</strong> - {kg_display}"]
                lines.append(f"<br><small style='color: #aaa;'>📦 {pallet['codigo']}</small>")
                
                if is_pending:
                    reception_state = pallet.get('ubicacion', 'Pendiente').replace('RECEPCIÓN PENDIENTE ', '')
                    lines.append(f"<br><small style='color: #ff9800;'>⚠️ EN RECEPCIÓN: {reception_state}</small>")
                    
                    lot_name = pallet.get('lot_name', '')
                    if lot_name:
                        lines.append(f"<small style='color: #aaa;'> | 🏷️ Lote: {lot_name}</small>")
                    
                    advertencia = pallet.get('advertencia', 'En recepción pendiente')
                    lines.append(f"<br><small style='color: orange;'>⚠️ {advertencia}</small>")
                else:
                    ubicacion = pallet.get('ubicacion', 'N/A')
                    if ubicacion and ubicacion != 'N/A':
                        lines.append(f"<br><small style='color: #aaa;'>📍 {ubicacion}</small>")
                    if pallet.get('advertencia'):
                        lines.append(f"<br><small style='color: orange;'>⚠️ {pallet['advertencia']}</small>")
                
                html_content = f"<div style='border-left: 4px solid {border_color}; padding: 10px; margin: 5px 0; background: rgba(255,255,255,0.05); border-radius: 4px;'>{''.join(lines)}</div>"
                st.markdown(html_content, unsafe_allow_html=True)
            
            with col2:
                if st.button("🗑️", key=f"delete_{idx}", help="Eliminar pallet"):
                    st.session_state.pallets_list.pop(idx)
                    st.rerun()
            
            if pallet.get('odoo_url'):
                st.markdown(f"[🔗 Abrir Recepción en Odoo]({pallet['odoo_url']})")


def _botones_accion(username, password, selected_tunel, buscar_ubicacion_auto):
    """Muestra los botones de acción."""
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            st.session_state.pallets_list = []
            st.rerun()
    
    if 'creando_orden' not in st.session_state:
        st.session_state.creando_orden = False
    
    with col2:
        # Verificar si hay duplicados pendientes de confirmar - mostrar modal
        if st.session_state.get('pending_duplicados'):
            show_duplicate_dialog(st.session_state.pending_duplicados)
        
        # Flag para ejecutar creación (se activa por botón O por confirmación de dialog)
        should_create = False
        
        # Si ya se confirmó desde el dialog, proceder automáticamente
        if st.session_state.get('confirmado_duplicados') and st.session_state.get('pallets_to_create'):
            should_create = True
            pallets_payload = st.session_state.pallets_to_create
            st.session_state.confirmado_duplicados = False
            st.session_state.pallets_to_create = None
            st.session_state.pending_duplicados = None
        
        if st.button(
            "✅ Crear Orden de Fabricación", 
            use_container_width=True, 
            type="primary",
            disabled=st.session_state.creando_orden or st.session_state.get('pending_duplicados')
        ):
            pallets_sin_kg = [p for p in st.session_state.pallets_list if p['kg'] <= 0]
            
            if pallets_sin_kg:
                st.error(f"❌ {len(pallets_sin_kg)} pallets sin cantidad. Ingresa los Kg manualmente.")
            else:
                # Preparar payload
                pallets_payload = []
                for p in st.session_state.pallets_list:
                    pallet_data = {'codigo': p['codigo'], 'kg': p['kg']}
                    
                    if p.get('pendiente_recepcion'):
                        pallet_data['pendiente_recepcion'] = True
                        pallet_data['producto_id'] = p.get('producto_id')
                        pallet_data['picking_id'] = p.get('picking_id')
                        pallet_data['lot_id'] = p.get('lot_id')
                        pallet_data['lot_name'] = p.get('lot_name')
                    elif p.get('manual'):
                        pallet_data['manual'] = True
                        pallet_data['producto_id'] = p.get('producto_id')
                    
                    pallets_payload.append(pallet_data)
                
                # Verificar duplicados
                duplicados = validar_duplicados(username, password, [p['codigo'] for p in st.session_state.pallets_list])
                if duplicados:
                    # Guardar payload para después de confirmación y mostrar modal
                    st.session_state.pallets_to_create = pallets_payload
                    st.session_state.pending_duplicados = duplicados
                    st.rerun()
                else:
                    should_create = True
        
        # Ejecutar creación (por botón directo O después de confirmar dialog)
        if should_create:
            st.session_state.creando_orden = True
            
            with st.spinner("Creando orden de fabricación..."):
                response = crear_orden(username, password, selected_tunel, pallets_payload, buscar_ubicacion_auto)
                
                if response and response.status_code == 200:
                    result = response.json()
                    
                    st.session_state.last_order_result = {
                        'success': True,
                        'mensaje': result.get('mensaje', 'Orden creada exitosamente'),
                        'mo_name': result.get('mo_name'),
                        'total_kg': result.get('total_kg'),
                        'pallets_count': result.get('pallets_count'),
                        'componentes_count': result.get('componentes_count'),
                        'subproductos_count': result.get('subproductos_count'),
                        'advertencias': result.get('advertencias', []),
                        'validation_warnings': result.get('validation_warnings', []),
                        'validation_errors': result.get('validation_errors', []),
                        'has_pending': result.get('has_pending', False),
                        'pending_count': result.get('pending_count', 0)
                    }
                    
                    st.session_state.pallets_list = []
                    st.session_state.creando_orden = False
                    st.balloons()
                    st.rerun()
                elif response:
                    error_detail = response.json().get('detail', 'Error desconocido')
                    st.error(f"❌ Error al crear orden: {error_detail}")
                    st.session_state.creando_orden = False
                else:
                    st.session_state.creando_orden = False

