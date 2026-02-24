import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { type ColumnDef } from '@tanstack/react-table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { FilterBar } from '@/components/forms/FilterBar'
import { KPICard } from '@/components/shared/KPICard'
import { DataTable } from '@/components/tables/DataTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { CURRENT_YEAR } from '@/lib/constants'
import { formatNumber, formatCurrency } from '@/lib/utils'
import {
  useRecepciones,
  useRecepcionesKPIs,
  useAprobaciones,
  useFletes,
  usePallets,
  useAprobarFlete,
  useRechazarFlete,
  useCurvaAbastecimiento,
  useEspeciesDisponibles,
  useKgLineaProductividad,
  useRutasLogistica,
  useProformasProveedores,
  useProformasBorradores,
  useCambiarMonedaProforma,
  useEliminarLineaProforma,
  type Recepcion,
  type AprobacionFlete,
  type PalletSeguimiento,
  type CurvaFilters,
  type RutaLogistica,
} from '@/api/recepciones'
import { BarChart } from '@/components/charts/BarChart'
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts'
import { CHART_COLORS } from '@/lib/constants'
import { MultiSelect } from '@/components/forms/MultiSelect'

const estadoBadge: Record<string, 'default' | 'success' | 'warning' | 'destructive'> = {
  aprobado: 'success',
  pendiente: 'warning',
  rechazado: 'destructive',
}

const columns: ColumnDef<Recepcion>[] = [
  { accessorKey: 'nombre', header: 'Recepción', enableSorting: true },
  { accessorKey: 'proveedor', header: 'Proveedor', enableSorting: true },
  { accessorKey: 'producto', header: 'Producto' },
  { accessorKey: 'cantidad_kg', header: 'Kg', cell: ({ getValue }) => Number(getValue()).toLocaleString('es-CL'), enableSorting: true },
  { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },
  {
    accessorKey: 'estado', header: 'Estado',
    cell: ({ getValue }) => {
      const v = String(getValue()).toLowerCase()
      return <Badge variant={estadoBadge[v] ?? 'secondary'}>{getValue() as string}</Badge>
    },
  },
]

// ─── Fletes Tab ────────────────────────────────────────────────────────────────

function FleteTab({ filters }: { filters: { year: number; months?: number[] } }) {
  const qc = useQueryClient()
  const [motivoRechazo, setMotivoRechazo] = useState<Record<number, string>>({})

  const { data: fletes = [], isLoading } = useFletes(filters)
  const aprobarMut = useAprobarFlete()
  const rechazarMut = useRechazarFlete()

  const pendientes = fletes.filter(f => f.estado === 'pendiente')
  const aprobados = fletes.filter(f => f.estado === 'aprobado')
  const rechazados = fletes.filter(f => f.estado === 'rechazado')

  const handleAprobar = async (id: number) => {
    await aprobarMut.mutateAsync(id)
    qc.invalidateQueries({ queryKey: ['recepciones', 'fletes'] })
  }

  const handleRechazar = async (id: number) => {
    const motivo = motivoRechazo[id] ?? ''
    if (!motivo.trim()) { alert('Ingresa un motivo de rechazo'); return }
    await rechazarMut.mutateAsync({ id, motivo })
    qc.invalidateQueries({ queryKey: ['recepciones', 'fletes'] })
  }

  const colsFletes: ColumnDef<AprobacionFlete>[] = [
    { accessorKey: 'id', header: 'ID' },
    { accessorKey: 'proveedor', header: 'Proveedor', enableSorting: true },
    { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },
    { accessorKey: 'monto', header: 'Monto', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ getValue }) => {
        const v = String(getValue())
        const variant = v === 'aprobado' ? 'success' : v === 'rechazado' ? 'destructive' : 'warning'
        return <Badge variant={variant}>{v.charAt(0).toUpperCase() + v.slice(1)}</Badge>
      },
    },
    {
      id: 'acciones',
      header: 'Acciones',
      cell: ({ row }) => {
        const flete = row.original
        if (flete.estado !== 'pendiente') return null
        return (
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={() => handleAprobar(flete.id)}
              disabled={aprobarMut.isPending}
            >
              ✅ Aprobar
            </Button>
            <Input
              className="w-32 h-7 text-xs"
              placeholder="Motivo..."
              value={motivoRechazo[flete.id] ?? ''}
              onChange={(e) => setMotivoRechazo(prev => ({ ...prev, [flete.id]: e.target.value }))}
            />
            <Button
              size="sm"
              variant="destructive"
              onClick={() => handleRechazar(flete.id)}
              disabled={rechazarMut.isPending}
            >
              ❌ Rechazar
            </Button>
          </div>
        )
      },
    },
  ]

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-3">
        <KPICard label="Pendientes" value={pendientes.length} loading={isLoading} />
        <KPICard label="Aprobados" value={aprobados.length} loading={isLoading} />
        <KPICard label="Rechazados" value={rechazados.length} loading={isLoading} />
      </div>
      <DataTable
        columns={colsFletes}
        data={fletes}
        loading={isLoading}
        searchPlaceholder="Buscar flete o proveedor..."
      />
    </div>
  )
}

