"""
Módulo compartido para Reconciliación y Trigger de ODFs.
Contiene funciones de utilidad, llamadas a API y configuración.
"""
import streamlit as st
import requests
import os
from typing import Dict, List, Optional
from datetime import datetime

# Determinar API_URL basado en ENV
ENV = os.getenv("ENV", "prod")
if ENV == "development":
    API_URL = "http://127.0.0.1:8002"
else:
    API_URL = "http://127.0.0.1:8000"

API_RECONCILIACION = f"{API_URL}/api/v1/produccion-reconciliacion"
API_ODF_RECONCILIACION = f"{API_URL}/api/v1/odf-reconciliation"


def init_session_state_reconciliacion():
    """Inicializa el estado de la sesión para reconciliación."""
    if 'recon_odfs_multi_so' not in st.session_state:
        st.session_state['recon_odfs_multi_so'] = []
    if 'recon_odf_seleccionada' not in st.session_state:
        st.session_state['recon_odf_seleccionada'] = None


def init_session_state_trigger():
    """Inicializa el estado de la sesión para trigger."""
    if 'trigger_odfs_pendientes' not in st.session_state:
        st.session_state['trigger_odfs_pendientes'] = []
    if 'trigger_total_pendientes' not in st.session_state:
        st.session_state['trigger_total_pendientes'] = 0
    if 'trigger_log_lines' not in st.session_state:
        st.session_state['trigger_log_lines'] = []
    if 'trigger_odfs_kg' not in st.session_state:
        st.session_state['trigger_odfs_kg'] = []


def get_api_headers() -> Dict[str, str]:
    """Retorna headers para autenticación API."""
    return {"X-API-Key": st.session_state.get('api_key', '')}


# ============================================================================
# FUNCIONES PARA TRIGGER SO ASOCIADA
# ============================================================================

def buscar_odfs_sin_so(
    fecha_inicio: str,
    fecha_fin: str,
    limit: int
) -> Dict:
    """Busca ODFs sin SO Asociada."""
    try:
        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "limit": limit
        }
        
        response = requests.get(
            f"{API_ODF_RECONCILIACION}/odfs-sin-so-asociada",
            params=params,
            headers=get_api_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": f"Error {response.status_code}: {response.text}",
                "total": 0,
                "odfs": []
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total": 0,
            "odfs": []
        }


def trigger_odf_individual(odf_id: int, wait_seconds: float) -> Dict:
    """Triggea SO Asociada para un ODF."""
    try:
        response = requests.post(
            f"{API_ODF_RECONCILIACION}/trigger-so-asociada/{odf_id}",
            params={"wait_seconds": wait_seconds},
            headers=get_api_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json() if response.text else {}
            return {
                "success": False,
                "error": error_data.get('detail', response.text)
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def add_log(line: str, tipo: str = "info"):
    """Agrega línea al log."""
    timestamp = datetime.now().strftime("%H:%M:%S")
    emoji = "ℹ️" if tipo == "info" else "✅" if tipo == "success" else "❌"
    st.session_state['trigger_log_lines'].append(f"[{timestamp}] {emoji} {line}")


def get_log_text(max_lines: int = 30) -> str:
    """Retorna texto del log."""
    lines = st.session_state.get('trigger_log_lines', [])
    return "\n".join(lines[-max_lines:])


def clear_log():
    """Limpia el log."""
    st.session_state['trigger_log_lines'] = []


# ============================================================================
# FUNCIONES PARA RECONCILIACIÓN KG
# ============================================================================

def buscar_odfs_para_reconciliar(
    fecha_inicio: str,
    fecha_fin: str,
    limit: int
) -> Dict:
    """Busca ODFs que necesitan reconciliación de KG."""
    try:
        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "limit": limit
        }
        
        # Por ahora usamos el mismo endpoint, pero podríamos crear uno específico
        response = requests.get(
            f"{API_ODF_RECONCILIACION}/odfs-sin-so-asociada",
            params=params,
            headers=get_api_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": f"Error {response.status_code}",
                "total": 0,
                "odfs": []
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "total": 0,
            "odfs": []
        }


def preview_reconciliacion_odf(odf_id: int) -> Dict:
    """Preview de reconciliación sin escribir."""
    try:
        response = requests.get(
            f"{API_ODF_RECONCILIACION}/odf/{odf_id}/preview",
            headers=get_api_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def reconciliar_odf_kg(odf_id: int, dry_run: bool = False) -> Dict:
    """Reconcilia KG de un ODF."""
    try:
        response = requests.post(
            f"{API_ODF_RECONCILIACION}/odf/{odf_id}/reconciliar",
            params={"dry_run": dry_run},
            headers=get_api_headers(),
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {
                "success": False,
                "error": response.text
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
