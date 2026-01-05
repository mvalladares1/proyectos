"""
Tab: Movimientos
Gestión de movimientos de pallets entre ubicaciones.
"""
import streamlit as st
import httpx
import os

from .shared import API_URL


@st.fragment
def render(username: str, password: str, camaras_data_all: list):
    """Renderiza el contenido del tab Movimientos como fragment independiente."""
    st.markdown("### 📲 Gestión de Movimientos")
    st.info(
        "💡 **Dual Logic**: Si el pallet está en inventario, crea una transferencia interna. "
        "Si pertenece a una recepción abierta (asignada), actualiza su destino en la recepción."
    )
    
    col_scan, col_dest = st.columns(2)
    
    with col_scan:
        st.markdown("##### 1. Escanear Pallet")
        pallet_code = st.text_input("Código de Tarja / Pallet", placeholder="Escanea aquí...", key="move_pallet_code")
        
    with col_dest:
        st.markdown("##### 2. Destino")
        opts_dest = {}
        if camaras_data_all:
            opts_dest = {c["id"]: c["name"] for c in camaras_data_all}
             
        dest_id = st.selectbox(
            "Seleccionar Cámara Destino", 
            options=opts_dest.keys(), 
            format_func=lambda x: opts_dest.get(x, str(x)), 
            key="move_dest_id"
        )

    btn_mover = st.button("✅ Confirmar Movimiento", type="primary", use_container_width=True)
    
    if btn_mover:
        if not pallet_code:
            st.error("⚠️ Debes ingresar un código de pallet.")
        elif not dest_id:
            st.error("⚠️ Debes seleccionar un destino.")
        else:
            with st.spinner(f"Procesando movimiento de {pallet_code}..."):
                try:
                    payload = {
                        "pallet_code": pallet_code.strip(),
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
                                st.caption("Reasignación pre-validación exitosa.")
                            else:
                                st.success(f"🚚 {msg}")
                                st.caption("Transferencia de stock creada y validada.")
                            
                            st.divider()
                            c1, c2, c3 = st.columns(3)
                            c1.metric("Pallet", pallet_code)
                            c2.metric("Destino", opts_dest.get(dest_id, "Desconocido"))
                            c3.metric("Tipo", "Recepción" if tipo=="realloc" else "Transferencia")
                            
                        else:
                            st.error(f"❌ {res_json.get('message')}")
                    else:
                        st.error(f"Error HTTP: {resp_move.status_code} - {resp_move.text}")
                        
                except Exception as e:
                    st.error(f"Error de conexión: {str(e)}")
