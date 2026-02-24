# Rio Futuro Dashboard — React SPA

Migración del sistema de dashboards empresarial desde Streamlit (Python) a una Single Page Application moderna en React. El backend FastAPI existente se reutiliza sin modificaciones.

## Stack

| Capa | Tecnología |
|------|-----------|
| UI | React 18 + Vite 5 + TypeScript 5 (strict) |
| Estilos | Tailwind CSS 3 + shadcn/ui (dark mode) |
| Estado servidor | TanStack Query v5 |
| Tablas | TanStack Table v8 |
| Gráficos | Recharts 2 |
| Routing | React Router v6 |
| HTTP | Axios 1.7 |
| Formularios | react-hook-form + Zod |
| Auth | JWT en localStorage |
| Exportación | xlsx |

## Módulos

| Ruta | Módulo |
|------|--------|
| `/` | Home / Dashboard |
| `/recepciones` | Recepciones (5 tabs) |
| `/produccion` | Producción (4 tabs) |
| `/bandejas` | Bandejas |
| `/stock` | Stock |
| `/pedidos-venta` | Pedidos de Venta |
| `/finanzas` | Finanzas (EERR + Flujo de Caja + CG) |
| `/rendimiento` | Rendimiento |
| `/compras` | Compras |
| `/relacion-comercial` | Relación Comercial |
| `/reconciliacion` | Reconciliación Producción |
| `/automatizaciones` | Monitor de Automatizaciones |
| `/permisos` | Gestión de Permisos (admin) |

## Inicio rápido

```bash
# 1. Copiar variables de entorno
cp .env.example .env
# Editar VITE_API_URL si el backend no corre en localhost:8002

# 2. Instalar dependencias
npm install

# 3. Levantar dev server (http://localhost:3000)
npm run dev
```

> El backend FastAPI debe estar corriendo en `http://localhost:8002`.  
> Vite proxea `/api/*` automáticamente para evitar problemas de CORS.

## Scripts

```bash
npm run dev        # Dev server con HMR
npm run build      # Build de producción en dist/
npm run preview    # Previsualizar build de producción
npm run lint       # ESLint
```

## Build de producción (Docker)

```bash
# Construir imagen
docker build -t rio-futuro-dashboard .

# Levantar con compose (incluye backend)
docker compose up -d
```

La imagen resultante (~25 MB) sirve el SPA con nginx y proxea `/api/*` al backend FastAPI.

## Estructura

```
src/
├── api/          # TanStack Query hooks + Axios (un archivo por módulo)
├── components/
│   ├── charts/   # LineChart, BarChart, PieChart, Heatmap
│   ├── forms/    # FilterBar, DateRangePicker, MultiSelect
│   ├── layout/   # MainLayout, Sidebar, Header
│   ├── shared/   # KPICard, LoadingSpinner, ErrorBoundary, EmptyState
│   ├── tables/   # DataTable, EnterpriseTable (flujo de caja), ExportButton
│   └── ui/       # shadcn/ui (Radix primitives)
├── features/     # Páginas por módulo
├── hooks/        # useAuth, usePermissions, useLocalStorage
├── lib/          # utils, constants, validators
├── providers/    # QueryProvider, AuthProvider
├── routes/       # Router + ProtectedRoute
└── types/        # Tipos TypeScript globales
```

## Convenciones

- Componentes en `PascalCase.tsx`
- Hooks en `useCamelCase.ts`
- API hooks en `src/api/<módulo>.ts`, exportando `use<Módulo>()`
- Siempre tipar retornos de `useQuery` con generics: `useQuery<TipoData[]>`
- Dark mode por defecto vía `class="dark"` en `<html>`
