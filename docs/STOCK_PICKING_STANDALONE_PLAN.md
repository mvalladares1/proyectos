# Plan: Sistema Standalone de Stock Picking

## 🎯 Objetivo
Crear un sistema independiente y altamente disponible para movimiento de pallets, separado de los dashboards principales.

---

## 🏗️ Arquitectura Propuesta

### **Opción 1: Streamlit Standalone + SQLite (Más Rápido)**
```
┌─────────────────────────────────────────┐
│  NGINX (riofuturoprocesos.com)          │
│  - /                  → Dashboards      │
│  - /stock-picking/    → Stock Picking   │
└─────────────────────────────────────────┘
         │                      │
         ▼                      ▼
┌──────────────────┐   ┌──────────────────┐
│ Streamlit Main   │   │ Streamlit Picking│
│ (Puerto 8501)    │   │ (Puerto 8502)    │
│ Dashboard Multi  │   │ SOLO Picking     │
└──────────────────┘   └──────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ FastAPI Picking        │
                    │ (Puerto 8100)          │
                    │ - Cache SQLite local   │
                    │ - Queue de operaciones │
                    │ - Health monitoring    │
                    └────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ Odoo API               │
                    │ (con retry & fallback) │
                    └────────────────────────┘
```

**Pros:**
- Rápido de implementar (ya conoces Streamlit)
- Reutilizas código existente
- SQLite para cache offline
- Deploy simple (Docker)

**Contras:**
- Streamlit puede ser limitante para UX avanzada
- Menos control sobre performance

---

### **Opción 2: React PWA + FastAPI (Producción Seria)**
```
┌─────────────────────────────────────────┐
│  NGINX (riofuturoprocesos.com)          │
│  - /                  → Dashboards      │
│  - /stock-picking/    → React PWA       │
└─────────────────────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ React PWA              │
                    │ - Service Worker       │
                    │ - IndexedDB local      │
                    │ - Offline-first        │
                    │ - Barcode scanner API  │
                    └────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ FastAPI Picking        │
                    │ - Redis cache          │
                    │ - Celery queue         │
                    │ - Prometheus metrics   │
                    │ - Health endpoints     │
                    └────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ PostgreSQL Local       │
                    │ - Sync queue           │
                    │ - Audit log            │
                    │ - Offline operations   │
                    └────────────────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
                    │ Odoo API               │
                    │ (background sync)      │
                    └────────────────────────┘
```

**Pros:**
- 100% offline-capable
- Performance máximo
- UX nativa mobile
- Escalable ilimitadamente

**Contras:**
- Más tiempo de desarrollo
- Necesitas frontend dev
- Más complejo mantener

---

## 🔧 Características Críticas

### 1. **Alta Disponibilidad (99.9% uptime)**
- ✅ Health checks cada 10 segundos
- ✅ Auto-restart si falla
- ✅ Múltiples workers (mínimo 2)
- ✅ Load balancer (NGINX)
- ✅ Failover a modo offline

### 2. **Cache Inteligente**
```python
# Niveles de cache
1. Memoria (Redis) - 1 min
   - Ubicaciones activas
   - Pallets escaneados recientemente
   
2. SQLite Local - 1 hora
   - Catálogo de ubicaciones
   - Últimas operaciones
   
3. Offline Mode
   - Cola de operaciones pendientes
   - Sync cuando vuelva conexión
```

### 3. **Fallbacks**
```
Odoo disponible
    ↓
1. Operación normal → Odoo API
    ↓ (falla)
2. Retry 3 veces (exponencial backoff)
    ↓ (falla)
3. Guardar en cola local (SQLite)
    ↓
4. Notificar usuario: "Guardado offline"
    ↓
5. Background worker intenta sync cada 30s
    ↓
6. Cuando Odoo vuelve → sync automático
```

### 4. **Monitoreo**
- **Health endpoint**: `/health` (JSON con status)
- **Metrics endpoint**: `/metrics` (Prometheus)
- **Logs estructurados**: JSON logs
- **Alertas**:
  - Email si downtime > 5 min
  - Telegram bot para errores críticos
  - Dashboard de status

