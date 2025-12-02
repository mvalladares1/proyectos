Standard for adding Streamlit dashboard pages

To allow the `Home.py` to automatically discover and render new dashboards, pages should follow this simple pattern:

1) Add a top-level docstring at the beginning of the file (first triple-quoted string) with a short description of the dashboard. Example:

"""
Dashboard de Producción - Órdenes de Fabricación
"""

2) Use `st.set_page_config` to set `page_title` and `page_icon`:

st.set_page_config(page_title='Producción', page_icon='📦')

3) Ensure the file is placed under `pages/` and ends with `.py`. The `Home.py` will scan that folder and create a card for each page automatically using these metadata values.

Optional: You can add a YAML or comment block with additional fields in the future; the current auto-discovery uses the docstring and `set_page_config` call.

Prompt template to request a new dashboard (for developers or ChatGPT):

```
Crear un nuevo dashboard llamado "<NOMBRE>" con icono "<EMOJI>" y la descripción breve: "<Descripción corta>".

Detalle de los requerimientos:
- API Backend: endpoint(s) principales a usar (por ejemplo `/api/v1/mi_endpoint`)
- Filtros requeridos: lista (fechas, estado, sucursal, etc.)
- KPI o métricas principales: enumerar
- Tablas / Gráficos requeridos: especificar tipos (tabla, pie, bar, line, gauge)
- Exportación: CSV / XLS / PDF (si aplica)

Ejemplo:
Crear un nuevo dashboard llamado "Empaques" con icono "📦". Debe mostrar:
- KPI: total empaques hoy, empaques por operador
- Filtros: rango de fecha, sala, operador
- Tabla: registros con columnas [id, producto, kg, operador, fecha]
- Gráficos: barras por producto, gauge de cumplimiento
```

Checklist para agregar un nuevo dashboard (resumen):
1. Crear archivo en `pages/` con nombre `N_EMOJI_Nombre.py` (ej: `5_🧪_Insights.py`).
2. Añadir docstring (triple-quoted) con la descripción del dashboard.
3. Add `st.set_page_config(page_title="Nombre", page_icon="EMOJI")` at the top.
4. Llamadas API: usar cache `@st.cache_data(ttl=300)` para llamadas pesadas.
5. Protección: `from shared.auth import proteger_pagina` y `if not proteger_pagina(): st.stop()`.
6. Agregar el archivo al repo, commit y push.
7. Pull en el servidor y reiniciar `rio-futuro-web` (ya automatizado):
```
cd /home/debian/rio-futuro-dashboards/app
git pull origin main
sudo systemctl restart rio-futuro-web
```
   
Si quieres hacer un deploy rápido y comprobar el endpoint demo, puedes ejecutar el script `scripts/deploy-and-verify.sh` del repo (ajusta la ruta si es necesario):
```bash
sudo bash scripts/deploy-and-verify.sh
```

También puedes ejecutar las pruebas unitarias localmente para verificar que el endpoint existe (útil para CI):
```bash
cd backend
pytest -q
```

Notas adicionales:
- Para imágenes/activos, colócalos en `pages/assets/` y usa rutas relativas o `st.image`.
- Si el dashboard requiere endpoints backend nuevos, crea `backend/routers/<nombre>.py` y `backend/services/<nombre>_service.py` y registra la ruta en `backend/main.py`.
- Para permisos o roles, puedes añadir metadatos en un encabezado comentado y luego extender `shared.auth` para filtrar (opcional).

Ejemplo mínimo (Plantilla) ya se incluyó como `pages/5_🧪_Template.py`.
