import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { FilterBar } from '@/components/forms/FilterBar'
import { EnterpriseTable } from '@/components/tables/EnterpriseTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { DataTable } from '@/components/tables/DataTable'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { CURRENT_YEAR } from '@/lib/constants'
import { formatCurrency } from '@/lib/utils'
import { useFlujoCaja, useComposicion, useEERR, useEERRYTD, useEERRMensualizado, useCuentas, useEERRAgrupado, useEERRDetalle } from '@/api/finanzas'
import type { FlujoCajaRow, EERRYTDRow } from '@/types/finanzas'
import type { ColumnDef } from '@tanstack/react-table'
import { KPICard } from '@/components/shared/KPICard'
import { BarChart } from '@/components/charts/BarChart'

interface ModalState {
  open: boolean
  row?: FlujoCajaRow
  periodo?: string
  value?: number
}

export function FinanzasPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])
  const [modal, setModal] = useState<ModalState>({ open: false })
  const [agrupMeses, setAgrupMeses] = useState<number[]>([])

  const filters = { year, months: months.length ? months : undefined }

  const { data: flujoCaja, isLoading: loadingFC } = useFlujoCaja(filters)
  const { data: eerr, isLoading: loadingEERR } = useEERR(filters)
  const { data: ytd, isLoading: loadingYTD } = useEERRYTD(filters)
  const { data: mensualizado, isLoading: loadingMens } = useEERRMensualizado(filters)
  const { data: cuentas = [], isLoading: loadingCuentas } = useCuentas(filters)
  const { data: composicion = [], isLoading: loadingComp } = useComposicion(
    { cuenta_id: modal.row?.id ?? '', periodo: modal.periodo ?? '' },
    modal.open && !!modal.row,
  )
  const { data: agrupado = [], isLoading: loadingAgrup } = useEERRAgrupado(year, agrupMeses)
  const { data: detalle = [], isLoading: loadingDetalle } = useEERRDetalle(year, months)

  const handleCellClick = (row: FlujoCajaRow, periodo: string, value: number) => {
    if (row.nivel < 2) return // Only show detail for leaf/near-leaf rows
    setModal({ open: true, row, periodo, value })
  }

  const composicionCols: ColumnDef<typeof composicion[0]>[] = [
    { accessorKey: 'descripcion', header: 'Descripción' },
    { accessorKey: 'cuenta', header: 'Cuenta' },
    {
      accessorKey: 'monto',
      header: 'Monto',
      cell: ({ getValue }) => formatCurrency(Number(getValue())),
    },
    {
      accessorKey: 'porcentaje',
      header: '%',
      cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`,
    },
    { accessorKey: 'documento', header: 'Documento' },
  ]

  return (
    <div className="space-y-4">
      <PageHeader title="Finanzas" description="Estado de resultados, flujo de caja y cuentas contables" />

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <Tabs defaultValue="flujo-caja">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="eerr">📊 Estado de Resultados</TabsTrigger>
          <TabsTrigger value="ytd">📈 YTD</TabsTrigger>
          <TabsTrigger value="mensualizado">💰 Mensualizado</TabsTrigger>
          <TabsTrigger value="flujo-caja">💵 Flujo de Caja</TabsTrigger>
          <TabsTrigger value="cuentas">📁 Cuentas (CG)</TabsTrigger>
          <TabsTrigger value="agrupado">📋 Agrupado</TabsTrigger>
          <TabsTrigger value="detalle">🔍 Detalle Jerárquico</TabsTrigger>
        </TabsList>

        {/* EERR Tab */}
        <TabsContent value="eerr" className="mt-4">
          {loadingEERR ? (
            <LoadingSpinner />
          ) : !eerr ? (
            <EmptyState title="Sin datos" description="No hay datos de estado de resultados para el período seleccionado." />
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Estado de Resultados — {eerr.periodo}</CardTitle>
              </CardHeader>
              <CardContent className="overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/40">
                      <th className="px-4 py-2 text-left">Cuenta</th>
                      <th className="px-4 py-2 text-right">Período Actual</th>
                      <th className="px-4 py-2 text-right">Período Anterior</th>
                      <th className="px-4 py-2 text-right">Variación</th>
                      <th className="px-4 py-2 text-right">Var %</th>
                    </tr>
                  </thead>
                  <tbody>
                    {eerr.rows.map((row, i) => (
                      <tr
                        key={i}
                        className="border-b hover:bg-muted/20"
                        style={{ paddingLeft: row.nivel * 12 }}
                      >
                        <td className="px-4 py-2" style={{ paddingLeft: 16 + row.nivel * 12 }}>
                          <span className={row.nivel === 0 ? 'font-bold' : row.nivel === 1 ? 'font-medium' : ''}>
                            {row.descripcion}
                          </span>
                        </td>
                        <td className="px-4 py-2 text-right tabular-nums">{formatCurrency(row.actual)}</td>
                        <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{formatCurrency(row.anterior)}</td>
                        <td className={`px-4 py-2 text-right tabular-nums ${row.variacion >= 0 ? 'text-green-400' : 'text-red-400'}`}>{formatCurrency(row.variacion)}</td>
                        <td className={`px-4 py-2 text-right ${row.variacion_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{row.variacion_pct.toFixed(1)}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>

                {/* EERR Bar Chart */}
                {eerr.rows.filter(r => r.nivel === 0).length > 0 && (
                  <div className="mt-6">
                    <p className="text-sm font-medium mb-2 text-muted-foreground">Comparación Actual vs Anterior — Cuentas Principales</p>
                    <BarChart
                      data={eerr.rows.filter(r => r.nivel === 0).map(r => ({ cuenta: r.descripcion, actual: r.actual, anterior: r.anterior }))}
                      xKey="cuenta"
                      bars={[
                        { key: 'actual', name: 'Período Actual' },
                        { key: 'anterior', name: 'Período Anterior' },
                      ]}
                      yFormatter={(v) => formatCurrency(v)}
                      height={320}
                    />
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Flujo de Caja Tab */}
        <TabsContent value="flujo-caja" className="mt-4">
          {loadingFC ? (
            <LoadingSpinner />
          ) : !flujoCaja ? (
            <EmptyState title="Sin datos" description="No hay datos de flujo de caja para el período seleccionado." />
          ) : (
            <EnterpriseTable
              data={flujoCaja}
              onCellClick={handleCellClick}
              heatmapConfig={{ enabled: true, type: 'blue' }}
            />
          )}
        </TabsContent>

        {/* YTD Tab */}
        <TabsContent value="ytd" className="mt-4">
          {loadingYTD ? (
            <LoadingSpinner />
          ) : !ytd ? (
            <EmptyState title="Sin datos" description="No hay datos YTD para el período seleccionado." />
          ) : (
            <div className="space-y-4">
              {/* KPI Summary */}
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <KPICard
                  label="Ingresos (Real)"
                  value={ytd.kpis.ingresos_real}
                  change={((ytd.kpis.ingresos_real - ytd.kpis.ingresos_ppto) / Math.abs(ytd.kpis.ingresos_ppto || 1)) * 100}
                  change_type={ytd.kpis.ingresos_real >= ytd.kpis.ingresos_ppto ? 'increase' : 'decrease'}
                  format="currency"
                  loading={false}
                />
                <KPICard
                  label="Costos (Real)"
                  value={ytd.kpis.costos_real}
                  change={((ytd.kpis.costos_real - ytd.kpis.costos_ppto) / Math.abs(ytd.kpis.costos_ppto || 1)) * 100}
                  change_type={ytd.kpis.costos_real <= ytd.kpis.costos_ppto ? 'increase' : 'decrease'}
                  format="currency"
                  loading={false}
                />
                <KPICard
                  label="Utilidad Bruta"
                  value={ytd.kpis.utilidad_bruta}
                  format="currency"
                  loading={false}
                />
                <KPICard
                  label="EBIT"
                  value={ytd.kpis.ebit}
                  format="currency"
                  loading={false}
                />
              </div>

              {/* YTD Table */}
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-base">Estado de Resultados YTD — {ytd.year} (hasta mes {ytd.meses_incluidos})</CardTitle>
                </CardHeader>
                <CardContent className="overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="px-4 py-2 text-left">Concepto</th>
                        <th className="px-4 py-2 text-right">Real YTD</th>
                        <th className="px-4 py-2 text-right">PPTO YTD</th>
                        <th className="px-4 py-2 text-right">Diferencia</th>
                        <th className="px-4 py-2 text-right">Dif %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {ytd.rows.map((row: EERRYTDRow, i: number) => (
                        <tr key={i} className="border-b hover:bg-muted/20">
                          <td
                            className="px-4 py-2"
                            style={{ paddingLeft: 16 + (row.nivel ?? 0) * 12 }}
                          >
                            <span className={row.nivel === 0 ? 'font-bold' : row.nivel === 1 ? 'font-medium' : ''}>
                              {row.concepto}
                            </span>
                          </td>
                          <td className="px-4 py-2 text-right tabular-nums">{formatCurrency(row.real_ytd)}</td>
                          <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{formatCurrency(row.ppto_ytd)}</td>
                          <td className={`px-4 py-2 text-right tabular-nums ${row.diferencia >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {formatCurrency(row.diferencia)}
                          </td>
                          <td className={`px-4 py-2 text-right ${row.diferencia_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {row.diferencia_pct.toFixed(1)}%
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            </div>
          )}
        </TabsContent>

        {/* Mensualizado Tab */}
        <TabsContent value="mensualizado" className="mt-4">
          {loadingMens ? (
            <LoadingSpinner />
          ) : !mensualizado ? (
            <EmptyState title="Sin datos" description="No hay datos mensualizado para el período seleccionado." />
          ) : (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">EERR Mensualizado — {mensualizado.year}</CardTitle>
              </CardHeader>
              <CardContent className="overflow-auto">
                <table className="w-full text-sm min-w-max">
                  <thead>
                    <tr className="border-b bg-muted/40">
                      <th className="px-4 py-2 text-left sticky left-0 bg-muted/40 z-10">Concepto</th>
                      {mensualizado.meses.map((mes) => (
                        <>
                          <th key={`${mes}-r`} className="px-3 py-2 text-right whitespace-nowrap">
                            {new Date(2000, Number(mes) - 1).toLocaleString('es-CL', { month: 'short' }).toUpperCase()} Real
                          </th>
                          <th key={`${mes}-p`} className="px-3 py-2 text-right whitespace-nowrap text-muted-foreground">
                            PPTO
                          </th>
                        </>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {mensualizado.rows.map((row, i) => (
                      <tr key={i} className="border-b hover:bg-muted/20">
                        <td
                          className="px-4 py-2 sticky left-0 bg-background z-10"
                          style={{ paddingLeft: 16 + (row.nivel ?? 0) * 12 }}
                        >
                          <span className={row.nivel === 0 ? 'font-bold' : row.nivel === 1 ? 'font-medium' : ''}>
                            {row.concepto}
                          </span>
                        </td>
                        {mensualizado.meses.map((mes) => {
                          const m = row.meses?.[mes]
                          const diff = m ? (m.real ?? 0) - (m.ppto ?? 0) : 0
                          return (
                            <>
                              <td key={`${mes}-r`} className={`px-3 py-2 text-right tabular-nums ${diff >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {m ? formatCurrency(m.real ?? 0) : '—'}
                              </td>
                              <td key={`${mes}-p`} className="px-3 py-2 text-right tabular-nums text-muted-foreground">
                                {m ? formatCurrency(m.ppto ?? 0) : '—'}
                              </td>
                            </>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Cuentas Tab */}
        <TabsContent value="cuentas" className="mt-4">
          <DataTable
            columns={[
              { accessorKey: 'codigo', header: 'Código', enableSorting: true },
              { accessorKey: 'nombre', header: 'Nombre', enableSorting: true },
              { accessorKey: 'tipo', header: 'Tipo' },
              { accessorKey: 'saldo', header: 'Saldo', cell: ({ getValue }) => formatCurrency(Number(getValue() ?? 0)), enableSorting: true },
              {
                accessorKey: 'activa',
                header: 'Activa',
                cell: ({ getValue }) => (
                  <Badge variant={getValue() ? 'success' : 'default'}>{getValue() ? 'Sí' : 'No'}</Badge>
                ),
              },
            ]}
            data={cuentas}
            loading={loadingCuentas}
            searchPlaceholder="Buscar cuenta por código o nombre..."
          />
        </TabsContent>

        {/* EERR Agrupado por meses seleccionados */}
        <TabsContent value="agrupado" className="mt-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">EERR Agrupado — Selecciona meses a consolidar</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'].map((m, i) => {
                    const n = i + 1
                    const active = agrupMeses.includes(n)
                    return (
                      <button
                        key={n}
                        onClick={() => setAgrupMeses(prev => active ? prev.filter(x => x !== n) : [...prev, n])}
                        className={`rounded-md border px-3 py-1 text-sm transition-colors ${active ? 'border-primary bg-primary text-primary-foreground' : 'border-border hover:border-primary/50'}`}
                      >{m}</button>
                    )
                  })}
                </div>
              </CardContent>
            </Card>

            {agrupMeses.length === 0 ? (
              <div className="rounded-lg border border-dashed p-10 text-center text-muted-foreground">
                Selecciona al menos un mes para generar el Estado de Resultados agrupado.
              </div>
            ) : loadingAgrup ? <LoadingSpinner /> : agrupado.length === 0 ? (
              <EmptyState title="Sin datos" description="No hay datos EERR para los meses seleccionados." />
            ) : (
              <Card>
                <CardHeader className="py-3">
                  <CardTitle className="text-base">EERR Consolidado — {year} meses: {agrupMeses.join(', ')}</CardTitle>
                </CardHeader>
                <CardContent className="overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/40">
                        <th className="px-4 py-2 text-left">Concepto</th>
                        <th className="px-4 py-2 text-right">Real</th>
                        <th className="px-4 py-2 text-right">Ppto</th>
                        <th className="px-4 py-2 text-right">Dif</th>
                        <th className="px-4 py-2 text-right">Dif %</th>
                      </tr>
                    </thead>
                    <tbody>
                      {agrupado.map((row, i) => (
                        <tr key={i} className={`border-b ${row.es_calculado ? 'bg-muted/50 font-semibold' : 'hover:bg-muted/20'}`}>
                          <td className="px-4 py-2">{row.concepto}</td>
                          <td className="px-4 py-2 text-right tabular-nums">{formatCurrency(row.real)}</td>
                          <td className="px-4 py-2 text-right tabular-nums text-muted-foreground">{formatCurrency(row.ppto)}</td>
                          <td className={`px-4 py-2 text-right tabular-nums ${row.dif >= 0 ? 'text-green-400' : 'text-red-400'}`}>{formatCurrency(row.dif)}</td>
                          <td className={`px-4 py-2 text-right ${row.dif_pct >= 0 ? 'text-green-400' : 'text-red-400'}`}>{row.dif_pct.toFixed(1)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* EERR Detalle Jerárquico */}
        <TabsContent value="detalle" className="mt-4">
          {loadingDetalle ? <LoadingSpinner /> : detalle.length === 0 ? (
            <EmptyState title="Sin datos" description="No hay datos de detalle para el período seleccionado." />
          ) : (
            <div className="space-y-4">
              {detalle.map((cat, ci) => (
                <Card key={ci} className={cat.es_calculado ? 'border-primary/30 bg-primary/5' : ''}>
                  <CardHeader className="py-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-bold">{cat.nombre}</CardTitle>
                      <div className="flex gap-6 text-sm tabular-nums">
                        <span className="text-muted-foreground">Real: <span className="text-foreground font-medium">{formatCurrency(cat.real_ytd)}</span></span>
                        <span className="text-muted-foreground">Ppto: <span className="text-foreground font-medium">{formatCurrency(cat.ppto_ytd)}</span></span>
                        <span className={cat.dif >= 0 ? 'text-green-400' : 'text-red-400'}>Dif: {formatCurrency(cat.dif)}</span>
                      </div>
                    </div>
                  </CardHeader>
                  {cat.subcategorias?.length > 0 && (
                    <CardContent className="pt-0">
                      <details>
                        <summary className="cursor-pointer text-xs text-muted-foreground hover:text-foreground mb-2">
                          Ver detalle ({cat.subcategorias.length} subcategorías)
                        </summary>
                        <div className="pl-4 space-y-2 mt-2">
                          {cat.subcategorias.map((sub, si) => (
                            <div key={si} className="rounded border border-border/50 p-2">
                              <div className="flex items-center justify-between text-xs font-medium mb-1">
                                <span>{sub.nombre}</span>
                                <span className={sub.dif >= 0 ? 'text-green-400' : 'text-red-400'}>{formatCurrency(sub.dif)}</span>
                              </div>
                              {sub.nivel3?.length > 0 && (
                                <div className="pl-3 text-xs space-y-1">
                                  {sub.nivel3.map((n3, ni) => (
                                    <div key={ni} className="flex justify-between text-muted-foreground">
                                      <span>{n3.nombre}</span>
                                      <span>{formatCurrency(n3.real_ytd)}</span>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </details>
                    </CardContent>
                  )}
                </Card>
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* Composición Modal */}
      <Dialog open={modal.open} onOpenChange={(o) => !o && setModal({ open: false })}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              Composición — {modal.row?.cuenta} / {modal.periodo}
            </DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground mb-2">
            Total: <span className="text-foreground font-medium">{modal.value !== undefined ? formatCurrency(modal.value) : '—'}</span>
          </p>
          {loadingComp ? (
            <LoadingSpinner />
          ) : (
            <DataTable columns={composicionCols} data={composicion} searchable={false} />
          )}
        </DialogContent>
      </Dialog>
    </div>
  )
}

export default FinanzasPage
