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
│   │   └── compras.py
│   └── services/
│       ├── rendimiento_service.py
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
│   └── 9_Permisos.py
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

## 7. Endpoints API Completos

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

## 10. TODOs / WIP

- [ ] **Persistencia de sesión**: `st.query_params` no persiste en recarga de Streamlit
- [ ] Investigar alternativas: proxy con nginx para cookies, o iframe approach

---

*Documento actualizado el 12 de Diciembre 2025*
