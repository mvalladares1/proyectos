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
import { formatCurrency } from '@/lib/utils'
import { usePedidosVenta, useProyeccionVentas, useCalendarioVentas, useProgresoVentas, type PedidoVenta } from '@/api/pedidos'

const badgeVariant: Record<string, 'success' | 'warning' | 'default' | 'destructive'> = {
  sale: 'success',
  draft: 'warning',
  cancel: 'destructive',
}

const columns: ColumnDef<PedidoVenta>[] = [
  { accessorKey: 'name', header: 'Pedido', enableSorting: true },
  { accessorKey: 'cliente', header: 'Cliente', enableSorting: true },
  { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },
  {
    accessorKey: 'estado',
    header: 'Estado',
    cell: ({ getValue }) => {
      const v = String(getValue())
      const labels: Record<string, string> = { sale: 'Confirmado', draft: 'Borrador', cancel: 'Cancelado' }
      return <Badge variant={badgeVariant[v] ?? 'default'}>{labels[v] ?? v}</Badge>
    },
  },
  { accessorKey: 'lineas', header: 'Líneas' },
  {
    accessorKey: 'monto_total',
    header: 'Total',
    cell: ({ getValue }) => formatCurrency(Number(getValue())),
    enableSorting: true,
  },
]

export function PedidosVentaPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])

  // Proyección date range (default: today → +90d)
  const [proyFechaInicio, setProyFechaInicio] = useState(() => new Date().toISOString().slice(0, 10))
  const [proyFechaFin, setProyFechaFin] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() + 90); return d.toISOString().slice(0, 10)
  })
  const [proyEstado, setProyEstado] = useState('')
  const [proyEnabled, setProyEnabled] = useState(false)

  // Calendario date range
  const [calFechaInicio, setCalFechaInicio] = useState(() => new Date().toISOString().slice(0, 10))
  const [calFechaFin, setCalFechaFin] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() + 30); return d.toISOString().slice(0, 10)
  })
  const [calEnabled, setCalEnabled] = useState(false)

  const { data: pedidos = [], isLoading } = usePedidosVenta(year, months)
  const { data: progreso = [], isLoading: loadingProg } = useProgresoVentas(year, months)
  const { data: proyeccion = [], isLoading: loadingProy, refetch: refetchProy } = useProyeccionVentas(proyFechaInicio, proyFechaFin, proyEstado || undefined, proyEnabled)
  const { data: calendario = [], isLoading: loadingCal, refetch: refetchCal } = useCalendarioVentas(calFechaInicio, calFechaFin, calEnabled)

  const confirmados = pedidos.filter(r => r.estado === 'sale')
  const totalMonto = pedidos.reduce((s, r) => s + r.monto_total, 0)
  const montoPromedio = pedidos.length ? totalMonto / pedidos.length : 0

  // Group by cliente for chart
  const porCliente = Object.entries(
    pedidos.reduce((acc, r) => {
      acc[r.cliente] = (acc[r.cliente] ?? 0) + r.monto_total
      return acc
    }, {} as Record<string, number>)
  )
    .map(([cliente, monto_total]) => ({ cliente, monto_total }))
    .sort((a, b) => b.monto_total - a.monto_total)
    .slice(0, 15)

  return (
    <div className="space-y-4">
      <PageHeader title="Pedidos de Venta" description="Listado y estado de pedidos de venta">
        <ExportButton data={pedidos as unknown as Record<string, unknown>[]} filename="pedidos_venta" />
      </PageHeader>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Total Pedidos" value={pedidos.length} loading={isLoading} />
        <KPICard label="Confirmados" value={confirmados.length} loading={isLoading} />
        <KPICard label="Monto Total" value={totalMonto} format="currency" loading={isLoading} />
        <KPICard label="Monto Promedio" value={montoPromedio} format="currency" loading={isLoading} />
      </div>

      <Tabs defaultValue="listado">
        <TabsList>
          <TabsTrigger value="listado">📋 Listado</TabsTrigger>
          <TabsTrigger value="clientes">👥 Por Cliente</TabsTrigger>
          <TabsTrigger value="progreso">📊 Progreso Ventas</TabsTrigger>
          <TabsTrigger value="proyeccion">🔭 Proyección</TabsTrigger>
          <TabsTrigger value="calendario">📅 Calendario</TabsTrigger>
        </TabsList>

        <TabsContent value="listado" className="mt-4">
          <DataTable
            columns={columns}
            data={pedidos}
            loading={isLoading}
            searchPlaceholder="Buscar pedido o cliente..."
          />
        </TabsContent>

        <TabsContent value="clientes" className="mt-4">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">Monto por Cliente (Top 15)</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? <LoadingSpinner /> : (
                <BarChart
                  data={porCliente}
                  xKey="cliente"
                  bars={[{ key: 'monto_total', name: 'Monto Total' }]}
                  yFormatter={(v) => formatCurrency(v)}
                  horizontal
                  height={420}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Progreso de Ventas */}
        <TabsContent value="progreso" className="mt-4">
          <DataTable
            columns={[
              { accessorKey: 'cliente', header: 'Cliente', enableSorting: true },
              { accessorKey: 'pedidos_total', header: 'Total Pedidos', enableSorting: true },
              { accessorKey: 'pedidos_confirmados', header: 'Confirmados', enableSorting: true },
              { accessorKey: 'pedidos_entregados', header: 'Entregados', enableSorting: true },
              { accessorKey: 'monto_total', header: 'Monto Total', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
              { accessorKey: 'monto_facturado', header: 'Facturado', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
              { accessorKey: 'avance_pct', header: 'Avance %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },
            ]}
            data={progreso}
            loading={loadingProg}
            searchPlaceholder="Buscar cliente..."
          />
        </TabsContent>

        {/* Proyección de Ventas */}
        <TabsContent value="proyeccion" className="mt-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-base">Filtros — Proyección de Ventas</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Desde</label>
                    <input type="date" value={proyFechaInicio} onChange={e => setProyFechaInicio(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Hasta</label>
                    <input type="date" value={proyFechaFin} onChange={e => setProyFechaFin(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Estado</label>
                    <select value={proyEstado} onChange={e => setProyEstado(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm">
                      <option value="">Todos</option>
                      <option value="sale">Confirmado</option>
                      <option value="draft">Borrador</option>
                    </select>
                  </div>
                  <button
                    onClick={() => { setProyEnabled(true); refetchProy() }}
                    className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
                  >Buscar</button>
                </div>
              </CardContent>
            </Card>

            {loadingProy ? <LoadingSpinner /> : proyeccion.length > 0 ? (
              <DataTable
                columns={[
                  { accessorKey: 'name', header: 'Pedido', enableSorting: true },
                  { accessorKey: 'cliente', header: 'Cliente', enableSorting: true },
                  { accessorKey: 'fecha_entrega', header: 'Fecha Entrega', enableSorting: true },
                  { accessorKey: 'especie', header: 'Especie' },
                  { accessorKey: 'kg_comprometidos', header: 'KG Comprometidos', cell: ({ getValue }) => `${Number(getValue()).toLocaleString('es-CL')} kg`, enableSorting: true },
                  { accessorKey: 'monto_total', header: 'Monto', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
                  { accessorKey: 'dias_para_entrega', header: 'Días restantes', enableSorting: true },
                  {
                    accessorKey: 'estado',
                    header: 'Estado',
                    cell: ({ getValue }) => {
                      const v = String(getValue())
                      return <Badge variant={v === 'sale' ? 'success' : v === 'draft' ? 'warning' : 'default'}>{v === 'sale' ? 'Confirmado' : v === 'draft' ? 'Borrador' : v}</Badge>
                    },
                  },
                ]}
                data={proyeccion}
                loading={loadingProy}
                searchPlaceholder="Buscar pedido o cliente..."
              />
            ) : proyEnabled ? (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">No se encontraron pedidos en el período seleccionado.</div>
            ) : (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
                Selecciona un rango de fechas y presiona <strong>Buscar</strong> para cargar la proyección.
              </div>
            )}
          </div>
        </TabsContent>

        {/* Calendario de Entregas */}
        <TabsContent value="calendario" className="mt-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-base">Filtros — Calendario de Entregas</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Desde</label>
                    <input type="date" value={calFechaInicio} onChange={e => setCalFechaInicio(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Hasta</label>
                    <input type="date" value={calFechaFin} onChange={e => setCalFechaFin(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <button
                    onClick={() => { setCalEnabled(true); refetchCal() }}
                    className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:bg-primary/90"
                  >Buscar</button>
                </div>
              </CardContent>
            </Card>

            {loadingCal ? <LoadingSpinner /> : calendario.length > 0 ? (
              <div className="space-y-3">
                {calendario.map((dia, i) => (
                  <Card key={i}>
                    <CardHeader className="py-2">
                      <div className="flex items-center justify-between">
                        <CardTitle className="text-sm font-semibold">{dia.fecha}</CardTitle>
                        <div className="flex gap-4 text-xs text-muted-foreground">
                          <span>{dia.num_pedidos} pedido{dia.num_pedidos !== 1 ? 's' : ''}</span>
                          <span>{Number(dia.total_kg).toLocaleString('es-CL')} kg</span>
                          <span>{formatCurrency(dia.total_monto)}</span>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="pt-0">
                      <div className="divide-y divide-border/50">
                        {dia.pedidos.map((p, j) => (
                          <div key={j} className="flex items-center justify-between py-1.5 text-xs">
                            <div className="flex gap-3">
                              <span className="font-medium">{p.name}</span>
                              <span className="text-muted-foreground">{p.cliente}</span>
                              <span className="text-muted-foreground">{p.especie}</span>
                            </div>
                            <div className="flex gap-3 tabular-nums">
                              <span>{Number(p.kg).toLocaleString('es-CL')} kg</span>
                              <span>{formatCurrency(p.monto)}</span>
                              <Badge variant={p.estado === 'sale' ? 'success' : 'warning'} className="text-xs px-1.5 py-0">
                                {p.estado === 'sale' ? 'Confirmado' : 'Borrador'}
                              </Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            ) : calEnabled ? (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">No hay entregas programadas para el período seleccionado.</div>
            ) : (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
                Selecciona un rango de fechas y presiona <strong>Buscar</strong> para cargar el calendario.
              </div>
            )}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default PedidosVentaPage
