# Estructura del Proyecto - Rio Futuro Dashboards

Este documento describe la estructura del repositorio `rio-futuro-dashboards`.

**Última actualización:** 26 de Diciembre 2024

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
├── Home.py                       # Página principal (navegación)
├── Home_Content.py               # Contenido de Home (login/dashboard)
├── requirements.txt              # Dependencias Python
├── DASHBOARD_STRUCTURE.md        # Este archivo
├── PAGES.md                      # Guía para agregar páginas
│
├── backend/                      # API FastAPI
│   ├── main.py                   # Entry point
│   ├── config/settings.py        # Configuración
│   ├── routers/                  # Endpoints por feature
│   │   ├── auth.py               # 🔐 Autenticación con tokens
│   │   ├── produccion.py
│   │   ├── bandejas.py
│   │   ├── stock.py
│   │   ├── containers.py
│   │   ├── estado_resultado.py
│   │   ├── presupuesto.py
│   │   ├── permissions.py
│   │   ├── recepciones_mp.py
│   │   ├── rendimiento.py
│   │   ├── compras.py
│   │   └── automatizaciones.py   # 🆕 Túneles Estáticos
│   └── services/
│       ├── rendimiento_service.py
│       ├── tuneles_service.py    # 🆕 Lógica de MO automáticas
│       └── session_service.py    # 🆕 Gestión de sesiones JWT
│
├── pages/                        # Páginas Streamlit
│   ├── 1_Recepciones.py
│   ├── 2_Produccion.py
│   ├── 3_Bandejas.py
│   ├── 4_Stock.py
│   ├── 5_Containers.py
│   ├── 6_Finanzas.py
│   ├── 7_Rendimiento.py
│   ├── 8_Compras.py
│   ├── 9_Permisos.py
│   └── 10_Automatizaciones.py    # 🆕 Túneles Estáticos
│
├── shared/                       # Módulos compartidos
│   ├── auth.py                   # 🔐 Autenticación frontend
│   ├── cookies.py                # 🆕 Manejo de cookies/persistencia
│   ├── constants.py
│   └── odoo_client.py
│
└── data/
    └── sessions.json             # 🆕 Almacenamiento de sesiones
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
| 7 | Rendimiento | `7_Rendimiento.py` | Análisis de rendimiento por lote (MP → PT) |
| 8 | Compras | `8_Compras.py` | Órdenes de compra, líneas de crédito |
| 9 | Permisos | `9_Permisos.py` | Panel de administración |
| 10 | **Automatizaciones** | `10_Automatizaciones.py` | **🆕 Túneles Estáticos - Creación de MO** |

---

## 4. Sistema de Autenticación

### Módulos Nuevos

| Archivo | Descripción |
|---------|-------------|
| `backend/services/session_service.py` | Generación y validación de tokens JWT |
| `backend/routers/auth.py` | Endpoints de autenticación |
| `shared/auth.py` | Manejo de sesión en frontend |
| `shared/cookies.py` | Persistencia de cookies (WIP) |

### Características Implementadas

| Feature | Estado | Descripción |
|---------|--------|-------------|
| Token JWT | ✅ | Tokens firmados con HMAC-SHA256 |
| Expiración 8h | ✅ | Sesión máxima de 8 horas |
| Inactividad 30min | ✅ | Timeout por inactividad |
| Password encriptado | ✅ | XOR + session_key en servidor |
| Persistencia recarga | ⚠️ WIP | Problema con st.query_params |

