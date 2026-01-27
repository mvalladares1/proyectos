# 📋 PLAN DE TRABAJO: Stock Picking PWA

## 🎯 DIVISIÓN DE TRABAJO (2 IAs)

### **IA ORQUESTADOR (Yo - Claude Principal)**
- Arquitectura general y decisiones técnicas
- **Backend completo** (FastAPI, modelos, servicios, API)
- Integración con Odoo
- Docker y DevOps
- Coordinación y revisión

### **IA SECUNDARIA (Agente/Subagente)**
- **Frontend completo** (React PWA, componentes, UI)
- Service Workers y offline
- IndexedDB con Dexie
- Testing E2E
- Estilos y UX

---

## 📁 ESTRUCTURA DEL PROYECTO

```
proyectos/
├── stock-picking/                    # 🆕 NUEVO PROYECTO
│   ├── backend/                      # FastAPI API
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py              # FastAPI app
│   │   │   ├── config.py            # Settings
│   │   │   ├── database.py          # PostgreSQL connection
│   │   │   ├── models/              # SQLAlchemy models
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── location.py
│   │   │   │   ├── pallet.py
│   │   │   │   └── operation.py
│   │   │   ├── schemas/             # Pydantic schemas
│   │   │   │   ├── __init__.py
│   │   │   │   ├── user.py
│   │   │   │   ├── location.py
│   │   │   │   ├── pallet.py
│   │   │   │   └── operation.py
│   │   │   ├── routers/             # API endpoints
│   │   │   │   ├── __init__.py
│   │   │   │   ├── auth.py
│   │   │   │   ├── locations.py
│   │   │   │   ├── pallets.py
│   │   │   │   └── operations.py
│   │   │   ├── services/            # Business logic
│   │   │   │   ├── __init__.py
│   │   │   │   ├── odoo_service.py
│   │   │   │   ├── cache_service.py
│   │   │   │   └── sync_service.py
│   │   │   ├── core/                # Core utilities
│   │   │   │   ├── __init__.py
│   │   │   │   ├── security.py      # JWT, hashing
│   │   │   │   └── deps.py          # Dependencies
│   │   │   └── tasks/               # Celery tasks
│   │   │       ├── __init__.py
│   │   │       └── sync_tasks.py
│   │   ├── alembic/                 # Migrations
│   │   │   ├── versions/
│   │   │   ├── env.py
│   │   │   └── alembic.ini
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   │
│   ├── frontend/                    # React PWA
│   │   ├── src/
│   │   │   ├── main.tsx
│   │   │   ├── App.tsx
│   │   │   ├── vite-env.d.ts
│   │   │   ├── components/          # UI Components
│   │   │   │   ├── ui/              # Base components
│   │   │   │   │   ├── Button.tsx
│   │   │   │   │   ├── Input.tsx
│   │   │   │   │   ├── Card.tsx
│   │   │   │   │   └── Modal.tsx
│   │   │   │   ├── BarcodeScanner.tsx
│   │   │   │   ├── LocationSelector.tsx
│   │   │   │   ├── PalletCard.tsx
│   │   │   │   ├── OfflineIndicator.tsx
│   │   │   │   └── Navigation.tsx
│   │   │   ├── pages/               # Page components
│   │   │   │   ├── Login.tsx
│   │   │   │   ├── Dashboard.tsx
│   │   │   │   ├── ScanPallet.tsx
│   │   │   │   ├── MovePallet.tsx
│   │   │   │   ├── History.tsx
│   │   │   │   └── Settings.tsx
│   │   │   ├── hooks/               # Custom hooks
│   │   │   │   ├── useAuth.ts
│   │   │   │   ├── useOffline.ts
│   │   │   │   ├── useScanner.ts
│   │   │   │   └── useSync.ts
│   │   │   ├── services/            # API services
│   │   │   │   ├── api.ts
│   │   │   │   ├── auth.ts
│   │   │   │   └── operations.ts
│   │   │   ├── store/               # Zustand stores
│   │   │   │   ├── authStore.ts
│   │   │   │   ├── operationsStore.ts
│   │   │   │   └── syncStore.ts
│   │   │   ├── db/                  # IndexedDB (Dexie)
│   │   │   │   ├── database.ts
│   │   │   │   └── sync.ts
│   │   │   ├── types/               # TypeScript types
│   │   │   │   └── index.ts
│   │   │   └── utils/               # Utilities
│   │   │       └── helpers.ts
│   │   ├── public/
│   │   │   ├── manifest.json
│   │   │   ├── sw.js
│   │   │   └── icons/
│   │   ├── index.html
│   │   ├── vite.config.ts
│   │   ├── tailwind.config.js
│   │   ├── tsconfig.json
│   │   ├── package.json
│   │   └── Dockerfile
│   │
│   ├── docker-compose.yml           # Desarrollo local
│   ├── docker-compose.prod.yml      # Producción
│   ├── nginx/
│   │   └── stock-picking.conf
│   └── README.md
```

