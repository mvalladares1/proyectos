import { useState } from 'react'

import { type ColumnDef } from '@tanstack/react-table'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { PageHeader } from '@/components/layout/PageHeader'

import { FilterBar } from '@/components/forms/FilterBar'

import { KPICard } from '@/components/shared/KPICard'

import { LineChart } from '@/components/charts/LineChart'

import { BarChart } from '@/components/charts/BarChart'

import { DataTable } from '@/components/tables/DataTable'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

import { Button } from '@/components/ui/button'

import { CURRENT_YEAR } from '@/lib/constants'

import { formatNumber, formatCurrency } from '@/lib/utils'

import {

  useRendimiento,

  useRendimientoKPIs,

  useRendimientoPorLinea,

  useRendimientoVentas,

  useRendimientoCompras,

  useRendimientoStockRotacion,

  useStockTeoricoAnual,

  useInventarioTrazabilidad,

  useProduccionRendimiento,

} from '@/api/rendimiento'

interface LineaData {

  linea: string

  rendimiento: number

  merma: number

  kg_procesados: number

}

const colsLinea: ColumnDef<LineaData>[] = [

  { accessorKey: 'linea', header: 'Línea', enableSorting: true },

  { accessorKey: 'rendimiento', header: 'Rendimiento %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },

  { accessorKey: 'merma', header: 'Merma %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },

  { accessorKey: 'kg_procesados', header: 'Kg Procesados', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

]

export function RendimientoPage() {

  const [year, setYear] = useState(CURRENT_YEAR)

  const [months, setMonths] = useState<number[]>([])

  const [fechaDesde, setFechaDesde] = useState(`${CURRENT_YEAR - 2}-01-01`)

  const [fechaHasta, setFechaHasta] = useState(new Date().toISOString().slice(0, 10))

  const [stockEnabled, setStockEnabled] = useState(false)

  // Inventario Trazabilidad
  const [invDesde, setInvDesde] = useState(`${CURRENT_YEAR}-01-01`)
  const [invHasta, setInvHasta] = useState(new Date().toISOString().slice(0, 10))
  const [invEnabled, setInvEnabled] = useState(false)

  // Producción Rendimiento
  const [prodDesde, setProdDesde] = useState(`${CURRENT_YEAR}-01-01`)
  const [prodHasta, setProdHasta] = useState(new Date().toISOString().slice(0, 10))
  const [prodEnabled, setProdEnabled] = useState(false)

  const { data: rendimiento = [], isLoading } = useRendimiento(year, months)

  const { data: kpis, isLoading: loadingKPIs } = useRendimientoKPIs(year, months)

  const { data: lineas = [], isLoading: loadingLineas } = useRendimientoPorLinea(year, months)

  const { data: ventas = [], isLoading: loadingVentas } = useRendimientoVentas(year, months)

  const { data: comprasData = [], isLoading: loadingCompras } = useRendimientoCompras(year, months)

  const { data: rotacion = [], isLoading: loadingRot } = useRendimientoStockRotacion(year, months)

  const { data: stockTeorico, isLoading: loadingStock, refetch: refetchStock } = useStockTeoricoAnual(fechaDesde, fechaHasta, stockEnabled)

  const { data: inventario, isLoading: loadingInv, refetch: refetchInv } = useInventarioTrazabilidad(invDesde, invHasta, invEnabled)

  const { data: produccionRend, isLoading: loadingProdRend, refetch: refetchProdRend } = useProduccionRendimiento(prodDesde, prodHasta, prodEnabled)

  return (

    <div className="space-y-4">

      <PageHeader title="Rendimiento" description="Métricas de rendimiento, ventas, compras y stock empresarial" />

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

        <KPICard label="Rendimiento Promedio" value={kpis?.rendimiento_promedio} unit="%" format="number" loading={loadingKPIs} />

        <KPICard label="Merma Promedio" value={kpis?.merma_promedio} unit="%" format="number" loading={loadingKPIs} />

        <KPICard label="Eficiencia Promedio" value={kpis?.eficiencia_promedio} unit="%" format="number" loading={loadingKPIs} />

        <Card className="p-4">

          <p className="text-sm text-muted-foreground">Mejor Mes</p>

          {loadingKPIs ? <div className="h-8 w-24 rounded bg-muted animate-pulse mt-1" /> : (

            <p className="text-2xl font-bold mt-1">{kpis?.mejor_mes ?? '—'}</p>

          )}

        </Card>

      </div>

      <Tabs defaultValue="evolucion">

        <TabsList className="flex-wrap h-auto gap-1">

          <TabsTrigger value="evolucion">📈 Evolución</TabsTrigger>

          <TabsTrigger value="lineas">🏭 Por Línea</TabsTrigger>

          <TabsTrigger value="ventas">💰 Ventas</TabsTrigger>

          <TabsTrigger value="compras">🛒 Compras</TabsTrigger>

          <TabsTrigger value="rotacion">🔄 Stock Rotación</TabsTrigger>

          <TabsTrigger value="stock-teorico">📊 Stock Teórico</TabsTrigger>

          <TabsTrigger value="inventario">🗂️ Inventario</TabsTrigger>

          <TabsTrigger value="produccion-rend">⚙️ Prod. Rendimiento</TabsTrigger>

        </TabsList>

        {/* Evolución */}

        <TabsContent value="evolucion" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">Evolución de Rendimiento y Merma</CardTitle>

            </CardHeader>

            <CardContent>

              {isLoading ? <LoadingSpinner /> : (

                <LineChart

                  data={rendimiento}

                  xKey="periodo"

                  lines={[

                    { key: 'rendimiento', name: 'Rendimiento %' },

                    { key: 'eficiencia', name: 'Eficiencia %' },

                    { key: 'merma', name: 'Merma %' },

                  ]}

                  yFormatter={(v) => `${formatNumber(v, 1)}%`}

                  height={360}

                />

              )}

            </CardContent>

          </Card>

        </TabsContent>

        {/* Por Línea */}

        <TabsContent value="lineas" className="mt-4">

          <div className="grid gap-4">

            <Card>

              <CardHeader className="py-3">

                <CardTitle className="text-base">Rendimiento por Línea de Proceso</CardTitle>

              </CardHeader>

              <CardContent>

                {loadingLineas ? <LoadingSpinner /> : (

                  <BarChart

                    data={lineas as LineaData[]}

                    xKey="linea"

                    bars={[

                      { key: 'rendimiento', name: 'Rendimiento %' },

                      { key: 'merma', name: 'Merma %' },

                    ]}

                    yFormatter={(v) => `${formatNumber(v, 1)}%`}

                    height={320}

                  />

                )}

              </CardContent>

            </Card>

            <DataTable

              columns={colsLinea}

              data={lineas as LineaData[]}

              loading={loadingLineas}

              searchPlaceholder="Buscar línea..."

            />

          </div>

        </TabsContent>

        {/* Ventas */}

        <TabsContent value="ventas" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">Evolución de Ventas (Productos Terminados)</CardTitle>

            </CardHeader>

            <CardContent>

              {loadingVentas ? <LoadingSpinner /> : (

                <LineChart

                  data={ventas as { periodo: string; monto: number; unidades: number }[]}

                  xKey="periodo"

                  lines={[

                    { key: 'monto', name: 'Monto ($)' },

                  ]}

                  yFormatter={(v) => formatCurrency(v)}

                  height={340}

                />

              )}

            </CardContent>

          </Card>

          <div className="mt-4">

            <DataTable

              columns={[

                { accessorKey: 'periodo', header: 'Período', enableSorting: true },

                { accessorKey: 'producto', header: 'Producto' },

                { accessorKey: 'cliente', header: 'Cliente' },

                { accessorKey: 'unidades', header: 'Unidades', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                { accessorKey: 'monto', header: 'Monto', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },

              ]}

              data={ventas as Record<string, unknown>[]}

              loading={loadingVentas}

              searchPlaceholder="Buscar producto o cliente..."

            />

          </div>

        </TabsContent>

        {/* Compras */}

        <TabsContent value="compras" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">Evolución de Compras de MP</CardTitle>

            </CardHeader>

            <CardContent>

              {loadingCompras ? <LoadingSpinner /> : (

                <BarChart

                  data={comprasData as { periodo: string; monto: number; kg: number }[]}

                  xKey="periodo"

                  bars={[

                    { key: 'kg', name: 'Kg Comprados' },

                  ]}

                  yFormatter={(v) => formatNumber(v, 0)}

                  height={320}

                />

              )}

            </CardContent>

          </Card>

          <div className="mt-4">

            <DataTable

              columns={[

                { accessorKey: 'periodo', header: 'Período', enableSorting: true },

                { accessorKey: 'proveedor', header: 'Proveedor', enableSorting: true },

                { accessorKey: 'especie', header: 'Especie' },

                { accessorKey: 'kg', header: 'Kg', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                { accessorKey: 'monto', header: 'Monto', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },

                { accessorKey: 'precio_kg', header: '$/kg', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },

              ]}

              data={comprasData as Record<string, unknown>[]}

              loading={loadingCompras}

              searchPlaceholder="Buscar proveedor o especie..."

            />

          </div>

        </TabsContent>

        {/* Stock Rotación */}

        <TabsContent value="rotacion" className="mt-4">

          <div className="grid gap-4">

            <Card>

              <CardHeader className="py-3">

                <CardTitle className="text-base">Rotación de Stock por Producto</CardTitle>

              </CardHeader>

              <CardContent>

                {loadingRot ? <LoadingSpinner /> : (

                  <BarChart

                    data={(rotacion as { producto: string; dias_rotacion: number; stock_promedio: number }[]).slice(0, 20)}

                    xKey="producto"

                    bars={[{ key: 'dias_rotacion', name: 'Días Rotación' }]}

                    yFormatter={(v) => `${v}d`}

                    horizontal

                    height={400}

                  />

                )}

              </CardContent>

            </Card>

            <DataTable

              columns={[

                { accessorKey: 'producto', header: 'Producto', enableSorting: true },

                { accessorKey: 'stock_promedio', header: 'Stock Prom.', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                { accessorKey: 'consumo_diario', header: 'Consumo/día', cell: ({ getValue }) => formatNumber(Number(getValue()), 1), enableSorting: true },

                { accessorKey: 'dias_rotacion', header: 'Días Rotación', cell: ({ getValue }) => `${Number(getValue()).toFixed(0)}d`, enableSorting: true },

              ]}

              data={rotacion as Record<string, unknown>[]}

              loading={loadingRot}

              searchPlaceholder="Buscar producto..."

            />

          </div>

        </TabsContent>

        {/* Stock Teórico Anual */}

        <TabsContent value="stock-teorico" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">📊 Stock Teórico Anual — Proyección Multi-anual</CardTitle>

            </CardHeader>

            <CardContent className="space-y-4">

              <div className="flex flex-wrap gap-4 items-end">

                <div>

                  <p className="text-xs text-muted-foreground mb-1">Desde</p>

                  <input

                    type="date"

                    value={fechaDesde}

                    onChange={(e) => setFechaDesde(e.target.value)}

                    className="border rounded px-2 py-1 text-sm bg-background text-foreground"

                  />

                </div>

                <div>

                  <p className="text-xs text-muted-foreground mb-1">Hasta</p>

                  <input

                    type="date"

                    value={fechaHasta}

                    onChange={(e) => setFechaHasta(e.target.value)}

                    className="border rounded px-2 py-1 text-sm bg-background text-foreground"

                  />

                </div>

                <Button

                  onClick={() => { if (!stockEnabled) setStockEnabled(true); else refetchStock() }}

                  disabled={loadingStock}

                >

                  {loadingStock ? 'Calculando...' : '\ud83d\udd04 Calcular Stock Te\u00f3rico'}

                </Button>

              </div>

              {loadingStock && <LoadingSpinner />}

              {stockTeorico && (

                <>

                  <LineChart

                    data={(stockTeorico as Record<string, unknown>[])}

                    xKey="periodo"

                    lines={[

                      { key: 'stock_proyectado', name: 'Stock Proyectado (kg)' },

                      { key: 'stock_real', name: 'Stock Real (kg)' },

                    ]}

                    yFormatter={(v) => formatNumber(v, 0)}

                    height={360}

                  />

                  <DataTable

                    columns={[

                      { accessorKey: 'periodo', header: 'Período', enableSorting: true },

                      { accessorKey: 'especie', header: 'Especie' },

                      { accessorKey: 'stock_proyectado', header: 'Stock Proy. (kg)', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                      { accessorKey: 'stock_real', header: 'Stock Real (kg)', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                      { accessorKey: 'merma_proyectada', header: 'Merma Proy.', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%` },

                    ]}

                    data={stockTeorico as Record<string, unknown>[]}

                    loading={loadingStock}

                    searchPlaceholder="Buscar especie..."

                  />
                </>

              )}

            </CardContent>

          </Card>

        </TabsContent>

        {/* Inventario Trazabilidad */}
        <TabsContent value="inventario" className="mt-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-base">Trazabilidad Inventario — Compras vs Ventas</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Desde</label>
                    <input type="date" value={invDesde} onChange={e => setInvDesde(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Hasta</label>
                    <input type="date" value={invHasta} onChange={e => setInvHasta(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <Button onClick={() => { setInvEnabled(true); refetchInv() }}>Buscar</Button>
                </div>
              </CardContent>
            </Card>

            {loadingInv ? <LoadingSpinner /> : inventario ? (
              <>
                <p className="text-xs text-amber-400 bg-amber-400/10 border border-amber-400/30 rounded px-3 py-2">
                  &#9888;&#65039; Compras en PSP, Ventas en PTT — no son comparables 1:1 por diferencias de manejo.
                </p>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <KPICard label="Total Comprado (kg)" value={inventario.total_comprado_kg} format="number" loading={false} />
                  <KPICard label="Total Comprado ($)" value={inventario.total_comprado_monto} format="currency" loading={false} />
                  <KPICard label="Precio Prom. Compra" value={inventario.total_comprado_precio_promedio} format="currency" loading={false} />
                  <KPICard label="Total Vendido (kg)" value={inventario.total_vendido_kg} format="number" loading={false} />
                  <KPICard label="Total Vendido ($)" value={inventario.total_vendido_monto} format="currency" loading={false} />
                  <KPICard label="Precio Prom. Venta" value={inventario.total_vendido_precio_promedio} format="currency" loading={false} />
                </div>
                <Card>
                  <CardHeader className="py-3"><CardTitle className="text-base">Compras vs Ventas por Tipo Fruta</CardTitle></CardHeader>
                  <CardContent>
                    <BarChart
                      data={inventario.por_tipo_fruta}
                      xKey="tipo_fruta"
                      bars={[
                        { key: 'comprado_kg', name: 'Comprado (kg)' },
                        { key: 'vendido_kg', name: 'Vendido (kg)' },
                      ]}
                      yFormatter={(v) => formatNumber(v, 0)}
                      height={360}
                    />
                  </CardContent>
                </Card>
                <DataTable
                  columns={[
                    { accessorKey: 'tipo_fruta', header: 'Tipo Fruta', enableSorting: true },
                    { accessorKey: 'manejo', header: 'Manejo' },
                    { accessorKey: 'comprado_kg', header: 'Comprado kg', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
                    { accessorKey: 'comprado_monto', header: 'Comprado $', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
                    { accessorKey: 'vendido_kg', header: 'Vendido kg', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
                    { accessorKey: 'vendido_monto', header: 'Vendido $', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
                  ]}
                  data={inventario.por_tipo_fruta}
                  loading={loadingInv}
                  searchPlaceholder="Buscar tipo fruta..."
                />
              </>
            ) : (
              <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
                Selecciona un rango de fechas y presiona <strong>Buscar</strong> para cargar datos.
              </div>
            )}
          </div>
        </TabsContent>

        {/* Producción Rendimiento PSP→PTT */}
        <TabsContent value="produccion-rend" className="mt-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="py-3"><CardTitle className="text-base">Análisis Producción — Rendimiento PSP→PTT</CardTitle></CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Desde</label>
                    <input type="date" value={prodDesde} onChange={e => setProdDesde(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Hasta</label>
                    <input type="date" value={prodHasta} onChange={e => setProdHasta(e.target.value)} className="rounded border border-input bg-background px-2 py-1 text-sm" />
                  </div>
                  <Button onClick={() => { setProdEnabled(true); refetchProdRend() }}>Buscar</Button>
                </div>
              </CardContent>
            </Card>

            {loadingProdRend ? <LoadingSpinner /> : produccionRend ? (
              <>
                <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
                  <KPICard label="MP Consumida (kg)" value={produccionRend.resumen.kg_consumido} format="number" loading={false} />
                  <KPICard label="PT Producido (kg)" value={produccionRend.resumen.kg_producido} format="number" loading={false} />
                  <KPICard label="Rendimiento %" value={produccionRend.resumen.rendimiento_pct} format="number" unit="%" loading={false} />
                  <KPICard label="Merma Proceso %" value={produccionRend.resumen.merma_pct} format="number" unit="%" loading={false} />
                  <KPICard label="Merma (kg)" value={produccionRend.resumen.merma_kg} format="number" loading={false} />
                  <KPICard label="Órdenes Producción" value={produccionRend.resumen.ordenes_total} loading={false} />
                </div>

                <Card>
                  <CardHeader className="py-3"><CardTitle className="text-base">MP Consumida vs PT Producido por Tipo Fruta</CardTitle></CardHeader>
                  <CardContent>
                    <BarChart
                      data={produccionRend.rendimientos_por_tipo}
                      xKey="tipo_fruta"
                      bars={[
                        { key: 'kg_consumido', name: 'MP Consumida (kg)' },
                        { key: 'kg_producido', name: 'PT Producido (kg)' },
                      ]}
                      yFormatter={(v) => formatNumber(v, 0)}
                      height={340}
                    />
                  </CardContent>
                </Card>

                <DataTable
                  columns={[
                    { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },
                    { accessorKey: 'orden', header: 'Orden', enableSorting: true },
                    { accessorKey: 'tipo_fruta', header: 'Tipo Fruta' },
                    { accessorKey: 'estado', header: 'Estado' },
                    { accessorKey: 'kg_consumido', header: 'MP (kg)', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
                    { accessorKey: 'kg_producido', header: 'PT (kg)', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
                    { accessorKey: 'rendimiento_pct', header: 'Rendimiento %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },
                    { accessorKey: 'merma_pct', header: 'Merma %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },
                  ]}
                  data={produccionRend.detalle_ordenes}
                  loading={loadingProdRend}
                  searchPlaceholder="Buscar orden o tipo fruta..."
                />
              </>
            ) : (
              <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
                Selecciona un rango de fechas y presiona <strong>Buscar</strong> para cargar datos.
              </div>
            )}
          </div>
        </TabsContent>

      </Tabs>

    </div>

  )

}

export default RendimientoPage
