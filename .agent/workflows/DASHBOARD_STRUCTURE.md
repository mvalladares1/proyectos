# Estructura del Proyecto - Rio Futuro Dashboards

Este documento describe la estructura del repositorio `rio-futuro-dashboards`.

**Última actualización:** 07 de Enero 2026

---

## 1. Resumen General

| Componente | Tecnología | Puerto |
|------------|------------|--------|
| Frontend | Streamlit | 8501 |
| Backend | FastAPI + Uvicorn | 8000 |
| Base de datos | Odoo 16 (XML-RPC) | - |
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
├── .agent/workflows/             # Workflows de desarrollo
│   ├── project-structure.md      # 📂 Estructura del proyecto
│   └── debugging.md              # 🐛 Estándares de debugging
│
├── backend/                      # API FastAPI
│   ├── main.py                   # Entry point
│   ├── cache.py                  # Sistema de caché
│   ├── config/settings.py        # Configuración
│   ├── routers/                  # 16 endpoints por feature
│   │   ├── auth.py               # 🔐 Autenticación con tokens
│   │   ├── produccion.py
│   │   ├── bandejas.py
│   │   ├── stock.py
│   │   ├── containers.py
│   │   ├── estado_resultado.py
│   │   ├── presupuesto.py
│   │   ├── permissions.py
│   │   ├── recepcion.py          # Recepciones MP
│   │   ├── rendimiento.py
│   │   ├── compras.py
│   │   ├── flujo_caja.py         # 💰 Flujo de caja
│   │   ├── comercial.py          # 🤝 Relación comercial
│   │   └── automatizaciones.py   # 🤖 Túneles Estáticos
│   └── services/                 # 22 servicios de negocio
│       ├── rendimiento_service.py
│       ├── tuneles_service.py
│       ├── session_service.py
│       ├── flujo_caja_service.py # 💰 Flujo de caja
│       ├── comercial_service.py  # 🤝 Relación comercial
│       └── ...                   # Ver .agent/workflows/project-structure.md
│
├── pages/                        # Páginas Streamlit
│   ├── 1_Recepciones.py          # 📥 KPIs, Curva, Gestión
│   ├── 2_Produccion.py           # 🏭 Órdenes de fabricación
│   ├── 3_Bandejas.py             # 📊 Control de bandejas
│   ├── 4_Stock.py                # 📦 Inventario en cámaras
│   ├── 5_Containers.py           # 🚢 Pedidos y avance
│   ├── 6_Finanzas.py             # 💰 EERR, Flujo Caja
│   ├── 7_Rendimiento.py          # ⚡ Rendimiento MP → PT
│   ├── 8_Compras.py              # 🛒 OC, Líneas Crédito
│   ├── 9_Permisos.py             # ⚙️ Panel de administración
│   ├── 10_Automatizaciones.py    # 🤖 Túneles Estáticos
│   └── 11_Relacion_Comercial.py  # 🤝 Deudas y saldos
│
├── shared/                       # Módulos compartidos
│   ├── auth.py                   # 🔐 Autenticación frontend
│   ├── cookies.py                # Manejo de cookies
│   ├── constants.py
│   └── odoo_client.py
│
└── data/
    └── sessions.json             # Almacenamiento de sesiones
