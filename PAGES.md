# Guía para Agregar Páginas

## Convención de Nombres

Los archivos de páginas siguen el patrón: `N_Nombre.py`
- `N` = número de orden (1-9)
- `Nombre` = nombre del dashboard en PascalCase

**Ejemplo:** `1_Recepciones.py`, `2_Produccion.py`

Los iconos se inyectan via CSS en `Home.py`, no en los nombres de archivo.

---

## Estructura Mínima de una Página

```python
"""
Descripción breve del dashboard (usada por Home.py)
"""
import streamlit as st
from shared.auth import proteger_pagina, get_credenciales

st.set_page_config(page_title="Nombre", page_icon="📊", layout="wide")

if not proteger_pagina():
    st.stop()

username, password = get_credenciales()

st.title("📊 Nombre del Dashboard")
# ... contenido
```

---

## Checklist para Nuevo Dashboard

1. [ ] Crear archivo `pages/N_Nombre.py`
2. [ ] Agregar docstring con descripción
3. [ ] Configurar `st.set_page_config`
4. [ ] Agregar autenticación (`proteger_pagina`)
5. [ ] Si necesita API: crear router en `backend/routers/`
6. [ ] Si necesita servicio: crear en `backend/services/`
7. [ ] Actualizar `Home.py` con el slug en `DASHBOARD_CATEGORIES`
8. [ ] Agregar icono CSS en `Home.py` (sección sidebar)
9. [ ] Commit, push y deploy

---

## Dashboards Actuales

| Archivo | Título | Icono |
|---------|--------|-------|
| `1_Recepciones.py` | Recepciones | 📥 |
| `2_Produccion.py` | Producción | 🏭 |
| `3_Bandejas.py` | Bandejas | 📊 |
| `4_Stock.py` | Stock | 📦 |
| `5_Containers.py` | Containers | 🚢 |
| `6_Finanzas.py` | Finanzas | 💰 |
| `9_Permisos.py` | Permisos | ⚙️ |

---

*Actualizado: 11 de Diciembre 2025*
