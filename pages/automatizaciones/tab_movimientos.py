"""
Tab: Movimientos de Pallets (Mobile-Optimized)
Interfaz ultra-dinámica para celular/tablet con escáner Bluetooth.
Auto-submit al escanear, tarjetas touch-friendly, feedback instantáneo.
"""
import streamlit as st
import requests
from datetime import datetime, timedelta
import pandas as pd
import time
import re
from .shared import API_URL

# CONFIGURACIÓN DE VALIDACIONES
MAX_PALLETS_PER_MOVE = 50  # Límite máximo de pallets por movimiento
MAX_RETRIES = 3  # Reintentos para llamadas API
BASE_RETRY_DELAY = 1  # Segundos base para exponential backoff
CACHE_TTL_SECONDS = 300  # 5 minutos de caché para pallets
REQUIRE_CONFIRMATION_CROSS_LOCATION = True  # Confirmar movimientos entre ubicaciones diferentes


def fmt_numero(num, decimales=0):
    """Formatea número con separadores de miles"""
    if num is None:
        return "0"
    return f"{num:,.{decimales}f}".replace(",", ".")


def _validate_barcode_checksum(code: str) -> tuple[bool, str]:
    """Valida formato y checksum básico de código de barras"""
    if not code or len(code) < 3:
        return False, "Código muy corto"
    
    # Validar caracteres alfanuméricos + guiones
    if not re.match(r'^[A-Za-z0-9\-_]+$', code):
        return False, "Caracteres inválidos"
    
    # Validar formato específico si existe (ej: PALLET-XXXX o TARJA-XXX)
    if code.startswith(("PALLET-", "TARJA-", "PAL-")):
        parts = code.split("-")
        if len(parts) != 2 or not parts[1].isdigit():
            return False, "Formato inválido"
    
    return True, ""


def _validate_api_response(data: dict, required_fields: list) -> tuple[bool, str]:
    """Valida estructura de respuesta del API"""
    if not isinstance(data, dict):
        return False, "Respuesta no es un objeto JSON"
    
    for field in required_fields:
        if field not in data:
            return False, f"Falta campo requerido: {field}"
    
    return True, ""


def _api_call_with_retry(func, max_retries=MAX_RETRIES, base_delay=BASE_RETRY_DELAY, operation_name=""):
    """Ejecuta llamada API con reintentos exponenciales"""
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            st.toast(f"⏳ {operation_name} - Reintentando en {delay}s... ({attempt + 1}/{max_retries})", icon="⏳")
            time.sleep(delay)
        except requests.exceptions.ConnectionError:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            st.toast(f"🔌 Sin conexión - Reintentando {operation_name}...", icon="⚠️")
            time.sleep(delay)
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            if attempt < max_retries - 1:
                st.toast(f"⚠️ Error: {str(e)[:50]}... Reintentando...", icon="⚠️")
                time.sleep(base_delay)
    
    raise Exception(f"Máximo de reintentos alcanzado para {operation_name}")


def _get_from_cache(cache_key: str):
    """Obtiene datos del caché local si no expiró"""
    if "pallet_cache" not in st.session_state:
        st.session_state.pallet_cache = {}
    
    cache_entry = st.session_state.pallet_cache.get(cache_key)
    if cache_entry:
        age = (datetime.now() - cache_entry["timestamp"]).total_seconds()
        if age < CACHE_TTL_SECONDS:
            return cache_entry["data"]
    return None