### Endpoints de Autenticación

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/auth/login` | POST | Login y generación de token |
| `/api/v1/auth/validate` | POST | Validar token |
| `/api/v1/auth/refresh` | POST | Refrescar actividad |
| `/api/v1/auth/logout` | POST | Cerrar sesión |
| `/api/v1/auth/session-info` | GET | Info de sesión |
| `/api/v1/auth/credentials` | GET | Obtener credenciales Odoo |

---

## 5. Dashboard de Rendimiento (Detalle)

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

---

## 6. Dashboard de Compras

### Secciones

| Sección | Descripción |
|---------|-------------|
| KPIs | Total, pendientes, promedio días |
| OC por Estado | Tabla y gráfico |
| Líneas de Crédito | Monitoreo de uso por proveedor |

### Gráfico de Líneas de Crédito

- Eje Y: % de uso
- Colores: 🔴 ≥80%, 🟡 ≥60%, 🟢 <60%
- Línea de referencia: 100%

---

## 7. Dashboard de Automatizaciones (Túneles Estáticos) 🆕

### Descripción General

Dashboard para automatizar la creación de Órdenes de Fabricación (MO) en Odoo 16 para procesos de congelado en túneles estáticos. Sistema mobile-first diseñado para celulares Zebra con entrada por escaneo o manual.

### Pestañas Disponibles

| Tab | Descripción |
|-----|-------------|
| 📦 **Crear Orden** | Input de pallets, validación y creación de MO |
| 📊 **Monitor de Órdenes** | Listado y filtrado de órdenes creadas |

### Túneles Configurados

| Código | Proceso | Sucursal | Ubicación Origen |
|--------|---------|----------|------------------|
| TE1 | Túnel Estático 1 | RF | RF/Stock/Camara 0°C REAL |
| TE2 | Túnel Estático 2 | RF | RF/Stock/Camara 0°C REAL |
| TE3 | Túnel Estático 3 | RF | RF/Stock/Camara 0°C REAL |
| VLK | Túnel Estático VLK | VLK | VLK/Camara 0° |

### Funcionalidades Implementadas

#### Validación de Pallets
- ✅ Buscar lote por código en `stock.lot`
- ✅ Obtener Kg automáticamente desde `stock.quant`
- ✅ Detectar pallets sin stock y permitir ingreso manual
- ✅ Mostrar ubicación real del pallet
- ✅ Búsqueda automática de ubicación (VLK con pallets mal ubicados)

#### Creación de Órdenes
- ✅ Crear MO en estado Borrador
- ✅ Validar todos los pallets antes de crear
- ✅ **Crear componentes (`move_raw_ids`)** con `stock.move` y `stock.move.line`
- ✅ **Crear subproductos (`move_finished_ids`)** con sufijo `-C`
- ✅ **Generar lotes automáticamente** con sufijo `-C` (ej: PAC0002683-C)
- ✅ **Crear `result_package_id`** con formato PACK0002XXX-C
- ✅ Mapeo automático producto fresco → congelado

#### Monitor
- ✅ Listar últimas 20 órdenes
- ✅ Filtrar por túnel (TE1/TE2/TE3/VLK)
- ✅ Filtrar por estado (draft/confirmed/progress/done/cancel)
- ✅ Visualización con cards y badges de colores

### Lógica de Creación de MO

```
Input: Pallets de fruta fresca (ej: PAC0002683, 426 Kg)

1. Validar pallets → Obtener Kg y ubicación
2. Crear MO en borrador
3. Crear componentes (move_raw_ids):
   - stock.move por producto
   - stock.move.line por pallet
   - Asignar lot_id original (PAC0002683)
   
4. Crear subproductos (move_finished_ids):
   - stock.move con producto congelado
   - stock.move.line por pallet con sufijo -C
   - Buscar/crear lot_id: PAC0002683-C
   - Crear result_package_id: PACK0002683-C

Output: MO completa lista en Odoo
```

### Arquitectura Backend

| Componente | Descripción |
|------------|-------------|
| `tuneles_service.py` | Lógica completa de validación y creación |
| `automatizaciones.py` | 5 endpoints REST API |

### Endpoints API

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/api/v1/automatizaciones/tuneles-estaticos/procesos` | GET | Lista túneles disponibles |
| `/api/v1/automatizaciones/tuneles-estaticos/validar-pallets` | POST | Valida lista de pallets |
| `/api/v1/automatizaciones/tuneles-estaticos/crear` | POST | Crea orden de fabricación |
| `/api/v1/automatizaciones/tuneles-estaticos/ordenes` | GET | Lista órdenes recientes |
| `/api/v1/automatizaciones/tuneles-estaticos/ordenes/{id}` | GET | Detalle de orden |

### Estado del Desarrollo

| Feature | Estado | Notas |
|---------|--------|-------|
| Backend Service | ✅ | 100% implementado |
| API Endpoints | ✅ | 5 endpoints operativos |
| Frontend Streamlit | ✅ | Mobile-first completado |
| Validación de pallets | ✅ | Con/sin stock |
| Creación de componentes | ✅ | stock.move + move.line |
| Creación de subproductos | ✅ | Con sufijo -C y packages |
| Permisos | ✅ | Integrado en sistema de permisos |
| Navegación Home | ✅ | Cards clicables |

### TODOs Pendientes

- [ ] Testing en Odoo real con pallets de producción
- [ ] Agregar escaneo con cámara (streamlit-camera-input-live)
- [ ] Confirmación antes de crear orden
- [ ] Validar duplicados en lista de pallets
- [ ] Logs y trazabilidad de automatizaciones
- [ ] Estadísticas de uso (órdenes por túnel, Kg procesados)

