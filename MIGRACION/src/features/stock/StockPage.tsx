import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { FilterBar } from '@/components/forms/FilterBar'
import { DataTable } from '@/components/tables/DataTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { KPICard } from '@/components/shared/KPICard'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { BarChart } from '@/components/charts/BarChart'
import { CURRENT_YEAR } from '@/lib/constants'
import { formatNumber, formatCurrency } from '@/lib/utils'
import { useStock, useStockKPIs, useStockMovimientos, usePallets, useLotes, type StockItem, type PalletStock, type Lote } from '@/api/stock'

interface MovimientoStock {
  id: number
  fecha: string
  tipo: string
  producto: string
  ubicacion_origen?: string
  ubicacion_destino?: string
  cantidad: number
  unidad: string
  referencia: string
}

const colsStock: ColumnDef<StockItem>[] = [
  { accessorKey: 'producto', header: 'Producto', enableSorting: true },
  { accessorKey: 'ubicacion', header: 'Ubicación' },
  { accessorKey: 'categoria', header: 'Categoría' },
  {
    accessorKey: 'cantidad',
    header: 'Cantidad',
    cell: ({ row, getValue }) => `${formatNumber(Number(getValue()), 0)} ${row.original.unidad}`,
    enableSorting: true,
  },
  {
    accessorKey: 'valor',
    header: 'Valor',
    cell: ({ getValue }) => formatCurrency(Number(getValue())),
    enableSorting: true,
  },
]

const colsMov: ColumnDef<MovimientoStock>[] = [
  { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },
  {
    accessorKey: 'tipo',
    header: 'Tipo',
    cell: ({ getValue }) => {
      const v = String(getValue())
      const variant = v === 'entrada' ? 'success' : v === 'salida' ? 'destructive' : 'default'
      return <Badge variant={variant}>{v.charAt(0).toUpperCase() + v.slice(1)}</Badge>
    },
  },
  { accessorKey: 'producto', header: 'Producto', enableSorting: true },
  { accessorKey: 'ubicacion_origen', header: 'Origen' },
  { accessorKey: 'ubicacion_destino', header: 'Destino' },
  {
    accessorKey: 'cantidad',
    header: 'Cantidad',
    cell: ({ row, getValue }) => `${formatNumber(Number(getValue()), 0)} ${row.original.unidad}`,
    enableSorting: true,
  },
  { accessorKey: 'referencia', header: 'Referencia' },
]

// Cámaras tab — group by ubicacion
function camarasDesdeStock(stock: StockItem[]) {
  const map: Record<string, { cantidad: number; valor: number; productos: number }> = {}
  for (const item of stock) {
    if (!map[item.ubicacion]) map[item.ubicacion] = { cantidad: 0, valor: 0, productos: 0 }
    map[item.ubicacion].cantidad += item.cantidad
    map[item.ubicacion].valor += item.valor
    map[item.ubicacion].productos += 1
  }
  return Object.entries(map).map(([ubicacion, v]) => ({ ubicacion, ...v }))
}

