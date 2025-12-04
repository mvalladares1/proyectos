# Estructura del Proyecto - Rio Futuro Dashboards

Este documento describe la estructura del repositorio `rio-futuro-dashboards`, la forma en que los dashboards se organizan, los endpoints del backend y el modo recomendado de desplegar y añadir nuevos dashboards.

**Última actualización:** 4 de Diciembre 2025

---

## 1. Resumen General

| Componente | Tecnología | Puerto |
|------------|------------|--------|
| Frontend | Streamlit | 8501 |
| Backend | FastAPI + Uvicorn | 8000 |
| Base de datos | Odoo (XML-RPC) | - |
| Servidor | debian@167.114.114.51 | - |

---

## 2. Estructura de Carpetas

```
rio-futuro-dashboards/
├── .env                          # Variables de entorno (Odoo credentials, API config)
├── .streamlit/config.toml        # Configuración Streamlit
├── Home.py                       # Página principal del dashboard
├── requirements.txt              # Dependencias Python
├── DASHBOARD_STRUCTURE.md        # Este archivo
├── PAGES.md                      # Guía para agregar páginas
│
├── backend/                      # API FastAPI
│   ├── main.py                   # Entry point - registro de routers y CORS
│   ├── config/
│   │   └── settings.py           # Configuración desde .env
│   ├── routers/                  # Endpoints organizados por feature
│   │   ├── auth.py               # Autenticación
│   │   ├── produccion.py         # /api/v1/produccion/*
│   │   ├── bandejas.py           # /api/v1/bandejas/*
│   │   ├── stock.py              # /api/v1/stock/*
│   │   ├── containers.py         # /api/v1/containers/*
│   │   └── demo.py               # /api/v1/example (pruebas)
│   ├── services/                 # Lógica de negocio + conexión Odoo
│   │   ├── produccion_service.py # Consultas OFs, componentes, subproductos
│   │   ├── bandejas_service.py
│   │   ├── stock_service.py
│   └── tests/
│       └── test_demo.py
│
├── pages/                        # Páginas Streamlit (cada archivo = un dashboard)
│   ├── 1_📦_Produccion.py        # Dashboard de Órdenes de Fabricación
│   ├── 2_📊_Bandejas.py          # Dashboard de Bandejas
│   ├── 3_📦_Stock.py             # Dashboard de Stock
│   └── 4_🚢_Containers.py        # Dashboard de Containers
│
├── shared/                       # Módulos compartidos
│   ├── auth.py                   # proteger_pagina(), get_credentials()
│   ├── constants.py              # Constantes globales
│   └── odoo_client.py            # Cliente XML-RPC para Odoo
│
└── scripts/
    └── deploy-and-verify.sh      # Script de deploy automatizado
```

---

## 3. Configuración (.env)

```env
ODOO_URL=https://riofuturo.server98c6e.oerpondemand.net
ODOO_DB=riofuturo-master
ODOO_USER=usuario@riofuturo.cl
ODOO_PASSWORD=api_key_odoo
API_URL=http://127.0.0.1:8000
API_HOST=0.0.0.0
API_PORT=8000
```

---

## 4. Backend (FastAPI)

### Endpoints Principales

| Endpoint | Método | Descripción |
|----------|--------|-------------|

| `/api/v1/produccion/of/{of_name}` | GET | Detalle de una OF |
| `/api/v1/produccion/of/{of_name}/componentes` | GET | Componentes de la OF |
| `/api/v1/produccion/of/{of_name}/subproductos` | GET | Subproductos de la OF |
| `/api/v1/bandejas/...` | GET | Endpoints de bandejas |
| `/api/v1/stock/...` | GET | Endpoints de stock |
| `/api/v1/containers/...` | GET | Endpoints de containers |

### Agregar Nuevo Endpoint