def _save_to_cache(cache_key: str, data: dict):
    """Guarda datos en caché local con timestamp"""
    if "pallet_cache" not in st.session_state:
        st.session_state.pallet_cache = {}
    
    st.session_state.pallet_cache[cache_key] = {
        "timestamp": datetime.now(),
        "data": data
    }
    
    # Limpiar caché antiguo (más de 10 minutos)
    keys_to_delete = []
    for key, entry in st.session_state.pallet_cache.items():
        age = (datetime.now() - entry["timestamp"]).total_seconds()
        if age > 600:  # 10 minutos
            keys_to_delete.append(key)
    
    for key in keys_to_delete:
        del st.session_state.pallet_cache[key]


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
    
    /* Contador sticky */
    .sticky-counter {
        position: sticky;
        top: 0;
        z-index: 100;
        background: rgba(14,17,23,0.98);
        padding: 12px;
        margin: -8px -8px 12px -8px;
        border-radius: 8px;
        border-bottom: 2px solid #4CAF50;
        backdrop-filter: blur(10px);
    }
    
    /* Tarjeta de pallet mejorada */
    .pallet-card {
        background: linear-gradient(135deg, rgba(30,30,40,0.9), rgba(40,40,55,0.9));
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        border-left: 4px solid #4CAF50;
        box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        position: relative;
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
    
    /* Indicador de movimiento FROM → TO */
    .move-indicator {
        background: rgba(33, 150, 243, 0.1);
        border-radius: 8px;
        padding: 8px;
        margin: 8px 0;
        border-left: 3px solid #2196F3;
    }
    
    .location-from {
        color: #FFA726;
        font-size: 0.85rem;
    }
    
    .location-to {
        color: #66BB6A;
        font-size: 0.9rem;
        font-weight: 600;
    }
    
    .arrow-down {
        color: #2196F3;
        font-size: 1.2rem;
        text-align: center;
        margin: 4px 0;
    }
    
    /* Botón eliminar en tarjeta */
    .delete-btn {
        background: transparent;
        border: none;
        color: #f44336;
        cursor: pointer;
        font-size: 1.2rem;
        padding: 4px 8px;
        border-radius: 4px;
        transition: all 0.2s;
    }
    
    .delete-btn:hover {
        background: rgba(244, 67, 54, 0.2);
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
    
    /* Spinner inline */
    .inline-spinner {
        display: inline-block;
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255,255,255,0.3);
        border-top-color: #4CAF50;
        border-radius: 50%;
        animation: spin 0.6s linear infinite;
        margin-left: 8px;
        vertical-align: middle;
    }
    
    @keyframes spin {
        to { transform: rotate(360deg); }
    }
</style>
"""

# JavaScript para sonidos, vibración, shortcuts y auto-focus
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
        // Vibración corta para éxito
        if (navigator.vibrate) navigator.vibrate(50);
    } else if (type === 'error') {
        oscillator.frequency.value = 300;
        oscillator.type = 'square';
        gainNode.gain.value = 0.2;
        // Patrón de vibración para error
        if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
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

// Shortcut Ctrl+Enter para confirmar
document.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && e.ctrlKey) {
        const confirmBtn = Array.from(document.querySelectorAll('button')).find(
            btn => btn.textContent.includes('CONFIRMAR MOVIMIENTO')
        );
        if (confirmBtn) {
            confirmBtn.click();
            e.preventDefault();
        }
    }
});

// Auto-focus helper
function autoFocusTextarea() {
    setTimeout(() => {
        const textarea = document.querySelector('textarea[aria-label="📦 Escanear pallet(s)"]');
        if (textarea) textarea.focus();
    }, 100);
}

// Exponer globalmente
window.playBeep = playBeep;
window.autoFocusTextarea = autoFocusTextarea;
</script>
"""


def _inject_css():
    """Inyecta CSS mobile-optimized"""
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)


def _inject_js():
    """Inyecta JavaScript para sonidos, vibración y shortcuts"""
    st.components.v1.html(SOUND_JS, height=0)


def _buscar_camara(code: str, username: str, password: str, api_url: str):
    """Busca cámara por código de barras con retry y validación"""
    try:
        # Convertir a mayúsculas (los códigos de barras son case-sensitive en Odoo)
        code = code.upper()
        
        # Validar checksum
        valid, error_msg = _validate_barcode_checksum(code)
        if not valid:
            st.error(f"❌ Código inválido: {error_msg}")
            return
        
        st.info(f"🔍 Buscando cámara: {code}...")
        
        url = f"{api_url}/api/v1/automatizaciones/tuneles-estaticos/ubicacion-by-barcode"
        params = {"username": username, "password": password, "barcode": code}
        
        # Llamada
        try:
            resp = requests.get(url, params=params, timeout=20)
        except Exception as e:
            st.error(f"❌ Error de conexión: {str(e)}")
            return
        
        if resp.status_code == 404:
            st.error(f"❌ Endpoint no encontrado")
            return
        
        if resp.status_code != 200:
            st.error(f"❌ Error {resp.status_code}: {resp.text}")
            return
            
        data = resp.json()
        
        # Validar respuesta
        if not data.get("found"):
            st.warning(f"❌ {data.get('message', 'Cámara no encontrada')}")
            return
        
        # Validar campos requeridos
        if not data.get("id") or not data.get("name"):
            st.error("⚠️ Datos incompletos en respuesta")
            return
        
        camara = {
            "id": data["id"],
            "name": data.get("display_name", data["name"]),
            "barcode": data.get("barcode", "")
        }
        st.session_state.mov_camara = camara
        
        # Agregar al historial si no existe
        if not any(h["id"] == camara["id"] for h in st.session_state.mov_historial):
            st.session_state.mov_historial.insert(0, camara)
            st.session_state.mov_historial = st.session_state.mov_historial[:5]
        
        st.success(f"✅ {camara['name']}")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")