```

---

## 3. Dashboards Disponibles (11)

| # | Nombre | Archivo | Descripción |
|---|--------|---------|-------------|
| 1 | Recepciones | `1_Recepciones.py` | KPIs de Kg, costos, calidad, curva abastecimiento |
| 2 | Producción | `2_Produccion.py` | Órdenes de fabricación, rendimientos |
| 3 | Bandejas | `3_Bandejas.py` | Control de bandejas por proveedor |
| 4 | Stock | `4_Stock.py` | Inventario en cámaras y pallets |
| 5 | Containers | `5_Containers.py` | Pedidos y avance de producción |
| 6 | Finanzas | `6_Finanzas.py` | Estado de Resultado, Flujo Caja, Presupuesto |
| 7 | Rendimiento | `7_Rendimiento.py` | Análisis de rendimiento MP → PT |
| 8 | Compras | `8_Compras.py` | Órdenes de compra, líneas de crédito |
| 9 | Permisos | `9_Permisos.py` | Panel de administración |
| 10 | Automatizaciones | `10_Automatizaciones.py` | Túneles Estáticos - Creación de MO |
| 11 | **Relación Comercial** | `11_Relacion_Comercial.py` | **Deudas y saldos proveedores** |

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

## 11. Infraestructura del Servidor VPS

> **Estado:** Producción funcional y estable  
> **Última limpieza:** 2 de Enero 2026

### 11.1 Visión General

Este servidor aloja tres capas bien separadas:

| Capa | Descripción |
|------|-------------|
| **NGINX** | Reverse proxy y frontend HTTP (puerto 80) |
| **FastAPI** | API de datos Python (127.0.0.1:8000) |
| **Laravel** | Sistema de cargas / logística |

Todo corre sobre **Debian**, gestionado con **systemd** y puertos internos aislados.

### 11.2 Arquitectura Final

```
Internet
   |
   v
