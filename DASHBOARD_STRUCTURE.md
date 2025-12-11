# Estructura del Proyecto - Rio Futuro Dashboards

Este documento describe la estructura del repositorio `rio-futuro-dashboards`.

**Última actualización:** 11 de Diciembre 2025

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
proyectos/
├── .env                          # Variables de entorno
├── .streamlit/config.toml        # Configuración Streamlit
├── Home.py                       # Página principal
├── requirements.txt              # Dependencias Python
├── DASHBOARD_STRUCTURE.md        # Este archivo
├── PAGES.md                      # Guía para agregar páginas
│
├── backend/                      # API FastAPI
│   ├── main.py                   # Entry point
│   ├── config/settings.py        # Configuración
│   ├── routers/                  # Endpoints por feature
│   │   ├── auth.py
│   │   ├── produccion.py
│   │   ├── bandejas.py
│   │   ├── stock.py
│   │   ├── containers.py
│   │   ├── estado_resultado.py
│   │   ├── presupuesto.py
│   │   ├── permissions.py
│   │   └── recepciones_mp.py
│   └── services/                 # Lógica de negocio
│
├── pages/                        # Páginas Streamlit
│   ├── 1_Recepciones.py          # 📥 Recepciones MP
│   ├── 2_Produccion.py           # 🏭 Producción
│   ├── 3_Bandejas.py             # 📊 Bandejas
│   ├── 4_Stock.py                # 📦 Stock
│   ├── 5_Containers.py           # 🚢 Containers
│   ├── 6_Finanzas.py             # 💰 Finanzas (Estado Resultado)
│   └── 9_Permisos.py             # ⚙️ Panel Admin
│
├── shared/                       # Módulos compartidos
│   ├── auth.py
│   ├── constants.py
│   └── odoo_client.py
│
└── data/                         # Archivos de datos (presupuesto)
```

---

## 3. Dashboards Disponibles

| # | Nombre | Archivo | Descripción |
|---|--------|---------|-------------|
| 1 | Recepciones | `1_Recepciones.py` | KPIs de Kg, costos, calidad por productor |
| 2 | Producción | `2_Produccion.py` | Órdenes de fabricación, rendimientos |
| 3 | Bandejas | `3_Bandejas.py` | Control de bandejas por proveedor |
| 4 | Stock | `4_Stock.py` | Inventario en cámaras y pallets |
| 5 | Containers | `5_Containers.py` | Pedidos y avance de producción |
| 6 | Finanzas | `6_Finanzas.py` | Estado de Resultado vs Presupuesto |
| 9 | Permisos | `9_Permisos.py` | Panel de administración |

---

## 4. Endpoints API

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/auth/login` | Autenticación |
| `/api/v1/recepciones-mp/` | Recepciones de materia prima |
| `/api/v1/produccion/ordenes` | Órdenes de fabricación |
| `/api/v1/stock/camaras` | Stock por cámaras |
| `/api/v1/containers/` | Containers |
| `/api/v1/estado-resultado/` | Estado de resultado |
| `/api/v1/presupuesto/` | Presupuesto |
| `/api/v1/permissions/` | Gestión de permisos |

---

## 5. Despliegue

### Comandos Rápidos

```bash
# Conectar al servidor
ssh debian@167.114.114.51

# Ir a la app
cd /home/debian/rio-futuro-dashboards/app

# Backup .env, pull y restaurar
cp .env ../env_backup.env
git reset --hard HEAD && git pull
cp ../env_backup.env .env

# Reiniciar servicios
sudo systemctl restart rio-futuro-api rio-futuro-web

# Ver logs
sudo journalctl -u rio-futuro-web -n 100 -f
```

---

## 6. Servicios Systemd

- `rio-futuro-api.service` → Backend (puerto 8000)
- `rio-futuro-web.service` → Frontend (puerto 8501)

---

*Documento actualizado el 11 de Diciembre 2025*