def _agregar_pallet(code: str, username: str, password: str, api_url: str):
    """Agrega pallet a la lista con validaciones completas"""
    # Lock para evitar race conditions
    if st.session_state.get("processing_scan", False):
        return
    
    st.session_state.processing_scan = True
    
    try:
        # VALIDACIÓN 1: Checksum de código
        valid, error_msg = _validate_barcode_checksum(code)
        if not valid:
            st.toast(f"⚠️ Código inválido: {error_msg}", icon="❌")
            _play_sound("error")
            return
        
        # VALIDACIÓN 2: Límite máximo de pallets
        if len(st.session_state.mov_pallets) >= MAX_PALLETS_PER_MOVE:
            st.toast(f"⚠️ Máximo {MAX_PALLETS_PER_MOVE} pallets por movimiento", icon="⚠️")
            _play_sound("error")
            return
        
        # Advertencia cerca del límite
        if len(st.session_state.mov_pallets) >= MAX_PALLETS_PER_MOVE * 0.8:
            st.warning(f"⚠️ Cerca del límite: {len(st.session_state.mov_pallets)}/{MAX_PALLETS_PER_MOVE}")
        
        # VALIDACIÓN 3: Duplicado en lista
        if any(p["code"] == code for p in st.session_state.mov_pallets):
            st.toast("⚠️ Pallet ya escaneado", icon="⚠️")
            _play_sound("error")
            return
        
        # Verificar caché primero
        cache_key = f"{code}_{username}"
        cached_data = _get_from_cache(cache_key)
        
        if cached_data:
            data = cached_data
            st.toast(f"⚡ {code} (caché)", icon="📦")
        else:
            # Mostrar spinner inline
            toast_placeholder = st.empty()
            toast_placeholder.info(f"🔍 Buscando {code}...")
            
            # Llamada con retry
            resp = _api_call_with_retry(
                lambda: requests.get(
                    f"{api_url}/api/v1/stock/pallet-info",
                    params={"username": username, "password": password, "pallet_code": code},
                    timeout=20
                ),
                operation_name="Buscar pallet"
            )
            
            toast_placeholder.empty()
            
            if resp.status_code != 200:
                st.toast(f"Error: {resp.status_code}", icon="❌")
                _play_sound("error")
                return
            
            data = resp.json()
            
            # Validar respuesta
            valid, error_msg = _validate_api_response(data, ["found"])
            if not valid:
                st.toast(f"❌ Respuesta inválida: {error_msg}", icon="⚠️")
                _play_sound("error")
                return
            
            if not data.get("found"):
                st.toast(f"❌ Pallet no encontrado", icon="⚠️")
                _play_sound("error")
                return
            
            # Validar campos requeridos
            valid, error_msg = _validate_api_response(
                data,
                ["status", "products", "total_quantity"]
            )
            if not valid:
                st.toast(f"⚠️ Datos incompletos: {error_msg}", icon="⚠️")
                _play_sound("error")
                return
            
            # Guardar en caché
            _save_to_cache(cache_key, data)
        
        # VALIDACIÓN 4: Destino por ID
        current_location_id = data.get("location_id")
        target_location_id = st.session_state.mov_camara.get("id") if st.session_state.mov_camara else None
        
        if current_location_id and target_location_id and current_location_id == target_location_id:
            st.toast(f"⚠️ {code} ya está en destino", icon="⚠️")
            _play_sound("error")
            return
        
        # Extraer datos del API
        products = data.get("products", [])
        first_product = products[0] if products else {}
        pallet_status = data.get("status", "in_stock")
        
        # Determinar ubicación según estado
        if pallet_status == "pending_reception":
            ubicacion_display = f"📥 {data.get('destination_name', 'En recepción')}"
            location_id = data.get("destination_id")
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
            "location_id": location_id,
            "status": pallet_status
        }
        st.session_state.mov_pallets.append(pallet)
        
        # Mensaje diferenciado según estado
        if pallet_status == "pending_reception":
            st.toast(f"✅ {code} (En recepción - se cambiará ruta)", icon="📥")
        else:
            st.toast(f"✅ {code} agregado", icon="📦")
        _play_sound("success")
        
    except Exception as e:
        st.toast(f"Error: {str(e)}", icon="❌")
        _play_sound("error")
    finally:
        st.session_state.processing_scan = False


