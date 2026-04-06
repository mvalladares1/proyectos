# Proyectos - Dashboard de Gestión Empresarial

Sistema de dashboards empresarial para gestión y análisis de datos Odoo utilizando Streamlit como frontend y FastAPI como backend.

---

## Tabla de Contenidos

1. [Información General](#información-general)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura](#arquitectura)
4. [Módulos del Sistema](#módulos-del-sistema)
5. [Backend API](#backend-api)
6. [Servicios](#servicios)
7. [Despliegue](#despliegue)
8. [Desarrollo Local](#desarrollo-local)
9. [Variables de Entorno](#variables-de-entorno)
10. [Scripts de Utilidad](#scripts-de-utilidad)

---

## Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | Rio Futuro - Dashboard de Gestión |
| **Propósito** | Dashboard ERP unificado para operaciones y finanzas |
| **Frontend** | Streamlit (Python) |
| **Backend** | FastAPI (Python) |
| **Datos** | Odoo vía XML-RPC |
| **Servidor** | 167.114.114.51 |
| **URL Producción** | https://riofuturoprocesos.com/ |
| **Estado** | Producción - Legacy (en migración a React) |

---

## Stack Tecnológico

### Frontend (Streamlit)
| Tecnología | Uso |
|------------|-----|
| Streamlit | Framework dashboard |
| Pandas | Procesamiento datos |
| Plotly | Gráficos interactivos |
| Altair | Visualizaciones |

### Backend (FastAPI)
| Tecnología | Uso |
|------------|-----|
| FastAPI | Framework API |
| Python 3.11 | Runtime |
| Pydantic | Validación |
| Redis | Cache |
| XML-RPC | Conexión Odoo |

### Infraestructura
| Tecnología | Uso |
|------------|-----|
| Docker | Contenedorización |
| Docker Compose | Orquestación |
| Nginx | Reverse proxy |

---

## Arquitectura

### Estructura del Proyecto

```
proyectos/
├── Home.py                           # Entry point Streamlit
├── Home_Content.py                   # Contenido página principal
├── requirements.txt                  # Dependencias Python
│
├── backend/                          # API FastAPI
│   ├── main.py                      # Entry point API
│   ├── cache.py                     # Sistema de cache
│   ├── config/                      # Configuración
│   ├── data/                        # Datos estáticos
│   ├── routers/                     # Endpoints API
│   │   ├── auth.py
│   │   ├── recepcion.py
│   │   ├── produccion.py
│   │   ├── bandejas.py
│   │   ├── stock.py
│   │   ├── compras.py
│   │   ├── comercial.py
│   │   ├── flujo_caja.py
│   │   ├── estado_resultado.py
│   │   ├── rendimiento.py
│   │   ├── permissions.py
│   │   ├── automatizaciones.py
│   │   ├── aprobaciones_fletes.py
│   │   └── ...
│   ├── services/                    # Lógica de negocio
│   │   ├── recepcion_service.py
│   │   ├── produccion_service.py
│   │   ├── flujo_caja_service.py
│   │   ├── estado_resultado_service.py
│   │   ├── bandejas_service.py
│   │   ├── comercial_service.py
│   │   ├── compras/
│   │   ├── flujo_caja/
│   │   ├── rendimiento/
│   │   ├── stock/
│   │   └── ...
│   ├── utils/                       # Utilidades
│   └── tests/                       # Tests
│
├── pages/                            # Páginas Streamlit
│   ├── 1_Recepciones.py
│   ├── 2_Produccion.py
│   ├── 3_Bandejas.py
│   ├── 4_Stock.py
│   ├── 5_Pedidos_Venta.py
│   ├── 6_Finanzas.py
│   ├── 7_Rendimiento.py
│   ├── 8_Compras.py
│   ├── 9_Permisos.py
│   ├── 10_Automatizaciones.py
│   ├── 11_Relacion_Comercial.py
│   ├── 12_Reconciliacion_Produccion.py
│   │
│   ├── recepciones/                 # Submódulos
│   │   ├── shared.py
│   │   ├── tab_kpis.py
│   │   ├── tab_gestion.py
│   │   ├── tab_curva.py
│   │   ├── tab_aprobaciones.py
│   │   ├── tab_aprobaciones_fletes.py
│   │   └── tab_pallets.py
│   ├── produccion/
│   ├── bandejas/
│   ├── finanzas/
│   ├── compras/
│   ├── stock/
│   ├── rendimiento/
│   ├── reconciliacion/
│   ├── relacion_comercial/
│   ├── permisos/
│   ├── automatizaciones/
│   └── containers/
│
├── shared/                           # Código compartido
│   ├── auth.py                      # Autenticación
│   ├── odoo_client.py               # Cliente Odoo
│   └── utils.py                     # Utilidades
│
├── components/                       # Componentes reutilizables
│
├── scripts/                          # Scripts utilidades
│   ├── analisis/
│   ├── verificacion/
│   ├── transportes/
│   ├── limpieza_ocs/
│   ├── ocs_especificas/
│   └── aprobaciones/
│
├── data/                             # Datos estáticos
├── docs/                             # Documentación
├── output/                           # Archivos generados
│
├── .streamlit/                       # Config Streamlit
│   └── config.toml
│
├── docker-compose.dev.yml
├── docker-compose.prod.yml
├── docker-compose.test.yml
├── Dockerfile.web                    # Frontend
├── Dockerfile.api                    # Backend
└── *.nginx.conf                      # Configs Nginx
```

---

## Módulos del Sistema

### 1. Recepciones (`1_Recepciones.py`)
Gestión integral de recepciones de materia prima.

| Tab | Funcionalidad |
|-----|---------------|
| KPIs y Calidad | Monitoreo de métricas de recepción |
| Gestión | Administración de recepciones |
| Pallets | Control de pallets por recepción |
| Curva Abastecimiento | Análisis de tendencias |
| Aprobaciones MP | Aprobación compras materia prima |
| Aprobaciones Fletes | Aprobación órdenes de transporte |

### 2. Producción (`2_Produccion.py`)
Monitoreo de producción en tiempo real.

**Funcionalidades:**
- Dashboard de producción
- KPIs de eficiencia
- Trazabilidad de lotes
- Órdenes de fabricación

### 3. Bandejas (`3_Bandejas.py`)
Análisis de producción de bandejas.

**Funcionalidades:**
- Análisis IQF vs Block
- Métricas de rendimiento
- Producción por turno

### 4. Stock (`4_Stock.py`)
Control de inventario.

**Funcionalidades:**
- Inventario teórico vs real
- Movimientos de stock
- Alertas de stock bajo
- Valorización

### 5. Pedidos de Venta (`5_Pedidos_Venta.py`)
Gestión de ventas y despachos.

**Funcionalidades:**
- Gestión de pedidos
- Seguimiento de entregas
- Análisis de ventas
- Proformas

### 6. Finanzas (`6_Finanzas.py`)
Análisis financiero completo.

| Tab | Funcionalidad |
|-----|---------------|
| Estado de Resultados | EERR por periodo |
| Flujo de Caja | Cash flow proyectado y real |
| Cartera | Cuentas por cobrar/pagar |
| Presupuesto | Control presupuestario |

### 7. Rendimiento (`7_Rendimiento.py`)
Trazabilidad y rendimiento.

**Funcionalidades:**
- Trazabilidad de productos
- Análisis de rendimiento
- Reconciliación de producción

### 8. Compras (`8_Compras.py`)
Gestión de compras y proveedores.

**Funcionalidades:**
- Órdenes de compra
- Análisis de proveedores
- Seguimiento de entregas
- Aprobaciones

### 9. Permisos (`9_Permisos.py`)
Administración del sistema.

**Funcionalidades:**
- Gestión de usuarios
- Control de acceso por módulo
- Roles y permisos

### 10. Automatizaciones (`10_Automatizaciones.py`)
Monitor de procesos automáticos.

**Funcionalidades:**
- Estado de automatizaciones
- Configuración de reglas
- Logs de ejecución

### 11. Relación Comercial (`11_Relacion_Comercial.py`)
CRM y análisis de clientes.

**Funcionalidades:**
- Análisis de clientes
- Histórico de ventas
- Proyecciones

### 12. Reconciliación Producción (`12_Reconciliacion_Produccion.py`)
Reconciliación de datos de producción.

**Funcionalidades:**
- Comparación de datos
- Ajustes de producción
- Reportes de diferencias

---

## Backend API

### Routers Principales

| Router | Archivo | Endpoints |
|--------|---------|-----------|
| auth | `auth.py` | Login, permisos |
| recepcion | `recepcion.py` | Recepciones MP |
| produccion | `produccion.py` | Producción |
| bandejas | `bandejas.py` | Análisis bandejas |
| stock | `stock.py` | Inventario |
| compras | `compras.py` | Órdenes compra |
| comercial | `comercial.py` | CRM |
| flujo_caja | `flujo_caja.py` | Cash flow |
| estado_resultado | `estado_resultado.py` | EERR |
| rendimiento | `rendimiento.py` | Trazabilidad |
| permissions | `permissions.py` | Gestión permisos |
| automatizaciones | `automatizaciones.py` | Monitor autos |
| aprobaciones_fletes | `aprobaciones_fletes.py` | Aprobar fletes |
| reconciliacion | `reconciliacion.py` | Reconciliación |
| presupuesto | `presupuesto.py` | Presupuestos |
| proyecciones | `proyecciones.py` | Proyecciones |

### Endpoints Clave

#### Autenticación (`/api/auth`)
```
POST /api/auth/login           # Login Odoo
GET  /api/auth/permissions     # Permisos usuario
```

#### Recepciones (`/api/recepcion`)
```
GET  /api/recepcion/kpis       # KPIs recepciones
GET  /api/recepcion/list       # Lista recepciones
POST /api/recepcion/approve    # Aprobar recepción
```

#### Producción (`/api/produccion`)
```
GET  /api/produccion/dashboard    # Dashboard producción
GET  /api/produccion/mos          # Órdenes fabricación
GET  /api/produccion/kpis         # KPIs producción
```

#### Flujo de Caja (`/api/flujo-caja`)
```
GET  /api/flujo-caja/resumen      # Resumen cash flow
GET  /api/flujo-caja/proyectado   # Proyecciones
GET  /api/flujo-caja/detalle      # Detalle movimientos
```

#### Stock (`/api/stock`)
```
GET  /api/stock/summary           # Resumen stock
GET  /api/stock/movements         # Movimientos
GET  /api/stock/valuation         # Valorización
```

---

## Servicios

### Servicios Principales

| Servicio | Archivo | Responsabilidad |
|----------|---------|-----------------|
| Recepción | `recepcion_service.py` | Lógica recepciones |
| Producción | `produccion_service.py` | Lógica producción |
| Flujo Caja | `flujo_caja_service.py` | Cash flow |
| Estado Resultado | `estado_resultado_service.py` | EERR |
| Bandejas | `bandejas_service.py` | Análisis bandejas |
| Comercial | `comercial_service.py` | CRM |
| Compras | `analisis_compras_service.py` | Análisis compras |
| Aprobaciones | `aprobaciones_service.py` | Sistema aprobaciones |
| Permissions | `permissions_service.py` | Gestión permisos |
| Rendimiento | `rendimiento_service.py` | Trazabilidad |
| Presupuesto | `presupuesto_service.py` | Presupuestos |
| Proyecciones | `proyecciones_service.py` | Proyecciones |

### Servicios de Soporte

| Servicio | Archivo | Responsabilidad |
|----------|---------|-----------------|
| Excel | `excel_service.py` | Exportación Excel |
| Currency | `currency_service.py` | Conversión monedas |
| Session | `session_service.py` | Manejo sesiones |
| Report | `report_service.py` | Generación reportes |
| Cache | `cache.py` | Sistema de cache |

---

## Despliegue

### Docker Compose

**Producción:**
```bash
# Deploy completo
docker-compose -f docker-compose.prod.yml up -d

# Solo frontend
docker-compose -f docker-compose.prod.yml up -d web

# Solo backend
docker-compose -f docker-compose.prod.yml up -d api
```

**Desarrollo:**
```bash
docker-compose -f docker-compose.dev.yml up -d
```

### Despliegue en Servidor

```bash
# Conectar
ssh debian@167.114.114.51

# Ir al directorio
cd /home/debian/apps/proyectos

# Actualizar
git pull

# Reconstruir
docker-compose -f docker-compose.prod.yml up -d --build
```

### Contenedores

| Contenedor | Puerto | Servicio |
|------------|--------|----------|
| proyectos-web | 8501 | Streamlit |
| proyectos-api | 8002 | FastAPI |

---

## Desarrollo Local

### Requisitos
- Python 3.11+
- Docker (opcional)

### Instalación

```bash
# Clonar repositorio
git clone <repo>
cd proyectos

# Crear entorno virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Copiar variables de entorno
cp .env.example .env
# Editar .env con credenciales
```

### Iniciar Servicios

```bash
# Frontend Streamlit
streamlit run Home.py

# Backend FastAPI (otra terminal)
cd backend
uvicorn main:app --reload --port 8002
```

### URLs Desarrollo Local

| Servicio | URL |
|----------|-----|
| Dashboard | http://localhost:8501 |
| API | http://127.0.0.1:8002 |
| API Docs | http://127.0.0.1:8002/docs |

---

## Variables de Entorno

### `.env`

```env
# Odoo
ODOO_URL=https://riofuturo.server98c6e.oerpondemand.net
ODOO_DB=riofuturo-master
ODOO_API_USER=api_user
ODOO_API_KEY=api_key

# API
API_URL=http://127.0.0.1:8002

# Streamlit
STREAMLIT_SERVER_PORT=8501
STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Redis (cache)
REDIS_URL=redis://localhost:6379/0
```

---

## Scripts de Utilidad

Los scripts están organizados en `scripts/`:

### Estructura

```
scripts/
├── README.md                        # Documentación scripts
├── analisis/                        # Scripts de análisis
├── verificacion/                    # Verificación de datos
├── transportes/                     # Gestión transportes
├── limpieza_ocs/                    # Limpieza órdenes compra
├── ocs_especificas/                 # OCs específicas
└── aprobaciones/                    # Sistema aprobaciones
```

### Scripts Comunes

| Script | Ubicación | Uso |
|--------|-----------|-----|
| Análisis OCs | `analisis/` | Análisis órdenes compra |
| Verificación Stock | `verificacion/` | Validación stock |
| Limpieza | `limpieza_ocs/` | Limpieza de datos |

---

## Autenticación

### Sistema de Login

El sistema usa autenticación contra Odoo:

1. Usuario ingresa credenciales
2. Backend valida contra Odoo XML-RPC
3. Se genera sesión local
4. Permisos se cargan desde configuración

### Roles y Permisos

Los permisos se configuran por módulo:
- Cada usuario tiene acceso a módulos específicos
- Los permisos se almacenan en el backend
- La interfaz se adapta según permisos

---

## Estado y Migración

### Estado Actual
- **Producción:** Funcional y estable
- **Uso:** Sistema principal de dashboards
- **Mantenimiento:** Activo

### Migración a React

Este sistema está siendo migrado a **dashboards-react**:
- El frontend Streamlit será reemplazado por React SPA
- El backend FastAPI se mantiene sin cambios
- La migración es progresiva por módulos

### Razones de Migración
- Mejor experiencia de usuario
- Mayor rendimiento
- Interfaz más moderna
- Mejor mantenibilidad

---

## Documentación Adicional

| Documento | Ubicación |
|-----------|-----------|
| Deploy Producción | `/DEPLOY_PRODUCTION.md` |
| Scripts | `/scripts/README.md` |
| API Docs | `http://localhost:8002/docs` |

---

## Estado y Madurez

| Aspecto | Estado |
|---------|--------|
| **Documentación** | Parcial |
| **Tests** | Básicos |
| **CI/CD** | Docker |
| **Ambientes** | Prod + Dev |
| **Estabilidad** | Alta |
| **Mantenimiento** | Activo |

**Nivel de madurez: Producción - Legacy (en migración)**
