"""
Tab: Automatización OF
Permite agregar pallets a una orden de fabricación existente como componentes o subproductos.
Extrae automáticamente lote, paquete y kg de los pallets escaneados.
"""
import streamlit as st
import requests
from typing import List, Dict

from .shared import API_URL


@st.fragment
def render(username: str, password: str):
    """Renderiza el contenido del tab Automatización OF."""
    st.header("⚙️ Automatización OF")
    st.markdown("**Agregar pallets a una orden existente** - Componentes o Subproductos")
    
    # Inicializar session state específico
    if 'of_pallets_list' not in st.session_state:
        st.session_state.of_pallets_list = []
    if 'of_orden_info' not in st.session_state:
        st.session_state.of_orden_info = None
    if 'of_last_result' not in st.session_state:
        st.session_state.of_last_result = None
    
    # === MOSTRAR RESULTADO PERSISTENTE ===
    if st.session_state.of_last_result:
        result = st.session_state.of_last_result
        with st.container(border=True):
            if result.get('success'):
                st.success(f"### ✅ {result.get('mensaje', 'Operación completada')}")
                col1, col2 = st.columns(2)
                col1.metric("📦 Pallets agregados", result.get('pallets_agregados', 0))
                col2.metric("⚖️ Kg totales", f"{result.get('kg_total', 0):,.2f}")
                
                if result.get('errores'):
                    for err in result['errores']:
                        st.error(f"❌ {err}")
            else:
                st.error(f"### ❌ {result.get('error', 'Error desconocido')}")
            
            if st.button("✖️ Cerrar mensaje", key="close_of_result"):
                st.session_state.of_last_result = None
                st.rerun()
        st.divider()
    
    # === PASO 1: ORDEN DE FABRICACIÓN ===
    st.subheader("1️⃣ Orden de Fabricación")
    
    col_orden, col_btn = st.columns([3, 1])
    
    with col_orden:
        orden_input = st.text_input(
            "Nombre de la orden (ej: MO/RF/00123)",
            placeholder="MO/RF/00123 o solo el número 123",
            key="of_orden_input"
        ).upper()
    
    with col_btn:
        st.write("")  # Espaciador
        st.write("")
        if st.button("🔍 Buscar", key="btn_buscar_of", use_container_width=True):
            if orden_input:
                _buscar_orden(username, password, orden_input)
    
    # Mostrar info de orden encontrada
    if st.session_state.of_orden_info:
        orden = st.session_state.of_orden_info
        with st.container(border=True):
            col1, col2, col3 = st.columns(3)
            col1.metric("📋 Orden", orden['nombre'])
            col2.metric("📦 Producto", orden['producto'][:30] + "..." if len(orden['producto']) > 30 else orden['producto'])
            col3.metric("📊 Estado", _get_estado_label(orden['estado']))
            
            col4, col5, col6 = st.columns(3)
            col4.metric("🔵 Componentes", orden.get('componentes_count', 0))
            col5.metric("🟢 Subproductos", orden.get('subproductos_count', 0))
            col6.metric("⚖️ Kg Total", f"{orden.get('cantidad', 0):,.2f}")
        
        st.divider()
        
        # === PASO 2: TIPO DE MOVIMIENTO ===
        st.subheader("2️⃣ Tipo de Movimiento")
        
        tipo_mov = st.radio(
            "¿Dónde agregar los pallets?",
            options=["componentes", "subproductos"],
            format_func=lambda x: "🔵 COMPONENTES (Materia Prima - Entrada)" if x == "componentes" else "🟢 SUBPRODUCTOS (Producto Terminado - Salida)",
            horizontal=True,
            key="of_tipo_movimiento"
        )
        
        st.divider()
        
        # === PASO 3: PALLETS ===
        st.subheader("3️⃣ Agregar Pallets")
        
        # Función callback para convertir a mayúsculas
        def _convert_to_uppercase():
            if 'of_pallets_input' in st.session_state:
                st.session_state.of_pallets_input = st.session_state.of_pallets_input.upper()
        
        pallets_textarea = st.text_area(
            "Ingresa los códigos de pallet (uno por línea)",
            placeholder="PACK0009900\nPACK0009901\nPACK0009902\n...",
            height=200,
            key="of_pallets_input",
            on_change=_convert_to_uppercase,
            help="Escanea o pega los códigos de pallet. Puede ser PACK0009900 o PAC0009900"
        )
        
        if st.button("➕ Validar y Agregar", use_container_width=True, type="primary", key="btn_validar_of"):
            _procesar_pallets(username, password, pallets_textarea.upper(), tipo_mov)
        
        # === LISTA DE PALLETS VALIDADOS ===
        if st.session_state.of_pallets_list:
            st.divider()
            st.subheader("4️⃣ Pallets a Agregar")
            
            # Resumen
            total_kg = sum(p['kg'] for p in st.session_state.of_pallets_list)
            col_res1, col_res2 = st.columns(2)
            col_res1.metric("📦 Total Pallets", len(st.session_state.of_pallets_list))
            col_res2.metric("⚖️ Total Kg", f"{total_kg:,.2f}")
            
            # Lista de pallets
            for idx, pallet in enumerate(st.session_state.of_pallets_list):
                with st.container(border=True):
                    col_info, col_del = st.columns([5, 1])
                    
                    with col_info:
                        tipo_icon = "🟢" if tipo_mov == "subproductos" else "🔵"
                        st.markdown(f"""
                        **{tipo_icon} {pallet['codigo']}** - {pallet['kg']:,.2f} kg
                        
                        📍 Lote: `{pallet.get('lote_nombre', 'N/A')}` | Producto: {pallet.get('producto_nombre', 'N/A')[:40]}
                        """)
                    
                    with col_del:
                        if st.button("🗑️", key=f"del_of_pallet_{idx}", help="Eliminar pallet"):
                            st.session_state.of_pallets_list.pop(idx)
                            st.rerun()
            
            # Botones de acción
            st.divider()
            col_clear, col_submit = st.columns(2)
            
            with col_clear:
                if st.button("🗑️ Limpiar Lista", use_container_width=True, key="btn_clear_of"):
                    st.session_state.of_pallets_list = []
                    st.rerun()
            
            with col_submit:
                if st.button(f"✅ Agregar a {tipo_mov.upper()}", use_container_width=True, type="primary", key="btn_submit_of"):
                    _agregar_a_orden(username, password, st.session_state.of_orden_info['id'], tipo_mov)


