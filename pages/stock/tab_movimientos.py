"""
Tab: Movimientos
Gestión de movimientos de pallets entre ubicaciones.
Flujo en 3 pasos: Buscar → Validar → Confirmar
"""
import streamlit as st
import httpx
import os

from .shared import API_URL, fetch_pallet_info, fmt_numero, CAMARAS_CONFIG


@st.fragment
def render(username: str, password: str, camaras_data_all: list):
    """Renderiza el contenido del tab Movimientos como fragment independiente."""
    # DEBUG: Mostrar API_URL actual
    st.info(f"🔍 DEBUG: Usando API URL: {API_URL}")
    st.markdown("### 📲 Gestión de Movimientos")
    st.info(
        "💡 **Flujo**: Busca el pallet → Verifica la información → Confirma el movimiento"
    )
    
    # === PASO 1: BÚSQUEDA DE PALLET ===
    st.markdown("##### 1️⃣ Buscar Pallet")
    
    col_scan, col_btn = st.columns([3, 1])
    
    with col_scan:
        pallet_code = st.text_input(
            "Código de Tarja / Pallet", 
            placeholder="Escanea o ingresa el código aquí...", 
            key="move_pallet_code",
            label_visibility="collapsed"
        )
        
    with col_btn:
        btn_buscar = st.button("🔍 Buscar", type="secondary", use_container_width=True)
    
    # Ejecutar búsqueda
    if btn_buscar and pallet_code:
        with st.spinner(f"Buscando {pallet_code}..."):
            info = fetch_pallet_info(username, password, pallet_code.strip())
            st.session_state["pallet_info"] = info
    
    # === PASO 2: MOSTRAR INFORMACIÓN DEL PALLET ===
    pallet_info = st.session_state.get("pallet_info")
    
    if pallet_info:
        st.markdown("##### 2️⃣ Información del Pallet")
        
        if not pallet_info.get("found"):
            st.error(f"❌ {pallet_info.get('message', 'Pallet no encontrado')}")
            return
        
        # Mostrar info según estado
        status = pallet_info.get("status")
        
        if status == "in_stock":
            st.success(f"✅ Pallet **{pallet_info['pallet_code']}** encontrado en inventario")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📍 Ubicación Actual", pallet_info.get("location_name", "N/A"))
            col2.metric("📦 Items", fmt_numero(pallet_info.get("items_count", 0)))
            col3.metric("⚖️ Cantidad Total", f"{fmt_numero(pallet_info.get('total_quantity', 0), 2)} kg")
            
            # Mostrar productos
            products = pallet_info.get("products", [])
            if products:
                with st.expander("📋 Detalle de Productos", expanded=False):
                    for p in products:
                        st.markdown(f"- **{p['name']}**: {fmt_numero(p['quantity'], 2)} kg (Lote: {p.get('lot', 'N/A')})")
                        
        elif status == "pending_reception":
            st.warning(f"⏳ Pallet **{pallet_info['pallet_code']}** en recepción pendiente")
            
            col1, col2, col3 = st.columns(3)
            col1.metric("📄 Recepción", pallet_info.get("picking_name", "N/A"))
            col2.metric("📍 Destino Asignado", pallet_info.get("destination_name", "N/A"))
            col3.metric("📦 Items", fmt_numero(pallet_info.get("items_count", 0)))
            
            st.caption("💡 Al mover este pallet, se reasignará el destino en la recepción.")
        
        st.divider()
        
        # === PASO 3: SELECCIONAR DESTINO Y CONFIRMAR ===
        st.markdown("##### 3️⃣ Seleccionar Destino y Confirmar")
        
        # Separar destinos por grupo
        vlk_destinos = {}
        rf_destinos = {}
        
        if camaras_data_all:
            for c in camaras_data_all:
                cam_id = c.get("id")
                cam_name = c.get("name", "")
                full_name = c.get("full_name", "")
                
                # Detectar grupo
                if "VLK" in full_name or "VLK" in cam_name:
                    vlk_destinos[cam_id] = cam_name
                else:
                    rf_destinos[cam_id] = cam_name
        
        col_dest1, col_dest2 = st.columns(2)
        
        with col_dest1:
            st.markdown("**🏢 Cámaras VLK**")
            dest_vlk = st.selectbox(
                "Destino VLK",
                options=[None] + list(vlk_destinos.keys()),
                format_func=lambda x: "-- Seleccionar --" if x is None else vlk_destinos.get(x, str(x)),
                key="move_dest_vlk",
                label_visibility="collapsed"
            )
            
        with col_dest2:
            st.markdown("**🏭 Cámaras RF/Stock**")
            dest_rf = st.selectbox(
                "Destino RF",
                options=[None] + list(rf_destinos.keys()),
                format_func=lambda x: "-- Seleccionar --" if x is None else rf_destinos.get(x, str(x)),
                key="move_dest_rf",
                label_visibility="collapsed"
            )
        
        # Determinar destino seleccionado
        dest_id = dest_vlk if dest_vlk else dest_rf
        dest_name = vlk_destinos.get(dest_vlk) or rf_destinos.get(dest_rf) or "No seleccionado"
        
        # Validar que no sea la misma ubicación
        current_loc_id = pallet_info.get("location_id") or pallet_info.get("destination_id")
        
        st.divider()
        
        # Botón de confirmación
        col_confirm, col_clear = st.columns([3, 1])
        
        with col_confirm:
            btn_mover = st.button(
                f"✅ Confirmar Movimiento a {dest_name}", 
                type="primary", 
                use_container_width=True,
                disabled=dest_id is None
            )
            
        with col_clear:
            btn_limpiar = st.button("🗑️ Limpiar", use_container_width=True)
        
        if btn_limpiar:
            st.session_state["pallet_info"] = None
        
        if btn_mover:
            if not dest_id:
                st.error("⚠️ Debes seleccionar un destino.")
            elif dest_id == current_loc_id:
                st.error("⚠️ El pallet ya está en esa ubicación.")
            else:
                with st.spinner(f"Procesando movimiento de {pallet_info['pallet_code']} a {dest_name}..."):
                    try:
                        payload = {
                            "pallet_code": pallet_info['pallet_code'],
                            "target_location_id": dest_id,
                            "username": username,
                            "password": password
                        }
                        
                        resp_move = httpx.post(
                            f"{API_URL}/api/v1/stock/move",
                            json=payload, 
                            timeout=30.0
                        )
                        
                        if resp_move.status_code == 200:
                            res_json = resp_move.json()
                            if res_json.get("success"):
                                msg = res_json.get("message", "Movimiento exitoso")
                                tipo = res_json.get("type", "unknown")
                                
                                if tipo == "realloc":
                                    st.success(f"📋 {msg}")
                                    st.caption("Reasignación de destino en recepción exitosa.")
                                else:
                                    st.success(f"🚚 {msg}")
                                    st.caption("Transferencia de stock creada y validada.")
                                
                                st.divider()
                                c1, c2, c3 = st.columns(3)
                                c1.metric("Pallet", pallet_info['pallet_code'])
                                c2.metric("Destino", dest_name)
                                c3.metric("Tipo", "Recepción" if tipo=="realloc" else "Transferencia")
                                
                                # Limpiar para siguiente operación
                                st.session_state["pallet_info"] = None
                                
                            else:
                                st.error(f"❌ {res_json.get('message')}")
                        else:
                            st.error(f"Error HTTP: {resp_move.status_code} - {resp_move.text}")
                            
                    except Exception as e:
                        st.error(f"Error de conexión: {str(e)}")
    else:
        # Mostrar instrucciones iniciales
        st.caption("👆 Ingresa el código del pallet y presiona 'Buscar' para ver su información.")
