import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { FilterBar } from '@/components/forms/FilterBar'
import { DataTable } from '@/components/tables/DataTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { Badge } from '@/components/ui/badge'
import { KPICard } from '@/components/shared/KPICard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { BarChart } from '@/components/charts/BarChart'
import { CURRENT_YEAR } from '@/lib/constants'
import { cn, formatCurrency } from '@/lib/utils'
import {
  useCompras, useComprasKPIs, useComprasPorProveedor,
  useLineasCreditoResumen, useLineasCredito,
  type OrdenCompra, type LineaCreditoProveedor,
} from '@/api/compras'

const estadoBadge: Record<string, 'success' | 'warning' | 'default' | 'destructive'> = {
  purchase: 'success',
  draft: 'warning',
  cancel: 'destructive',
}

const columns: ColumnDef<OrdenCompra>[] = [
  { accessorKey: 'name', header: 'OC', enableSorting: true },
  { accessorKey: 'proveedor', header: 'Proveedor', enableSorting: true },
  { accessorKey: 'producto', header: 'Producto' },
  { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },
  {
    accessorKey: 'estado',
    header: 'Estado',
    cell: ({ getValue }) => {
      const v = String(getValue())
      const labels: Record<string, string> = { purchase: 'Confirmada', draft: 'Borrador', cancel: 'Cancelada' }
      return <Badge variant={estadoBadge[v] ?? 'default'}>{labels[v] ?? v}</Badge>
    },
  },
  {
    accessorKey: 'monto_total',
    header: 'Total',
    cell: ({ getValue }) => formatCurrency(Number(getValue())),
    enableSorting: true,
  },
]

