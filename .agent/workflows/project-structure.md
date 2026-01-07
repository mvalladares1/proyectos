# Estructura del Proyecto Rio Futuro Dashboard

**Última actualización:** 07 de Enero 2026

---

## 1. Estructura de Directorios

```
proyectos/
├── Home.py                   # Entrada principal
├── Home_Content.py           # Contenido Home (login/dashboard)
├── DASHBOARD_STRUCTURE.md    # Documentación técnica
├── PAGES.md                  # Guía para agregar páginas
├── requirements.txt          # Dependencias Python
│
├── Dockerfile.api            # Docker image para FastAPI
├── Dockerfile.web            # Docker image para Streamlit
├── docker-compose.prod.yml   # Compose PROD (8000, 8501)
├── docker-compose.dev.yml    # Compose DEV (8002, 8502)
├── riofuturoprocesos.com.nginx # Configuración NGINX
│
├── backend/                  # API FastAPI
│   ├── main.py               # Entry point
│   ├── cache.py              # Sistema de caché
│   ├── config/               # Configuración
│   ├── routers/              # 16 endpoints REST
│   ├── services/             # 22 servicios de negocio
│   ├── utils/                # Utilidades
│   └── tests/                # Tests
│
├── pages/                    # Dashboards Streamlit
│   ├── 1_Recepciones.py      # 📥 Recepciones MP
│   ├── 2_Produccion.py       # 🏭 Órdenes de fabricación
│   ├── 3_Bandejas.py         # 📊 Control de bandejas
│   ├── 4_Stock.py            # 📦 Inventario cámaras
│   ├── 5_Containers.py       # 🚢 Pedidos y contenedores
│   ├── 6_Finanzas.py         # 💰 Estado Resultado
│   ├── 7_Rendimiento.py      # ⚡ Rendimiento MP→PT
│   ├── 8_Compras.py          # 🛒 Órdenes de compra
│   ├── 9_Permisos.py         # ⚙️ Administración
│   ├── 10_Automatizaciones.py # 🤖 Túneles Estáticos
│   └── 11_Relacion_Comercial.py # 🤝 Deudas y saldos
│   ├── recepciones/          # Tabs de Recepciones
│   ├── finanzas/             # Tabs de Finanzas
│   ├── produccion/           # Tabs de Producción
│   ├── stock/                # Tabs de Stock
│   └── ...                   # Otros subdirectorios
│
├── shared/                   # Módulos compartidos
│   ├── auth.py               # Autenticación frontend
│   ├── constants.py          # Constantes globales
│   └── odoo_client.py        # Cliente Odoo XML-RPC
│
├── components/               # Componentes UI reutilizables
├── data/                     # Archivos de datos
├── docs/                     # Documentación adicional
└── .agent/workflows/         # Workflows de desarrollo
```

---

## 2. Deployment

### Servidor: debian@167.114.114.51

**Entornos activos**:
- PROD: Puertos 8000 (API), 8501 (Web)
- DEV: Puertos 8002 (API), 8502 (Web)

**Tecnologías**:
- Docker Compose para orquestación
- NGINX como reverse proxy (Blue-Green failover)
- Network mode `host` para web containers (solución a conectividad)

**Guía completa**: Ver `.agent/workflows/docker-deployment.md`

---

## 3. Dashboards Disponibles

| # | Dashboard | Archivo | Descripción |
|---|-----------|---------|-------------|
| 1 | Recepciones | `1_Recepciones.py` | KPIs, curva abastecimiento, gestión |
| 2 | Producción | `2_Produccion.py` | Órdenes de fabricación, rendimientos |
| 3 | Bandejas | `3_Bandejas.py` | Control por proveedor |
| 4 | Stock | `4_Stock.py` | Inventario cámaras y pallets |
| 5 | Containers | `5_Containers.py` | Pedidos y producción |
| 6 | Finanzas | `6_Finanzas.py` | Estado Resultado, Flujo Caja |
| 7 | Rendimiento | `7_Rendimiento.py` | Análisis MP → PT |
| 8 | Compras | `8_Compras.py` | OC y líneas de crédito |
| 9 | Permisos | `9_Permisos.py` | Panel administración |
| 10 | Automatizaciones | `10_Automatizaciones.py` | Túneles estáticos MO |
| 11 | Relación Comercial | `11_Relacion_Comercial.py` | Deudas y saldos |

---

## 4. Backend Services (22)

| Servicio | Descripción |
|----------|-------------|
| `abastecimiento_service.py` | Proyecciones Excel |
| `aprobaciones_service.py` | Gestión de aprobaciones |
| `bandejas_service.py` | Control de bandejas |
| `comercial_service.py` | Relación comercial |
| `compras_service.py` | Órdenes de compra |
| `containers_service.py` | Gestión contenedores |
| `currency_service.py` | Conversión divisas |
| `estado_resultado_service.py` | Estado de resultados |
| `excel_service.py` | Procesamiento Excel |
| `flujo_caja_service.py` | Flujo de caja proyectado |
| `permissions_service.py` | Permisos usuarios |
| `presupuesto_service.py` | Presupuesto anual |
| `produccion_report_service.py` | Reportes producción |
| `produccion_service.py` | Órdenes fabricación |
| `recepcion_service.py` | Recepciones MP |
| `recepciones_gestion_service.py` | Gestión recepciones |
| `rendimiento_service.py` | Cálculo rendimientos |
| `report_service.py` | Generación reportes |
| `session_service.py` | Sesiones JWT |
| `stock_service.py` | Stock y cámaras |
| `tuneles_service.py` | Automatización túneles |

---

## 4. API Routers (16)

| Router | Prefijo | Descripción |
|--------|---------|-------------|
| `auth.py` | `/api/v1/auth` | Autenticación |
| `automatizaciones.py` | `/api/v1/automatizaciones` | Túneles |
| `bandejas.py` | `/api/v1/bandejas` | Bandejas |
| `comercial.py` | `/api/v1/comercial` | Comercial |
| `compras.py` | `/api/v1/compras` | Compras |
| `containers.py` | `/api/v1/containers` | Contenedores |
| `estado_resultado.py` | `/api/v1/estado-resultado` | EERR |
| `flujo_caja.py` | `/api/v1/flujo-caja` | Flujo Caja |
| `permissions.py` | `/api/v1/permissions` | Permisos |
| `presupuesto.py` | `/api/v1/presupuesto` | Presupuesto |
| `produccion.py` | `/api/v1/produccion` | Producción |
| `recepcion.py` | `/api/v1/recepciones-mp` | Recepciones |
| `rendimiento.py` | `/api/v1/rendimiento` | Rendimiento |
| `stock.py` | `/api/v1/stock` | Stock |

---

## 5. Stack Tecnológico

| Componente | Tecnología |
|------------|------------|
| Frontend | Streamlit |
| Backend | FastAPI + Uvicorn |
| Base de datos | Odoo 16 (XML-RPC) |
| Servidor | Debian VPS |
| Proxy | Nginx + Cloudflare |
| Auth | JWT + Session tokens |
