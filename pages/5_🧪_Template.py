"""
Template: Nuevo Dashboard - Plantilla

Descripción:
Este archivo es una plantilla mínima para crear un nuevo dashboard. Incluye:
- Docstring al principio con descripción (usada por el Home dinámico)
- `st.set_page_config` con `page_title` y `page_icon`
- Protección de página por autenticación (si la app usa auth)
- Ejemplo mínimo de una llamada a la API con `httpx` y caching
"""

import streamlit as st
import httpx
from shared.auth import get_credenciales, proteger_pagina

# Config de la página
st.set_page_config(page_title="Template", page_icon="🧪", layout="wide")

# Proteger página
if not proteger_pagina():
    st.stop()

username, password = get_credenciales()

st.title("🧪 Plantilla de Dashboard")
st.write("Usa esta plantilla para crear rápidamente un nuevo dashboard y asegúrate de seguir el README / PAGES.md para el estilo y metadatos.")

@st.cache_data(ttl=300)
def fetch_sample_data(username: str, password: str):
    try:
        url = st.secrets.get("API_URL", "http://127.0.0.1:8000")
        resp = httpx.get(f"{url}/api/v1/example", params={"username": username, "password": password}, timeout=10.0)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        # Mostrar advertencia y devolver lista vacía para que el UI pueda usar un fallback
        st.warning("No fue posible cargar datos de ejemplo: " + str(e))
        return []

SAMPLE_FALLBACK = {
    "meta": {"source": "fallback", "count": 3},
    "data": [
        {"id": "F1", "name": "Fallback A", "value": 111, "status": "ok"},
        {"id": "F2", "name": "Fallback B", "value": 222, "status": "ok"},
        {"id": "F3", "name": "Fallback C", "value": 333, "status": "warning"},
    ],
}

if username and password:
    data = fetch_sample_data(username, password)
    if not data:
        st.info("Usando datos de ejemplo locales porque la API no respondió. Verifique que la URL de la API esté correctamente configurada en `st.secrets['API_URL']` o que el backend esté en ejecución.")
        data = SAMPLE_FALLBACK
    st.write(data)
else:
    st.info("Inicia sesión para ver datos de ejemplo.")