---

## 8. Dataset de Compras

### Rendimiento

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/rendimiento/overview` | KPIs consolidados |
| `/api/v1/rendimiento/lotes` | Por lote MP |
| `/api/v1/rendimiento/proveedores` | Por proveedor |
| `/api/v1/rendimiento/consolidado` | Por fruta/manejo/producto |

### Compras

| Endpoint | Descripción |
|----------|-------------|
| `/api/v1/compras/overview` | KPIs de compras |
| `/api/v1/compras/ordenes` | Lista de OC |
| `/api/v1/compras/lineas-credito` | Proveedores con línea |
| `/api/v1/compras/lineas-credito/resumen` | KPIs líneas |

---

## 8. Despliegue

```bash
# Conectar al servidor
ssh debian@167.114.114.51

# Ir a la app
cd /home/debian/rio-futuro-dashboards/app

# Actualizar
git pull

# Instalar dependencias (si hay nuevas)
source venv/bin/activate
pip install -r requirements.txt

# Reiniciar servicios
sudo systemctl restart rio-futuro-api rio-futuro-web

# Ver logs
sudo journalctl -u rio-futuro-web -n 50 -f
```

---

## 9. Dependencias Nuevas

```txt
extra-streamlit-components>=0.1.60  # Cookies (opcional)
```

---

## 10. Troubleshooting

### Problema: "Port 8501 is already in use"

**Síntoma:** El servicio `rio-futuro-web` falla con error "Port 8501 is already in use"

**Causa:** Alguien ejecutó un Streamlit manualmente sin detenerlo, ocupando el puerto.

**Solución:**
```bash
# 1. Identificar el proceso fantasma
sudo lsof -i :8501

# 2. Matar el proceso (reemplazar PID con el número real)
sudo kill -9 [PID]

# 3. Reiniciar el servicio
sudo systemctl restart rio-futuro-web

# 4. Verificar
sudo systemctl status rio-futuro-web
```

---

### Problema: "404 Not Found" al acceder a /dashboards/ (sin puerto)

**Síntoma:** El dashboard funciona con `http://IP:8501/dashboards/` pero no con `http://IP/dashboards/`

**Causa:** Configuración incorrecta del proxy en Nginx. El `proxy_pass` tiene trailing slash `/` que elimina el path base.

**Configuración INCORRECTA:**
```nginx
location ^~ /dashboards/ {
    proxy_pass http://127.0.0.1:8501/;  # ❌ El / final quita /dashboards/
}
```

**Configuración CORRECTA:**
```nginx
location ^~ /dashboards/ {
    proxy_pass http://127.0.0.1:8501;   # ✅ Sin / final, preserva /dashboards/
}
```

**Solución:**
```bash
# 1. Editar configuración
sudo nano /etc/nginx/sites-available/rio-futuro-dashboards

# 2. Cambiar proxy_pass (quitar el / final)
# De: proxy_pass http://127.0.0.1:8501/;
# A:  proxy_pass http://127.0.0.1:8501;

# 3. Probar sintaxis
sudo nginx -t

# 4. Recargar Nginx
sudo systemctl reload nginx
```

---

### Configuración de Referencia

**Archivos de servicio systemd:**
- `/etc/systemd/system/rio-futuro-api.service` → Backend FastAPI (puerto 8000)
- `/etc/systemd/system/rio-futuro-web.service` → Frontend Streamlit (puerto 8501)

**Configuración Nginx:**
- `/etc/nginx/sites-available/rio-futuro-dashboards`

**Configuración Streamlit:**
- `/home/debian/rio-futuro-dashboards/app/.streamlit/config.toml`
  - `baseUrlPath = "dashboards"` (requiere que Nginx preserve el path)

**Comandos útiles:**
```bash
# Ver logs en tiempo real
sudo journalctl -u rio-futuro-web -f
sudo journalctl -u rio-futuro-api -f

# Ver qué usa cada puerto
sudo lsof -i :8501
sudo lsof -i :8000

# Reiniciar todo
sudo systemctl restart rio-futuro-api rio-futuro-web nginx
```

---

## 11. TODOs / WIP

- [ ] **Persistencia de sesión**: `st.query_params` no persiste en recarga de Streamlit
- [ ] Investigar alternativas: proxy con nginx para cookies, o iframe approach

---

*Documento actualizado el 30 de Diciembre 2024*
