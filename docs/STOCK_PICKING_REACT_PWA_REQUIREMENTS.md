# React PWA + FastAPI: Requisitos y Consideraciones

## 🎯 Stack Tecnológico Completo

### **Frontend (React PWA)**
```
┌─────────────────────────────────────────────────────────────┐
│ FRONTEND                                                    │
├─────────────────────────────────────────────────────────────┤
│ Framework:      React 18 + TypeScript                       │
│ Build Tool:     Vite (más rápido que webpack)              │
│ UI Library:     TailwindCSS + Headless UI                  │
│ State:          Zustand (simple) o Redux Toolkit           │
│ Offline:        Workbox (Service Worker)                   │
│ Local DB:       IndexedDB via Dexie.js                     │
│ HTTP Client:    Axios + React Query (cache automático)     │
│ Scanner:        QuaggaJS o ZXing (barcode scanning)        │
│ PWA:            Vite-plugin-pwa                            │
└─────────────────────────────────────────────────────────────┘
```

### **Backend (FastAPI)**
```
┌─────────────────────────────────────────────────────────────┐
│ BACKEND                                                     │
├─────────────────────────────────────────────────────────────┤
│ Framework:      FastAPI + Python 3.11                       │
│ Server:         Uvicorn + Gunicorn (workers)               │
│ Database:       PostgreSQL 15                              │
│ Cache:          Redis 7                                     │
│ Queue:          Celery + Redis (background jobs)           │
│ ORM:            SQLAlchemy 2.0 + Alembic (migrations)      │
│ Validation:     Pydantic v2                                │
│ Auth:           JWT + OAuth2                               │
│ WebSocket:      FastAPI WebSocket                          │
└─────────────────────────────────────────────────────────────┘
```

### **Infraestructura**
```
┌─────────────────────────────────────────────────────────────┐
│ INFRAESTRUCTURA                                             │
├─────────────────────────────────────────────────────────────┤
│ Container:      Docker + Docker Compose                     │
│ Reverse Proxy:  NGINX                                       │
│ SSL:            Let's Encrypt (Certbot)                    │
│ Monitoring:     Prometheus + Grafana                       │
│ Logs:           Loki + Promtail                            │
│ Alertas:        Alertmanager → Email/Telegram              │
│ CI/CD:          GitHub Actions                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📦 Dependencias a Instalar

### **Frontend (package.json)**
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@tanstack/react-query": "^5.8.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "dexie": "^3.2.0",
    "dexie-react-hooks": "^1.1.0",
    "@zxing/browser": "^0.1.4",
    "@zxing/library": "^0.20.0",
    "tailwindcss": "^3.3.0",
    "@headlessui/react": "^1.7.0",
    "@heroicons/react": "^2.0.0",
    "date-fns": "^2.30.0",
    "react-hot-toast": "^2.4.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vite-plugin-pwa": "^0.17.0",
    "@vitejs/plugin-react": "^4.2.0",
    "workbox-window": "^7.0.0"
  }
}
```

### **Backend (requirements.txt)**
```txt
# Core
fastapi==0.104.1
uvicorn[standard]==0.24.0
gunicorn==21.2.0
python-multipart==0.0.6

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1
psycopg2-binary==2.9.9

# Cache & Queue
redis==5.0.1
celery==5.3.4

# Auth
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Validation
pydantic==2.5.0
pydantic-settings==2.1.0

# HTTP Client (para Odoo)
httpx==0.25.2
xmlrpc-client==1.0.1

# Monitoring
prometheus-client==0.19.0
structlog==23.2.0

# Utils
python-dotenv==1.0.0
```

---

## 👨‍💻 Habilidades de Frontend Dev Necesarias

### **Nivel Mínimo: Mid-Level (2-3 años exp)**