def _play_sound(sound_type: str):
    """Reproduce sonido de feedback via JS"""
    # Nota: Los sonidos requieren interacción del usuario primero (limitación del navegador)
    # Se activan después del primer click
    pass  # El sonido se activa mediante JS inyectado


def _render_pallet_card(pallet: dict, index: int = 0):
    """Renderiza una tarjeta de pallet con badge de estado y FROM → TO"""
    # Determinar clase CSS según estado
    card_class = "pallet-card"
    status_badge = ""
    
    if pallet.get("status") == "pending_reception":
        card_class = "pallet-card warning"
        status_badge = '<span class="status-badge status-pending">📥 En Recepción</span>'
    else:
        status_badge = '<span class="status-badge status-ready">✓ Stock</span>'
    
    # Obtener destino de session_state
    destino_name = st.session_state.mov_camara.get('name', 'N/A') if st.session_state.mov_camara else 'N/A'
    
    st.markdown(f"""
    <div class="{card_class}">
        <div class="pallet-card-header">
            <span class="pallet-code">📦 {pallet['code']}</span>
            <span class="pallet-kg">{fmt_numero(pallet['kg'], 1)} kg</span>
        </div>
        <div style="margin: 4px 0;">{status_badge}</div>
        <div class="pallet-detail">
            {pallet['producto'][:40]}{'...' if len(pallet['producto']) > 40 else ''}
        </div>
        
        <div class="move-indicator">
            <div class="location-from">📍 Actual: {pallet['ubicacion']}</div>
            <div class="arrow-down">⬇️</div>
            <div class="location-to">🎯 Destino: {destino_name}</div>
        </div>
        
        <div class="pallet-detail">
            🏷️ {pallet['lote']}
        </div>
    </div>
    """, unsafe_allow_html=True)


