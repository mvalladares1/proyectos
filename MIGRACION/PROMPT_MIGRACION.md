# 🚀 Proyecto: Migración Dashboard Rio Futuro - Streamlit a React

## 📋 Resumen Ejecutivo

Migración completa del sistema de dashboards empresarial "Rio Futuro" desde Streamlit (Python) a una Single Page Application (SPA) moderna en React. El backend FastAPI existente se reutiliza sin modificaciones.

---

## 🎯 Objetivo

Crear un frontend moderno, responsivo y altamente interactivo que reemplace completamente la interfaz Streamlit actual, manteniendo todas las funcionalidades existentes y mejorando significativamente la experiencia de usuario.

---

## 🛠️ Stack Tecnológico Seleccionado

### Core
| Tecnología | Versión | Propósito |
|------------|---------|-----------|
| **React** | 18+ | Framework UI |
| **Vite** | 5+ | Build tool y dev server |
| **TypeScript** | 5+ | Type safety |
| **React Router** | v6 | Client-side routing |

### Estado y Data Fetching
| Tecnología | Propósito |
|------------|-----------|
| **TanStack Query** (v5) | Server state, caching, mutations |
| **Zustand** | Client state global (si necesario) |

### UI y Estilos
| Tecnología | Propósito |
|------------|-----------|
| **shadcn/ui** | Componentes base (Radix + Tailwind) |
| **Tailwind CSS** | Utility-first styling |
| **Lucide React** | Iconografía |
| **clsx + tailwind-merge** | Class composition |

### Tablas y Gráficos
| Tecnología | Propósito |
|------------|-----------|
| **TanStack Table** | Tablas complejas con sorting, filtering |
| **AG-Grid Community** | Alternativa para tablas tipo Excel |
| **Recharts** | Gráficos principales |
| **Tremor** | Componentes dashboard-ready |

### Formularios y Validación
| Tecnología | Propósito |
|------------|-----------|
| **React Hook Form** | Manejo de formularios |
| **Zod** | Schema validation |

### Utilidades
| Tecnología | Propósito |
|------------|-----------|
| **date-fns** | Manejo de fechas |
| **xlsx** | Exportación a Excel |
| **react-hot-toast** | Notificaciones |

---

## 🔌 Backend Existente (FastAPI)

### Información de Conexión

```typescript
// Configuración de APIs
const API_CONFIG = {
  production: 'https://riofuturoprocesos.com/api',
  development: 'http://localhost:8002',
};
```

### Endpoints Principales

| Ruta Base | Descripción | Métodos Principales |
|-----------|-------------|---------------------|
| `/auth` | Autenticación | `POST /login`, `GET /me` |
| `/permissions` | Sistema de permisos | `POST /check`, `GET /dashboards/{user}` |
| `/produccion` | Datos de producción | `GET /lineas`, `GET /tuneles`, `GET /fabricaciones` |
| `/bandejas` | Gestión de bandejas | `GET /`, `GET /seguimiento` |
| `/stock` | Inventario | `GET /`, `GET /movimientos` |
| `/flujo-caja` | Flujo de caja | `GET /`, `GET /composicion` |
| `/recepciones` | Recepciones MP | `GET /`, `GET /kpis`, `GET /aprobaciones` |
| `/comercial` | Relación comercial | `GET /analisis`, `GET /clientes` |
| `/reconciliacion` | Reconciliación | `GET /`, `GET /detalle` |
| `/automatizaciones` | Automatizaciones | `GET /monitor`, `POST /ejecutar` |
| `/compras` | Órdenes de compra | `GET /`, `GET /pendientes` |
| `/rendimiento` | Métricas rendimiento | `GET /`, `GET /historico` |
| `/estado-resultado` | Estado de resultados | `GET /`, `GET /comparativo` |
| `/presupuesto` | Presupuestos | `GET /`, `GET /vs-real` |

### Autenticación

El backend usa autenticación básica contra Odoo:

