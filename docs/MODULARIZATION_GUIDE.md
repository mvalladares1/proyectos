# Guía de Modularización de Páginas Streamlit

## Objetivo

Extraer el contenido de cada tab en archivos separados para mejorar:
- **Mantenibilidad**: Archivos más pequeños y enfocados
- **Testabilidad**: Funciones aisladas más fáciles de probar
- **Colaboración**: Múltiples desarrolladores pueden trabajar sin conflictos
- **Reutilización**: Componentes compartidos entre páginas

---

## Estructura Propuesta

```
pages/
├── 1_Recepciones.py          # Archivo principal (orquestador)
├── recepciones/              # Módulo por página
│   ├── __init__.py
│   ├── shared.py             # Funciones compartidas del módulo
│   ├── tab_kpis.py           # Contenido del tab KPIs
│   ├── tab_gestion.py        # Contenido del tab Gestión
│   ├── tab_curva.py          # Contenido del tab Curva
│   └── tab_aprobaciones.py   # Contenido del tab Aprobaciones
├── 2_Produccion.py
├── produccion/
│   ├── __init__.py
│   ├── shared.py
│   ├── tab_reporteria.py
│   └── tab_detalle.py
...
```

---

## Patrón de Implementación

### 1. Módulo Shared (`pages/recepciones/shared.py`)

```python
"""
Módulo compartido para Recepciones.
Contiene funciones de utilidad, formateo y llamadas a API.
"""
import streamlit as st
import pandas as pd
import requests
import os

API_URL = os.getenv("API_URL", "http://127.0.0.1:8000")

def fmt_numero(valor, decimales=0):
    """Formatea número con punto de miles (formato chileno)."""
    if valor is None or (isinstance(valor, float) and pd.isna(valor)):
        return "0"
    try:
        if decimales > 0:
            formatted = f"{valor:,.{decimales}f}"
        else:
            formatted = f"{valor:,.0f}"
        return formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return str(valor)

@st.cache_data(ttl=120)
def fetch_data(endpoint: str, username: str, password: str, **params):
    """Función genérica para llamadas a la API."""
    try:
        response = requests.get(
            f"{API_URL}{endpoint}",
            params={"username": username, "password": password, **params},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error al cargar datos: {e}")
        return None

def init_session_state():
    """Inicializa variables de session_state para el módulo."""
    defaults = {
        'recepciones_kpis_data': None,
        'recepciones_gestion_data': None,
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default
```

### 2. Archivo de Tab (`pages/recepciones/tab_kpis.py`)

```python
"""
Tab: KPIs y Calidad
"""
import streamlit as st
from datetime import datetime, timedelta
from .shared import fmt_numero, fetch_data

def render(username: str, password: str):
    """Renderiza el contenido del tab."""
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        fecha_inicio = st.date_input("Fecha inicio", key="recepciones_kpi_fecha_ini")
    with col2:
        fecha_fin = st.date_input("Fecha fin", key="recepciones_kpi_fecha_fin")
    
    if st.button("🔄 Consultar", key="recepciones_kpi_btn"):
        data = fetch_data("/api/v1/recepciones/kpis", username, password)
        st.session_state.recepciones_kpis_data = data
    
    data = st.session_state.get('recepciones_kpis_data')
    if data:
        _render_metrics(data)

def _render_metrics(data: dict):
    """Renderiza métricas (función auxiliar privada)."""
    cols = st.columns(4)
    with cols[0]:
        st.metric("Total", fmt_numero(data.get('total', 0)))
```

### 3. Archivo Principal Refactorizado

```python
"""
Recepciones de Materia Prima (MP)
"""
import streamlit as st
from shared.auth import proteger_modulo, get_credenciales, tiene_acceso_pagina
from recepciones import shared, tab_kpis, tab_gestion, tab_curva, tab_aprobaciones

st.set_page_config(page_title="Recepciones", page_icon="📥", layout="wide")

if not proteger_modulo("recepciones"):
    st.stop()

username, password = get_credenciales()
shared.init_session_state()

st.title("📥 Recepciones de Materia Prima")

# Permisos
_perm_kpis = tiene_acceso_pagina("recepciones", "kpis_calidad")
_perm_gestion = tiene_acceso_pagina("recepciones", "gestion_recepciones")

# Tabs
tabs = st.tabs(["📊 KPIs", "📋 Gestión", "📈 Curva", "📥 Aprobaciones"])

with tabs[0]:
    if _perm_kpis:
        tab_kpis.render(username, password)
    else:
        st.error("🚫 Acceso Restringido")
```

---

## Consideraciones Importantes

### Session State Keys
Usar prefijos únicos: `recepciones_kpis_data`, no `data`

### Widget Keys  
Usar prefijos únicos: `recepciones_kpi_fecha_inicio`, no `fecha`

### Imports
Usar imports relativos dentro del módulo: `from .shared import fetch_data`

---

## Proceso de Migración (por tab)

1. Crear directorio `pages/modulo/`
2. Crear `__init__.py` vacío
3. Crear `shared.py` con funciones comunes
4. Crear `tab_nombre.py` con función `render()`
5. Mover código del tab
6. Ajustar imports y keys
7. Probar
8. Repetir para cada tab

---

## Tiempo Estimado

| Página | Tabs | Tiempo |
|--------|------|--------|
| Stock | 3 | 2-3h |
| Compras | 2 | 1-2h |
| Producción | 2 | 1-2h |
| Automatizaciones | 2 | 1-2h |
| Finanzas | 5 | 3-4h |
| Recepciones | 4 | 3-4h |

**Total: ~12-17 horas**

---

## Priorización Recomendada

1. Stock (más simple)
2. Compras
3. Producción  
4. Automatizaciones
5. Finanzas
6. Recepciones (el más complejo)