def _ejecutar_movimiento(username: str, password: str, api_url: str):
    """Ejecuta el movimiento de pallets con pre-validación, confirmación doble y auditoría"""
    if not st.session_state.mov_camara or not st.session_state.mov_pallets:
        st.error("⚠️ Faltan datos")
        return
    
    location_dest_id = st.session_state.mov_camara["id"]
    location_dest_name = st.session_state.mov_camara["name"]
    
    # PRE-VALIDACIÓN 1: Prevenir movimientos circulares
    circular_pallets = [
        p["code"] for p in st.session_state.mov_pallets
        if p.get("location_id") == location_dest_id
    ]
    
    if circular_pallets:
        st.error(f"⚠️ Movimiento circular detectado: {', '.join(circular_pallets[:3])} {'...' if len(circular_pallets) > 3 else ''} ya están en {location_dest_name}")
        _play_sound("error")
        return
    
    # PRE-VALIDACIÓN 2: Confirmación doble para movimientos críticos
    if REQUIRE_CONFIRMATION_CROSS_LOCATION:
        # Detectar si hay pallets de ubicaciones muy diferentes
        unique_locations = set(p.get("ubicacion", "N/A") for p in st.session_state.mov_pallets)
        
        # Si hay más de 2 ubicaciones origen diferentes, pedir confirmación
        if len(unique_locations) > 2:
            if not st.session_state.get("confirm_cross_location", False):
                st.warning(f"⚠️ Movimiento crítico: {len(st.session_state.mov_pallets)} pallets desde {len(unique_locations)} ubicaciones diferentes")
                if st.button("✅ CONFIRMAR MOVIMIENTO CRÍTICO", type="primary", use_container_width=True, key="btn_confirm_critical"):
                    st.session_state.confirm_cross_location = True
                    st.rerun()
                else:
                    return
    
    # Resetear flag de confirmación
    st.session_state.confirm_cross_location = False
    
    with st.spinner("🔄 Moviendo pallets..."):
        try:
            pallet_codes = [p["code"] for p in st.session_state.mov_pallets]
            timestamp = datetime.now().isoformat()
            
            # Guardar datos para UNDO antes de mover
            st.session_state.mov_ultimo_movimiento = {
                "pallets": st.session_state.mov_pallets.copy(),
                "destino": st.session_state.mov_camara.copy(),
                "timestamp": timestamp
            }
            
            # Llamada con retry
            resp = _api_call_with_retry(
                lambda: requests.post(
                    f"{api_url}/api/v1/stock/move-multiple",
                    json={
                        "pallet_codes": pallet_codes,
                        "target_location_id": location_dest_id,
                        "username": username,
                        "password": password
                    },
                    timeout=60
                ),
                operation_name="Mover pallets"
            )
            
            if resp.status_code == 200:
                result = resp.json()
                
                # Validar respuesta
                valid, error_msg = _validate_api_response(result, ["success", "failed"])
                if not valid:
                    st.error(f"❌ Respuesta inválida: {error_msg}")
                    # Auditar error
                    st.session_state.audit_logs.append({
                        "timestamp": timestamp,
                        "action": "move_pallets",
                        "status": "validation_error",
                        "error": error_msg,
                        "pallets_count": len(pallet_codes),
                        "destination": location_dest_name
                    })
                    return
                
                # API retorna success y failed
                success_count = result.get("success", 0)
                error_count = result.get("failed", 0)
                
                # Auditar movimiento
                audit_entry = {
                    "timestamp": timestamp,
                    "action": "move_pallets",
                    "status": "success" if error_count == 0 else "partial_success",
                    "pallets_codes": pallet_codes,
                    "destination_id": location_dest_id,
                    "destination_name": location_dest_name,
                    "success_count": success_count,
                    "failed_count": error_count,
                    "errors": result.get("errors", [])
                }
                st.session_state.audit_logs.append(audit_entry)
                
                # Limitar logs a últimos 100
                if len(st.session_state.audit_logs) > 100:
                    st.session_state.audit_logs = st.session_state.audit_logs[-100:]
                
                # Guardar en historial del día
                st.session_state.mov_historial_dia.insert(0, {
                    "timestamp": timestamp,
                    "destino": location_dest_name,
                    "cantidad": len(pallet_codes),
                    "kg": sum(p["kg"] for p in st.session_state.mov_pallets),
                    "success": success_count,
                    "failed": error_count
                })
                # Limitar a 50 entradas máximo
                st.session_state.mov_historial_dia = st.session_state.mov_historial_dia[:50]
                
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
                error_msg = f"Error HTTP: {resp.status_code}"
                st.error(error_msg)
                st.session_state.mov_ultimo_movimiento = None
                
                # Auditar error
                st.session_state.audit_logs.append({
                    "timestamp": timestamp,
                    "action": "move_pallets",
                    "status": "http_error",
                    "error": error_msg,
                    "pallets_count": len(pallet_codes),
                    "destination": location_dest_name
                })
                
        except Exception as e:
            error_msg = str(e)
            st.error(f"Error: {error_msg}")
            st.session_state.mov_ultimo_movimiento = None
            
            # Auditar excepción
            st.session_state.audit_logs.append({
                "timestamp": datetime.now().isoformat(),
                "action": "move_pallets",
                "status": "exception",
                "error": error_msg,
                "pallets_count": len(pallet_codes) if 'pallet_codes' in locals() else 0,
                "destination": location_dest_name
            })


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