```typescript
// Login request
POST /auth/login
Body: { username: string, password: string }
Response: { access_token: string, user: { name, email, roles } }

// Las credenciales se envían como Basic Auth en cada request
// O se usa el JWT token en header Authorization: Bearer <token>
```

### Sistema de Permisos

```typescript
// Verificar acceso a página
POST /permissions/check
Body: { username: string, dashboard: string, page: string }
Response: { allowed: boolean, reason?: string }

// Obtener dashboards permitidos
GET /permissions/dashboards/{username}
Response: { dashboards: string[], pages: Record<string, string[]> }
```

---

## 📱 Páginas a Migrar (12 Módulos)

### 1. Home (`/`)
- Landing con métricas generales del negocio
- Cards con KPIs principales
- Accesos rápidos a módulos
- Estado de sistemas

### 2. Recepciones (`/recepciones`)
**Tabs internos:**
- 📊 KPIs - Indicadores de recepción
- 📋 Gestión - Tabla de recepciones con acciones
- 📈 Curva - Gráfico de curva de recepciones
- ✅ Aprobaciones - Workflow de aprobaciones
- 🚛 Fletes - Aprobaciones de fletes
- 📦 Pallets - Seguimiento de pallets

### 3. Producción (`/produccion`)
**Tabs internos:**
- 📊 Por Línea - Gráficos de producción por línea
- 🏭 Por Túnel - Producción por túnel de congelado
- 📈 Rendimiento - Métricas de rendimiento
- 🔄 Clasificación - Clasificación de producto
- 📋 Detalle - Tabla detallada de producción

### 4. Bandejas (`/bandejas`)
- Seguimiento de bandejas en planta
- Estados y ubicaciones
- Historial de movimientos

### 5. Stock (`/stock`)
- Inventario actual por ubicación
- Movimientos de stock
- Alertas de stock mínimo
- Valorización

### 6. Pedidos Venta (`/pedidos-venta`)
- Lista de pedidos de venta
- Estados de pedidos
- Detalle de líneas

### 7. Finanzas (`/finanzas`) ⚠️ **COMPLEJO**
**Tabs internos:**
- 📊 Estado de Resultados - Ingresos, costos, márgenes
- 📁 Cuentas (CG) - Plan de cuentas contables
- 💵 Flujo de Caja - **Tabla enterprise compleja con:**
  - Filas expandibles multinivel (4 niveles)
  - Frozen columns (columna izquierda fija)
  - Heatmaps por celda según valor
  - Click en celda → Modal de composición
  - Drag & drop para reordenar
  - Exportación a Excel

### 8. Rendimiento (`/rendimiento`)
- Métricas de rendimiento por período
- Comparativos históricos
- Gráficos de tendencia

### 9. Compras (`/compras`)
- Órdenes de compra
- Estado de OCs
- Proveedores

### 10. Permisos (`/permisos`) 🔒 **ADMIN**
- Gestión de usuarios y permisos
- Asignación de dashboards por usuario
- Configuración de accesos por página

### 11. Relación Comercial (`/relacion-comercial`)
- Análisis de clientes
- Métricas comerciales
- Seguimiento de ventas

### 12. Reconciliación Producción (`/reconciliacion`)
- Reconciliación de consumos vs producción
- Diferencias y ajustes
- Reportes de discrepancias

---

## 🏗️ Estructura de Carpetas