// ─── Pallets Tab ───────────────────────────────────────────────────────────────

function PalletsTab({ filters }: { filters: { year: number; months?: number[] } }) {
  const { data: pallets = [], isLoading } = usePallets(filters)

  const totalPallets = pallets.length
  const totalKg = pallets.reduce((s, r) => s + r.cantidad, 0)

  const colsPallets: ColumnDef<PalletSeguimiento>[] = [
    { accessorKey: 'id', header: 'Pallet ID', enableSorting: true },
    { accessorKey: 'producto', header: 'Producto', enableSorting: true },
    { accessorKey: 'ubicacion', header: 'Ubicación' },
    { accessorKey: 'cantidad', header: 'Kg', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
    {
      accessorKey: 'estado',
      header: 'Estado',
      cell: ({ getValue }) => {
        const v = String(getValue())
        const variant = v === 'disponible' ? 'success' : v === 'en_proceso' ? 'warning' : 'default'
        return <Badge variant={variant}>{v.replace('_', ' ')}</Badge>
      },
    },
    { accessorKey: 'fecha_ingreso', header: 'Fecha Ingreso', enableSorting: true },
  ]

  return (
    <div className="space-y-4">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KPICard label="Total Pallets" value={totalPallets} loading={isLoading} />
        <KPICard label="Total Kg" value={totalKg} loading={isLoading} />
        <KPICard label="Disponibles" value={pallets.filter(p => p.estado === 'disponible').length} loading={isLoading} />
        <KPICard label="En Proceso" value={pallets.filter(p => p.estado === 'en_proceso').length} loading={isLoading} />
      </div>
      <DataTable
        columns={colsPallets}
        data={pallets}
        loading={isLoading}
        searchPlaceholder="Buscar pallet, producto o ubicación..."
      />
    </div>
  )
}

// ─── Curva Tab ────────────────────────────────────────────────────────────────
const PLANTAS = ['RFP', 'VILKUN', 'SAN JOSE']

function CurvaTab() {
  const [plantasSeleccionadas, setPlantasSeleccionadas] = useState<string[]>(['RFP', 'VILKUN', 'SAN JOSE'])
  const [especiesSeleccionadas, setEspeciesSeleccionadas] = useState<string[]>([])
  const [loaded, setLoaded] = useState(false)

  const { data: especiesDisponibles = [] } = useEspeciesDisponibles()

  const curvaFilters: CurvaFilters = {
    plantas: plantasSeleccionadas,
    especies: especiesSeleccionadas.length ? especiesSeleccionadas : undefined,
  }

  const { data: curva, isLoading, refetch } = useCurvaAbastecimiento(curvaFilters, loaded)

  const handleCargar = () => {
    if (!loaded) {
      setLoaded(true)
    } else {
      refetch()
    }
  }

  return (
    <div className="space-y-4">
      {/* Filters */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-medium">Filtros de Curva de Abastecimiento</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-wrap gap-6">
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-2">Plantas</p>
              <div className="flex gap-3">
                {PLANTAS.map((p) => (
                  <label key={p} className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={plantasSeleccionadas.includes(p)}
                      onChange={(e) =>
                        setPlantasSeleccionadas(e.target.checked
                          ? [...plantasSeleccionadas, p]
                          : plantasSeleccionadas.filter((x) => x !== p)
                        )
                      }
                      className="rounded"
                    />
                    <span className="text-sm">{p}</span>
                  </label>
                ))}
              </div>
            </div>

            {especiesDisponibles.length > 0 && (
              <div>
                <p className="text-xs font-medium text-muted-foreground mb-2">Especies</p>
                <MultiSelect
                  options={especiesDisponibles.map((e) => ({ label: e, value: e }))}
                  selected={especiesSeleccionadas}
                  onChange={setEspeciesSeleccionadas}
                  placeholder="Todas las especies"
                />
              </div>
            )}
          </div>

          <Button onClick={handleCargar} disabled={isLoading || plantasSeleccionadas.length === 0}>
            {isLoading ? 'Cargando...' : '📊 Cargar Curva de Abastecimiento'}
          </Button>
        </CardContent>
      </Card>

      {/* Summary KPIs */}
      {curva && (
        <div className="grid gap-4 sm:grid-cols-3">
          <KPICard label="Total Proyectado" value={curva.total_proyectado} loading={isLoading} />
          <KPICard label="Total Recepcionado" value={curva.total_recepcionado} loading={isLoading} />
          <KPICard label="Cumplimiento Promedio" value={curva.cumplimiento_promedio} format="number" unit="%" loading={isLoading} />
        </div>
      )}

      {/* Chart */}
      {isLoading && <LoadingSpinner />}
      {curva && curva.puntos.length > 0 && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">Proyectado vs Recepcionado por Semana</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={curva.puntos} margin={{ top: 8, right: 32, bottom: 8, left: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                <XAxis
                  dataKey="semana"
                  tickFormatter={(v) => `S${v}`}
                  tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 12 }}
                  stroke="hsl(var(--border))"
                />
                <YAxis
                  yAxisId="kg"
                  tickFormatter={(v) => `${formatNumber(v / 1000, 0)}t`}
                  tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                  stroke="hsl(var(--border))"
                />
                <YAxis
                  yAxisId="pct"
                  orientation="right"
                  tickFormatter={(v) => `${v}%`}
                  tick={{ fill: 'hsl(var(--muted-foreground))', fontSize: 11 }}
                  stroke="hsl(var(--border))"
                  domain={[0, 150]}
                />
                <Tooltip
                  contentStyle={{ backgroundColor: 'hsl(var(--popover))', border: '1px solid hsl(var(--border))', borderRadius: 8 }}
                  labelFormatter={(v) => `Semana ${v}`}
                  formatter={(v: number, name: string) => [
                    name === 'cumplimiento_pct' ? `${v.toFixed(1)}%` : `${formatNumber(v, 0)} kg`,
                    name === 'proyectado_kg' ? 'Proyectado' : name === 'recepcionado_kg' ? 'Recepcionado' : 'Cumplimiento',
                  ]}
                />
                <Legend />
                <Bar yAxisId="kg" dataKey="proyectado_kg" name="Proyectado (kg)" fill={CHART_COLORS[1]} opacity={0.7} radius={[3, 3, 0, 0]} />
                <Bar yAxisId="kg" dataKey="recepcionado_kg" name="Recepcionado (kg)" fill={CHART_COLORS[0]} radius={[3, 3, 0, 0]} />
                <Line
                  yAxisId="pct"
                  type="monotone"
                  dataKey="cumplimiento_pct"
                  name="Cumplimiento %"
                  stroke={CHART_COLORS[4]}
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </ComposedChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ─── Proforma Consolidada Tab ──────────────────────────────────────────────────

function ProformaConsolidadaTab() {
  const today = new Date().toISOString().slice(0, 10)
  const firstDay = today.slice(0, 8) + '01'

  const [fechaDesde, setFechaDesde] = useState(firstDay)
  const [fechaHasta, setFechaHasta] = useState(today)
  const [enabled, setEnabled] = useState(false)

  const { data: rutas = [], isLoading } = useRutasLogistica(fechaDesde, fechaHasta, enabled)

  const grouped = rutas.reduce<Record<string, RutaLogistica[]>>((acc, r) => {
    const key = r.transportista
    if (!acc[key]) acc[key] = []
    acc[key].push(r)
    return acc
  }, {})

  const totalRutas = rutas.length
  const totalKms = rutas.reduce((s, r) => s + r.kms, 0)
  const totalKg = rutas.reduce((s, r) => s + r.kg_total, 0)
  const totalCosto = rutas.reduce((s, r) => s + r.costo_total, 0)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">Filtros — Rutas Logísticas por Período</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Desde</label>
              <Input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="w-36" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Hasta</label>
              <Input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="w-36" />
            </div>
            <Button onClick={() => { setEnabled(true) }} disabled={isLoading}>
              {isLoading ? 'Cargando...' : 'Cargar Rutas'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingSpinner />
      ) : !enabled ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Selecciona un rango de fechas y presiona <strong>Cargar Rutas</strong>.
        </div>
      ) : rutas.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Sin rutas logísticas para el período seleccionado.
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <KPICard label="Total Rutas" value={totalRutas} loading={false} />
            <KPICard label="Transportistas" value={Object.keys(grouped).length} loading={false} />
            <KPICard label="Total KMs" value={totalKms} format="number" loading={false} />
            <KPICard label="Costo Total" value={totalCosto} format="currency" loading={false} />
          </div>

          {Object.entries(grouped).map(([transportista, ruts]) => {
            const subtotalKms = ruts.reduce((s, r) => s + r.kms, 0)
            const subtotalKg = ruts.reduce((s, r) => s + r.kg_total, 0)
            const subtotalCosto = ruts.reduce((s, r) => s + r.costo_total, 0)
            return (
              <Card key={transportista}>
                <CardHeader className="py-3">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <CardTitle className="text-base">🚛 {transportista}</CardTitle>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span>{ruts.length} rutas</span>
                      <span>{formatNumber(subtotalKms, 0)} km</span>
                      <span>{formatNumber(subtotalKg, 0)} kg</span>
                      <span className="font-semibold text-foreground">{formatCurrency(subtotalCosto)}</span>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <DataTable
                    columns={[
                      { accessorKey: 'nombre', header: 'Ruta', enableSorting: true },
                      {
                        accessorKey: 'oc_nombres',
                        header: 'OCs',
                        cell: ({ getValue }) => (getValue() as string[]).join(', '),
                      },
                      { accessorKey: 'num_ocs', header: 'N° OCs', enableSorting: true },
                      {
                        accessorKey: 'kms',
                        header: 'KMs',
                        cell: ({ getValue }) => formatNumber(Number(getValue()), 0),
                        enableSorting: true,
                      },
                      {
                        accessorKey: 'kg_total',
                        header: 'KG',
                        cell: ({ getValue }) => formatNumber(Number(getValue()), 0),
                        enableSorting: true,
                      },
                      {
                        accessorKey: 'costo_total',
                        header: 'Costo',
                        cell: ({ getValue }) => formatCurrency(Number(getValue())),
                        enableSorting: true,
                      },
                    ]}
                    data={ruts}
                    loading={false}
                    searchPlaceholder="Buscar ruta..."
                  />
                </CardContent>
              </Card>
            )
          })}
        </>
      )}
    </div>
  )
}

