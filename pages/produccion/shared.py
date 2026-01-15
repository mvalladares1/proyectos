"""
Módulo compartido para Trigger SO Asociada.
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

API_ENDPOINT = f"{API_URL}/api/v1/odf-reconciliation"


def init_session_state():
    """Inicializa el estado de la sesión."""
    if 'trigger_odfs_pendientes' not in st.session_state:
        st.session_state['trigger_odfs_pendientes'] = []
    if 'trigger_total_pendientes' not in st.session_state:
        st.session_state['trigger_total_pendientes'] = 0
    if 'trigger_log_lines' not in st.session_state:
        st.session_state['trigger_log_lines'] = []


def get_api_headers() -> Dict[str, str]:
    """Retorna headers para autenticación API."""
    return {"X-API-Key": st.session_state.get('api_key', '')}


def buscar_odfs_pendientes(
    fecha_inicio: str,
    fecha_fin: str,
    limit: int
) -> Dict:
    """
    Busca ODFs que tienen PO Cliente pero no SO Asociada.
    
    Args:
        fecha_inicio: Fecha inicio (YYYY-MM-DD)
        fecha_fin: Fecha fin (YYYY-MM-DD)
        limit: Límite de registros
        
    Returns:
        Diccionario con 'success', 'total' y 'odfs'
    """
    try:
        params = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "limit": limit
        }
        
        response = requests.get(
            f"{API_ENDPOINT}/odfs-sin-so-asociada",
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


def trigger_odf_individual(
    odf_id: int,
    wait_seconds: float
) -> Dict:
    """
    Triggea la automatización para un ODF específico.
    
    Args:
        odf_id: ID del ODF
        wait_seconds: Segundos a esperar entre operaciones
        
    Returns:
        Diccionario con resultado
    """
    try:
        response = requests.post(
            f"{API_ENDPOINT}/trigger-so-asociada/{odf_id}",
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
    """
    Agrega una línea al log.
    
    Args:
        line: Texto del log
        tipo: 'info', 'success' o 'error'
    """
    timestamp = datetime.now().strftime("%H:%M:%S")
    emoji = "ℹ️" if tipo == "info" else "✅" if tipo == "success" else "❌"
    st.session_state['trigger_log_lines'].append(f"[{timestamp}] {emoji} {line}")


def get_log_text(max_lines: int = 30) -> str:
    """Retorna el texto del log (últimas N líneas)."""
    lines = st.session_state.get('trigger_log_lines', [])
    return "\n".join(lines[-max_lines:])


def clear_log():
    """Limpia el log."""
    st.session_state['trigger_log_lines'] = []


def format_odf_info(odf: Dict) -> str:
    """Formatea información de un ODF para mostrar."""
    product_name = odf.get('product_id', ['N/A'])[1] if isinstance(odf.get('product_id'), list) else 'N/A'
    return f"""
**ID:** {odf['id']}  
**Producto:** {product_name}  
**Estado:** {odf.get('state', 'N/A')}  
**Fecha:** {odf.get('date_planned_start', 'N/A')[:10]}  
**PO Cliente:** {odf.get('x_studio_po_cliente_1', 'N/A')}
"""