```
MIGRACION/
├── 📁 src/
│   ├── 📁 api/                    # TanStack Query hooks
│   │   ├── client.ts              # Axios/fetch base config
│   │   ├── auth.ts                # useLogin, useLogout, useMe
│   │   ├── permissions.ts         # usePermissions, useCheckAccess
│   │   ├── produccion.ts          # useProduccion, useLineas, etc.
│   │   ├── finanzas.ts            # useFlujoCaja, useEERR, etc.
│   │   ├── recepciones.ts         # useRecepciones, useKPIs, etc.
│   │   └── ...                    # Un archivo por dominio
│   │
│   ├── 📁 components/
│   │   ├── 📁 ui/                 # shadcn components (button, card, etc)
│   │   ├── 📁 layout/
│   │   │   ├── MainLayout.tsx     # Layout principal con sidebar
│   │   │   ├── Sidebar.tsx        # Navegación lateral
│   │   │   ├── Header.tsx         # Header con user info
│   │   │   └── PageHeader.tsx     # Header de cada página
│   │   ├── 📁 charts/
│   │   │   ├── LineChart.tsx      # Wrapper Recharts
│   │   │   ├── BarChart.tsx
│   │   │   ├── PieChart.tsx
│   │   │   └── Heatmap.tsx
│   │   ├── 📁 tables/
│   │   │   ├── DataTable.tsx      # Tabla base con TanStack
│   │   │   ├── EnterpriseTable.tsx # Tabla tipo Flujo de Caja
│   │   │   └── ExportButton.tsx   # Exportar a Excel
│   │   ├── 📁 forms/
│   │   │   ├── DateRangePicker.tsx
│   │   │   ├── MultiSelect.tsx
│   │   │   └── FilterBar.tsx
│   │   └── 📁 shared/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorBoundary.tsx
│   │       ├── EmptyState.tsx
│   │       └── KPICard.tsx
│   │
│   ├── 📁 features/               # Módulos por dominio
│   │   ├── 📁 auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── AuthProvider.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── 📁 home/
│   │   │   └── Dashboard.tsx
│   │   ├── 📁 recepciones/
│   │   │   ├── RecepcionesPage.tsx
│   │   │   ├── tabs/
│   │   │   │   ├── KPIsTab.tsx
│   │   │   │   ├── GestionTab.tsx
│   │   │   │   ├── CurvaTab.tsx
│   │   │   │   └── AprobacionesTab.tsx
│   │   │   └── components/
│   │   │       └── RecepcionCard.tsx
│   │   ├── 📁 produccion/
│   │   │   ├── ProduccionPage.tsx
│   │   │   └── tabs/...
│   │   ├── 📁 finanzas/
│   │   │   ├── FinanzasPage.tsx
│   │   │   ├── tabs/
│   │   │   │   ├── EERRTab.tsx
│   │   │   │   ├── CGTab.tsx
│   │   │   │   └── FlujoCajaTab.tsx
│   │   │   └── components/
│   │   │       ├── FlujoCajaTable.tsx  # Tabla enterprise
│   │   │       └── ComposicionModal.tsx
│   │   └── ...                    # Resto de features
│   │
│   ├── 📁 hooks/
│   │   ├── useAuth.ts             # Auth context hook
│   │   ├── usePermissions.ts      # Permisos hook
│   │   ├── useTheme.ts            # Dark/light mode
│   │   └── useLocalStorage.ts
│   │
│   ├── 📁 lib/
│   │   ├── utils.ts               # cn(), formatters, etc.
│   │   ├── constants.ts           # Constantes globales
│   │   └── validators.ts          # Zod schemas
│   │
│   ├── 📁 providers/
│   │   ├── QueryProvider.tsx      # TanStack Query provider
│   │   ├── AuthProvider.tsx       # Auth context
│   │   └── ThemeProvider.tsx      # Theme context
│   │
│   ├── 📁 routes/
│   │   ├── index.tsx              # Router config
│   │   └── ProtectedRoute.tsx
│   │
│   ├── 📁 styles/
│   │   └── globals.css            # Tailwind + custom styles
│   │
│   ├── 📁 types/
│   │   ├── api.ts                 # API response types
│   │   ├── auth.ts                # User, Session types
│   │   ├── produccion.ts          # Domain types
│   │   └── finanzas.ts
│   │
│   ├── App.tsx                    # Root component
│   ├── main.tsx                   # Entry point
│   └── vite-env.d.ts
│
├── 📁 public/
│   ├── favicon.ico
│   └── logo.svg
│
├── .env.example
├── .gitignore
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
├── tsconfig.json
├── tsconfig.node.json
├── vite.config.ts
└── README.md
```

