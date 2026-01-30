# 🏭 Rio Futuro - Dashboard de Gestión

Sistema unificado de dashboards para gestión y análisis de datos Odoo.

## 📁 Estructura del Proyecto

```
proyectos/
├── 📄 Home.py                    # Archivo principal del dashboard
├── 📄 Home_Content.py            # Contenido de la página home
├── 📄 requirements.txt           # Dependencias del proyecto
│
├── 📁 backend/                   # API FastAPI
│   ├── main.py
│   ├── routers/
│   └── services/
│
├── 📁 pages/                     # Páginas del dashboard Streamlit
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
│   └── 📁 recepciones/           # Módulo de recepciones
│       ├── shared.py
│       ├── tab_kpis.py
│       ├── tab_gestion.py
│       ├── tab_curva.py
│       ├── tab_aprobaciones.py
│       ├── tab_aprobaciones_fletes.py  # ✨ Nuevo
│       └── tab_pallets.py
│
├── 📁 shared/                    # Código compartido
│   ├── auth.py
│   ├── odoo_client.py
│   └── utils.py
│
├── 📁 components/                # Componentes reutilizables
│   └── ...
│
├── 📁 scripts/                   # Scripts de utilidades (ver scripts/README.md)
│   ├── analisis/
│   ├── verificacion/
│   ├── transportes/
│   ├── limpieza_ocs/
│   ├── ocs_especificas/
│   └── aprobaciones/
│
├── 📁 data/                      # Datos estáticos
├── 📁 docs/                      # Documentación
└── 📁 .streamlit/                # Configuración de Streamlit
```

## 🚀 Inicio Rápido

### Desarrollo Local

1. **Instalar dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configurar variables de entorno:**
   ```bash
   cp .env.example .env
   # Editar .env con tus credenciales
   ```

3. **Iniciar el dashboard:**
   ```bash
   streamlit run Home.py
   ```

4. **Iniciar el backend (opcional):**
   ```bash
   cd backend
   uvicorn main:app --reload
   ```

### Producción con Docker

```bash
# Dashboard (Frontend)
docker-compose -f docker-compose.prod.yml up -d web

# API (Backend)
docker-compose -f docker-compose.prod.yml up -d api
```

## 📊 Módulos Principales

### 1. Recepciones 📥
- **KPIs y Calidad**: Monitoreo de recepciones de materia prima
- **Gestión de Recepciones**: Administración de recepciones
- **Pallets**: Control de pallets por recepción
- **Curva de Abastecimiento**: Análisis de tendencias
- **Aprobaciones MP**: Aprobación de compras de materia prima
- **Aprobaciones Fletes**: Aprobación de órdenes de transporte (Maximo/Felipe)

### 2. Producción 🏭
- Monitoreo de producción en tiempo real
- KPIs de eficiencia
- Trazabilidad de lotes

### 3. Bandejas 📊
- Análisis de bandeja IQF vs Block
- Métricas de rendimiento

### 4. Stock 📦
- Inventario teórico vs real
- Movimientos de stock
- Alertas de stock bajo

### 5. Pedidos de Venta 🚢
- Gestión de pedidos
- Seguimiento de entregas
- Análisis de ventas

### 6. Finanzas 💰
- Análisis financiero
- Costos y márgenes
- Reportes contables

### 7. Rendimiento/Trazabilidad 🔍
- Trazabilidad de productos
- Análisis de rendimiento

### 8. Compras 🛒
- Gestión de órdenes de compra
- Análisis de proveedores

### 9. Permisos 👥
- Administración de usuarios
- Control de acceso

### 10. Automatizaciones 🦾
- Configuración de flujos automáticos
- Reglas de negocio

### 11. Relación Comercial 🤝
- CRM y análisis de clientes

### 12. Reconciliación de Producción 🔄
- Reconciliación de datos de producción

## 🔐 Autenticación

El sistema usa autenticación centralizada:
- Login vía Odoo
- Gestión de permisos por módulo
- Roles de usuario configurables

## 🛠️ Tecnologías

- **Frontend**: Streamlit
- **Backend**: FastAPI
- **Base de Datos**: PostgreSQL (via Odoo)
- **ORM**: Odoo XML-RPC
- **Containerización**: Docker

## 📝 Scripts de Utilidades

Los scripts de debugging, análisis y configuración están organizados en `scripts/`.
Ver [scripts/README.md](scripts/README.md) para más detalles.

## 🔧 Configuración

### Variables de Entorno

```env
# Odoo
ODOO_URL=https://riofuturo.server98c6e.oerpondemand.net
ODOO_DB=riofuturo-master

# API
API_URL=http://127.0.0.1:8000

# Streamlit
STREAMLIT_SERVER_PORT=8501
```

## 📄 Archivos de Configuración

- `docker-compose.dev.yml` - Docker compose para desarrollo
- `docker-compose.prod.yml` - Docker compose para producción
- `Dockerfile.web` - Imagen Docker para frontend
- `Dockerfile.api` - Imagen Docker para backend
- `*.nginx.conf` - Configuraciones de Nginx

## 🤝 Contribución

1. Crear feature branch
2. Hacer cambios
3. Commit con mensaje descriptivo
4. Push y crear Pull Request

## 📞 Soporte

Para soporte contactar al equipo de desarrollo.

---

**Última actualización**: Enero 2026