[ NGINX :80 ]
   |
   ├── /cargas        ──▶ Laravel (PHP-FPM)
   ├── /api/v1/*      ──▶ FastAPI (127.0.0.1:8000)
   └── /dashboards/*  ──▶ Streamlit (127.0.0.1:8501)
```

### 11.3 Servicios Activos

#### FastAPI – Rio Backend

| Propiedad | Valor |
|-----------|-------|
| Servicio systemd | `rio-backend.service` |
| Usuario | `debian` |
| Puerto interno | `127.0.0.1:8000` |
| Arranque automático | ✅ |

**Archivo de servicio:** `/etc/systemd/system/rio-backend.service`

```ini
[Unit]
Description=Rio Futuro Dashboards Backend (FastAPI)
After=network.target

[Service]
User=debian
Group=debian
WorkingDirectory=/home/debian/rio-futuro-dashboards/app
Environment="PATH=/home/debian/rio-futuro-dashboards/app/venv/bin"
ExecStart=/home/debian/rio-futuro-dashboards/app/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

**Healthcheck:**
```
GET /api/v1
→ {"status": "ok", "service": "rio-futuro-backend", "env": "production"}
```

#### Laravel – Log System / Cargas

| Propiedad | Valor |
|-----------|-------|
| Root | `/home/debian/log-system/public` |
| Backend | PHP 8.4 + PHP-FPM |
| Ruta pública | `/cargas` |

### 11.4 Configuración NGINX

**📍 Sitios habilitados:** `/etc/nginx/sites-enabled/`

| Archivo | Servicio |
|---------|----------|
| `log-system.conf` | Laravel `/cargas` |
| `rio-futuro-dashboards.conf` | API FastAPI + Streamlit |

**Reglas relevantes:**

```nginx
# FastAPI
location /api/v1/ {
    proxy_pass http://127.0.0.1:8000/api/v1/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}

# Laravel
location /cargas {
    try_files $uri /index.php?$query_string;
}
```

### 11.5 Estructura de Directorios (Servidor)

```
📍 /home/debian/

rio-futuro-dashboards/
├── app/
│   ├── backend/
│   │   ├── main.py
│   │   ├── routers/
│   │   ├── services/
│   │   └── utils/
│   ├── venv/
│   ├── pages/           (Streamlit)
│   ├── shared/
│   └── requirements.txt

log-system/
├── app/
├── public/
├── routes/
└── vendor/
```

**🧹 Directorios eliminados (limpieza):**
- `dashboards_streamlit/`
- `integra_reporteria/`
- `graphhopper/`
- `gravity/`
- `apps/`
- `dashboards/`

### 11.6 Firewall (UFW)

| Puerto | Uso |
|--------|-----|
| 22 | SSH |
| 80 | HTTP |
| 443 | HTTPS (preparado) |

Todo lo demás cerrado.

### 11.7 Docker

- Docker instalado ✅
- Sin contenedores corriendo
- Listo para uso futuro

### 11.8 Decisiones Técnicas

| Decisión | Justificación |
|----------|---------------|
| FastAPI nunca en puerto 80 | NGINX es único punto de entrada |
| systemd único gestor | Nada "levantado a mano" en producción |
| Healthcheck implementado | Antes de escalar |
| Puertos internos aislados | Seguridad |

### 11.9 Estado Final

| Componente | Estado |
|------------|--------|
| NGINX | ✅ OK |
| FastAPI | ✅ OK |
| Laravel | ✅ OK |
| systemd | ✅ OK |
| Firewall | ✅ OK |
| Swagger | ✅ OK |
| Healthcheck | ✅ OK |

---

## 12. Registro de Cambios en Producción (2 Enero 2026)

> **Objetivo:** Documentar exactamente qué se modificó, por qué, y cómo quedó funcionando.

---

### 12.1 Limpieza Inicial de Nginx

**Antes:**
- Existían múltiples archivos en `/etc/nginx/sites-enabled/`:
  - `log-system.conf`
  - `rio-futuro-dashboards.conf`
  - `default`
- Varios `server {}` bloques escuchando en puerto 80 con `default_server`
- Conflictos de configuración causaban errores al recargar Nginx

**Acción realizada:**
```bash
sudo rm /etc/nginx/sites-enabled/log-system.conf
sudo rm /etc/nginx/sites-enabled/default
```

**Resultado:**
- Nginx quedó con un único virtual host activo
- Configuración consolidada en: `/etc/nginx/sites-available/riofuturoprocesos.com`

---

### 12.2 Nueva Estructura de Virtual Host

**Antes:**
- Configuraciones fragmentadas entre múltiples archivos
- Sin redirección HTTP → HTTPS
- Rutas inconsistentes

**Acción realizada:**
Creación de `/etc/nginx/sites-available/riofuturoprocesos.com`:

```nginx
# Redirección HTTP → HTTPS
server {
    listen 80;
    server_name riofuturoprocesos.com www.riofuturoprocesos.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS principal
server {
    listen 443 ssl http2;
    server_name riofuturoprocesos.com www.riofuturoprocesos.com;

    ssl_certificate /etc/nginx/ssl/cloudflare-origin.crt;
    ssl_certificate_key /etc/nginx/ssl/cloudflare-origin.key;

    # Laravel - Sistema de Cargas
    location /cargas {
        alias /home/debian/log-system/public;
        try_files $uri $uri/ @cargas;
        location ~ \.php$ {
            fastcgi_pass unix:/var/run/php/php8.4-fpm.sock;
            fastcgi_param SCRIPT_FILENAME $request_filename;
            include fastcgi_params;
        }
    }

    # FastAPI
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Streamlit Dashboards
    location /dashboards/ {
        proxy_pass http://127.0.0.1:8501/dashboards/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # Reportería
    location /reporteria/ {
        proxy_pass http://127.0.0.1:8503/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

**Resultado:**
- Rutas unificadas por contexto
- WebSocket habilitado para Streamlit
- SSL configurado correctamente

---

### 12.3 Integración con Cloudflare

**Antes:**
- DNS apuntaba directamente a IP del servidor
- Sin CDN ni protección DDoS
- Certificados Let's Encrypt autogestionados

**Acción realizada:**
1. Migración de DNS a Cloudflare
2. Activación de proxy (orange cloud) para:
   - `riofuturoprocesos.com`
   - `www.riofuturoprocesos.com`
3. Configuración de SSL/TLS mode: **Full (strict)**

**Resultado:**
- Tráfico pasa por Cloudflare antes de llegar al servidor
- Protección DDoS activa
- Certificado edge manejado por Cloudflare

---

### 12.4 Certificados SSL (Cloudflare Origin Certificate)

**Antes:**
- Certificados Let's Encrypt con renovación manual
- Error 521 al acceder vía Cloudflare

**Acción realizada:**

1. Generación de Origin Certificate en Cloudflare Dashboard:
   - Hostnames: `riofuturoprocesos.com`, `*.riofuturoprocesos.com`
   - Validez: 15 años

2. Instalación en servidor:
```bash
sudo mkdir -p /etc/nginx/ssl
sudo nano /etc/nginx/ssl/cloudflare-origin.crt   # Pegar certificado
sudo nano /etc/nginx/ssl/cloudflare-origin.key   # Pegar clave privada
sudo chmod 600 /etc/nginx/ssl/cloudflare-origin.key
```

3. Verificación de coincidencia:
```bash
openssl x509 -noout -modulus -in /etc/nginx/ssl/cloudflare-origin.crt | md5sum
openssl rsa -noout -modulus -in /etc/nginx/ssl/cloudflare-origin.key | md5sum
# Ambos MD5 deben coincidir
```

**Resultado:**
- Certificados Origin instalados correctamente
- Comunicación Cloudflare ↔ Servidor cifrada

---

### 12.5 Corrección de Error 521

**Síntoma:**
- Error 521 (Web server is down) al acceder a `https://riofuturoprocesos.com`

**Causa raíz:**
- Certificado `.crt` mal pegado (faltaba contenido)
- Nginx fallaba silenciosamente al cargar SSL

**Diagnóstico:**
```bash
sudo nginx -t
# nginx: [emerg] cannot load certificate "/etc/nginx/ssl/cloudflare-origin.crt": 
#        PEM_read_bio_X509_AUX() failed
```

**Corrección:**
1. Re-copiar certificado completo desde Cloudflare Dashboard
2. Verificar que archivo termina con `-----END CERTIFICATE-----`
3. Recargar Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

**Resultado:**
- `nginx -t` exitoso
- HTTPS funcional vía Cloudflare

---

### 12.6 Servicios Backend

**Puertos internos (solo localhost):**

| Puerto | Servicio | Gestión |
|--------|----------|---------|
| 8000 | FastAPI (Uvicorn) | systemd: `rio-backend.service` |
| 8501 | Streamlit Dashboards | systemd: `rio-futuro-web.service` |
| 8503 | Reportería | (pendiente systemd) |

**Nginx expone únicamente:**
- Puerto 80 (redirección a 443)
- Puerto 443 (HTTPS)

**Verificación:**
```bash
sudo lsof -i :8000  # FastAPI corriendo
sudo lsof -i :8501  # Streamlit corriendo
sudo lsof -i :80    # Nginx
sudo lsof -i :443   # Nginx
```

---

### 12.7 Estado Final Validado

**Pruebas realizadas:**

```bash
# Sintaxis Nginx
sudo nginx -t
# nginx: configuration file /etc/nginx/nginx.conf test is successful

# HTTP → HTTPS redirect
curl -I http://riofuturoprocesos.com
# HTTP/1.1 301 Moved Permanently
# Location: https://riofuturoprocesos.com/

# HTTPS funcional
curl -I https://riofuturoprocesos.com
# HTTP/2 200

# API healthcheck
curl https://riofuturoprocesos.com/api/v1/
# {"status":"ok","service":"rio-futuro-backend","env":"production"}
```

**Estado de componentes:**

| Componente | Estado | Verificación |
|------------|--------|--------------|
| Nginx | ✅ OK | `nginx -t` exitoso |
| SSL/TLS | ✅ OK | Certificado válido |
| Cloudflare | ✅ OK | Full (strict) activo |
| FastAPI | ✅ OK | Healthcheck responde |
| Laravel | ✅ OK | `/cargas` accesible |
| Streamlit | ✅ OK | `/dashboards` accesible |

---

### 12.8 Archivos de Configuración Finales

| Archivo | Propósito |
|---------|-----------|
| `/etc/nginx/sites-available/riofuturoprocesos.com` | Virtual host principal |
| `/etc/nginx/sites-enabled/riofuturoprocesos.com` | Symlink activo |
| `/etc/nginx/ssl/cloudflare-origin.crt` | Certificado Origin |
| `/etc/nginx/ssl/cloudflare-origin.key` | Clave privada |
| `/etc/systemd/system/rio-backend.service` | FastAPI service |
| `/etc/systemd/system/rio-futuro-web.service` | Streamlit service |

---

## 13. TODOs Pendientes

- [ ] Crear servicio systemd para Reportería (puerto 8503)
- [ ] Configurar renovación automática de Origin Certificate (15 años)
- [ ] Agregar monitoring con uptime checks

---

*Documento actualizado el 2 de Enero 2026*