---

## 🎨 Diseño y UX

### Tema
- **Dark mode por defecto** (consistente con la app actual)
- Paleta de colores:
  ```css
  --background: #0a0a0a
  --foreground: #fafafa
  --primary: #3b82f6 (blue-500)
  --secondary: #6366f1 (indigo-500)
  --accent: #8b5cf6 (violet-500)
  --success: #22c55e (green-500)
  --warning: #f59e0b (amber-500)
  --danger: #ef4444 (red-500)
  ```

### Layout Principal
```
┌─────────────────────────────────────────────────────────┐
│  HEADER: Logo | Breadcrumb | User Menu | Notifications  │
├──────────┬──────────────────────────────────────────────┤
│          │                                              │
│  SIDEBAR │           MAIN CONTENT                       │
│          │                                              │
│  - Home  │   ┌────────────────────────────────────┐    │
│  - Recep │   │  PAGE HEADER + FILTERS             │    │
│  - Prod  │   ├────────────────────────────────────┤    │
│  - ...   │   │                                    │    │
│          │   │  TABS (si aplica)                  │    │
│          │   │                                    │    │
│          │   │  CONTENT                           │    │
│          │   │                                    │    │
│          │   └────────────────────────────────────┘    │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

### Responsive
- **Desktop**: Sidebar visible, tablas completas
- **Tablet**: Sidebar colapsable, tablas con scroll horizontal
- **Mobile**: Sidebar tipo drawer, tablas en modo card/list

---

## 🔐 Autenticación y Permisos

### Flujo de Auth
```
1. Usuario accede a /login
2. Ingresa credenciales
3. POST /auth/login → obtiene token + user info
4. Token se guarda en localStorage/cookie
5. Redirect a Home
6. En cada request: Authorization: Bearer <token>
7. En cada página: verificar permisos con usePermissions
```

### Hook usePermissions
```typescript
const usePermissions = () => {
  const { user } = useAuth();
  
  const checkAccess = async (dashboard: string, page?: string) => {
    const response = await api.post('/permissions/check', {
      username: user.username,
      dashboard,
      page
    });
    return response.data.allowed;
  };
  
  return { checkAccess };
};
```

### Componente ProtectedRoute
```typescript
const ProtectedRoute = ({ 
  children, 
  dashboard, 
  page 
}: { 
  children: ReactNode;
  dashboard: string;
  page?: string;
}) => {
  const { isAuthenticated } = useAuth();
  const { checkAccess } = usePermissions();
  const [hasAccess, setHasAccess] = useState<boolean | null>(null);
  
  useEffect(() => {
    if (isAuthenticated) {
      checkAccess(dashboard, page).then(setHasAccess);
    }
  }, [isAuthenticated, dashboard, page]);
  
  if (!isAuthenticated) return <Navigate to="/login" />;
  if (hasAccess === null) return <LoadingSpinner />;
  if (!hasAccess) return <AccessDenied />;
  
  return <>{children}</>;
};
```

---

## 📊 Componentes Críticos a Implementar

### 1. EnterpriseTable (Flujo de Caja)

Características requeridas:
- ✅ Filas expandibles (4 niveles de anidación)
- ✅ Columna izquierda frozen (sticky)
- ✅ Heatmap por celda (colores según valor)
- ✅ Click en celda → Modal de composición
- ✅ Totales y subtotales por fila/columna
- ✅ Sparklines en columna total
- ✅ Exportación a Excel
- ⚠️ Drag & drop para reordenar (nice to have)

```typescript
interface EnterpriseTableProps {
  data: FlujoCajaData;
  columns: ColumnDef[];
  onCellClick?: (row: Row, column: Column, value: number) => void;
  expandable?: boolean;
  frozenColumns?: number;
  heatmapConfig?: HeatmapConfig;
}
```

### 2. FilterBar
```typescript
interface FilterBarProps {
  filters: {
    year?: { options: number[]; default: number };
    months?: { options: string[]; multiple: boolean };
    dateRange?: boolean;
    custom?: FilterConfig[];
  };
  onFilterChange: (filters: FilterValues) => void;
}
```

### 3. KPICard
```typescript
interface KPICardProps {
  title: string;
  value: string | number;
  change?: { value: number; type: 'increase' | 'decrease' };
  icon?: ReactNode;
  trend?: number[];
  loading?: boolean;
}
```

---

## 📝 Tareas de Implementación

### Fase 1: Setup Inicial (1-2 días)
- [ ] Crear proyecto Vite + React + TypeScript
- [ ] Configurar Tailwind CSS
- [ ] Instalar y configurar shadcn/ui
- [ ] Configurar TanStack Query
- [ ] Crear estructura de carpetas
- [ ] Configurar ESLint + Prettier

### Fase 2: Core (2-3 días)
- [ ] Implementar AuthProvider y login
- [ ] Crear MainLayout con Sidebar
- [ ] Implementar sistema de rutas
- [ ] Crear ProtectedRoute con permisos
- [ ] Implementar API client base

### Fase 3: Componentes Base (2-3 días)
- [ ] DataTable genérico
- [ ] Charts (Line, Bar, Pie)
- [ ] FilterBar
- [ ] KPICard
- [ ] LoadingSpinner, ErrorBoundary

### Fase 4: Páginas Simples (3-4 días)
- [ ] Home Dashboard
- [ ] Recepciones (con tabs)
- [ ] Producción
- [ ] Stock
- [ ] Bandejas

### Fase 5: Páginas Complejas (4-5 días)
- [ ] Finanzas con EnterpriseTable
- [ ] Permisos (admin)
- [ ] Reconciliación
- [ ] Relación Comercial

### Fase 6: Polish (2-3 días)
- [ ] Responsive design
- [ ] Animaciones y transiciones
- [ ] Exportación Excel
- [ ] Testing básico
- [ ] Documentación

---

## 🐳 Docker & Deployment

### Dockerfile
```dockerfile
# Build stage
FROM node:20-alpine as builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Nginx Config
```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;
    
    location / {
        try_files $uri $uri/ /index.html;
    }
    
    location /api {
        proxy_pass http://rio-api-prod:8000;
    }
}
```

