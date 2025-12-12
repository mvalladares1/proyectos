# Estructura del Proyecto - Rio Futuro Dashboards

Este documento describe la estructura del repositorio `rio-futuro-dashboards`.

**Última actualización:** 12 de Diciembre 2025

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
│   │   ├── recepciones_mp.py
│   │   └── rendimiento.py        # 🆕 Rendimiento endpoints
│   └── services/
│       └── rendimiento_service.py # 🆕 Lógica de rendimiento
│
├── pages/                        # Páginas Streamlit
│   ├── 1_Recepciones.py          # 📥 Recepciones MP
│   ├── 2_Produccion.py           # 🏭 Producción
│   ├── 3_Bandejas.py             # 📊 Bandejas
│   ├── 4_Stock.py                # 📦 Stock
│   ├── 5_Containers.py           # 🚢 Containers
│   ├── 6_Finanzas.py             # 💰 Finanzas
│   ├── 7_Rendimiento.py          # 🍓 Rendimiento (NUEVO)
│   └── 9_Permisos.py             # ⚙️ Panel Admin
│
├── shared/                       # Módulos compartidos
│   ├── auth.py
│   ├── constants.py
│   └── odoo_client.py
│
└── data/                         # Archivos de datos
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
| **7** | **Rendimiento** | `7_Rendimiento.py` | **Análisis de rendimiento por lote (MP → PT)** |
| **8** | **Compras** | `8_Compras.py` | **Órdenes de compra, aprobación y recepción** |
| 9 | Permisos | `9_Permisos.py` | Panel de administración |

---

## 4. Dashboard de Rendimiento (Detalle)

### Pestañas Disponibles

| Tab | Descripción |
|-----|-------------|
| 🍓 **Consolidado** | Vista ejecutiva por Fruta/Manejo/Producto |
| 🧺 Por Lote | Detalle de cada lote MP con PT asociado |
| 🏭 Por Proveedor | Ranking y comparativa de proveedores |
| ⚙️ Por MO | Órdenes de fabricación individuales |
| 🏠 Por Sala | Productividad por sala de proceso |
| 📊 Gráficos | Distribución, scatter, línea temporal |
| 🔍 Trazabilidad | Inversa: PT → MP original |

### KPIs Calculados

| KPI | Fórmula |
|-----|---------|
| Rendimiento % | `(Kg_PT / Kg_MP) × 100` (ponderado) |
| Merma | `Kg_MP - Kg_PT` |
| Kg/HH | `Kg_PT / Horas_Hombre` |
| Kg/Hora | `Kg_PT / Horas_Proceso` |
| Kg/Operario | `Kg_PT / Dotación` |

### Alertas de Rendimiento

- 🟢 **≥ 95%** - Excelente
- 🟡 **90-95%** - Atención
- 🔴 **< 90%** - Crítico

### Funcionalidades Especiales

- **Detalle PT por Lote**: Expander con productos de salida
- **Filtros**: Proveedor, Tipo Fruta, Manejo, Sala
- **OC y Fecha Recepción**: Trazabilidad completa
- **Ranking Top/Bottom 5**: Mejores y peores proveedores
- **Exportación Excel**: Con formato

---

## 5. Endpoints API

### Generales

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

### Rendimiento (Nuevos)

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/rendimiento/overview` | KPIs consolidados del período |
| `/api/v1/rendimiento/lotes` | Rendimiento por lote MP |
| `/api/v1/rendimiento/proveedores` | Rendimiento por proveedor |
| `/api/v1/rendimiento/mos` | Rendimiento por MO |
| `/api/v1/rendimiento/ranking` | Top/Bottom N proveedores |
| `/api/v1/rendimiento/salas` | Productividad por sala |
| `/api/v1/rendimiento/pt-detalle` | Productos PT por lote MP |
| `/api/v1/rendimiento/consolidado` | Vista ejecutiva por fruta/manejo/producto |
| `/api/v1/rendimiento/trazabilidad-inversa/{lote}` | PT → MP original |

### Compras

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/compras/overview` | KPIs consolidados de compras |
| `/api/v1/compras/ordenes` | Lista de OC con estados |
| `/api/v1/compras/lineas-credito` | Proveedores con línea de crédito |
| `/api/v1/compras/lineas-credito/resumen` | KPIs de líneas de crédito |

---

## 6. Despliegue

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

## 7. Servicios Systemd

- `rio-futuro-api.service` → Backend (puerto 8000)
- `rio-futuro-web.service` → Frontend (puerto 8501)

---

*Documento actualizado el 12 de Diciembre 2025*