### 5. **Performance**
- Response time < 200ms (95 percentile)
- Barcode scan → UI update < 100ms
- API calls en background (no bloquean UI)
- WebSocket para updates en tiempo real

---

## 📁 Estructura de Archivos Propuesta

```
proyectos/
├── stock-picking/                    # NUEVO sistema standalone
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── App.jsx              # App principal
│   │   │   ├── components/
│   │   │   │   ├── BarcodeScanner.jsx
│   │   │   │   ├── PalletCard.jsx
│   │   │   │   └── LocationSelector.jsx
│   │   │   ├── hooks/
│   │   │   │   ├── useOfflineSync.js
│   │   │   │   └── useBarcodeScanner.js
│   │   │   └── utils/
│   │   │       ├── cache.js
│   │   │       └── offline.js
│   │   ├── public/
│   │   │   ├── manifest.json        # PWA manifest
│   │   │   └── service-worker.js    # Offline capability
│   │   ├── package.json
│   │   └── vite.config.js
│   │
│   ├── backend/
│   │   ├── main.py                  # FastAPI app
│   │   ├── routes/
│   │   │   ├── picking.py           # Endpoints picking
│   │   │   ├── health.py            # Health checks
│   │   │   └── sync.py              # Offline sync
│   │   ├── services/
│   │   │   ├── odoo_service.py      # Wrapper Odoo
│   │   │   ├── cache_service.py     # Redis/SQLite
│   │   │   └── queue_service.py     # Cola offline
│   │   ├── models/
│   │   │   └── database.py          # SQLite schema
│   │   └── workers/
│   │       ├── sync_worker.py       # Background sync
│   │       └── monitor_worker.py    # Health monitor
│   │
│   ├── docker/
│   │   ├── Dockerfile.frontend
│   │   ├── Dockerfile.backend
│   │   └── docker-compose.yml
│   │
│   ├── monitoring/
│   │   ├── prometheus.yml
│   │   └── grafana-dashboard.json
│   │
│   └── README.md
│
├── nginx/
│   └── riofuturoprocesos.conf       # Config NGINX
│
└── docs/
    └── STOCK_PICKING_ARCHITECTURE.md
```

---

## 🚀 Plan de Implementación

### **Fase 1: MVP Streamlit (1-2 días)**
1. ✅ Extraer código de movimientos actual
2. ✅ Crear app Streamlit standalone
3. ✅ Agregar SQLite para cache
4. ✅ Health check básico
5. ✅ Deploy en puerto 8502
6. ✅ Configurar NGINX para /stock-picking/

### **Fase 2: Cache & Fallbacks (2-3 días)**
1. ✅ Implementar cache de ubicaciones (SQLite)
2. ✅ Cola de operaciones offline
3. ✅ Background worker para sync
4. ✅ Retry logic con exponential backoff
5. ✅ UI para indicar modo offline

### **Fase 3: Monitoreo (1 día)**
1. ✅ Health endpoint completo
2. ✅ Logs estructurados (JSON)
3. ✅ Metrics básicos (request count, latency)
4. ✅ Alertas por email

### **Fase 4: Optimización (opcional)**
1. Redis para cache en memoria
2. WebSocket para updates real-time
3. Migrar a React PWA (si se necesita)

---

## 🔒 Seguridad

### **Autenticación**
```python
# Opción 1: Token session (simple)
- Cookie HTTP-only con token
- Refresh token cada 24h
- Logout automático después de inactividad

# Opción 2: OAuth con Odoo (robusto)
- Login con credenciales Odoo
- Token JWT
- Permisos basados en grupos Odoo
```

### **Validaciones**
- Rate limiting: 100 requests/min por IP
- CORS configurado solo para dominio propio
- Input sanitization (prevenir SQL injection)
- HTTPS obligatorio

---

## 💾 Base de Datos Local (SQLite)