---

## 📅 FASES DE DESARROLLO

### **FASE 1: Infraestructura Base (Día 1-2)**
| Tarea | Responsable | Prioridad |
|-------|-------------|-----------|
| Crear estructura de carpetas | Orquestador | P0 |
| Setup Docker Compose (PostgreSQL + Redis) | Orquestador | P0 |
| Setup proyecto Vite + React + TypeScript | IA Secundaria | P0 |
| Configurar TailwindCSS | IA Secundaria | P0 |
| Setup PWA básico (manifest, SW) | IA Secundaria | P1 |

### **FASE 2: Backend Core (Día 3-5)**
| Tarea | Responsable | Prioridad |
|-------|-------------|-----------|
| Modelos SQLAlchemy (User, Location, Pallet, Operation) | Orquestador | P0 |
| Configurar Alembic + primera migración | Orquestador | P0 |
| Sistema de autenticación JWT | Orquestador | P0 |
| Endpoints CRUD básicos | Orquestador | P0 |
| Servicio de integración Odoo | Orquestador | P0 |
| Cache con Redis | Orquestador | P1 |
| Celery tasks para sync | Orquestador | P1 |

### **FASE 3: Frontend Core (Día 3-5)** [PARALELO]
| Tarea | Responsable | Prioridad |
|-------|-------------|-----------|
| Componentes UI base (Button, Input, Card) | IA Secundaria | P0 |
| Layout y navegación | IA Secundaria | P0 |
| Página de Login | IA Secundaria | P0 |
| Configurar React Query | IA Secundaria | P0 |
| Configurar Zustand stores | IA Secundaria | P0 |
| Setup IndexedDB con Dexie | IA Secundaria | P0 |

### **FASE 4: Funcionalidades Core (Día 6-10)**
| Tarea | Responsable | Prioridad |
|-------|-------------|-----------|
| Endpoint POST /operations/move-pallet | Orquestador | P0 |
| Endpoint GET /locations (con cache) | Orquestador | P0 |
| Endpoint GET /pallets/search | Orquestador | P0 |
| WebSocket para actualizaciones | Orquestador | P1 |
| Componente BarcodeScanner | IA Secundaria | P0 |
| Página ScanPallet | IA Secundaria | P0 |
| Página MovePallet | IA Secundaria | P0 |
| Lógica offline-first | IA Secundaria | P0 |
| Background sync | IA Secundaria | P1 |

### **FASE 5: Polish y Deploy (Día 11-14)**
| Tarea | Responsable | Prioridad |
|-------|-------------|-----------|
| Testing backend (pytest) | Orquestador | P1 |
| NGINX config producción | Orquestador | P0 |
| Health checks y monitoring | Orquestador | P1 |
| Testing E2E (Playwright) | IA Secundaria | P1 |
| Optimización mobile | IA Secundaria | P0 |
| PWA icons y splash screens | IA Secundaria | P1 |
| Deploy final | Ambos | P0 |

---

## 🔧 COMANDOS PARA IA SECUNDARIA

