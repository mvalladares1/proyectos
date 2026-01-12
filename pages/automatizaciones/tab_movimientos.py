"""
Tab: Movimientos de Pallets
Interfaz simple para mover pallets entre cámaras usando escáner Bluetooth.
Diseñado para recepcionistas.
"""
import streamlit as st
import requests
from datetime import datetime
import pandas as pd


def fmt_numero(num, decimales=0):
    """Formatea número con separadores de miles"""
    if num is None:
        return "0"
    return f"{num:,.{decimales}f}".replace(",", ".")


@st.fragment
def render(username: str, password: str, api_url: str):
    """Renderiza el tab de Movimientos de Pallets"""
    
    st.title("📦 Movimientos de Pallets")
    st.markdown("Escanea la cámara destino y luego los pallets que deseas mover.")
    
    # Inicializar session state
    if "movimientos_camara_destino" not in st.session_state:
        st.session_state.movimientos_camara_destino = None
    if "movimientos_pallets" not in st.session_state:
        st.session_state.movimientos_pallets = []
    if "movimientos_input_camara" not in st.session_state:
        st.session_state.movimientos_input_camara = ""
    if "movimientos_input_pallet" not in st.session_state:
        st.session_state.movimientos_input_pallet = ""
    
    # === SECCIÓN 1: CÁMARA DESTINO ===
    st.markdown("### 📍 1. Escanear Cámara Destino")
    
    col_camara1, col_camara2 = st.columns([3, 1])
    
    with col_camara1:
        input_camara = st.text_input(
            "Código de cámara",
            value=st.session_state.movimientos_input_camara,
            key="input_camara_barcode",
            placeholder="Escanea o escribe el código de barras de la cámara...",
            label_visibility="collapsed"
        )
    
    with col_camara2:
        if st.button("🔍 Buscar", key="btn_buscar_camara", use_container_width=True):
            if input_camara.strip():
                with st.spinner("Buscando cámara..."):
                    try:
                        resp = requests.get(
                            f"{api_url}/api/v1/stock/ubicacion-by-barcode",
                            params={
                                "username": username,
                                "password": password,
                                "barcode": input_camara.strip()
                            },
                            timeout=10
                        )
                        
                        if resp.status_code == 200:
                            data = resp.json()
                            if data.get("found"):
                                st.session_state.movimientos_camara_destino = {
                                    "id": data["id"],
                                    "name": data["name"],
                                    "display_name": data["display_name"],
                                    "barcode": data["barcode"]
                                }
                                st.session_state.movimientos_input_camara = input_camara.strip()
                                st.success(f"✅ Cámara encontrada: **{data['display_name']}**")
                            else:
                                st.error(f"❌ {data.get('message', 'Cámara no encontrada')}")
                        else:
                            st.error(f"Error {resp.status_code}: {resp.text}")
                    except Exception as e:
                        st.error(f"Error al buscar cámara: {str(e)}")
            else:
                st.warning("Ingresa un código de cámara")
    
    # Mostrar cámara seleccionada
    if st.session_state.movimientos_camara_destino:
        st.success(f"**Cámara destino:** {st.session_state.movimientos_camara_destino['display_name']} ✅")
    else:
        st.info("⚠️ Escanea primero la cámara destino")
    
    st.markdown("---")
    
    # === SECCIÓN 2: ESCANEAR PALLETS ===
    st.markdown("### 📋 2. Escanear Pallets")
    
    # Solo permitir escanear pallets si hay cámara destino
    if st.session_state.movimientos_camara_destino:
        col_pallet1, col_pallet2 = st.columns([3, 1])
        
        with col_pallet1:
            input_pallet = st.text_input(
                "Código de pallet",
                value=st.session_state.movimientos_input_pallet,
                key="input_pallet_code",
                placeholder="Escanea el código del pallet...",
                label_visibility="collapsed"
            )
        
        with col_pallet2:
            if st.button("➕ Agregar", key="btn_agregar_pallet", use_container_width=True, type="primary"):
                if input_pallet.strip():
                    # Verificar que no esté duplicado
                    if any(p["code"] == input_pallet.strip() for p in st.session_state.movimientos_pallets):
                        st.warning("⚠️ Este pallet ya está en la lista")
                    else:
                        with st.spinner("Buscando pallet..."):
                            try:
                                resp = requests.get(
                                    f"{api_url}/api/v1/stock/pallet-info",
                                    params={
                                        "username": username,
                                        "password": password,
                                        "pallet_code": input_pallet.strip()
                                    },
                                    timeout=10
                                )
                                
                                if resp.status_code == 200:
                                    data = resp.json()
                                    if data.get("found"):
                                        # Extraer información relevante
                                        pallet_info = {
                                            "code": input_pallet.strip(),
                                            "producto": data.get("product_name", "N/A"),
                                            "kg": data.get("quantity", 0),
                                            "ubicacion": data.get("location_name", "N/A"),
                                            "lote": data.get("lot_name", "N/A"),
                                            "productor": data.get("producer", "N/A"),
                                            "status": data.get("status", "unknown")
                                        }
                                        st.session_state.movimientos_pallets.append(pallet_info)
                                        st.session_state.movimientos_input_pallet = ""
                                        st.success(f"✅ Pallet agregado: {input_pallet.strip()}")
                                    else:
                                        st.error(f"❌ {data.get('message', 'Pallet no encontrado')}")
                                else:
                                    st.error(f"Error {resp.status_code}: {resp.text}")
                            except Exception as e:
                                st.error(f"Error al buscar pallet: {str(e)}")
                else:
                    st.warning("Ingresa un código de pallet")
        
        # Mostrar tabla de pallets escaneados
        if st.session_state.movimientos_pallets:
            st.markdown(f"**Pallets escaneados ({len(st.session_state.movimientos_pallets)}):**")
            
            # Crear DataFrame para mostrar
            df_pallets = pd.DataFrame(st.session_state.movimientos_pallets)
            
            # Formatear columnas para mejor visualización
            df_display = df_pallets.copy()
            df_display["kg"] = df_display["kg"].apply(lambda x: fmt_numero(x, 1))
            
            # Mostrar tabla con columnas seleccionadas
            st.dataframe(
                df_display[["code", "producto", "kg", "productor", "ubicacion", "lote"]],
                column_config={
                    "code": st.column_config.TextColumn("Pallet", width="small"),
                    "producto": st.column_config.TextColumn("Producto", width="medium"),
                    "kg": st.column_config.TextColumn("Kg", width="small"),
                    "productor": st.column_config.TextColumn("Productor", width="medium"),
                    "ubicacion": st.column_config.TextColumn("Ubicación Actual", width="medium"),
                    "lote": st.column_config.TextColumn("Lote", width="small")
                },
                hide_index=True,
                use_container_width=True
            )
            
            # Botones de acción
            col_btn1, col_btn2, col_btn3 = st.columns([1, 1, 2])
            
            with col_btn1:
                if st.button("🚨 Quitar último", key="btn_quitar_ultimo", use_container_width=True):
                    if st.session_state.movimientos_pallets:
                        removed = st.session_state.movimientos_pallets.pop()
                        st.info(f"Quitado: {removed['code']}")
            
            with col_btn2:
                if st.button("🗑️ Limpiar todo", key="btn_limpiar_todo", use_container_width=True):
                    st.session_state.movimientos_pallets = []
                    st.info("Lista limpiada")
        else:
            st.info("📦 No hay pallets escaneados. Escanea el primer pallet.")
    else:
        st.warning("⚠️ Primero debes seleccionar una cámara destino")
    
    st.markdown("---")
    
    # === SECCIÓN 3: CONFIRMAR MOVIMIENTOS ===
    st.markdown("### ✅ 3. Confirmar Movimientos")
    
    if st.session_state.movimientos_camara_destino and st.session_state.movimientos_pallets:
        total_pallets = len(st.session_state.movimientos_pallets)
        total_kg = sum(p["kg"] for p in st.session_state.movimientos_pallets)
        
        st.info(f"**{total_pallets} pallets** ({fmt_numero(total_kg, 1)} kg) → **{st.session_state.movimientos_camara_destino['display_name']}**")
        
        if st.button(
            f"✅ CONFIRMAR MOVIMIENTOS ({total_pallets} pallets)",
            key="btn_confirmar_movimientos",
            type="primary",
            use_container_width=True
        ):
            with st.spinner("Moviendo pallets..."):
                try:
                    # Preparar lista de códigos de pallets
                    pallet_codes = [p["code"] for p in st.session_state.movimientos_pallets]
                    
                    # Llamar al endpoint de movimiento múltiple
                    resp = requests.post(
                        f"{api_url}/api/v1/stock/move-multiple",
                        json={
                            "pallet_codes": pallet_codes,
                            "target_location_id": st.session_state.movimientos_camara_destino["id"],
                            "username": username,
                            "password": password
                        },
                        timeout=60
                    )
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        
                        # Mostrar resumen
                        st.success(f"✅ **{result['success']} pallets movidos correctamente**")
                        
                        if result["failed"] > 0:
                            st.warning(f"⚠️ **{result['failed']} pallets fallaron**")
                        
                        # Mostrar detalles
                        with st.expander("Ver detalles", expanded=result["failed"] > 0):
                            for detail in result["details"]:
                                if detail["status"] == "ok":
                                    st.success(f"✅ {detail['pallet']}: {detail['message']}")
                                else:
                                    st.error(f"❌ {detail['pallet']}: {detail['message']}")
                        
                        # Limpiar datos
                        st.session_state.movimientos_pallets = []
                        st.session_state.movimientos_camara_destino = None
                        st.session_state.movimientos_input_camara = ""
                        st.session_state.movimientos_input_pallet = ""
                        
                        st.balloons()
                        
                        # Esperar un poco y recargar
                        import time
                        time.sleep(2)
                    else:
                        st.error(f"Error {resp.status_code}: {resp.text}")
                except Exception as e:
                    st.error(f"Error al mover pallets: {str(e)}")
    else:
        if not st.session_state.movimientos_camara_destino:
            st.warning("⚠️ Selecciona una cámara destino")
        elif not st.session_state.movimientos_pallets:
            st.warning("⚠️ Escanea al menos un pallet")