### docker-compose.yml
```yaml
version: '3.8'
services:
  frontend:
    build: .
    container_name: rio-frontend
    ports:
      - "3000:80"
    depends_on:
      - api
    networks:
      - rio-network
```

---

## ⚠️ Notas Importantes

1. **Backend no se modifica** - Solo consumimos la API existente
2. **Mantener paridad funcional** - Toda feature de Streamlit debe existir en React
3. **Dark mode obligatorio** - Consistencia con la app actual
4. **Mobile-first en diseño** - Aunque desktop es prioridad
5. **Performance** - Lazy loading de rutas, memoización, virtualized tables
6. **Accesibilidad** - shadcn/ui ya incluye ARIA, mantenerlo
7. **Código limpio** - TypeScript estricto, componentes pequeños

---

## 🔗 Referencias

- [Vite](https://vitejs.dev/)
- [shadcn/ui](https://ui.shadcn.com/)
- [TanStack Query](https://tanstack.com/query)
- [TanStack Table](https://tanstack.com/table)
- [Recharts](https://recharts.org/)
- [Tremor](https://tremor.so/)
- [React Router](https://reactrouter.com/)
- [React Hook Form](https://react-hook-form.com/)
- [Zod](https://zod.dev/)

---

## 📞 Contacto

Proyecto: Rio Futuro Dashboards
Repositorio: `proyectos/MIGRACION`
Backend API: `/backend` (mismo repo)