### **Prompt inicial para Frontend:**
```
CONTEXTO: Estamos desarrollando una PWA para Stock Picking de bodega.
STACK: React 18 + TypeScript + Vite + TailwindCSS + Zustand + React Query + Dexie.js

TU RESPONSABILIDAD:
1. Crear toda la estructura frontend en: proyectos/stock-picking/frontend/
2. Implementar componentes, páginas, hooks y stores
3. Configurar PWA (manifest, service worker, offline)
4. Implementar scanner de código de barras
5. Manejar sincronización offline con IndexedDB

ENDPOINTS DEL BACKEND (los creo yo):
- POST /api/auth/login
- GET /api/auth/me
- GET /api/locations
- GET /api/pallets?barcode={code}
- POST /api/operations/move-pallet
- GET /api/operations/history
- GET /api/sync/pending

FLUJO PRINCIPAL:
1. Usuario escanea código de barras del pallet
2. Sistema muestra info del pallet y ubicación actual
3. Usuario selecciona nueva ubicación
4. Usuario confirma movimiento
5. Si offline, guardar en IndexedDB y sincronizar después
```

---

## 📊 MÉTRICAS DE PROGRESO

| Fase | Backend | Frontend | Estado |
|------|---------|----------|--------|
| Infraestructura | ✅ 100% | ✅ 100% | **COMPLETADO** |
| Core | ✅ 100% | ✅ 100% | **COMPLETADO** |
| Funcionalidades | ✅ 90% | ✅ 100% | **EN PROGRESO** |
| Polish | ⬜ 20% | ✅ 80% | **PENDIENTE** |
| Deploy | ⬜ 0% | ⬜ 0% | No iniciado |

---

## ✅ RESUMEN DE ARCHIVOS CREADOS

### Backend (FastAPI)
- ✅ `main.py` - Aplicación FastAPI con routers
- ✅ `config.py` - Configuración con Pydantic Settings
- ✅ `database.py` - Conexión async PostgreSQL
- ✅ `models/` - User, Location, Pallet, Operation
- ✅ `schemas/` - Pydantic schemas
- ✅ `routers/` - auth, locations, pallets, operations, sync
- ✅ `services/` - odoo_service, cache_service
- ✅ `core/` - security, deps (JWT)
- ✅ `alembic/` - Migraciones iniciales

### Frontend (React PWA)
- ✅ `components/ui/` - Button, Input, Card, Modal
- ✅ `components/` - BarcodeScanner, LocationSelector, PalletCard, Navigation, OfflineIndicator, Layout
- ✅ `pages/` - Login, Dashboard, ScanPallet, MovePallet, History, Settings
- ✅ `store/` - authStore, operationsStore, syncStore
- ✅ `hooks/` - useAuth, useOffline, useSync
- ✅ `services/` - api, auth, operations
- ✅ `db/` - database.ts (Dexie IndexedDB)
- ✅ `types/` - TypeScript definitions
- ✅ PWA config (vite-plugin-pwa)
- ✅ Tailwind config
- ✅ Docker + NGINX

---

## 🚀 COMENZAMOS CON:

### **PASO 1 (Ahora):**
1. Crear estructura de carpetas del proyecto
2. Crear docker-compose.yml con PostgreSQL y Redis
3. Crear backend base con FastAPI
4. IA Secundaria: Crear frontend base con Vite

### **Archivos a crear inmediatamente:**
```
stock-picking/
├── docker-compose.yml          ← Orquestador
├── backend/
│   ├── requirements.txt        ← Orquestador
│   ├── Dockerfile              ← Orquestador
│   └── app/main.py             ← Orquestador
├── frontend/
│   ├── package.json            ← IA Secundaria
│   ├── vite.config.ts          ← IA Secundaria
│   └── src/                    ← IA Secundaria
└── README.md                   ← Orquestador
```

---

## ✅ CHECKLIST INICIAL

- [ ] Crear directorio stock-picking/
- [ ] docker-compose.yml con PostgreSQL + Redis
- [ ] Backend: requirements.txt
- [ ] Backend: Dockerfile
- [ ] Backend: app/main.py básico
- [ ] Backend: app/config.py
- [ ] Backend: app/database.py
- [ ] Frontend: package.json
- [ ] Frontend: vite.config.ts
- [ ] Frontend: tsconfig.json
- [ ] Frontend: tailwind.config.js
- [ ] README.md con instrucciones

**¿COMENZAMOS?**