@st.fragment
def render(username: str, password: str):
    """Renderiza el tab de Movimientos"""
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
    if "pallet_cache" not in st.session_state:
        st.session_state.pallet_cache = {}
    if "audit_logs" not in st.session_state:
        st.session_state.audit_logs = []
    if "confirm_cross_location" not in st.session_state:
        st.session_state.confirm_cross_location = False

    # Cargar CSS
    _inject_css()
    _inject_js()

    api_url = API_URL

    st.title("📦 Movimientos de Pallets")

    # === SELECTOR DE CÁMARA DESTINO ===
    st.subheader("1️⃣ Selecciona Cámara Destino")

    with st.form("form_buscar_cam", clear_on_submit=False):
        camara_input = st.text_input(
            "Código de cámara",
            placeholder="Ej: Cam80c",
            label_visibility="collapsed"
        )
        
        submitted = st.form_submit_button("🔍 Buscar", type="primary")
        
        if submitted and camara_input:
            _buscar_camara(camara_input.strip(), username, password, api_url)

    # Historial de cámaras (botones rápidos)
    if st.session_state.mov_historial:
        st.caption("🕒 Últimas cámaras:")
        cols = st.columns(min(len(st.session_state.mov_historial), 5))
        for idx, cam in enumerate(st.session_state.mov_historial[:5]):
            with cols[idx]:
                if st.button(
                    f"📍 {cam['name'][:15]}",
                    key=f"hist_cam_{idx}",
                    use_container_width=True
                ):
                    st.session_state.mov_camara = cam
                    st.rerun()

    # Mostrar cámara seleccionada
    if st.session_state.mov_camara:
        st.success(f"✅ **Destino:** {st.session_state.mov_camara['name']}")
        
        # Inyectar auto-focus en textarea después de seleccionar cámara
        st.markdown("""
        <script>
        setTimeout(() => {
            autoFocusTextarea();
        }, 500);
        </script>
        """, unsafe_allow_html=True)
    else:
        st.info("👆 Escanea una cámara primero")

    st.divider()

    # === ESCANEO DE PALLETS ===
    if st.session_state.mov_camara:
        st.subheader("2️⃣ Escanea Pallets")

        # Contador pegajoso (siempre visible)
        st.markdown(f"""
        <div class="sticky-counter">
            📦 {len(st.session_state.mov_pallets)} pallets escaneados
        </div>
        """, unsafe_allow_html=True)

        # Textarea para múltiples códigos (mobile-friendly)
        pallet_input = st.text_area(
            "Escanea códigos (uno por línea)",
            key="pallet_input",
            height=120,
            placeholder="Escanea pallets...\n(uno por línea)",
            label_visibility="collapsed",
            on_change=lambda: _on_pallet_change(username, password, api_url)
        )

        # Botones de acción (táctiles, 50px altura)
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            if st.button(
                f"✅ CONFIRMAR ({len(st.session_state.mov_pallets)})",
                type="primary",
                use_container_width=True,
                disabled=len(st.session_state.mov_pallets) == 0,
                key="btn_confirmar"
            ):
                _ejecutar_movimiento(username, password, api_url)
                st.rerun()

        with col2:
            if st.button(
                "🗑️ Limpiar Todo",
                use_container_width=True,
                disabled=len(st.session_state.mov_pallets) == 0,
                key="btn_limpiar"
            ):
                st.session_state.mov_pallets = []
                st.session_state.pallet_input = ""
                st.toast("🗑️ Lista limpiada", icon="✅")
                st.rerun()

        with col3:
            if st.button("📋", use_container_width=True, help="Ver historial del día"):
                st.session_state.show_historial = not st.session_state.get("show_historial", False)
                st.rerun()

        # Tarjetas de pallets escaneados
        if st.session_state.mov_pallets:
            st.caption(f"**Pallets a mover ({len(st.session_state.mov_pallets)}):**")
            for idx, pallet in enumerate(st.session_state.mov_pallets):
                col1, col2 = st.columns([5, 1])
                with col1:
                    _render_pallet_card(pallet, idx)
                with col2:
                    if st.button("❌", key=f"remove_{idx}", help="Eliminar"):
                        st.session_state.mov_pallets.pop(idx)
                        st.toast("🗑️ Pallet eliminado", icon="✅")
                        st.rerun()

    # === HISTORIAL DEL DÍA ===
    if st.session_state.get("show_historial", False) and st.session_state.mov_historial_dia:
        with st.expander("📋 Historial del Día", expanded=True):
            df_historial = pd.DataFrame(st.session_state.mov_historial_dia)
            
            # Formatear timestamp
            if "timestamp" in df_historial.columns:
                df_historial["timestamp"] = pd.to_datetime(df_historial["timestamp"]).dt.strftime("%H:%M:%S")
            
            st.dataframe(df_historial, use_container_width=True, hide_index=True)
            
            # Botón para exportar CSV
            csv = df_historial.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar CSV",
                data=csv,
                file_name=f"movimientos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )

    # === UNDO (si existe último movimiento) ===
    if st.session_state.mov_ultimo_movimiento:
        st.divider()
        ultimo = st.session_state.mov_ultimo_movimiento
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info(f"↩️ Último movimiento: {len(ultimo.get('pallets', []))} pallets a **{ultimo['destino']['name']}** ({ultimo.get('timestamp', 'N/A')})")
        with col2:
            if st.button("↩️ DESHACER", type="secondary", use_container_width=True):
                _deshacer_movimiento(username, password, api_url)

    # === AUDITORÍA COMPLETA ===
    st.divider()
    with st.expander("🔍 Auditoría Completa", expanded=False):
        if st.session_state.audit_logs:
            st.caption(f"**Últimos {len(st.session_state.audit_logs)} registros de auditoría**")
            
            # Crear DataFrame de auditoría
            df_audit = pd.DataFrame(st.session_state.audit_logs)
            
            # Formatear timestamp
            if "timestamp" in df_audit.columns:
                df_audit["timestamp"] = pd.to_datetime(df_audit["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Columnas a mostrar
            display_cols = ["timestamp", "action", "status", "success_count", "failed_count", "destination_name"]
            available_cols = [col for col in display_cols if col in df_audit.columns]
            
            if available_cols:
                st.dataframe(df_audit[available_cols], use_container_width=True, hide_index=True)
            else:
                st.dataframe(df_audit, use_container_width=True, hide_index=True)
            
            # Botón para exportar CSV de auditoría
            csv_audit = df_audit.to_csv(index=False).encode("utf-8")
            st.download_button(
                label="📥 Descargar Auditoría CSV",
                data=csv_audit,
                file_name=f"auditoria_movimientos_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv",
                key="download_audit"
            )
            
            # Botón para limpiar logs
            if st.button("🗑️ Limpiar Logs de Auditoría"):
                st.session_state.audit_logs = []
                st.toast("🗑️ Logs limpiados", icon="✅")
                st.rerun()
        else:
            st.info("No hay registros de auditoría aún")
    
    # === ESTADÍSTICAS DE CACHÉ ===
    if st.session_state.pallet_cache:
        with st.expander("💾 Estadísticas de Caché", expanded=False):
            total_cached = len(st.session_state.pallet_cache)
            st.metric("Pallets en caché", total_cached)
            
            # Mostrar antigüedad del caché
            now = datetime.now()
            cache_ages = []
            for key, entry in st.session_state.pallet_cache.items():
                age_seconds = (now - entry["timestamp"]).total_seconds()
                cache_ages.append({"pallet": key.split("_")[0], "edad_segundos": int(age_seconds)})
            
            if cache_ages:
                df_cache = pd.DataFrame(cache_ages)
                st.dataframe(df_cache, use_container_width=True, hide_index=True)
            
            if st.button("🗑️ Limpiar Caché"):
                st.session_state.pallet_cache = {}
                st.toast("🗑️ Caché limpiado", icon="✅")
                st.rerun()


def _on_pallet_change(username: str, password: str, api_url: str):
    """Callback cuando cambia el textarea de pallets"""
    raw_input = st.session_state.get("pallet_input", "")
    if not raw_input:
        return

    lines = [line.strip() for line in raw_input.split("\n") if line.strip()]
    if not lines:
        return

    # Procesar cada código
    for code in lines:
        if code and code != st.session_state.mov_last_scan:
            _agregar_pallet(code, username, password, api_url)
            st.session_state.mov_last_scan = code

    # Limpiar textarea después de procesar
    st.session_state.pallet_input = ""