1. Crear `backend/routers/<nombre>.py`
2. Crear `backend/services/<nombre>_service.py`
3. Registrar en `backend/main.py`:
   ```python
   from backend.routers import nuevo_router
   app.include_router(nuevo_router.router, prefix="/api/v1")
   ```

---

## 5. Frontend (Streamlit)

### Estructura de una Página

```python
"""
Descripción del dashboard (usada por Home.py)
"""
import streamlit as st

st.set_page_config(
    page_title="Nombre Dashboard",
    page_icon="📊",
    layout="wide"
)

# Proteger página (opcional)
from shared.auth import proteger_pagina
proteger_pagina()

# Contenido del dashboard...
```

### Agregar Nueva Página

1. Crear `pages/N_📊_NombreDashboard.py`
2. Agregar docstring y `st.set_page_config`
3. Implementar UI con Streamlit
4. Actualizar `PAGES.md`

---

## 6. Despliegue

### URLs de Producción

| Servicio | URL |
|----------|-----|
| GitHub | https://github.com/mvalladares1/proyectos.git |
| Dashboard | http://167.114.114.51:8501 |
| API | http://167.114.114.51:8000 |

### Servicios Systemd

- `rio-futuro-api` → Backend FastAPI (puerto 8000)
- `rio-futuro-web` → Frontend Streamlit (puerto 8501)

### Ruta en Servidor

```
/home/debian/rio-futuro-dashboards/app/
```

---

## 7. Comandos de Deploy

### Subir a Git (desde Windows PowerShell)

```powershell
cd "c:\new\RIO FUTURO\DASHNBOARDS\rio-futuro-dashboards"
git add -A
git commit -m "Descripcion de los cambios"
git pull origin main --rebase
git push origin main
```

### Subir al Servidor

```powershell
# Subir archivos modificados
scp -r pages backend debian@167.114.114.51:/home/debian/rio-futuro-dashboards/app/

# Reiniciar servicios
ssh debian@167.114.114.51 "sudo systemctl restart rio-futuro-api rio-futuro-web"
```

### Verificar Estado

```bash
ssh debian@167.114.114.51 "sudo systemctl status rio-futuro-api rio-futuro-web"
```

### Ver Logs

```bash
# Logs del backend
ssh debian@167.114.114.51 "sudo journalctl -u rio-futuro-api -n 100 -f"

# Logs del frontend
ssh debian@167.114.114.51 "sudo journalctl -u rio-futuro-web -n 100 -f"
```

---

## 8. Desarrollo Local

### Iniciar Backend

```bash
cd rio-futuro-dashboards
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

### Iniciar Frontend

```bash
cd rio-futuro-dashboards
streamlit run Home.py --server.port 8501
```

### Ejecutar Tests

```bash
cd rio-futuro-dashboards/backend
pytest -q
```

---

## 9. Troubleshooting

### Error 404 en endpoint
1. Verificar que el router está registrado en `backend/main.py`
2. Reiniciar servicio: `sudo systemctl restart rio-futuro-api`
3. Ver logs: `sudo journalctl -u rio-futuro-api -n 200`

### Uvicorn no arranca
1. Verificar dependencias: `pip install -r requirements.txt`
2. Verificar `.env` tiene todas las variables
3. Ver traceback en logs

### Streamlit no carga
1. Verificar `API_URL` en `.env`
2. Verificar que backend está corriendo
3. Ver logs: `sudo journalctl -u rio-futuro-web -n 200`

---

## 10. Notas Importantes

- **Rendimiento en Producción:** Se calcula como `kg_out / kg_in * 100` donde:
  - `kg_in` = Componentes con categoría "PRODUCTOS" (solo fruta, no insumos)
  - `kg_out` = Subproductos excluyendo categorías "PROCESOS" y "MERMA"

- **Precio Unitario:** Usa campo `x_studio_precio_unitario` de `stock.move.line`

- **Formato Fechas:** DD/MM/YYYY (día/mes/año)

---

*Documento actualizado el 4 de Diciembre 2025*
