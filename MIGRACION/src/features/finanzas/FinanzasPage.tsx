import { useState } from 'react'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { FilterBar } from '@/components/forms/FilterBar'
import { ExportButton } from '@/components/tables/ExportButton'
import { DataTable } from '@/components/tables/DataTable'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { EmptyState } from '@/components/shared/EmptyState'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { CURRENT_YEAR } from '@/lib/constants'
import { formatCurrency } from '@/lib/utils'
import { useEERR, useEERRYTD, useEERRMensualizado, useCuentas, useEERRAgrupado, useEERRDetalle, useFlujoCajaMensual, useFlujoCajaSemanal } from '@/api/finanzas'
import type { EERRYTDRow } from '@/types/finanzas'
import type { ColumnDef } from '@tanstack/react-table'
import { KPICard } from '@/components/shared/KPICard'
import { BarChart } from '@/components/charts/BarChart'

const ACTIVITY_KEYS = ['OPERACION', 'INVERSION', 'FINANCIAMIENTO'] as const
const ACTIVITY_LABELS: Record<string, string> = {
  OPERACION: '🟢 Actividades de Operación',
  INVERSION: '🔵 Actividades de Inversión',
  FINANCIAMIENTO: '🟣 Actividades de Financiamiento',
}

function FlujoCajaTab() {
  const [odooUser, setOdooUser] = useState('')
  const [odooKey, setOdooKey] = useState('')
  const [fechaInicio, setFechaInicio] = useState(`${CURRENT_YEAR}-01-01`)
  const [fechaFin, setFechaFin] = useState(new Date().toISOString().split('T')[0])
  const [agrupacion, setAgrupacion] = useState<'mensual' | 'semanal'>('mensual')
  const [incluirProyecciones, setIncluirProyecciones] = useState(false)
  const [shouldLoad, setShouldLoad] = useState(false)
  const [filtroOp, setFiltroOp] = useState(true)
  const [filtroInv, setFiltroInv] = useState(true)
  const [filtroFin, setFiltroFin] = useState(true)

  const baseParams = { fechaInicio, fechaFin, odooUser, odooKey, incluirProyecciones }
  const mensualQuery = useFlujoCajaMensual({ ...baseParams, enabled: shouldLoad && agrupacion === 'mensual' })
  const semanalQuery = useFlujoCajaSemanal({ ...baseParams, enabled: shouldLoad && agrupacion === 'semanal' })
  const { data, isLoading, error } = agrupacion === 'mensual' ? mensualQuery : semanalQuery

  const hasCredentials = !!odooUser && !!odooKey

  const handleGenerar = () => {
    setShouldLoad(false)
    requestAnimationFrame(() => setShouldLoad(true))
  }

  const activityVisible: Record<string, boolean> = {
    OPERACION: filtroOp,
    INVERSION: filtroInv,
    FINANCIAMIENTO: filtroFin,
  }

  return (
    <div className="space-y-4">
      {/* Credentials */}
      <Card>
        <CardHeader><CardTitle className="text-sm font-medium text-muted-foreground">🔐 Credenciales Odoo</CardTitle></CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-3 items-center">
            <Input type="email" placeholder="usuario@riofuturo.cl" value={odooUser} onChange={e => setOdooUser(e.target.value)} className="w-56" />
            <Input type="password" placeholder="Odoo API key" value={odooKey} onChange={e => setOdooKey(e.target.value)} className="w-56" />
          </div>
        </CardContent>
      </Card>

      {/* Controls */}
      <Card>
        <CardContent className="pt-4">
          <div className="flex flex-wrap gap-4 items-end">
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Desde</label>
              <Input type="date" value={fechaInicio} onChange={e => setFechaInicio(e.target.value)} className="w-40" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Hasta</label>
              <Input type="date" value={fechaFin} onChange={e => setFechaFin(e.target.value)} className="w-40" />
            </div>
            <div className="flex flex-col gap-1">
              <label className="text-xs text-muted-foreground">Agrupación</label>
              <div className="flex gap-1">
                <Button size="sm" variant={agrupacion === 'mensual' ? 'default' : 'outline'} onClick={() => setAgrupacion('mensual')}>Mensual</Button>
                <Button size="sm" variant={agrupacion === 'semanal' ? 'default' : 'outline'} onClick={() => setAgrupacion('semanal')}>Semanal</Button>
              </div>
            </div>
            <div className="flex flex-col gap-2">
              <label className="text-xs text-muted-foreground">Opciones</label>
              <label className="flex items-center gap-2 text-sm cursor-pointer">
                <input type="checkbox" checked={incluirProyecciones} onChange={e => setIncluirProyecciones(e.target.checked)} className="accent-primary" />
                🔮 Incluir proyecciones
              </label>
            </div>
            <Button onClick={handleGenerar} disabled={!hasCredentials || isLoading} className="self-end">
              {isLoading ? '⏳ Cargando...' : '🔄 Generar'}
            </Button>
          </div>
          {/* Activity filters */}
          <div className="flex gap-4 mt-3">
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={filtroOp} onChange={e => setFiltroOp(e.target.checked)} className="accent-green-500" />🟢 Operación
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={filtroInv} onChange={e => setFiltroInv(e.target.checked)} className="accent-blue-500" />🔵 Inversión
            </label>
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input type="checkbox" checked={filtroFin} onChange={e => setFiltroFin(e.target.checked)} className="accent-purple-500" />🟣 Financiamiento
            </label>
          </div>
        </CardContent>
      </Card>

      {isLoading && <LoadingSpinner />}

      {error && (
        <Card className="border-red-500/30 bg-red-500/10">
          <CardContent className="pt-4 text-sm text-red-400">
            ❌ {(error as Error).message}
          </CardContent>
        </Card>
      )}

      {data && (
        <>
          {/* KPIs */}
          <div className="grid gap-4 sm:grid-cols-3">
            <KPICard label="Efectivo Inicial" value={data.conciliacion.efectivo_inicial} format="currency" />
            <KPICard label="Variación Neta" value={data.conciliacion.variacion} format="currency" change_type={data.conciliacion.variacion >= 0 ? 'increase' : 'decrease'} />
            <KPICard label="Efectivo Final" value={data.conciliacion.efectivo_final} format="currency" />
          </div>

          {/* Flujo Table */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Flujo de Caja IAS 7 — {agrupacion === 'mensual' ? 'Mensual' : 'Semanal'}</CardTitle>
            </CardHeader>
            <CardContent className="overflow-auto">
              <table className="w-full text-sm min-w-max">
                <thead>
                  <tr className="border-b bg-muted/40">
                    <th className="px-3 py-2 text-left sticky left-0 bg-muted/40 min-w-[240px]">Concepto</th>
                    {data.meses.map(m => (
                      <th key={m} className="px-3 py-2 text-right whitespace-nowrap">{m}</th>
                    ))}
                    <th className="px-3 py-2 text-right font-bold">Total</th>
                  </tr>
                </thead>
                <tbody>
                  {ACTIVITY_KEYS.map(actKey => {
                    if (!activityVisible[actKey]) return null
                    const actData = data.actividades[actKey]
                    if (!actData) return null
                    return (
                      <>
                        {/* Activity header */}
                        <tr key={`hdr-${actKey}`} className="bg-muted/60">
                          <td colSpan={data.meses.length + 2} className="px-3 py-2 font-bold text-foreground">
                            {ACTIVITY_LABELS[actKey]}
                          </td>
                        </tr>
                        {/* Conceptos */}
                        {actData.conceptos.map(c => (
                          <tr key={c.id} className="border-b border-border/30 hover:bg-muted/20">
                            <td className="px-3 py-1.5 sticky left-0 bg-background pl-6 truncate max-w-[240px]" title={c.nombre}>{c.nombre}</td>
                            {data.meses.map(m => {
                              const v = c.montos_por_mes[m] ?? 0
                              return (
                                <td key={m} className={`px-3 py-1.5 text-right tabular-nums ${v < 0 ? 'text-red-400' : v > 0 ? 'text-green-400' : 'text-muted-foreground'}`}>
                                  {v !== 0 ? formatCurrency(v) : '—'}
                                </td>
                              )
                            })}
                            <td className={`px-3 py-1.5 text-right tabular-nums font-medium ${c.total < 0 ? 'text-red-400' : c.total > 0 ? 'text-green-400' : 'text-muted-foreground'}`}>
                              {formatCurrency(c.total)}
                            </td>
                          </tr>
                        ))}
                        {/* Subtotal row */}
                        <tr key={`sub-${actKey}`} className="border-t-2 border-border bg-muted/30">
                          <td className="px-3 py-2 font-semibold sticky left-0 bg-muted/30">Subtotal {actKey.charAt(0) + actKey.slice(1).toLowerCase()}</td>
                          {data.meses.map(m => {
                            const v = actData.subtotal_por_mes[m] ?? 0
                            return (
                              <td key={m} className={`px-3 py-2 text-right tabular-nums font-semibold ${v < 0 ? 'text-red-400' : v > 0 ? 'text-green-400' : 'text-muted-foreground'}`}>
                                {formatCurrency(v)}
                              </td>
                            )
                          })}
                          <td className={`px-3 py-2 text-right tabular-nums font-bold ${actData.subtotal < 0 ? 'text-red-400' : 'text-green-400'}`}>
                            {formatCurrency(actData.subtotal)}
                          </td>
                        </tr>
                      </>
                    )
                  })}
                  {/* Conciliación */}
                  <tr className="border-t-2 border-primary/40 bg-primary/10">
                    <td className="px-3 py-2 font-bold sticky left-0 bg-primary/10">💧 Efectivo Inicial</td>
                    {data.meses.map(m => (
                      <td key={m} className="px-3 py-2 text-right tabular-nums">
                        {data.efectivo_por_mes[m] ? formatCurrency(data.efectivo_por_mes[m].inicial) : '—'}
                      </td>
                    ))}
                    <td className="px-3 py-2 text-right font-bold">{formatCurrency(data.conciliacion.efectivo_inicial)}</td>
                  </tr>
                  <tr className="bg-primary/5">
                    <td className="px-3 py-2 font-bold sticky left-0 bg-primary/5">📈 Variación</td>
                    {data.meses.map(m => {
                      const v = data.efectivo_por_mes[m]?.variacion ?? 0
                      return (
                        <td key={m} className={`px-3 py-2 text-right tabular-nums font-medium ${v < 0 ? 'text-red-400' : 'text-green-400'}`}>
                          {data.efectivo_por_mes[m] ? formatCurrency(v) : '—'}
                        </td>
                      )
                    })}
                    <td className={`px-3 py-2 text-right font-bold ${data.conciliacion.variacion < 0 ? 'text-red-400' : 'text-green-400'}`}>
                      {formatCurrency(data.conciliacion.variacion)}
                    </td>
                  </tr>
                  <tr className="border-t border-primary/40 bg-primary/10">
                    <td className="px-3 py-2 font-bold sticky left-0 bg-primary/10">💰 Efectivo Final</td>
                    {data.meses.map(m => (
                      <td key={m} className="px-3 py-2 text-right tabular-nums">
                        {data.efectivo_por_mes[m] ? formatCurrency(data.efectivo_por_mes[m].final) : '—'}
                      </td>
                    ))}
                    <td className="px-3 py-2 text-right font-bold text-primary">{formatCurrency(data.conciliacion.efectivo_final)}</td>
                  </tr>
                </tbody>
              </table>
            </CardContent>
          </Card>

          {data.cuentas_sin_clasificar && data.cuentas_sin_clasificar.length > 0 && (
            <Card className="border-yellow-500/30 bg-yellow-500/10">
              <CardContent className="pt-4">
                <p className="text-sm font-medium text-yellow-400 mb-2">⚠️ {data.cuentas_sin_clasificar.length} cuentas sin clasificar</p>
                <p className="text-xs text-muted-foreground">{data.cuentas_sin_clasificar.slice(0, 5).join(', ')}{data.cuentas_sin_clasificar.length > 5 ? ` y ${data.cuentas_sin_clasificar.length - 5} más...` : ''}</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

export function FinanzasPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])
  const [agrupMeses, setAgrupMeses] = useState<number[]>([])

  const filters = { year, months: months.length ? months : undefined }

  const { data: eerr, isLoading: loadingEERR } = useEERR(filters)
  const { data: ytd, isLoading: loadingYTD } = useEERRYTD(filters)
  const { data: mensualizado, isLoading: loadingMens } = useEERRMensualizado(filters)
  const { data: cuentas = [], isLoading: loadingCuentas } = useCuentas(filters)
  const { data: agrupado = [], isLoading: loadingAgrup } = useEERRAgrupado(year, agrupMeses)
  const { data: detalle = [], isLoading: loadingDetalle } = useEERRDetalle(year, months)

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
          <FlujoCajaTab />
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


    </div>
  )
}

export default FinanzasPage
