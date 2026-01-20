"""
Helper para tab de análisis de compras
"""
import requests
import streamlit as st
import os


def get_compras_data(username: str, password: str, fecha_desde: str, fecha_hasta: str):
    """
    Obtiene datos de análisis de compras desde API.
    
    Args:
        username: Usuario Odoo
        password: API key Odoo
        fecha_desde: Fecha inicio (YYYY-MM-DD)
        fecha_hasta: Fecha fin (YYYY-MM-DD)
    
    Returns:
        dict con datos de compras
    """
    try:
        # Intentar obtener API_URL de secrets, si no existe usar variable de entorno
        try:
            API_URL = st.secrets.get("API_URL", os.getenv("API_URL", "http://localhost:8000"))
        except:
            API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        response = requests.get(
            f"{API_URL}/api/v1/rendimiento/analisis-compras",
            params={
                "username": username,
                "password": password,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error HTTP {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"error": str(e)}


def get_ventas_data(username: str, password: str, fecha_desde: str, fecha_hasta: str):
    """
    Obtiene datos de análisis de ventas desde API.
    
    Args:
        username: Usuario Odoo
        password: API key Odoo
        fecha_desde: Fecha inicio (YYYY-MM-DD)
        fecha_hasta: Fecha fin (YYYY-MM-DD)
    
    Returns:
        dict con datos de ventas
    """
    try:
        try:
            API_URL = st.secrets.get("API_URL", os.getenv("API_URL", "http://localhost:8000"))
        except:
            API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        response = requests.get(
            f"{API_URL}/api/v1/rendimiento/analisis-ventas",
            params={
                "username": username,
                "password": password,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error HTTP {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"error": str(e)}


def get_produccion_data(username: str, password: str, fecha_desde: str, fecha_hasta: str):
    """
    Obtiene datos de análisis de producción desde API.
    
    Args:
        username: Usuario Odoo
        password: API key Odoo
        fecha_desde: Fecha inicio (YYYY-MM-DD)
        fecha_hasta: Fecha fin (YYYY-MM-DD)
    
    Returns:
        dict con datos de producción
    """
    try:
        try:
            API_URL = st.secrets.get("API_URL", os.getenv("API_URL", "http://localhost:8000"))
        except:
            API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        response = requests.get(
            f"{API_URL}/api/v1/rendimiento/analisis-produccion",
            params={
                "username": username,
                "password": password,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error HTTP {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"error": str(e)}


def get_inventario_rotacion_data(username: str, password: str, fecha_desde: str, fecha_hasta: str):
    """
    Obtiene datos de análisis de inventario y rotación desde API.
    
    Args:
        username: Usuario Odoo
        password: API key Odoo
        fecha_desde: Fecha inicio (YYYY-MM-DD)
        fecha_hasta: Fecha fin (YYYY-MM-DD)
    
    Returns:
        dict con datos de inventario
    """
    try:
        try:
            API_URL = st.secrets.get("API_URL", os.getenv("API_URL", "http://localhost:8000"))
        except:
            API_URL = os.getenv("API_URL", "http://localhost:8000")
        
        response = requests.get(
            f"{API_URL}/api/v1/rendimiento/analisis-inventario",
            params={
                "username": username,
                "password": password,
                "fecha_desde": fecha_desde,
                "fecha_hasta": fecha_hasta
            },
            timeout=120
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"Error HTTP {response.status_code}: {response.text}"}
    
    except Exception as e:
        return {"error": str(e)}