#### **Conocimientos OBLIGATORIOS:**
1. **React Hooks** (useState, useEffect, useCallback, useMemo, custom hooks)
2. **TypeScript** (tipos, interfaces, generics básicos)
3. **Estado global** (Context API o Zustand/Redux)
4. **React Query/TanStack** (fetching, caching, mutations)
5. **CSS moderno** (Flexbox, Grid, TailwindCSS)
6. **Git** (branching, PRs, merge conflicts)

#### **Conocimientos DESEABLES:**
1. **PWA** (Service Workers, manifest.json, caching strategies)
2. **IndexedDB** (o Dexie.js para abstracción)
3. **WebSockets** (real-time updates)
4. **Testing** (Jest, React Testing Library)
5. **Mobile-first design**

#### **Conocimientos que PUEDE APRENDER en el camino:**
1. Barcode scanning libraries
2. Offline-first patterns
3. Docker basics

---

## 💰 Estimación de Costos

### **Opción A: Desarrollador Freelance**
```
┌────────────────────────────────────────────────────────────┐
│ FREELANCER (Latino/Remote)                                 │
├────────────────────────────────────────────────────────────┤
│ Tarifa:        $20-40 USD/hora                            │
│ Tiempo:        80-120 horas                               │
│ Total:         $1,600 - $4,800 USD                        │
│ Plataformas:   Upwork, Freelancer, Workana, GetOnBoard   │
└────────────────────────────────────────────────────────────┘

Pros: Flexible, sin compromiso largo
Contras: Puede desaparecer, calidad variable
```

### **Opción B: Contratar Part-Time**
```
┌────────────────────────────────────────────────────────────┐
│ DESARROLLADOR PART-TIME (Chile)                            │
├────────────────────────────────────────────────────────────┤
│ Sueldo:        $800,000 - $1,200,000 CLP/mes              │
│ Horas:         20 hrs/semana                              │
│ Tiempo:        2-3 meses                                  │
│ Total:         $1,600,000 - $3,600,000 CLP               │
└────────────────────────────────────────────────────────────┘

Pros: Más control, puede mantener después
Contras: Compromiso mensual
```

### **Opción C: Agencia/Software Factory**
```
┌────────────────────────────────────────────────────────────┐
│ AGENCIA (proyecto cerrado)                                 │
├────────────────────────────────────────────────────────────┤
│ Costo:         $5,000 - $15,000 USD                       │
│ Tiempo:        4-8 semanas                                │
│ Incluye:       Dev + QA + Deploy                          │
└────────────────────────────────────────────────────────────┘

Pros: Llave en mano, garantía
Contras: Caro, menos flexibilidad
```

### **Opción D: TÚ + Claude (con guía)**
```
┌────────────────────────────────────────────────────────────┐
│ DIY CON ASISTENCIA AI                                      │
├────────────────────────────────────────────────────────────┤
│ Costo:         $0 (solo tu tiempo)                        │
│ Tiempo:        3-4 semanas (full dedication)              │
│ Requiere:      Conocimiento básico JS/React               │
│ Yo puedo:      Generar TODO el código, explicarte         │
└────────────────────────────────────────────────────────────┘

Pros: Sin costo, aprendes, control total
Contras: Más tiempo, curva de aprendizaje
```

---

## 🏗️ Infraestructura Necesaria

### **Servidor (ya tienes)**
```
┌────────────────────────────────────────────────────────────┐
│ SERVIDOR ACTUAL: 167.114.114.51                           │
├────────────────────────────────────────────────────────────┤
│ OS:            Debian                                      │
│ RAM:           ¿? (mínimo 4GB recomendado)                │
│ CPU:           ¿? (mínimo 2 cores)                        │
│ Disk:          ¿? (mínimo 20GB libres)                    │
│ Docker:        ✅ Ya instalado                            │
└────────────────────────────────────────────────────────────┘
```