def _buscar_orden(username: str, password: str, orden_input: str):
    """Busca una orden de fabricación por nombre o ID."""
    with st.spinner("Buscando orden..."):
        try:
            # Procesar input - puede ser nombre completo o solo número
            if orden_input.isdigit():
                search_term = orden_input
            elif '/' not in orden_input:
                search_term = orden_input
            else:
                search_term = orden_input
            
            response = requests.get(
                f"{API_URL}/api/v1/automatizaciones/procesos/buscar-orden",
                params={
                    "username": username,
                    "password": password,
                    "orden": search_term
                },
                timeout=15
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    st.session_state.of_orden_info = data['orden']
                    st.session_state.of_pallets_list = []  # Limpiar pallets
                    st.rerun()
                else:
                    st.error(f"❌ {data.get('error', 'Orden no encontrada')}")
            else:
                st.error(f"❌ Error HTTP {response.status_code}: {response.text[:200]}")
        
        except requests.exceptions.Timeout:
            st.error("❌ Timeout al buscar orden")
        except Exception as e:
            st.error(f"❌ Error: {e}")


def _procesar_pallets(username: str, password: str, pallets_text: str, tipo_mov: str):
    """Procesa y valida los pallets ingresados."""
    if not pallets_text.strip():
        st.warning("⚠️ Ingresa al menos un código de pallet")
        return
    
    codigos_raw = [c.strip() for c in pallets_text.split('\n') if c.strip()]
    
    # Normalizar códigos (PAC -> PACK)
    codigos = []
    for c in codigos_raw:
        if c.startswith('PAC') and not c.startswith('PACK'):
            c = 'PACK' + c[3:]
        codigos.append(c)
    
    # Filtrar duplicados ya en lista
    codigos_existentes = {p['codigo'] for p in st.session_state.of_pallets_list}
    codigos_nuevos = [c for c in codigos if c not in codigos_existentes]
    duplicados_ignorados = len(codigos) - len(codigos_nuevos)
    
    if not codigos_nuevos:
        st.warning("⚠️ Todos los pallets ya están en la lista")
        return
    
    with st.spinner(f"Validando {len(codigos_nuevos)} pallets..."):
        try:
            response = requests.post(
                f"{API_URL}/api/v1/automatizaciones/procesos/validar-pallets",
                params={"username": username, "password": password},
                json={
                    "pallets": codigos_nuevos,
                    "tipo": tipo_mov,
                    "orden_id": st.session_state.of_orden_info['id']
                },
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                agregados = 0
                errores = []
                
                for pallet in data.get('pallets', []):
                    if pallet.get('valido'):
                        st.session_state.of_pallets_list.append({
                            'codigo': pallet['codigo'],
                            'kg': pallet.get('kg', 0.0),
                            'lote_id': pallet.get('lote_id'),
                            'lote_nombre': pallet.get('lote_nombre', pallet['codigo']),
                            'producto_id': pallet.get('producto_id'),
                            'producto_nombre': pallet.get('producto_nombre', 'N/A'),
                            'ubicacion_id': pallet.get('ubicacion_id'),
                            'package_id': pallet.get('package_id'),
                        })
                        agregados += 1
                    else:
                        errores.append(f"{pallet['codigo']}: {pallet.get('error', 'No válido')}")
                
                # Mostrar resumen
                msgs = []
                if agregados > 0:
                    msgs.append(f"✅ {agregados} validados")
                if duplicados_ignorados > 0:
                    msgs.append(f"🔄 {duplicados_ignorados} duplicados ignorados")
                if errores:
                    msgs.append(f"❌ {len(errores)} con errores")
                
                if agregados > 0:
                    st.success(" | ".join(msgs))
                else:
                    st.warning(" | ".join(msgs))
                
                for err in errores:
                    st.error(err)
                
                # Limpiar textarea
                if 'of_pallets_input' in st.session_state:
                    st.session_state.of_pallets_input = ""
                
                st.rerun()
            else:
                st.error(f"❌ Error HTTP {response.status_code}: {response.text[:200]}")
        
        except requests.exceptions.Timeout:
            st.error("❌ Timeout validando pallets")
        except Exception as e:
            st.error(f"❌ Error: {e}")


def _agregar_a_orden(username: str, password: str, orden_id: int, tipo_mov: str):
    """Agrega los pallets validados a la orden como componentes o subproductos."""
    pallets = st.session_state.of_pallets_list
    
    if not pallets:
        st.warning("⚠️ No hay pallets para agregar")
        return
    
    with st.spinner(f"Agregando {len(pallets)} pallets a {tipo_mov}..."):
        try:
            payload = {
                "orden_id": orden_id,
                "tipo": tipo_mov,
                "pallets": [
                    {
                        "codigo": p['codigo'],
                        "kg": p['kg'],
                        "lote_id": p.get('lote_id'),
                        "lote_nombre": p.get('lote_nombre'),
                        "producto_id": p.get('producto_id'),
                        "ubicacion_id": p.get('ubicacion_id'),
                        "package_id": p.get('package_id'),
                    }
                    for p in pallets
                ]
            }
            
            response = requests.post(
                f"{API_URL}/api/v1/automatizaciones/procesos/agregar-pallets",
                params={"username": username, "password": password},
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                st.session_state.of_last_result = result
                
                if result.get('success'):
                    # Limpiar lista y actualizar orden
                    st.session_state.of_pallets_list = []
                    # Refrescar info de orden
                    _buscar_orden(username, password, st.session_state.of_orden_info['nombre'])
                
                st.rerun()
            else:
                st.error(f"❌ Error HTTP {response.status_code}: {response.text[:200]}")
        
        except requests.exceptions.Timeout:
            st.error("❌ Timeout agregando pallets")
        except Exception as e:
            st.error(f"❌ Error: {e}")


def _get_estado_label(estado: str) -> str:
    """Retorna etiqueta amigable para el estado."""
    estados = {
        'draft': '📝 Borrador',
        'confirmed': '✅ Confirmado',
        'progress': '🔄 En Proceso',
        'done': '✔️ Terminado',
        'cancel': '❌ Cancelado'
    }
    return estados.get(estado, estado)
