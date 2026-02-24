import { BarChart2, Package, ShoppingCart, Truck, TrendingUp, Warehouse } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { KPICard } from '@/components/shared/KPICard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { NAV_ITEMS } from '@/lib/constants'
import { usePermissions } from '@/hooks/usePermissions'
import { Link } from 'react-router-dom'
import { cn } from '@/lib/utils'

const MODULE_ICONS: Record<string, React.ElementType> = {
  home: BarChart2,
  recepciones: Truck,
  produccion: BarChart2,
  bandejas: Package,
  stock: Warehouse,
  pedidos: ShoppingCart,
  finanzas: TrendingUp,
}

export function HomeDashboard() {
  const { canAccess } = usePermissions()

  const kpis = [
    { label: 'Producción Mensual', value: 0, unit: 'kg', format: 'number' as const, loading: true },
    { label: 'Stock Total', value: 0, unit: 'kg', format: 'number' as const, loading: true },
    { label: 'Recepciones Pendientes', value: 0, format: 'number' as const, loading: true },
    { label: 'Pedidos Activos', value: 0, format: 'number' as const, loading: true },
  ]

  const modules = NAV_ITEMS.filter(
    (item) => item.path !== '/' && !item.adminOnly,
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="Dashboard"
        description={`Bienvenido al centro de control Rio Futuro · ${new Date().toLocaleDateString('es-CL', { dateStyle: 'long' })}`}
      />

      {/* KPIs */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((kpi) => (
          <KPICard key={kpi.label} {...kpi} />
        ))}
      </div>

      {/* Modules grid */}
      <div>
        <h2 className="mb-4 text-lg font-semibold">Módulos</h2>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {modules.map((module) => {
            const accessible = canAccess(module.dashboard)
            return (
              <Link
                key={module.path}
                to={accessible ? module.path : '#'}
                className={cn(
                  'group rounded-lg border bg-card p-4 transition-all hover:shadow-md',
                  accessible
                    ? 'hover:border-primary/50 hover:bg-primary/5'
                    : 'opacity-50 cursor-not-allowed',
                )}
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium">{module.label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {accessible ? 'Acceso permitido' : 'Sin acceso'}
                    </p>
                  </div>
                  {!accessible && (
                    <Badge variant="secondary" className="text-xs">Restringido</Badge>
                  )}
                </div>
              </Link>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default HomeDashboard