### **Servicios Adicionales (containers)**
```yaml
# docker-compose.stock-picking.yml
services:
  # Frontend (build estático servido por NGINX)
  frontend:
    build: ./frontend
    # Solo para build, NGINX sirve los archivos

  # Backend API
  api:
    build: ./backend
    ports:
      - "8100:8000"
    depends_on:
      - postgres
      - redis
    environment:
      - DATABASE_URL=postgresql://...
      - REDIS_URL=redis://...
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 10s
      timeout: 5s
      retries: 3

  # PostgreSQL
  postgres:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=stock_picking
      - POSTGRES_USER=picking
      - POSTGRES_PASSWORD=secure_password

  # Redis
  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  # Celery Worker (background jobs)
  celery-worker:
    build: ./backend
    command: celery -A app.celery worker -l info
    depends_on:
      - redis
      - postgres

  # Celery Beat (scheduled tasks)
  celery-beat:
    build: ./backend
    command: celery -A app.celery beat -l info
    depends_on:
      - redis

volumes:
  postgres_data:
  redis_data:
```

### **Recursos Estimados**
```
┌─────────────────────────────────────────────────────────────┐
│ RECURSOS POR SERVICIO                                       │
├─────────────────────────────────────────────────────────────┤
│ API (2 workers):        512MB RAM, 0.5 CPU                 │
│ PostgreSQL:             512MB RAM, 0.5 CPU                 │
│ Redis:                  128MB RAM, 0.2 CPU                 │
│ Celery Worker:          256MB RAM, 0.3 CPU                 │
│ Celery Beat:            128MB RAM, 0.1 CPU                 │
├─────────────────────────────────────────────────────────────┤
│ TOTAL MÍNIMO:           ~1.5GB RAM, ~1.6 CPU              │
│ RECOMENDADO:            ~2GB RAM, 2 CPU                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📅 Timeline Detallado

### **Semana 1: Setup + Backend Core**
```
Día 1-2: Estructura proyecto
├── Crear repos (frontend/backend)
├── Docker compose base
├── PostgreSQL + Redis setup
└── CI/CD básico (GitHub Actions)

Día 3-4: Backend - Modelos y Auth
├── SQLAlchemy models (locations, operations, users)
├── Alembic migrations
├── JWT authentication
└── Endpoints básicos (/health, /auth/login)

Día 5-7: Backend - Lógica Core
├── Servicio Odoo (con retry/fallback)
├── Cache service (Redis)
├── Operaciones de picking (/move-pallet)
├── Queue offline (Celery)
└── Tests básicos
```

### **Semana 2: Frontend + Integración**
```
Día 8-10: Frontend Base
├── Vite + React + TypeScript setup
├── TailwindCSS config
├── PWA manifest + Service Worker
├── IndexedDB setup (Dexie)
└── Router + Layout base

Día 11-12: Componentes Core
├── BarcodeScanner component
├── LocationSelector component
├── PalletCard component
├── OfflineIndicator component
└── Toast notifications

Día 13-14: Integración + Offline
├── React Query hooks
├── Offline sync logic
├── Background sync
└── Error handling
```

### **Semana 3: Polish + Deploy**
```
Día 15-16: Testing + Bugs
├── E2E testing (Playwright)
├── Mobile testing (dispositivos reales)
├── Fix bugs encontrados
└── Performance optimization

Día 17-18: Monitoring + Alertas
├── Prometheus metrics
├── Grafana dashboards
├── Alertmanager config
└── Health checks

Día 19-21: Deploy + Documentación
├── NGINX config producción
├── SSL certificates
├── Deploy final
├── Documentación usuario
└── Training básico
```

---

## 🔐 Seguridad a Implementar

### **Authentication Flow**
```
┌──────────┐      ┌──────────┐      ┌──────────┐
│  Mobile  │──1──▶│   API    │──2──▶│   Odoo   │
│   PWA    │◀──4──│  FastAPI │◀──3──│  Server  │
└──────────┘      └──────────┘      └──────────┘

