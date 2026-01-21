"""
Módulo compartido para Rendimiento/Trazabilidad.
Contiene funciones API y de formateo.
"""
import streamlit as st
import requests
import pandas as pd
import os
from typing import Optional

# Determinar API_URL
# - Si existe API_URL (por docker-compose/nginx), usarlo.
# - Si no, fallback por ENV a localhost.
ENV = os.getenv("ENV", "production")
API_URL = os.getenv("API_URL")
if not API_URL:
    if ENV == "development":
        API_URL = "http://127.0.0.1:8002"  # Puerto DEV
    else:
        API_URL = "http://127.0.0.1:8000"  # Puerto PROD


# --------------------- Funciones de formateo ---------------------

def fmt_numero(valor, decimales=0):
    """Formatea número con punto como miles y coma como decimal (formato chileno)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
        return formatted
    except:
        return str(valor)


# --------------------- Funciones API ---------------------

def get_inventario_data(username: str, password: str, fecha_desde: str, fecha_hasta: str):
    """Obtiene datos de inventario (compras vs ventas) desde el backend."""
    try:
        params = {
            "username": username,
            "password": password,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta
        }
        resp = requests.get(
            f"{API_URL}/api/v1/rendimiento/inventario-trazabilidad",
            params=params,
            timeout=120
        )
        resp.raise_for_status()
        data = resp.json()
        data['error'] = None
        return data
    except Exception as e:
        return {
            'fecha_desde': '',
            'fecha_hasta': '',
            'total_comprado_kg': 0,
            'total_comprado_monto': 0,
            'total_vendido_kg': 0,
            'total_vendido_monto': 0,
            'detalle': [],
            'error': f"Error llamando al backend: {str(e)}"
        }


def get_trazabilidad_inversa(username: str, password: str, lote_pt: str):
    """Obtiene trazabilidad inversa desde PT hacia MP."""
    try:
        params = {"username": username, "password": password}
        resp = requests.get(
            f"{API_URL}/api/v1/rendimiento/trazabilidad-inversa/{lote_pt}",
            params=params,
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()
        return {"error": f"Error HTTP: {resp.status_code}"}
    except Exception as e:
        return {"error": str(e)}


def get_sankey_data(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
):
    """Obtiene datos para diagrama Sankey basado en stock.move.line."""
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
        }
        resp = requests.get(
            f"{API_URL}/api/v1/containers/traceability/sankey",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def get_reactflow_data(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
):
    """Obtiene datos para diagrama React Flow."""
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
        }
        resp = requests.get(
            f"{API_URL}/api/v1/containers/traceability/reactflow",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def get_traceability_raw(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
):
    """Obtiene datos crudos de trazabilidad."""
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
        }
        resp = requests.get(
            f"{API_URL}/api/v1/containers/traceability/data",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


def get_traceability_by_identifier(
    username: str,
    password: str,
    identifier: str,
    output_format: str = "visjs",
    include_siblings: bool = True
):
    """
    Obtiene datos de trazabilidad por identificador (venta o paquete).
    
    Args:
        username: Usuario Odoo
        password: API Key Odoo
        identifier: Venta (ej: S00574) o Paquete (ej: PACK0014448)
        output_format: 'visjs' (network) o 'sankey'
        include_siblings: True = todos los pallets del proceso, False = solo cadena directa
    """
    try:
        params = {
            "username": username,
            "password": password,
            "identifier": identifier,
            "include_siblings": str(include_siblings).lower(),
        }
        endpoint = f"{API_URL}/api/v1/containers/traceability/by-identifier/{output_format}"
        resp = requests.get(endpoint, params=params, timeout=120)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None


@st.cache_data(ttl=300)
def get_sankey_producers(
    username: str,
    password: str,
    fecha_inicio: str,
    fecha_fin: str,
    partner_id: Optional[int] = None,
    limit: int = 50,
):
    """Lista productores disponibles (desde pallets IN) para el rango/cliente."""
    try:
        params = {
            "username": username,
            "password": password,
            "start_date": fecha_inicio,
            "end_date": fecha_fin,
            "limit": limit
        }
        if partner_id:
            params["partner_id"] = partner_id
        resp = requests.get(
            f"{API_URL}/api/v1/containers/sankey/producers",
            params=params,
            timeout=120
        )
        if resp.status_code == 200:
            return resp.json() or []
        return []
    except Exception:
        return []


@st.cache_data(ttl=600)
def get_container_partners(username: str, password: str):
    """Lista clientes (partners) que tienen pedidos con fabricaciones."""
    try:
        params = {"username": username, "password": password}
        resp = requests.get(
            f"{API_URL}/api/v1/containers/partners/list",
            params=params,
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json() or []
        return []
    except Exception:
        return []


def get_trazabilidad_pallets(username: str, password: str, pallet_names: list):
    """Obtiene trazabilidad completa de uno o varios pallets."""
    try:
        # DEBUG: Mostrar información de la petición
        url = f"{API_URL}/api/v1/rendimiento/trazabilidad-pallets"
        params = {"username": username, "password": password}
        body = pallet_names  # Lista de nombres de pallets
        
        print(f"🔍 DEBUG - URL: {url}")
        print(f"🔍 DEBUG - Params: {params}")
        print(f"🔍 DEBUG - Body (tipo: {type(body)}): {body}")
        st.info(f"**DEBUG INFO:**\n- URL: `{url}`\n- Pallets: `{body}`")
        
        resp = requests.post(
            url,
            params=params,
            json=body,
            timeout=120
        )
        
        # DEBUG: Mostrar respuesta completa
        print(f"🔍 DEBUG - Status Code: {resp.status_code}")
        print(f"🔍 DEBUG - Response Headers: {dict(resp.headers)}")
        print(f"🔍 DEBUG - Response Text: {resp.text[:500]}")
        
        st.warning(f"**DEBUG RESPONSE:**\n- Status: {resp.status_code}\n- URL Final: {resp.url}\n- Response: {resp.text[:200]}")
        
        if resp.status_code == 200:
            return resp.json()
        
        # Retornar error con detalles
        return {
            "error": f"Error HTTP: {resp.status_code}",
            "url": resp.url,
            "response": resp.text[:500]
        }
    except Exception as e:
        import traceback
        error_detail = traceback.format_exc()
        print(f"🔍 DEBUG - Exception: {error_detail}")
        st.error(f"**DEBUG EXCEPTION:**\n```\n{error_detail}\n```")
        return {"error": str(e), "detail": error_detail}