export function ComprasPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])
  const [fechaDesde, setFechaDesde] = useState('2025-11-20')
  const [lcEnabled, setLcEnabled] = useState(false)
  const [expandedProviders, setExpandedProviders] = useState<Set<number>>(new Set())

  const { data: ocs = [], isLoading } = useCompras(year, months)
  const { data: kpis, isLoading: loadingKPIs } = useComprasKPIs(year, months)
  const { data: porProveedor = [], isLoading: loadingProv } = useComprasPorProveedor(year, months)
  const { data: lcResumen, isLoading: loadingLcResumen } = useLineasCreditoResumen(fechaDesde, lcEnabled)
  const { data: lcProveedores = [], isLoading: loadingLcProv } = useLineasCredito(fechaDesde, lcEnabled)

  const toggleProvider = (id: number) => {
    setExpandedProviders(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const estadoColor = (estado: string) => {
    if (estado === 'Sin cupo') return 'text-red-400 border-red-500/30 bg-red-500/10'
    if (estado === 'Cupo bajo') return 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10'
    return 'text-green-400 border-green-500/30 bg-green-500/10'
  }

  return (
    <div className="space-y-4">
      <PageHeader title="Compras" description="Órdenes de compra, proveedores y estado">
        <ExportButton data={ocs as unknown as Record<string, unknown>[]} filename="compras" />
      </PageHeader>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Total OCs" value={kpis?.total_ocs ?? ocs.length} loading={loadingKPIs} />
        <KPICard label="Monto Total" value={kpis?.monto_total ?? ocs.reduce((s, r) => s + r.monto_total, 0)} format="currency" loading={loadingKPIs} />
        <KPICard label="OCs Confirmadas" value={kpis?.ocs_confirmadas ?? ocs.filter(r => r.estado === 'purchase').length} loading={loadingKPIs} />
        <KPICard label="Proveedores Activos" value={kpis?.proveedores_activos ?? new Set(ocs.map(r => r.proveedor)).size} loading={loadingKPIs} />
      </div>

      <Tabs defaultValue="listado">
        <TabsList>
          <TabsTrigger value="listado">📋 Listado OCs</TabsTrigger>
          <TabsTrigger value="proveedores">🏭 Por Proveedor</TabsTrigger>
          <TabsTrigger value="lineas-credito">💳 Líneas de Crédito</TabsTrigger>
        </TabsList>

        <TabsContent value="listado" className="mt-4">
          <DataTable
            columns={columns}
            data={ocs}
            loading={isLoading}
            searchPlaceholder="Buscar OC o proveedor..."
          />
        </TabsContent>

        <TabsContent value="proveedores" className="mt-4">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">Monto por Proveedor</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingProv ? <LoadingSpinner /> : (
                <BarChart
                  data={(porProveedor as { proveedor: string; monto_total: number }[]).slice(0, 20)}
                  xKey="proveedor"
                  bars={[{ key: 'monto_total', name: 'Monto Total' }]}
                  yFormatter={(v) => formatCurrency(v)}
                  horizontal
                  height={440}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Líneas de Crédito */}
        <TabsContent value="lineas-credito" className="mt-4 space-y-4">
          {/* Date filter + load button */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Desde</label>
                  <input
                    type="date"
                    value={fechaDesde}
                    onChange={e => setFechaDesde(e.target.value)}
                    className="rounded border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <button
                  onClick={() => setLcEnabled(true)}
                  className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  Cargar datos
                </button>
                {lcEnabled && (
                  <button
                    onClick={() => setLcEnabled(false)}
                    className="text-xs text-muted-foreground hover:text-foreground"
                  >
                    Limpiar
                  </button>
                )}
              </div>
            </CardContent>
          </Card>

          {!lcEnabled ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              Selecciona una fecha y presiona "Cargar datos" para ver las líneas de crédito.
            </div>
          ) : loadingLcResumen || loadingLcProv ? (
            <LoadingSpinner />
          ) : (
            <>
              {/* KPIs resumen */}
              {lcResumen && (
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <KPICard label="Proveedores" value={lcResumen.total_proveedores} />
                  <KPICard label="Línea Total" value={lcResumen.total_linea} format="currency" />
                  <KPICard label="Monto Usado" value={lcResumen.total_usado} format="currency" />
                  <KPICard label="Disponible" value={lcResumen.total_disponible} format="currency" />
                  <KPICard label="Uso Global %" value={lcResumen.pct_uso_global} format="percent" />
                  <KPICard label="Sin Cupo 🔴" value={lcResumen.sin_cupo} />
                  <KPICard label="Cupo Bajo 🟡" value={lcResumen.cupo_bajo} />
                  <KPICard label="Disponibles 🟢" value={lcResumen.disponibles} />
                </div>
              )}

              {/* Bar chart */}
              {lcProveedores.length > 0 && (
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">Uso % por Proveedor</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <BarChart
                      data={lcProveedores.slice(0, 25).map(p => ({ name: p.partner_name, pct: p.pct_uso }))}
                      xKey="name"
                      bars={[{ key: 'pct', name: 'Uso %' }]}
                      yFormatter={v => `${v}%`}
                      horizontal
                      height={Math.min(50 + lcProveedores.length * 24, 600)}
                    />
                  </CardContent>
                </Card>
              )}

              {/* Per-provider cards */}
              <div className="space-y-2">
                {(lcProveedores as LineaCreditoProveedor[]).map((prov) => {
                  const isOpen = expandedProviders.has(prov.partner_id)
                  return (
                    <Card key={prov.partner_id} className="overflow-hidden">
                      <button
                        className="w-full text-left"
                        onClick={() => toggleProvider(prov.partner_id)}
                      >
                        <CardHeader className="py-3">
                          <div className="flex flex-wrap items-center gap-3">
                            <span className="text-2xl">{prov.alerta}</span>
                            <div className="flex-1 min-w-0">
                              <p className="font-medium truncate">{prov.partner_name}</p>
                              <p className="text-xs text-muted-foreground">
                                {formatCurrency(prov.monto_usado)} / {formatCurrency(prov.linea_total)} &nbsp;|&nbsp; {prov.pct_uso.toFixed(1)}% usado
                              </p>
                            </div>
                            <span className={cn('text-xs px-2 py-1 rounded border', estadoColor(prov.estado))}>
                              {prov.estado}
                            </span>
                            <span className="text-muted-foreground text-sm">{isOpen ? '▲' : '▼'}</span>
                          </div>
                          {/* Progress bar */}
                          <div className="mt-2 h-2 rounded-full bg-muted overflow-hidden">
                            <div
                              className={cn('h-full rounded-full transition-all', prov.estado === 'Sin cupo' ? 'bg-red-500' : prov.estado === 'Cupo bajo' ? 'bg-yellow-500' : 'bg-green-500')}
                              style={{ width: `${Math.min(prov.pct_uso, 100)}%` }}
                            />
                          </div>
                        </CardHeader>
                      </button>

                      {isOpen && (
                        <CardContent className="pt-0 border-t">
                          {/* 5 KPI mini-cards */}
                          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2 mt-3 mb-4">
                            {[
                              { label: 'Línea Total', value: prov.linea_total },
                              { label: 'Facturas', value: prov.monto_facturas },
                              { label: 'Recepciones', value: prov.monto_recepciones },
                              { label: 'Total Usado', value: prov.monto_usado },
                              { label: 'Disponible', value: prov.disponible },
                            ].map(k => (
                              <div key={k.label} className="rounded border p-2 text-center">
                                <p className="text-xs text-muted-foreground">{k.label}</p>
                                <p className="text-sm font-semibold">{formatCurrency(k.value)}</p>
                              </div>
                            ))}
                          </div>

                          {/* Detail table */}
                          {prov.detalle && prov.detalle.length > 0 && (
                            <div className="overflow-auto">
                              <table className="w-full text-sm">
                                <thead>
                                  <tr className="border-b bg-muted/40">
                                    <th className="px-2 py-1 text-left">Tipo</th>
                                    <th className="px-2 py-1 text-left">Referencia</th>
                                    <th className="px-2 py-1 text-left">Fecha</th>
                                    <th className="px-2 py-1 text-right">Monto</th>
                                  </tr>
                                </thead>
                                <tbody>
                                  {prov.detalle.map((d, i) => (
                                    <tr key={i} className="border-b hover:bg-muted/20">
                                      <td className="px-2 py-1">
                                        <Badge variant="default">{d.tipo}</Badge>
                                      </td>
                                      <td className="px-2 py-1 font-mono text-xs">{d.referencia}</td>
                                      <td className="px-2 py-1 text-muted-foreground text-xs">{d.fecha}</td>
                                      <td className="px-2 py-1 text-right">{formatCurrency(d.monto)}</td>
                                    </tr>
                                  ))}
                                </tbody>
                              </table>
                            </div>
                          )}
                        </CardContent>
                      )}
                    </Card>
                  )
                })}
              </div>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ComprasPage