1. POST /auth/login {username, password}
2. Validar credenciales contra Odoo
3. Odoo retorna OK + user info
4. API genera JWT token (24h expiry)
```

### **Token Storage**
```javascript
// En PWA (seguro)
// Opción 1: HttpOnly Cookie (más seguro)
// Opción 2: Memory + Refresh Token en IndexedDB

// NUNCA: localStorage para tokens
```

### **Rate Limiting**
```python
# Por IP: 100 requests/min
# Por usuario: 300 requests/min
# Por endpoint sensible: 10 requests/min
```

---

## 📊 Métricas y Dashboards

### **Dashboard Grafana: Stock Picking**
```
┌─────────────────────────────────────────────────────────────┐
│ 📊 STOCK PICKING - LIVE DASHBOARD                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Operaciones Hoy      Latencia P95       Usuarios Online   │
│  ┌─────────────┐      ┌─────────────┐    ┌─────────────┐   │
│  │    1,234    │      │    45ms     │    │      3      │   │
│  └─────────────┘      └─────────────┘    └─────────────┘   │
│                                                             │
│  Operaciones/Hora                                          │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄ │   │
│  │ 6am                   12pm                   6pm    │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Cola Offline          Errores Odoo       Cache Hit %      │
│  ┌─────────────┐      ┌─────────────┐    ┌─────────────┐   │
│  │      0      │      │      2      │    │    98.5%    │   │
│  └─────────────┘      └─────────────┘    └─────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## ⚠️ Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Dev frontend no disponible | Media | Alto | Tener backup, o yo genero código |
| Odoo API cambia | Baja | Alto | Abstracción en servicio, tests |
| Server se queda sin RAM | Media | Alto | Monitoreo + alertas + escalado |
| PWA no funciona en iOS Safari | Media | Medio | Testing exhaustivo, fallbacks |
| IndexedDB corrupto | Baja | Medio | Backup automático, recovery |

---

## ✅ Checklist Pre-Inicio

### **Infraestructura**
- [ ] Verificar RAM disponible en servidor (mínimo 4GB total)
- [ ] Verificar espacio disco (mínimo 20GB libres)
- [ ] Confirmar acceso SSH a servidor
- [ ] Dominio/subdominio configurado (stock-picking.riofuturoprocesos.com)

### **Decisiones**
- [ ] Definir: ¿Contratar dev o DIY?
- [ ] Definir: ¿Presupuesto máximo?
- [ ] Definir: ¿Timeline deseado?

### **Accesos**
- [ ] Credenciales Odoo API (ya tienes)
- [ ] Acceso a DNS para subdominio
- [ ] GitHub repo para código

---

## 🤔 Preguntas para Ti

1. **¿Tienes conocimientos básicos de React/JavaScript?**
   - Si SÍ → Podemos hacerlo juntos (yo genero código, tú implementas)
   - Si NO → Mejor contratar frontend dev

2. **¿Cuánta RAM tiene el servidor actual?**
   - `ssh debian@167.114.114.51 "free -h"`

3. **¿Presupuesto disponible para infraestructura/dev?**
   - $0 = DIY con Claude
   - $1,000-3,000 USD = Freelancer
   - $5,000+ = Agencia

4. **¿Deadline duro o flexible?**
   - Duro = Contratar ayuda
   - Flexible = DIY viable

5. **¿Quieres subdominio separado o path?**
   - `stock-picking.riofuturoprocesos.com` (más limpio)
   - `riofuturoprocesos.com/stock-picking/` (más simple NGINX)

---

## 🚀 Próximo Paso Recomendado

**Si quieres proceder con Opción 2:**

1. **Verificar recursos del servidor** (te doy el comando)
2. **Decidir modelo de desarrollo** (DIY vs contratar)
3. **Crear estructura base del proyecto** (yo lo hago)
4. **Empezar con backend** (más crítico, yo puedo generar 100%)
5. **Frontend en paralelo o después** (dependiendo de decisión)

**¿Verificamos primero los recursos del servidor?**