export function StockPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])

  // Pallets tab state
  const [palletLocationId, setPalletLocationId] = useState<number | null>(null)
  const [palletCategory, setPalletCategory] = useState<string | null>(null)

  // Trazabilidad tab state
  const [trazCategory, setTrazCategory] = useState('')
  const [trazLocations, setTrazLocations] = useState<number[]>([])
  const [trazEnabled, setTrazEnabled] = useState(false)

  const { data: stock = [], isLoading } = useStock(year)
  const { data: kpis, isLoading: loadingKPIs } = useStockKPIs(year)
  const { data: movimientos = [], isLoading: loadingMov } = useStockMovimientos(year, months)
  const { data: pallets = [], isLoading: loadingPallets } = usePallets(palletLocationId, palletCategory, palletLocationId !== null)
  const { data: lotes = [], isLoading: loadingLotes } = useLotes(trazCategory, trazLocations.length ? trazLocations : null, trazEnabled)

  const camaras = camarasDesdeStock(stock)

  return (
    <div className="space-y-4">
      <PageHeader title="Stock" description="Inventario actual, movimientos y valorización">
        <ExportButton data={stock as unknown as Record<string, unknown>[]} filename="stock" />
      </PageHeader>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Total Productos" value={kpis?.total_productos ?? stock.length} loading={loadingKPIs} />
        <KPICard label="Valor Total" value={kpis?.valor_total ?? stock.reduce((s, r) => s + r.valor, 0)} format="currency" loading={loadingKPIs} />
        <KPICard label="Ubicaciones" value={kpis?.ubicaciones ?? camaras.length} loading={loadingKPIs} />
        <KPICard label="Alertas Mínimo" value={kpis?.alertas_minimo ?? 0} loading={loadingKPIs} />
      </div>

      <Tabs defaultValue="inventario">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="inventario">📦 Inventario</TabsTrigger>
          <TabsTrigger value="camaras">🏢 Cámaras</TabsTrigger>
          <TabsTrigger value="movimientos">📲 Movimientos</TabsTrigger>
          <TabsTrigger value="valorizado">💰 Valorizado</TabsTrigger>
          <TabsTrigger value="pallets">🏷️ Pallets</TabsTrigger>
          <TabsTrigger value="trazabilidad">🔍 Trazabilidad</TabsTrigger>
        </TabsList>

        <TabsContent value="inventario" className="mt-4">
          <DataTable
            columns={colsStock}
            data={stock}
            loading={isLoading}
            searchPlaceholder="Buscar producto o ubicación..."
          />
        </TabsContent>

        <TabsContent value="camaras" className="mt-4">
          <div className="grid gap-4">
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">Stock por Cámara / Ubicación</CardTitle>
              </CardHeader>
              <CardContent>
                {isLoading ? <LoadingSpinner /> : (
                  <BarChart
                    data={camaras}
                    xKey="ubicacion"
                    bars={[
                      { key: 'cantidad', name: 'Cantidad' },
                    ]}
                    yFormatter={(v) => formatNumber(v, 0)}
                    height={340}
                  />
                )}
              </CardContent>
            </Card>
            <DataTable
              columns={[
                { accessorKey: 'ubicacion', header: 'Ubicación', enableSorting: true },
                { accessorKey: 'productos', header: 'Productos', enableSorting: true },
                { accessorKey: 'cantidad', header: 'Cantidad', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
                { accessorKey: 'valor', header: 'Valor', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
              ]}
              data={camaras}
              loading={isLoading}
              searchPlaceholder="Buscar cámara..."
            />
          </div>
        </TabsContent>

        <TabsContent value="movimientos" className="mt-4">
          <DataTable
            columns={colsMov}
            data={movimientos as MovimientoStock[]}
            loading={loadingMov}
            searchPlaceholder="Buscar movimiento..."
          />
        </TabsContent>

        <TabsContent value="valorizado" className="mt-4">
          <Card>
            <CardHeader className="py-3">
              <CardTitle className="text-base">Valor por Categoría</CardTitle>
            </CardHeader>
            <CardContent>
              {isLoading ? <LoadingSpinner /> : (
                <BarChart
                  data={Object.entries(
                    stock.reduce((acc, r) => {
                      acc[r.categoria] = (acc[r.categoria] ?? 0) + r.valor
                      return acc
                    }, {} as Record<string, number>)
                  ).map(([categoria, valor]) => ({ categoria, valor }))}
                  xKey="categoria"
                  bars={[{ key: 'valor', name: 'Valor ($)' }]}
                  yFormatter={(v) => formatCurrency(v)}
                  height={340}
                />
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* ─── Pallets ─── */}
        <TabsContent value="pallets" className="mt-4 space-y-4">
          {/* Filters */}
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap gap-4">
                <div className="flex-1 min-w-[200px]">
                  <label className="text-xs text-muted-foreground block mb-1">Ubicación</label>
                  <select
                    value={palletLocationId ?? ''}
                    onChange={e => setPalletLocationId(e.target.value ? Number(e.target.value) : null)}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">— Seleccionar ubicación —</option>
                    {camaras.map(c => (
                      <option key={c.ubicacion} value={(stock.find(s => s.ubicacion === c.ubicacion) as StockItem & { id?: number })?.id ?? c.ubicacion}>
                        {c.ubicacion}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="flex-1 min-w-[180px]">
                  <label className="text-xs text-muted-foreground block mb-1">Categoría</label>
                  <select
                    value={palletCategory ?? ''}
                    onChange={e => setPalletCategory(e.target.value || null)}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">Todos</option>
                    {Array.from(new Set(stock.map(s => s.categoria).filter(Boolean))).sort().map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>
            </CardContent>
          </Card>

          {palletLocationId === null ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              Selecciona una ubicación para consultar pallets.
            </div>
          ) : loadingPallets ? <LoadingSpinner /> : (
            <>
              <div className="grid gap-3 sm:grid-cols-3">
                <KPICard label="Total Registros" value={(pallets as PalletStock[]).length} />
                <KPICard label="Stock Total (kg)" value={(pallets as PalletStock[]).reduce((s, p) => s + p.quantity, 0)} format="number" />
                <KPICard
                  label="Antigüedad Prom."
                  value={(pallets as PalletStock[]).length ? Math.round((pallets as PalletStock[]).reduce((s, p) => s + p.days_old, 0) / (pallets as PalletStock[]).length) : 0}
                  unit="días"
                />
              </div>

              <Card>
                <CardContent className="p-0 overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="px-3 py-2 text-left">Pallet</th>
                        <th className="px-3 py-2 text-left">Producto</th>
                        <th className="px-3 py-2 text-left">Lote</th>
                        <th className="px-3 py-2 text-right">Cantidad (kg)</th>
                        <th className="px-3 py-2 text-left">Categoría</th>
                        <th className="px-3 py-2 text-left">Condición</th>
                        <th className="px-3 py-2 text-left">F. Ingreso</th>
                        <th className="px-3 py-2 text-right">Días</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(pallets as PalletStock[]).map((p, i) => (
                        <tr
                          key={i}
                          className={`border-b hover:bg-muted/20 ${p.days_old >= 30 ? 'text-red-400' : p.days_old >= 15 ? 'text-yellow-400' : ''}`}
                        >
                          <td className="px-3 py-2 font-mono text-xs">{p.pallet}</td>
                          <td className="px-3 py-2">{p.product}</td>
                          <td className="px-3 py-2 text-muted-foreground">{p.lot}</td>
                          <td className="px-3 py-2 text-right font-semibold">{formatNumber(p.quantity, 2)}</td>
                          <td className="px-3 py-2">{p.category}</td>
                          <td className="px-3 py-2">{p.condition}</td>
                          <td className="px-3 py-2 text-xs text-muted-foreground">{p.in_date}</td>
                          <td className="px-3 py-2 text-right font-semibold">{p.days_old}</td>
                        </tr>
                      ))}
                      {(pallets as PalletStock[]).length === 0 && (
                        <tr><td colSpan={8} className="px-3 py-8 text-center text-muted-foreground">Sin pallets en esta ubicación.</td></tr>
                      )}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>

        {/* ─── Trazabilidad ─── */}
        <TabsContent value="trazabilidad" className="mt-4 space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-end gap-4">
                <div className="flex-1 min-w-[200px]">
                  <label className="text-xs text-muted-foreground block mb-1">Tipo Fruta / Manejo</label>
                  <select
                    value={trazCategory}
                    onChange={e => { setTrazCategory(e.target.value); setTrazEnabled(false) }}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">— Seleccionar categoría —</option>
                    {Array.from(new Set(stock.map(s => s.categoria).filter(Boolean))).sort().map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
                <div className="flex-1 min-w-[200px]">
                  <label className="text-xs text-muted-foreground block mb-1">Filtrar ubicaciones (opcional)</label>
                  <select
                    multiple
                    value={trazLocations.map(String)}
                    onChange={e => setTrazLocations(Array.from(e.target.selectedOptions).map(o => Number(o.value)))}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm h-20"
                  >
                    {camaras.map(c => (
                      <option key={c.ubicacion} value={(stock.find(s => s.ubicacion === c.ubicacion) as StockItem & { id?: number })?.id ?? 0}>
                        {c.ubicacion}
                      </option>
                    ))}
                  </select>
                </div>
                <button
                  disabled={!trazCategory}
                  onClick={() => setTrazEnabled(true)}
                  className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
                >
                  🔍 Consultar Lotes
                </button>
              </div>
            </CardContent>
          </Card>

          {!trazEnabled ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              Selecciona una categoría y presiona "Consultar Lotes".
            </div>
          ) : loadingLotes ? <LoadingSpinner /> : (
            <>
              <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                <KPICard label="Lotes" value={(lotes as Lote[]).length} />
                <KPICard label="Stock Total (kg)" value={(lotes as Lote[]).reduce((s, l) => s + l.quantity, 0)} format="number" />
                <KPICard label="Pallets" value={(lotes as Lote[]).reduce((s, l) => s + l.pallets, 0)} />
                <KPICard label="Lote Más Antiguo" value={Math.max(0, ...(lotes as Lote[]).map(l => l.days_old))} unit="días" />
              </div>

              {(lotes as Lote[]).length > 0 && (
                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">Antigüedad por Lote (días)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <BarChart
                      data={(lotes as Lote[]).slice(0, 40).map(l => ({ lot: l.lot, dias: l.days_old }))}
                      xKey="lot"
                      bars={[{ key: 'dias', name: 'Días' }]}
                      yFormatter={v => `${v}d`}
                      height={260}
                    />
                  </CardContent>
                </Card>
              )}

              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-base">Detalle de Lotes (ordenado por antigüedad)</CardTitle>
                </CardHeader>
                <CardContent className="p-0 overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="px-3 py-2 text-left">Lote</th>
                        <th className="px-3 py-2 text-left">Producto</th>
                        <th className="px-3 py-2 text-right">Cantidad (kg)</th>
                        <th className="px-3 py-2 text-right">Pallets</th>
                        <th className="px-3 py-2 text-left">F. Ingreso</th>
                        <th className="px-3 py-2 text-right">Días</th>
                        <th className="px-3 py-2 text-left">Ubicaciones</th>
                      </tr>
                    </thead>
                    <tbody>
                      {[...(lotes as Lote[])].sort((a, b) => b.days_old - a.days_old).map((l, i) => (
                        <tr
                          key={i}
                          className={`border-b hover:bg-muted/20 ${l.days_old >= 30 ? 'text-red-400' : l.days_old >= 15 ? 'text-yellow-400' : ''}`}
                        >
                          <td className="px-3 py-2 font-mono text-xs">{l.lot}</td>
                          <td className="px-3 py-2">{l.product}</td>
                          <td className="px-3 py-2 text-right">{formatNumber(l.quantity, 2)}</td>
                          <td className="px-3 py-2 text-right">{l.pallets}</td>
                          <td className="px-3 py-2 text-xs text-muted-foreground">{l.in_date}</td>
                          <td className="px-3 py-2 text-right font-semibold">{l.days_old}</td>
                          <td className="px-3 py-2 text-xs text-muted-foreground">{Array.isArray(l.locations) ? l.locations.join(', ') : l.locations}</td>
                        </tr>
                      ))}
                      {(lotes as Lote[]).length === 0 && (
                        <tr><td colSpan={7} className="px-3 py-8 text-center text-muted-foreground">Sin lotes para esta categoría.</td></tr>
                      )}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </>
          )}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default StockPage
