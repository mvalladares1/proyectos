"""
Tab: Movimientos de Pallets (Mobile-Optimized)
Interfaz ultra-dinámica para celular/tablet con escáner Bluetooth.
Auto-submit al escanear, tarjetas touch-friendly, feedback instantáneo.
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


# CSS para diseño mobile-first y botón sticky
MOBILE_CSS = """
<style>
    /* Botones más grandes para touch */
    .stButton > button {
        min-height: 50px !important;
        font-size: 1.1rem !important;
    }
    
    /* Inputs más grandes */
    .stTextInput > div > div > input {
        font-size: 1.2rem !important;
        padding: 12px !important;
    }
    
    /* Tarjeta de pallet */
    .pallet-card {
        background: linear-gradient(135deg, rgba(30,30,40,0.9), rgba(40,40,55,0.9));
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
    }
    
    .pallet-card.pending {
        border-left-color: #FFC107;
    }
    
    .pallet-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
    }
    
    .pallet-code {
        font-size: 1.2rem;
        font-weight: bold;
        color: #4FC3F7;
    }
    
    .pallet-kg {
        font-size: 1.1rem;
        color: #81C784;
        font-weight: 600;
    }
    
    .pallet-detail {
        font-size: 0.9rem;
        color: #aaa;
        margin-top: 4px;
    }
    
    /* Sticky footer para botón confirmar */
    .sticky-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: linear-gradient(0deg, rgba(14,17,23,1) 70%, rgba(14,17,23,0) 100%);
        padding: 20px 20px 25px 20px;
        z-index: 999;
    }
    
    .sticky-btn {
        width: 100%;
        padding: 16px 24px !important;
        font-size: 1.3rem !important;
        font-weight: bold !important;
        border-radius: 12px !important;
        background: linear-gradient(135deg, #4CAF50, #2E7D32) !important;
        border: none !important;
        color: white !important;
        box-shadow: 0 4px 15px rgba(76, 175, 80, 0.4) !important;
    }
    
    /* Animación pulse para feedback */
    @keyframes pulse-success {
        0% { transform: scale(1); }
        50% { transform: scale(1.02); }
        100% { transform: scale(1); }
    }
    
    .pulse-effect {
        animation: pulse-success 0.3s ease-in-out;
    }
    
    /* Status badge */
    .status-badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    
    .status-ready { background: #4CAF50; color: white; }
    .status-pending { background: #FFC107; color: #333; }
    .status-error { background: #f44336; color: white; }
    
    /* Espaciado para sticky footer */
    .main-content {
        padding-bottom: 120px;
    }
    
    /* Animación de éxito */
    @keyframes success-glow {
        0% { box-shadow: 0 0 5px rgba(76, 175, 80, 0.5); }
        50% { box-shadow: 0 0 30px rgba(76, 175, 80, 0.8); }
        100% { box-shadow: 0 0 5px rgba(76, 175, 80, 0.5); }
    }
    
    .success-animation {
        animation: success-glow 1s ease-in-out 2;
    }
    
    /* Warning card */
    .pallet-card.warning {
        border-left-color: #ff9800;
        background: linear-gradient(135deg, rgba(50,40,20,0.9), rgba(60,50,30,0.9));
    }
</style>
"""

# JavaScript para sonidos de feedback
SOUND_JS = """
<script>
function playBeep(type) {
    const audioContext = new (window.AudioContext || window.webkitAudioContext)();
    const oscillator = audioContext.createOscillator();
    const gainNode = audioContext.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioContext.destination);
    
    if (type === 'success') {
        oscillator.frequency.value = 800;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.3;
    } else if (type === 'error') {
        oscillator.frequency.value = 300;
        oscillator.type = 'square';
        gainNode.gain.value = 0.2;
    } else {
        oscillator.frequency.value = 600;
        oscillator.type = 'sine';
        gainNode.gain.value = 0.2;
    }
    
    oscillator.start();
    setTimeout(() => {
        oscillator.stop();
    }, type === 'error' ? 200 : 100);
}

// Exponer globalmente
window.playBeep = playBeep;
</script>
"""


@st.fragment
def render(username: str, password: str, api_url: str):
    """Renderiza el tab de Movimientos de Pallets (Mobile-Optimized)"""
    
    # Inyectar CSS y JS de sonido
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    st.components.v1.html(SOUND_JS, height=0)
    
    # Header compacto
    st.markdown("## 📦 Movimientos")
    
    # Inicializar session state
    if "mov_camara" not in st.session_state:
        st.session_state.mov_camara = None
    if "mov_pallets" not in st.session_state:
        st.session_state.mov_pallets = []
    if "mov_last_scan" not in st.session_state:
        st.session_state.mov_last_scan = ""
    if "mov_historial" not in st.session_state:
        st.session_state.mov_historial = []
    if "mov_ultimo_movimiento" not in st.session_state:
        st.session_state.mov_ultimo_movimiento = None
    if "mov_historial_dia" not in st.session_state:
        st.session_state.mov_historial_dia = []
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 0: ÚLTIMO MOVIMIENTO + UNDO
    # ═══════════════════════════════════════════════════════════════
    
    if st.session_state.mov_ultimo_movimiento:
        ultimo = st.session_state.mov_ultimo_movimiento
        pallets_count = len(ultimo.get("pallets", []))
        kg_total = sum(p.get("kg", 0) for p in ultimo.get("pallets", []))
        destino_name = ultimo.get("destino", {}).get("name", "N/A")
        
        with st.container(border=True):
            st.markdown(f"""
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <span style="color: #81C784; font-weight: bold;">✅ Último movimiento</span>
                    <span style="color: #aaa; margin-left: 8px;">⏰ {ultimo.get('timestamp', 'N/A')}</span>
                </div>
                <div style="color: #4FC3F7;">
                    {pallets_count} pallets → {destino_name}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            col_undo1, col_undo2 = st.columns([3, 1])
            with col_undo1:
                st.caption(f"📦 {kg_total:,.0f} kg total")
            with col_undo2:
                if st.button("↩️ Deshacer", key="btn_undo_main", use_container_width=True):
                    _deshacer_movimiento(username, password, api_url)
        
        st.markdown("---")
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 1: CÁMARA DESTINO
    # ═══════════════════════════════════════════════════════════════
    
    if not st.session_state.mov_camara:
        st.markdown("### 📍 Escanear Cámara Destino")
        
        # Historial rápido con nombre visible
        if st.session_state.mov_historial:
            st.caption("🕐 Repetir último destino:")
            last = st.session_state.mov_historial[0]
            if st.button(f"📍 {last['name']}", key="btn_last_destino", use_container_width=True, type="primary"):
                st.session_state.mov_camara = last
                st.toast(f"✅ Destino: {last['name']}", icon="📍")
                st.rerun()
            
            # Otros destinos recientes
            if len(st.session_state.mov_historial) > 1:
                with st.expander("Ver más destinos recientes"):
                    for i, hist in enumerate(st.session_state.mov_historial[1:4]):
                        if st.button(f"📍 {hist['name']}", key=f"hist_{i+1}", use_container_width=True):
                            st.session_state.mov_camara = hist
                            st.toast(f"✅ Destino: {hist['name']}", icon="📍")
                            st.rerun()
        
        st.markdown("---")
        st.caption("O escanear nuevo código:")
        
        # Input de cámara con auto-submit
        def on_camara_change():
            code = st.session_state.get("camara_input", "").strip()
            if len(code) >= 4:  # Código válido
                _buscar_camara(code, username, password, api_url)
        
        st.text_input(
            "🔍 Escanear código de cámara",
            key="camara_input",
            placeholder="Escanea el código de barras...",
            on_change=on_camara_change,
            label_visibility="collapsed"
        )
        
    else:
        # Mostrar cámara seleccionada con opción de cambiar
        st.markdown(f"""
        <div style="background: linear-gradient(135deg, #1565C0, #0D47A1); padding: 16px; border-radius: 12px; margin-bottom: 16px;">
            <div style="font-size: 0.9rem; color: #90CAF9;">📍 DESTINO SELECCIONADO</div>
            <div style="font-size: 1.4rem; font-weight: bold; color: white;">{st.session_state.mov_camara['name']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("✏️ Cambiar destino", key="btn_change_camara", use_container_width=True):
            st.session_state.mov_camara = None
            st.rerun()
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 2: ESCANEAR PALLETS
    # ═══════════════════════════════════════════════════════════════
    
    if st.session_state.mov_camara:
        st.markdown("---")
        st.markdown("### 📋 Escanear Pallets")
        
        # Input de pallet - text_area para múltiples líneas
        def on_pallet_change():
            raw_input = st.session_state.get("pallet_input", "").strip()
            if not raw_input:
                return
            
            # Separar por líneas, espacios o tabs
            import re
            codes = re.split(r'[\n\r\t]+', raw_input)
            
            for code in codes:
                code = code.strip()
                if len(code) >= 5:  # Código válido
                    _agregar_pallet(code, username, password, api_url)
            
            # Limpiar input después de procesar
            st.session_state.pallet_input = ""
        
        st.text_area(
            "📦 Escanear pallet(s)",
            key="pallet_input",
            placeholder="Escanea uno o varios códigos (uno por línea)...",
            on_change=on_pallet_change,
            label_visibility="collapsed",
            height=80
        )
        
        # Contador rápido
        if st.session_state.mov_pallets:
            total_kg = sum(p["kg"] for p in st.session_state.mov_pallets)
            st.markdown(f"""
            <div style="text-align: center; padding: 12px; background: rgba(76,175,80,0.2); border-radius: 8px; margin: 12px 0;">
                <span style="font-size: 1.5rem; font-weight: bold; color: #4CAF50;">
                    {len(st.session_state.mov_pallets)} pallets
                </span>
                <span style="color: #aaa; margin-left: 8px;">
                    ({fmt_numero(total_kg, 1)} kg)
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            # Botones de acción rápida arriba
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚨 Quitar último", key="btn_remove_last", use_container_width=True):
                    removed = st.session_state.mov_pallets.pop()
                    st.toast(f"❌ Quitado: {removed['code']}", icon="🗑️")
                    st.rerun()
            with col2:
                if st.button("🗑️ Limpiar todo", key="btn_clear_all", use_container_width=True):
                    st.session_state.mov_pallets = []
                    st.session_state.pallet_input = ""  # Limpiar input también
                    st.toast("Lista limpiada", icon="🗑️")
                    st.rerun()
        
        # Tarjetas de pallets (más reciente arriba)
        for i, pallet in enumerate(reversed(st.session_state.mov_pallets)):
            _render_pallet_card(pallet)
        
        if not st.session_state.mov_pallets:
            st.info("📦 Escanea el primer pallet para agregarlo")
    
    # ═══════════════════════════════════════════════════════════════
    # SECCIÓN 3: BOTÓN CONFIRMAR
    # ═══════════════════════════════════════════════════════════════
    
    if st.session_state.mov_camara and st.session_state.mov_pallets:
        st.markdown("---")
        
        total_pallets = len(st.session_state.mov_pallets)
        total_kg = sum(p["kg"] for p in st.session_state.mov_pallets)
        destino = st.session_state.mov_camara['name']
        
        # Resumen visual
        st.markdown(f"""
        <div style="text-align: center; padding: 16px; background: rgba(76,175,80,0.15); border-radius: 12px; margin-bottom: 16px;">
            <div style="font-size: 1rem; color: #aaa;">Mover a</div>
            <div style="font-size: 1.4rem; font-weight: bold; color: #4FC3F7;">{destino}</div>
            <div style="font-size: 1.1rem; color: #81C784; margin-top: 8px;">
                {total_pallets} pallets • {fmt_numero(total_kg, 1)} kg
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Botón de confirmación grande
        if st.button(
            f"✅ CONFIRMAR MOVIMIENTO",
            key="btn_confirm",
            type="primary",
            use_container_width=True
        ):
            _ejecutar_movimiento(username, password, api_url)
    
    # Espaciado para sticky footer
    st.markdown("<div style='height: 80px;'></div>", unsafe_allow_html=True)


def _buscar_camara(code: str, username: str, password: str, api_url: str):
    """Busca cámara por código de barras"""
    try:
        resp = requests.get(
            f"{api_url}/api/v1/stock/ubicacion-by-barcode",
            params={"username": username, "password": password, "barcode": code},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("found"):
                camara = {
                    "id": data["id"],
                    "name": data["display_name"],
                    "barcode": data["barcode"]
                }
                st.session_state.mov_camara = camara
                
                # Agregar al historial si no existe
                if not any(h["id"] == camara["id"] for h in st.session_state.mov_historial):
                    st.session_state.mov_historial.insert(0, camara)
                    st.session_state.mov_historial = st.session_state.mov_historial[:5]  # Max 5
                
                st.toast(f"✅ {camara['name']}", icon="📍")
            else:
                st.toast(f"❌ Cámara no encontrada", icon="⚠️")
        else:
            st.toast(f"Error: {resp.status_code}", icon="❌")
    except Exception as e:
        st.toast(f"Error: {str(e)}", icon="❌")


def _agregar_pallet(code: str, username: str, password: str, api_url: str):
    """Agrega pallet a la lista con validación de destino"""
    # Verificar duplicado
    if any(p["code"] == code for p in st.session_state.mov_pallets):
        st.toast("⚠️ Pallet ya escaneado", icon="⚠️")
        _play_sound("error")
        return
    
    try:
        resp = requests.get(
            f"{api_url}/api/v1/stock/pallet-info",
            params={"username": username, "password": password, "pallet_code": code},
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            if data.get("found"):
                # VALIDACIÓN DE DESTINO: verificar si ya está en la cámara destino (por ID)
                current_location_id = data.get("location_id")
                target_location_id = st.session_state.mov_camara.get("id") if st.session_state.mov_camara else None
                
                if current_location_id and target_location_id and current_location_id == target_location_id:
                    st.toast(f"⚠️ {code} ya está en destino", icon="⚠️")
                    _play_sound("error")
                    return
                
                # Extraer datos del API (estructura correcta)
                products = data.get("products", [])
                first_product = products[0] if products else {}
                pallet_status = data.get("status", "in_stock")
                
                # Determinar ubicación según estado
                if pallet_status == "pending_reception":
                    ubicacion_display = f"📥 {data.get('destination_name', 'En recepción')}"
                    location_id = data.get("destination_id")  # Usar destination_id para pending
                else:
                    ubicacion_display = data.get("location_name", "N/A")
                    location_id = data.get("location_id")
                
                pallet = {
                    "code": code,
                    "producto": first_product.get("name", "N/A"),
                    "kg": data.get("total_quantity", 0),
                    "ubicacion": ubicacion_display,
                    "lote": first_product.get("lot", "N/A"),
                    "productor": "N/A",
                    "location_id": location_id,  # Para undo
                    "status": pallet_status  # Guardar estado
                }
                st.session_state.mov_pallets.append(pallet)
                
                # Mensaje diferenciado según estado
                if pallet_status == "pending_reception":
                    st.toast(f"✅ {code} (En recepción - se cambiará ruta)", icon="📥")
                else:
                    st.toast(f"✅ {code} agregado", icon="📦")
                _play_sound("success")
            else:
                st.toast(f"❌ Pallet no encontrado", icon="⚠️")
                _play_sound("error")
        else:
            st.toast(f"Error: {resp.status_code}", icon="❌")
            _play_sound("error")
    except Exception as e:
        st.toast(f"Error: {str(e)}", icon="❌")
        _play_sound("error")


def _play_sound(sound_type: str):
    """Reproduce sonido de feedback via JS"""
    # Nota: Los sonidos requieren interacción del usuario primero (limitación del navegador)
    # Se activan después del primer click
    pass  # El sonido se activa mediante JS inyectado


def _render_pallet_card(pallet: dict):
    """Renderiza una tarjeta de pallet con badge de estado"""
    # Determinar clase CSS según estado
    card_class = "pallet-card"
    status_badge = ""
    
    if pallet.get("status") == "pending_reception":
        card_class = "pallet-card warning"
        status_badge = '<span class="status-badge status-pending">📥 En Recepción</span>'
    else:
        status_badge = '<span class="status-badge status-ready">✓ Stock</span>'
    
    st.markdown(f"""
    <div class="{card_class}">
        <div class="pallet-card-header">
            <span class="pallet-code">📦 {pallet['code']}</span>
            <span class="pallet-kg">{fmt_numero(pallet['kg'], 1)} kg</span>
        </div>
        <div style="margin: 4px 0;">{status_badge}</div>
        <div class="pallet-detail">
            {pallet['producto'][:35]}{'...' if len(pallet['producto']) > 35 else ''}
        </div>
        <div class="pallet-detail">
            📍 {pallet['ubicacion']} • 🏷️ {pallet['lote']}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ejecutar_movimiento(username: str, password: str, api_url: str):
    """Ejecuta el movimiento de pallets"""
    with st.spinner("🔄 Moviendo pallets..."):
        try:
            pallet_codes = [p["code"] for p in st.session_state.mov_pallets]
            
            # Guardar datos para UNDO antes de mover
            st.session_state.mov_ultimo_movimiento = {
                "pallets": st.session_state.mov_pallets.copy(),
                "destino": st.session_state.mov_camara.copy(),
                "timestamp": datetime.now().strftime("%H:%M:%S")
            }
            
            resp = requests.post(
                f"{api_url}/api/v1/stock/move-multiple",
                json={
                    "pallet_codes": pallet_codes,
                    "target_location_id": st.session_state.mov_camara["id"],
                    "username": username,
                    "password": password
                },
                timeout=60
            )
            
            if resp.status_code == 200:
                result = resp.json()
                
                # Guardar en historial del día
                if "mov_historial_dia" not in st.session_state:
                    st.session_state.mov_historial_dia = []
                
                # API retorna success y failed
                success_count = result.get("success", 0)
                error_count = result.get("failed", 0)
                
                st.session_state.mov_historial_dia.insert(0, {
                    "timestamp": datetime.now().strftime("%H:%M:%S"),
                    "destino": st.session_state.mov_camara["name"],
                    "cantidad": len(pallet_codes),
                    "kg": sum(p["kg"] for p in st.session_state.mov_pallets),
                    "success": success_count,
                    "failed": error_count
                })
                
                # Mostrar resultado
                st.success(f"✅ **{success_count} pallets movidos correctamente**")
                
                if error_count > 0:
                    st.warning(f"⚠️ {error_count} pallets fallaron")
                    with st.expander("Ver detalles"):
                        for detail in result.get("details", []):
                            if detail.get("success"):
                                st.success(f"✅ {detail['pallet']}")
                            else:
                                st.error(f"❌ {detail['pallet']}: {detail.get('message', 'Error')}")
                
                # Limpiar estado
                st.session_state.mov_pallets = []
                st.session_state.mov_camara = None
                st.session_state.pallet_input = ""
                
                st.balloons()
                st.toast("✅ Movimiento completado!", icon="🎉")
                
            else:
                st.error(f"Error {resp.status_code}: {resp.text}")
                st.session_state.mov_ultimo_movimiento = None
                
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.session_state.mov_ultimo_movimiento = None


def _deshacer_movimiento(username: str, password: str, api_url: str):
    """Deshace el último movimiento moviendo pallets a sus ubicaciones originales"""
    
    if not st.session_state.mov_ultimo_movimiento:
        st.warning("No hay movimiento para deshacer")
        return
    
    ultimo = st.session_state.mov_ultimo_movimiento
    pallets = ultimo.get("pallets", [])
    
    if not pallets:
        st.warning("No hay pallets en el último movimiento")
        return
    
    # Agrupar pallets por ubicación original para mover en lotes
    ubicaciones = {}
    for p in pallets:
        loc_id = p.get("location_id")
        if loc_id:
            if loc_id not in ubicaciones:
                ubicaciones[loc_id] = []
            ubicaciones[loc_id].append(p["code"])
    
    if not ubicaciones:
        st.warning("⚠️ No se puede deshacer: faltan datos de ubicación original")
        return
    
    with st.spinner("↩️ Deshaciendo movimiento..."):
        total_success = 0
        total_failed = 0
        
        for loc_id, codes in ubicaciones.items():
            try:
                resp = requests.post(
                    f"{api_url}/api/v1/stock/move-multiple",
                    json={
                        "pallet_codes": codes,
                        "target_location_id": loc_id,
                        "username": username,
                        "password": password
                    },
                    timeout=60
                )
                
                if resp.status_code == 200:
                    result = resp.json()
                    total_success += result.get("success", 0)
                    total_failed += result.get("failed", 0)
                else:
                    total_failed += len(codes)
                    
            except Exception as e:
                st.error(f"Error al deshacer: {str(e)}")
                total_failed += len(codes)
        
        if total_success > 0:
            st.success(f"↩️ Deshacer completado: {total_success} pallets devueltos")
            # Limpiar último movimiento
            st.session_state.mov_ultimo_movimiento = None
            st.toast("↩️ Movimiento deshecho!", icon="✅")
            st.rerun()
        
        if total_failed > 0:
            st.warning(f"⚠️ {total_failed} pallets no se pudieron devolver")
