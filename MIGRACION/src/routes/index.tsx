import { lazy, Suspense } from 'react'
import { createBrowserRouter, RouterProvider, Navigate } from 'react-router-dom'
import { MainLayout } from '@/components/layout/MainLayout'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { ProtectedRoute } from './ProtectedRoute'
import { LoginForm } from '@/features/auth/LoginForm'

// Lazy-loaded pages
const HomeDashboard = lazy(() => import('@/features/home/Dashboard'))
const RecepcionesPage = lazy(() => import('@/features/recepciones/RecepcionesPage'))
const ProduccionPage = lazy(() => import('@/features/produccion/ProduccionPage'))
const BandejasPage = lazy(() => import('@/features/bandejas/BandejasPage'))
const StockPage = lazy(() => import('@/features/stock/StockPage'))
const PedidosVentaPage = lazy(() => import('@/features/pedidos-venta/PedidosVentaPage'))
const FinanzasPage = lazy(() => import('@/features/finanzas/FinanzasPage'))
const RendimientoPage = lazy(() => import('@/features/rendimiento/RendimientoPage'))
const ComprasPage = lazy(() => import('@/features/compras/ComprasPage'))
const RelacionComercialPage = lazy(() => import('@/features/relacion-comercial/RelacionComercialPage'))
const ReconciliacionPage = lazy(() => import('@/features/reconciliacion/ReconciliacionPage'))
const AutomatizacionesPage = lazy(() => import('@/features/automatizaciones/AutomatizacionesPage'))
const PermisosPage = lazy(() => import('@/features/permisos/PermisosPage'))
const TrazabilidadPage = lazy(() => import('@/features/trazabilidad/TrazabilidadPage'))

const SuspenseWrapper = ({ children }: { children: React.ReactNode }) => (
  <Suspense fallback={<LoadingSpinner fullScreen />}>{children}</Suspense>
)

const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginForm />,
  },
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: (
          <ProtectedRoute dashboard="home">
            <SuspenseWrapper><HomeDashboard /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'recepciones',
        element: (
          <ProtectedRoute dashboard="recepciones">
            <SuspenseWrapper><RecepcionesPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'produccion',
        element: (
          <ProtectedRoute dashboard="produccion">
            <SuspenseWrapper><ProduccionPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'bandejas',
        element: (
          <ProtectedRoute dashboard="bandejas">
            <SuspenseWrapper><BandejasPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'stock',
        element: (
          <ProtectedRoute dashboard="stock">
            <SuspenseWrapper><StockPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'pedidos-venta',
        element: (
          <ProtectedRoute dashboard="pedidos">
            <SuspenseWrapper><PedidosVentaPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'finanzas',
        element: (
          <ProtectedRoute dashboard="finanzas">
            <SuspenseWrapper><FinanzasPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'rendimiento',
        element: (
          <ProtectedRoute dashboard="rendimiento">
            <SuspenseWrapper><RendimientoPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'compras',
        element: (
          <ProtectedRoute dashboard="compras">
            <SuspenseWrapper><ComprasPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'relacion-comercial',
        element: (
          <ProtectedRoute dashboard="comercial">
            <SuspenseWrapper><RelacionComercialPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'reconciliacion',
        element: (
          <ProtectedRoute dashboard="reconciliacion">
            <SuspenseWrapper><ReconciliacionPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'automatizaciones',
        element: (
          <ProtectedRoute dashboard="automatizaciones">
            <SuspenseWrapper><AutomatizacionesPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'permisos',
        element: (
          <ProtectedRoute dashboard="permisos">
            <SuspenseWrapper><PermisosPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      {
        path: 'trazabilidad',
        element: (
          <ProtectedRoute dashboard="rendimiento">
            <SuspenseWrapper><TrazabilidadPage /></SuspenseWrapper>
          </ProtectedRoute>
        ),
      },
      { path: '*', element: <Navigate to="/" replace /> },
    ],
  },
])

export function AppRouter() {
  return <RouterProvider router={router} />
}
