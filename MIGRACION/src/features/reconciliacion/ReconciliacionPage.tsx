import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import { type ColumnDef } from '@tanstack/react-table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { FilterBar } from '@/components/forms/FilterBar'
import { DataTable } from '@/components/tables/DataTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { KPICard } from '@/components/shared/KPICard'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { BarChart } from '@/components/charts/BarChart'
import { CURRENT_YEAR } from '@/lib/constants'
import { formatNumber } from '@/lib/utils'
import { useReconciliacion, useReconciliacionKPIs, type ReconciliacionRow } from '@/api/reconciliacion'
import apiClient from '@/api/client'

const columns: ColumnDef<ReconciliacionRow>[] = [
  { accessorKey: 'mo', header: 'OT', enableSorting: true },
  { accessorKey: 'producto', header: 'Producto' },
  { accessorKey: 'consumo_teorico', header: 'Cons. Teórico', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
  { accessorKey: 'consumo_real', header: 'Cons. Real', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
  {
    accessorKey: 'diferencia',
    header: 'Diferencia',
    cell: ({ getValue }) => {
      const v = Number(getValue())
      return <span className={v > 0 ? 'text-red-400' : 'text-green-400'}>{formatNumber(v, 0)}</span>
    },
    enableSorting: true,
  },
  { accessorKey: 'diferencia_pct', header: 'Dif %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },
  {
    accessorKey: 'estado',
    header: 'Estado',
    cell: ({ getValue }) => {
      const v = String(getValue())
      return <Badge variant={v === 'ok' ? 'success' : v === 'alerta' ? 'warning' : 'destructive'}>{v.toUpperCase()}</Badge>
    },
  },
]

export function ReconciliacionPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])
  const [actionResult, setActionResult] = useState<string | null>(null)

  const { data: rows = [], isLoading } = useReconciliacion(year, months)
  const { data: kpis, isLoading: loadingKPIs } = useReconciliacionKPIs(year, months)

  const alertas = rows.filter(r => r.estado === 'alerta').length
  const errores = rows.filter(r => r.estado === 'error').length

  // Diferencia por producto (for chart)
  const porProducto = Object.entries(
    rows.reduce((acc, r) => {
      acc[r.producto] = (acc[r.producto] ?? 0) + Math.abs(r.diferencia)
      return acc
    }, {} as Record<string, number>)
  )
    .map(([producto, diferencia]) => ({ producto, diferencia }))
    .sort((a, b) => b.diferencia - a.diferencia)
    .slice(0, 15)

  const triggerMutation = useMutation({
    mutationFn: async (mo: string) => {
      const { data } = await apiClient.post('/reconciliacion/trigger-so', { mo })
      return data
    },
    onSuccess: (data) => setActionResult(`✅ SO Asociada disparada correctamente. ${data?.message ?? ''}`),
    onError: () => setActionResult('❌ Error al disparar la automatización'),
  })

  const reconciliarMutation = useMutation({
    mutationFn: async () => {
      const { data } = await apiClient.post('/reconciliacion/reconciliar-kg', { year, months })
      return data
    },
    onSuccess: (data) => setActionResult(`✅ Reconciliación ejecutada. ${data?.message ?? ''}`),
    onError: () => setActionResult('❌ Error al ejecutar reconciliación KG'),
  })

  return (
    <div className="space-y-4">
      <PageHeader title="Reconciliación Producción" description="Reconciliación de consumos teóricos vs reales por OT">
        <ExportButton data={rows as unknown as Record<string, unknown>[]} filename="reconciliacion" />
      </PageHeader>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Total OTs" value={kpis?.total_ots ?? rows.length} loading={loadingKPIs} />
        <KPICard label="Sin Diferencias" value={kpis?.sin_diferencias ?? rows.filter(r => r.estado === 'ok').length} loading={loadingKPIs} />
        <KPICard label="Alertas" value={kpis?.alertas ?? alertas} loading={loadingKPIs} />
        <KPICard label="Errores" value={kpis?.errores ?? errores} loading={loadingKPIs} />
      </div>

      {actionResult && (
        <div className="rounded-md border px-4 py-2 text-sm bg-muted/30">{actionResult}</div>
      )}

      <Tabs defaultValue="listado">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="listado">📋 Listado OTs</TabsTrigger>
          <TabsTrigger value="analisis">📊 Análisis Diferencias</TabsTrigger>
          <TabsTrigger value="acciones">⚡ Acciones</TabsTrigger>
        </TabsList>

        <TabsContent value="listado" className="mt-4">
          <DataTable
            columns={columns}
            data={rows}
            loading={isLoading}
            searchPlaceholder="Buscar OT o producto..."
          />
        </TabsContent>

        <TabsContent value="analisis" className="mt-4">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">Diferencia Absoluta por Producto (Top 15)</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? <LoadingSpinner /> : (
                <BarChart
                  data={porProducto}
                  xKey="producto"
                  bars={[{ key: 'diferencia', name: 'Diferencia (kg)' }]}
                  yFormatter={(v) => formatNumber(v, 0)}
                  horizontal
                  height={420}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="acciones" className="mt-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">🔗 Trigger SO Asociada</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Activa la automatización de Odoo para asociar la Orden de Fabricación con su SO correspondiente.
                </p>
                <p className="text-xs text-muted-foreground">Selecciona una OT desde el listado y ejecuta la acción manualmente.</p>
                <Button
                  disabled={triggerMutation.isPending}
                  onClick={() => {
                    const mo = window.prompt('Ingresa el número de OT:')
                    if (mo) triggerMutation.mutate(mo)
                  }}
                >
                  {triggerMutation.isPending ? 'Ejecutando...' : 'Disparar SO Asociada'}
                </Button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">⚖️ Reconciliar KG</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  Calcula y actualiza los campos de seguimiento de KG en todas las ODFs del período seleccionado.
                </p>
                <p className="text-xs text-muted-foreground">Período: {year}{months.length ? ` — meses ${months.join(', ')}` : ' (año completo)'}</p>
                <Button
                  variant="destructive"
                  disabled={reconciliarMutation.isPending}
                  onClick={() => reconciliarMutation.mutate()}
                >
                  {reconciliarMutation.isPending ? 'Reconciliando...' : '⚖️ Ejecutar Reconciliación KG'}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default ReconciliacionPage
