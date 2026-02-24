import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { RefreshCw } from 'lucide-react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/tables/DataTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { KPICard } from '@/components/shared/KPICard'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { FilterBar } from '@/components/forms/FilterBar'
import { CURRENT_YEAR } from '@/lib/constants'
import { formatNumber, formatDate } from '@/lib/utils'
import {
  useMovimientosEntrada,
  useMovimientosSalida,
  useStockBandejas,
  type MovimientoEntrada,
  type MovimientoSalida,
  type StockBandeja,
} from '@/api/bandejas'

const colsEntrada: ColumnDef<MovimientoEntrada>[] = [
  { accessorKey: 'date_order', header: 'Fecha', cell: ({ getValue }) => formatDate(String(getValue())), enableSorting: true },
  { accessorKey: 'proveedor', header: 'Proveedor', enableSorting: true },
  { accessorKey: 'tipo_bandeja', header: 'Tipo' },
  { accessorKey: 'cantidad', header: 'Cantidad', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
  {
    accessorKey: 'estado', header: 'Estado',
    cell: ({ getValue }) => {
      const v = String(getValue()).toLowerCase()
      const variant: Record<string, 'success' | 'default' | 'warning'> = { done: 'success', confirmed: 'default', pending: 'warning' }
      return <Badge variant={variant[v] ?? 'default'}>{String(getValue())}</Badge>
    },
  },
  { accessorKey: 'origen', header: 'Origen' },
  { accessorKey: 'referencia', header: 'Referencia' },
]

const colsSalida: ColumnDef<MovimientoSalida>[] = [
  { accessorKey: 'date', header: 'Fecha', cell: ({ getValue }) => formatDate(String(getValue())), enableSorting: true },
  { accessorKey: 'proveedor', header: 'Proveedor', enableSorting: true },
  { accessorKey: 'tipo_bandeja', header: 'Tipo' },
  { accessorKey: 'cantidad', header: 'Cantidad', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
  { accessorKey: 'destino', header: 'Destino' },
  { accessorKey: 'referencia', header: 'Referencia' },
]

const colsStock: ColumnDef<StockBandeja>[] = [
  { accessorKey: 'tipo_bandeja', header: 'Tipo de Bandeja', enableSorting: true },
  { accessorKey: 'cantidad_limpia', header: 'Limpias', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
  { accessorKey: 'cantidad_sucia', header: 'Sucias', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
  { accessorKey: 'total', header: 'Total', cell: ({ getValue }) => <span className="font-semibold">{formatNumber(Number(getValue()), 0)}</span>, enableSorting: true },
  { accessorKey: 'ultima_actualizacion', header: 'Última Act.', cell: ({ getValue }) => formatDate(String(getValue())) },
]

export function BandejasPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])
  const filters = { year, months: months.length ? months : undefined }

  const { data: entradas = [], isLoading: loadingEnt, refetch: refetchEnt } = useMovimientosEntrada(filters)
  const { data: salidas = [], isLoading: loadingSal, refetch: refetchSal } = useMovimientosSalida(filters)
  const { data: stock = [], isLoading: loadingStock, refetch: refetchStock } = useStockBandejas()

  const totalEntradas = entradas.reduce((s, r) => s + r.cantidad, 0)
  const totalSalidas = salidas.reduce((s, r) => s + r.cantidad, 0)
  const totalStock = stock.reduce((s, r) => s + r.total, 0)
  const stockLimpias = stock.reduce((s, r) => s + r.cantidad_limpia, 0)
  const stockSucias = stock.reduce((s, r) => s + r.cantidad_sucia, 0)
  const proveedoresActivos = new Set(entradas.map((r) => r.proveedor)).size

  return (
    <div className="space-y-4">
      <PageHeader title="Bandejas" description="Recepción de bandejas — Control de cantidades y trazabilidad por proveedor">
        <Button variant="outline" size="sm" onClick={() => { refetchEnt(); refetchSal(); refetchStock() }}>
          <RefreshCw className="mr-2 h-4 w-4" />Actualizar
        </Button>
      </PageHeader>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Stock Total" value={totalStock} loading={loadingStock} />
        <KPICard label="Bandejas Limpias" value={stockLimpias} loading={loadingStock} />
        <KPICard label="Bandejas Sucias" value={stockSucias} loading={loadingStock} />
        <KPICard label="Proveedores activos" value={proveedoresActivos} loading={loadingEnt} />
      </div>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <div className="grid gap-4 sm:grid-cols-2">
        <KPICard label="Entradas (período)" value={totalEntradas} loading={loadingEnt} />
        <KPICard label="Salidas (período)" value={totalSalidas} loading={loadingSal} />
      </div>

      <Tabs defaultValue="stock">
        <TabsList>
          <TabsTrigger value="stock">📦 Stock Actual</TabsTrigger>
          <TabsTrigger value="entradas">📥 Entradas</TabsTrigger>
          <TabsTrigger value="salidas">📤 Salidas</TabsTrigger>
        </TabsList>

        <TabsContent value="stock" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-base">Stock por Tipo de Bandeja</CardTitle>
              <ExportButton data={stock as unknown as Record<string, unknown>[]} filename="stock_bandejas" />
            </CardHeader>
            <CardContent className="p-0">
              {loadingStock ? <div className="p-6"><LoadingSpinner /></div> : (
                <DataTable columns={colsStock} data={stock} loading={loadingStock} searchPlaceholder="Buscar tipo..." />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="entradas" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-base">Entradas — {entradas.length.toLocaleString('es-CL')} registros</CardTitle>
              <ExportButton data={entradas as unknown as Record<string, unknown>[]} filename="bandejas_entradas" />
            </CardHeader>
            <CardContent className="p-0">
              <DataTable columns={colsEntrada} data={entradas} loading={loadingEnt} searchPlaceholder="Buscar proveedor..." />
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="salidas" className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between py-3">
              <CardTitle className="text-base">Salidas — {salidas.length.toLocaleString('es-CL')} registros</CardTitle>
              <ExportButton data={salidas as unknown as Record<string, unknown>[]} filename="bandejas_salidas" />
            </CardHeader>
            <CardContent className="p-0">
              <DataTable columns={colsSalida} data={salidas} loading={loadingSal} searchPlaceholder="Buscar proveedor..." />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default BandejasPage