// ─── Ajuste Proformas Tab ──────────────────────────────────────────────────────

function AjusteProformasTab() {
  const qc = useQueryClient()
  const today = new Date().toISOString().slice(0, 10)
  const firstDay = today.slice(0, 8) + '01'

  const [proveedorId, setProveedorId] = useState<number | null>(null)
  const [fechaDesde, setFechaDesde] = useState(firstDay)
  const [fechaHasta, setFechaHasta] = useState(today)
  const [moneda, setMoneda] = useState('Todas')
  const [enviada, setEnviada] = useState('Todas')
  const [enabled, setEnabled] = useState(false)
  const [expanded, setExpanded] = useState<Set<number>>(new Set())

  const { data: proveedores = [] } = useProformasProveedores()

  const params = {
    proveedor_id: proveedorId ?? undefined,
    fecha_desde: fechaDesde,
    fecha_hasta: fechaHasta,
    moneda_filtro: moneda !== 'Todas' ? moneda : undefined,
    solo_enviadas: enviada === 'Todas' ? undefined : enviada === 'Enviadas',
  }

  const { data: borradores = [], isLoading, refetch } = useProformasBorradores(params, enabled)
  const cambiarMut = useCambiarMonedaProforma()
  const eliminarMut = useEliminarLineaProforma()

  const handleBuscar = () => { setEnabled(true); if (enabled) refetch() }

  const toggleExpanded = (id: number) => {
    setExpanded(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const handleCambiarMoneda = async (id: number) => {
    await cambiarMut.mutateAsync({ facturaId: id })
    qc.invalidateQueries({ queryKey: ['proformas', 'borradores'] })
  }

  const handleEliminarLinea = async (lineaId: number) => {
    if (!confirm('¿Eliminar esta línea? Esta acción no se puede deshacer en Odoo.')) return
    await eliminarMut.mutateAsync(lineaId)
    qc.invalidateQueries({ queryKey: ['proformas', 'borradores'] })
  }

  const totalUSD = borradores.filter(b => b.es_usd).length
  const totalCLP = borradores.filter(b => !b.es_usd).length

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">Filtros — Facturas en Borrador</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Proveedor</label>
              <Select
                value={proveedorId?.toString() ?? 'todos'}
                onValueChange={v => setProveedorId(v === 'todos' ? null : Number(v))}
              >
                <SelectTrigger className="w-48">
                  <SelectValue placeholder="Todos" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="todos">Todos</SelectItem>
                  {proveedores.map(p => (
                    <SelectItem key={p.id} value={p.id.toString()}>{p.nombre}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Desde</label>
              <Input type="date" value={fechaDesde} onChange={e => setFechaDesde(e.target.value)} className="w-36" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Hasta</label>
              <Input type="date" value={fechaHasta} onChange={e => setFechaHasta(e.target.value)} className="w-36" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Moneda</label>
              <Select value={moneda} onValueChange={setMoneda}>
                <SelectTrigger className="w-28">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todas">Todas</SelectItem>
                  <SelectItem value="USD">USD</SelectItem>
                  <SelectItem value="CLP">CLP</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Envío</label>
              <Select value={enviada} onValueChange={setEnviada}>
                <SelectTrigger className="w-36">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="Todas">Todas</SelectItem>
                  <SelectItem value="No Enviadas">No Enviadas</SelectItem>
                  <SelectItem value="Enviadas">Enviadas</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button onClick={handleBuscar} disabled={isLoading}>
              {isLoading ? 'Buscando...' : 'Buscar Facturas'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading ? (
        <LoadingSpinner />
      ) : !enabled ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          Configure los filtros y presione <strong>Buscar Facturas</strong>.
        </div>
      ) : borradores.length === 0 ? (
        <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
          No se encontraron facturas en borrador con los filtros seleccionados.
        </div>
      ) : (
        <>
          <div className="grid gap-4 sm:grid-cols-3">
            <KPICard label="Total Facturas" value={borradores.length} loading={false} />
            <KPICard label="En USD" value={totalUSD} loading={false} />
            <KPICard label="En CLP" value={totalCLP} loading={false} />
          </div>

          <div className="space-y-3">
            {borradores.map(factura => (
              <Card key={factura.id} className={factura.es_usd ? 'border-amber-500/50' : ''}>
                <CardHeader
                  className="py-3 cursor-pointer select-none"
                  onClick={() => toggleExpanded(factura.id)}
                >
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <div>
                      <p className="text-sm font-medium">{factura.nombre}</p>
                      <p className="text-xs text-muted-foreground">
                        {factura.proveedor_nombre} · {factura.fecha_creacion}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      <Badge variant={factura.es_usd ? 'warning' : 'default'}>{factura.moneda}</Badge>
                      <Badge variant={factura.enviada ? 'success' : 'secondary'}>
                        {factura.enviada ? 'Enviada' : 'No enviada'}
                      </Badge>
                      <span className="text-sm font-semibold">
                        {factura.es_usd
                          ? `USD ${formatNumber(factura.total_usd, 2)}`
                          : formatCurrency(factura.total_clp)}
                      </span>
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0">
                        {expanded.has(factura.id) ? '▲' : '▼'}
                      </Button>
                    </div>
                  </div>
                </CardHeader>

                {expanded.has(factura.id) && (
                  <CardContent className="pt-0 space-y-3">
                    <DataTable
                      columns={[
                        { accessorKey: 'descripcion', header: 'Descripción', enableSorting: true },
                        {
                          accessorKey: 'cantidad',
                          header: 'Cantidad',
                          cell: ({ getValue }) => formatNumber(Number(getValue()), 2),
                        },
                        {
                          accessorKey: 'precio_usd',
                          header: 'Precio USD',
                          cell: ({ getValue }) => `$${formatNumber(Number(getValue()), 4)}`,
                        },
                        {
                          accessorKey: 'precio_clp',
                          header: 'Precio CLP',
                          cell: ({ getValue }) => formatCurrency(Number(getValue())),
                        },
                        {
                          accessorKey: 'subtotal_usd',
                          header: 'Subtotal USD',
                          cell: ({ getValue }) => `$${formatNumber(Number(getValue()), 2)}`,
                          enableSorting: true,
                        },
                        {
                          id: 'acciones',
                          header: 'Acciones',
                          cell: ({ row }) => (
                            <Button
                              variant="destructive"
                              size="sm"
                              onClick={e => { e.stopPropagation(); handleEliminarLinea(row.original.id) }}
                              disabled={eliminarMut.isPending}
                            >
                              Eliminar
                            </Button>
                          ),
                        },
                      ]}
                      data={factura.lineas}
                      loading={false}
                      searchPlaceholder="Buscar línea..."
                    />
                    {factura.es_usd && (
                      <div className="flex justify-end pt-1">
                        <Button
                          onClick={() => handleCambiarMoneda(factura.id)}
                          disabled={cambiarMut.isPending}
                          className="bg-amber-600 hover:bg-amber-700"
                        >
                          💱 Convertir USD → CLP
                        </Button>
                      </div>
                    )}
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function RecepcionesPage() {
  const [year, setYear] = useState(CURRENT_YEAR)
  const [months, setMonths] = useState<number[]>([])

  // KG Línea date range (default: last 7 days)
  const [kgFechaInicio, setKgFechaInicio] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 7); return d.toISOString().slice(0, 10)
  })
  const [kgFechaFin, setKgFechaFin] = useState(() => new Date().toISOString().slice(0, 10))
  const [kgEnabled, setKgEnabled] = useState(false)

  const filters = { year, months: months.length ? months : undefined }

  const { data: recepciones = [], isLoading: loadingRec } = useRecepciones(filters)
  const { data: kpis = [], isLoading: loadingKPIs } = useRecepcionesKPIs(filters)
  const { data: aprobaciones = [], isLoading: loadingAprov } = useAprobaciones(filters)
  const { data: kgLinea, isLoading: loadingKgLinea, refetch: refetchKg } = useKgLineaProductividad(kgFechaInicio, kgFechaFin, kgEnabled)

  return (
    <div className="space-y-4">
      <PageHeader title="Recepciones" description="Gestión y seguimiento de recepciones de materia prima">
        <ExportButton data={recepciones as unknown as Record<string, unknown>[]} filename="recepciones" />
      </PageHeader>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      <Tabs defaultValue="kpis">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="kpis">📊 KPIs</TabsTrigger>
          <TabsTrigger value="gestion">📋 Gestión</TabsTrigger>
          <TabsTrigger value="aprobaciones">✅ Aprobaciones</TabsTrigger>
          <TabsTrigger value="curva">📈 Curva Abastec.</TabsTrigger>
          <TabsTrigger value="fletes">🚛 Fletes</TabsTrigger>
          <TabsTrigger value="pallets">📦 Pallets</TabsTrigger>
          <TabsTrigger value="kg-linea">⚡ KG por Línea</TabsTrigger>
          <TabsTrigger value="proforma-consolidada">🚚 Proforma Consolidada</TabsTrigger>
          <TabsTrigger value="ajuste-proformas">📄 Ajuste Proformas</TabsTrigger>
        </TabsList>

        <TabsContent value="kpis" className="mt-4">
          {loadingKPIs ? <LoadingSpinner /> : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {kpis.map((kpi) => <KPICard key={kpi.label} {...kpi} />)}
            </div>
          )}
        </TabsContent>

        <TabsContent value="gestion" className="mt-4">
          <DataTable columns={columns} data={recepciones} loading={loadingRec} searchPlaceholder="Buscar recepción..." />
        </TabsContent>

        <TabsContent value="aprobaciones" className="mt-4">
          <DataTable columns={columns} data={aprobaciones} loading={loadingAprov} searchPlaceholder="Buscar..." />
        </TabsContent>

        <TabsContent value="curva" className="mt-4">
          <CurvaTab />
        </TabsContent>

        <TabsContent value="fletes" className="mt-4">
          <FleteTab filters={filters} />
        </TabsContent>

        <TabsContent value="pallets" className="mt-4">
          <PalletsTab filters={filters} />
        </TabsContent>

        {/* KG por Línea / Productividad */}
        <TabsContent value="kg-linea" className="mt-4">
          <div className="space-y-4">
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">Filtros — KG/Hora por Sala de Proceso</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Desde</label>
                    <Input type="date" value={kgFechaInicio} onChange={e => setKgFechaInicio(e.target.value)} className="w-36" />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Hasta</label>
                    <Input type="date" value={kgFechaFin} onChange={e => setKgFechaFin(e.target.value)} className="w-36" />
                  </div>
                  <Button onClick={() => { setKgEnabled(true); refetchKg() }}>
                    Buscar
                  </Button>
                </div>
              </CardContent>
            </Card>

            {loadingKgLinea ? (
              <LoadingSpinner />
            ) : kgLinea ? (
              <>
                <div className="grid gap-4 sm:grid-cols-3">
                  <KPICard label="Total KG Producidos" value={kgLinea.total_kg} format="number" loading={false} />
                  <KPICard label="Promedio KG/Hora" value={kgLinea.prom_kg_hora} format="number" loading={false} />
                  <KPICard label="Salas Activas" value={kgLinea.salas_activas} loading={false} />
                </div>

                <Card>
                  <CardHeader className="py-3">
                    <CardTitle className="text-base">KG/Hora por Sala (Top 12)</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <BarChart
                      data={[...kgLinea.salas]
                        .sort((a, b) => b.kg_por_hora - a.kg_por_hora)
                        .slice(0, 12)}
                      xKey="sala"
                      bars={[{ key: 'kg_por_hora', name: 'KG/Hora' }]}
                      yFormatter={(v) => formatNumber(v, 0)}
                      horizontal
                      height={420}
                    />
                  </CardContent>
                </Card>

                <DataTable
                  columns={[
                    { accessorKey: 'sala', header: 'Sala', enableSorting: true },
                    { accessorKey: 'kg_pt', header: 'KG Producidos', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },
                    { accessorKey: 'kg_por_hora', header: 'KG/Hora', cell: ({ getValue }) => formatNumber(Number(getValue()), 1), enableSorting: true },
                    { accessorKey: 'rendimiento', header: 'Rendimiento %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },
                    { accessorKey: 'hh_total', header: 'HH Totales', cell: ({ getValue }) => formatNumber(Number(getValue()), 1), enableSorting: true },
                    { accessorKey: 'num_mos', header: 'Procesos', enableSorting: true },
                  ]}
                  data={kgLinea.salas}
                  loading={loadingKgLinea}
                  searchPlaceholder="Buscar sala..."
                />
              </>
            ) : (
              <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
                Selecciona un rango de fechas y presiona <strong>Buscar</strong> para cargar datos.
              </div>
            )}
          </div>
        </TabsContent>

        <TabsContent value="proforma-consolidada" className="mt-4">
          <ProformaConsolidadaTab />
        </TabsContent>

        <TabsContent value="ajuste-proformas" className="mt-4">
          <AjusteProformasTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default RecepcionesPage
