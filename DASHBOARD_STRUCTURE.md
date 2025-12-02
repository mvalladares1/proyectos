# Estructura del proyecto - Rio Futuro Dashboards

Este documento describe la estructura del repositorio `rio-futuro-dashboards`, la forma en que los dashboards se organizan, los endpoints del backend y el modo recomendado de desplegar y añadir nuevos dashboards.

## 1. Resumen general
- Frontend: Streamlit (app y páginas en `pages/`)
- Backend: FastAPI (`backend/`)
- Repositorio: unificado (página Home + páginas de dashboards en `pages/` + backend en `backend/`)
- Despliegue: `rio-futuro-api` (FastAPI/uvicorn) en puerto 8000, `rio-futuro-web` (Streamlit) en puerto 8501, nginx hace proxy y sirve `/dashboards/` y `/api/v1/` al backend.

---
## 2. Estructura de carpetas
```
/ (repo raíz)
├─ backend/                # FastAPI app
│  ├─ main.py              # App FastAPI principal y registro de routers
│  ├─ routers/             # Routers (endpoints) organizados por feature
│  │  ├─ auth.py
│  │  ├─ produccion.py
│  │  ├─ bandejas.py
│  │  ├─ containers.py
│  │  ├─ stock.py
│  │  └─ demo.py          # Endpoint demo (ej. /api/v1/example)
│  ├─ services/           # Lógica de negocio por feature
│  └─ config/             # Settings y variables de entorno
├─ pages/                  # Páginas Streamlit (cada archivo es un dashboard)
│  ├─ 1_📦_Produccion.py
│  ├─ 2_📊_Bandejas.py
│  ├─ 3_📦_Stock.py
│  ├─ 4_🚢_Containers.py
│  └─ 5_🧪_Template.py     # (mantiene placeholder para histórico / no mostrar)
├─ scripts/                # Helpers y scripts de deploy/verify
│  └─ deploy-and-verify.sh
├─ shared/                 # Módulos compartidos (auth, odoo client, constants)
└─ PAGES.md                # Guía para contribuir y agregar dashboards
```

---
## 3. Backend (FastAPI)
- `backend/main.py` registra los routers y configura CORS.
- Routers importantes:
  - `auth.router` → Autenticación
  - `produccion.router` → Endpoints relacionados con OFs (producción)
  - `bandejas.router` → Endpoints de bandejas
  - `stock.router` → Endpoints de stock
  - `containers.router` → Endpoints de containers
  - `demo.router` → Ejemplo: `GET /api/v1/example` (útil para plantillas)

- Buenas prácticas:
  - Añadir nuevos endpoints creando `backend/routers/<nombre>.py` y el correspondiente `backend/services`.
  - Registrar el nuevo router en `backend/main.py` y en `backend/routers/__init__.py` si lo deseas.
  - Usar `@app.get('/api/v1/...')` y prefijo de API versión `/api/v1/`.

---
## 4. Frontend (Streamlit)
- `Home.py`: descubre automáticamente las páginas en `pages/` leyendo docstrings y `st.set_page_config` con metadata (page_title, page_icon).
- Cada dashboard es un archivo en `pages/` con:
  - Docstring en la cabecera con una descripción (usada por el Home para mostrar tarjeta)
  - `st.set_page_config(page_title, page_icon)`
  - Opcional: protección `shared.auth.proteger_pagina()` y obtención de credenciales.

---
## 5. Añadir un nuevo dashboard (pasos rápidos)
1. Crear un archivo `pages/N_<Name>.py` con la docstring y `st.set_page_config`.
2. Implementar la UI y guardarla en `pages/`.
3. Si necesitas endpoints backend: crear `backend/routers/<name>.py` + `backend/services/<name>_service.py` y registrarlo en `backend/main.py`.
4. Actualizar `PAGES.md` con instrucciones de metadata y ejemplo si corresponde.
5. Commit, push y desplegar en el servidor; reiniciar `rio-futuro-api` y `rio-futuro-web`.

---
## 6. Despliegue y servicios
- Systemd units (nombre):
  - `rio-futuro-api` → backend (uvicorn). Comprueba `ExecStart` y `WorkingDirectory` para apuntar a la virtualenv y path correctos.
  - `rio-futuro-web` → frontend (streamlit) → puerto 8501.
- Puertos: 8000 backend, 8501 frontend.
- Nginx: proxy inverso; rutas importantes:
  - `/dashboards/` → Streamlit 8501
  - `/api/v1/` → FastAPI 8000
  - `/cargas` → Laravel / PHP-FPM

---
## 7. Comprobaciones y troubleshooting rápidas
- Si un endpoint devuelva 404 en front (Streamlit):
  - Verifica que el backend tiene la ruta (git pull y confirmar en `backend/routers`).
  - Reinicia `rio-futuro-api` y mira logs: `sudo journalctl -u rio-futuro-api -n 200`.
  - Asegúrate de que `nginx` proxyee al puerto correcto: `proxy_pass http://127.0.0.1:8000/api/v1/;`.
- Si `uvicorn` no arranca: buscar tracebacks en `journalctl` y confirmar que las dependencias estén instaladas en la venv (revisar `requirements.txt`).

---
## 8. Guía de pruebas locales
- Ejecutar unit tests (backend):
  ```bash
  cd backend
  pytest -q
  ```
- Ejecutar backend localmente:
  ```bash
  uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
  ```
- Ejecutar frontend localmente (Streamlit):
  ```bash
  streamlit run Home.py --server.port 8501
  ```

---
## 9. Notas y seguridad
- No exponer endpoints demo públicamente si retornan datos sensibles.
- Los `st.secrets` deben usarse para `API_URL` y credenciales; en producción, almacenarlos en el usuario que corre streamlit o en `~/.streamlit/secrets.toml` del servicio.
- Mantener backups antes de borrar archivos; usar branches y PRs para cambios importantes.

---
## 10. Contacto y mantenimiento
- Si necesitas que retire algún archivo del repo (por ejemplo, la plantilla completa), comunícamelo y lo hago.
- Si deseas proteger endpoints demo o moverlos a `api/v1/demo/`, dímelo y lo hago también.

---
*Documento generado automáticamente por solicitud del equipo. Para cualquier duda, pega aquí la salida de `git pull` y `systemctl status rio-futuro-api` y te guiaré.*