```sql
-- Tabla de cache de ubicaciones
CREATE TABLE locations_cache (
    id INTEGER PRIMARY KEY,
    odoo_id INTEGER UNIQUE,
    name TEXT,
    barcode TEXT,
    usage TEXT,
    synced_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de operaciones pendientes
CREATE TABLE pending_operations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    operation_type TEXT,  -- 'move_pallet'
    payload JSON,         -- Datos de la operación
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retry_count INTEGER DEFAULT 0,
    status TEXT DEFAULT 'pending',  -- pending, syncing, failed, completed
    error TEXT
);

-- Tabla de audit log
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_id INTEGER,
    action TEXT,
    pallet_code TEXT,
    location_from TEXT,
    location_to TEXT,
    success BOOLEAN,
    synced_to_odoo BOOLEAN DEFAULT FALSE
);
```

---

## 📊 Métricas a Monitorear

### **Application Metrics**
- `picking_operations_total` (counter)
- `picking_operation_duration_seconds` (histogram)
- `picking_errors_total` (counter)
- `cache_hit_ratio` (gauge)
- `offline_queue_size` (gauge)

### **Infrastructure Metrics**
- CPU usage
- Memory usage
- Disk I/O
- Network latency to Odoo

### **Business Metrics**
- Pallets movidos por hora
- Tiempo promedio por operación
- Tasa de error
- Usuarios activos

---

## 🎨 UI/UX Mejorado

### **Indicadores Visuales**
```
┌─────────────────────────────────┐
│ 🟢 Online  │  ⚡ 45ms latency   │  ← Status bar
├─────────────────────────────────┤
│ Escanea Cámara Destino          │
│ [___________________________]   │
│                                 │
│ 📍 Camara 0°C REAL              │  ← Selected
├─────────────────────────────────┤
│ Escanea Pallets (5)             │
│ [___________________________]   │
│                                 │
│ ✅ PACK0001234 - 456.7 kg       │
│ ✅ PACK0005678 - 234.5 kg       │
│                                 │
│ [CONFIRMAR MOVIMIENTO]          │  ← Táctil grande
└─────────────────────────────────┘

🔴 Offline Mode:
┌─────────────────────────────────┐
│ 🔴 Offline  │  ⏳ 3 pendientes │
│ Las operaciones se guardarán    │
│ y sincronizarán automáticamente │
└─────────────────────────────────┘
```

---

## 🤔 Preguntas para Decidir

### 1. **¿Qué tan crítico es el modo offline?**
- ❓ Si WiFi falla en bodega, ¿deben poder seguir trabajando?
- Si SÍ → React PWA + IndexedDB
- Si NO → Streamlit + cache básico

### 2. **¿Cuántos usuarios concurrentes?**
- < 5 usuarios → Streamlit OK
- 5-20 usuarios → Streamlit con optimizaciones
- \> 20 usuarios → React PWA

### 3. **¿Deploy en servidor separado?**
- Mismo servidor → Más fácil, menos costos
- Servidor separado → Más aislamiento, mejor para failover

### 4. **¿Presupuesto para infraestructura?**
- Básico: SQLite + mismo servidor
- Medio: Redis + PostgreSQL + mismo servidor
- Premium: Servidor separado + Redis + PostgreSQL + Monitoring

---

## 💡 Mi Recomendación

### **Para empezar AHORA (Fase 1):**
1. **Streamlit Standalone** en puerto 8502
2. **SQLite** para cache de ubicaciones
3. **Cola simple** para operaciones fallidas (tabla SQLite)
4. **Health endpoint** básico
5. **NGINX** reverse proxy

**Ventajas:**
- Listo en 1-2 días
- Reutilizas todo el código existente
- Funciona 24/7 con fallback básico
- Fácil de mantener

### **Luego optimizar (Fases 2-3):**
- Agregar Redis si crece
- Mejorar monitoring
- Migrar a React si la UX lo requiere

---

## 📝 Próximos Pasos

**¿Quieres que empecemos con Fase 1 (Streamlit Standalone)?**

1. ✅ Crear estructura de carpetas
2. ✅ Extraer código de movimientos
3. ✅ Configurar SQLite
4. ✅ Docker compose para stock-picking
5. ✅ NGINX config
6. ✅ Deploy y pruebas

**O prefieres planificar más antes de ejecutar?**
