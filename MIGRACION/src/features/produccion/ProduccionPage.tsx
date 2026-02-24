import { useState } from 'react'

import { type ColumnDef } from '@tanstack/react-table'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { PageHeader } from '@/components/layout/PageHeader'

import { FilterBar } from '@/components/forms/FilterBar'

import { DataTable } from '@/components/tables/DataTable'

import { ExportButton } from '@/components/tables/ExportButton'

import { BarChart } from '@/components/charts/BarChart'

import { LineChart } from '@/components/charts/LineChart'

import { PieChart } from '@/components/charts/PieChart'

import { KPICard } from '@/components/shared/KPICard'

import { Badge } from '@/components/ui/badge'

import { Button } from '@/components/ui/button'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

import { Input } from '@/components/ui/input'

import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

import { CURRENT_YEAR } from '@/lib/constants'

import { formatNumber } from '@/lib/utils'

import {

  useProduccionLineas,

  useProduccionTuneles,

  useFabricaciones,

  useClasificacion,

  useProduccionKPIs,

  useMonitorDiario,

  useKgPorLinea,

  usePalletsProduccion,

  useBuscarOrdenesEtiquetas,

  usePalletsOrden,

  useGenerarEtiquetasPDF,

  useBuscarOrdenProcesos,

  useValidarPalletsProcesos,

  useAgregarPalletsProcesos,

  type PalletValidadoProceso,

} from '@/api/produccion'

import type { FabricacionDetalle } from '@/types/produccion'

// ─── Credentials form subcomponent ────────────────────────────────────────────

function CredentialsForm({
  odooUser, odooKey,
  onUser, onKey,
}: { odooUser: string; odooKey: string; onUser: (v: string) => void; onKey: (v: string) => void }) {
  return (
    <Card>
      <CardHeader className="py-3">
        <CardTitle className="text-base">🔑 Credenciales Odoo</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="flex flex-wrap items-end gap-3">
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted-foreground">Usuario (email)</label>
            <Input
              type="email"
              placeholder="usuario@riofuturo.cl"
              value={odooUser}
              onChange={e => onUser(e.target.value)}
              className="w-56"
            />
          </div>
          <div className="flex items-center gap-2">
            <label className="text-sm text-muted-foreground">API Key</label>
            <Input
              type="password"
              placeholder="Odoo API key"
              value={odooKey}
              onChange={e => onKey(e.target.value)}
              className="w-56"
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Etiquetas Tab ─────────────────────────────────────────────────────────────

function EtiquetasTab() {
  const [odooUser, setOdooUser] = useState('')
  const [odooKey, setOdooKey] = useState('')
  const [termino, setTermino] = useState('')
  const [buscarEnabled, setBuscarEnabled] = useState(false)
  const [selectedOrden, setSelectedOrden] = useState<string | null>(null)
  const [selectedPallets, setSelectedPallets] = useState<Set<number>>(new Set())
  const [fechaElab, setFechaElab] = useState(() => new Date().toISOString().slice(0, 10))
  const [cliente, setCliente] = useState('')

  const { data: ordenes = [], isLoading: loadingOrdenes } = useBuscarOrdenesEtiquetas(
    termino, odooUser, odooKey, buscarEnabled,
  )
  const { data: pallets = [], isLoading: loadingPallets } = usePalletsOrden(
    selectedOrden ?? '', odooUser, odooKey, !!selectedOrden,
  )
  const genPDF = useGenerarEtiquetasPDF()

  const hasCredentials = !!odooUser && !!odooKey

  const togglePallet = (id: number) => {
    setSelectedPallets(prev => {
      const next = new Set(prev)
      next.has(id) ? next.delete(id) : next.add(id)
      return next
    })
  }

  const selAll = () => setSelectedPallets(new Set(pallets.map(p => p.package_id)))
  const selNone = () => setSelectedPallets(new Set())

  const handleDescargar = () => {
    genPDF.mutate({
      packageIds: [...selectedPallets],
      fechaElaboracion: fechaElab,
      cliente,
      odooUser,
      odooKey,
    })
  }

  return (
    <div className="space-y-4">
      <CredentialsForm odooUser={odooUser} odooKey={odooKey} onUser={setOdooUser} onKey={setOdooKey} />

      {hasCredentials && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">🔍 Buscar Orden de Producción</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-end gap-3">
              <Input
                placeholder="MO/RF/00123 o término de búsqueda"
                value={termino}
                onChange={e => { setTermino(e.target.value); setBuscarEnabled(false) }}
                className="w-64"
              />
              <Button
                onClick={() => setBuscarEnabled(true)}
                disabled={!termino || loadingOrdenes}
              >
                {loadingOrdenes ? 'Buscando...' : 'Buscar'}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {ordenes.length > 0 && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">Órdenes encontradas</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {ordenes.map(o => (
                <div
                  key={o.id}
                  className={`flex items-center justify-between rounded-lg border p-3 cursor-pointer transition-colors ${
                    selectedOrden === o.name ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                  }`}
                  onClick={() => { setSelectedOrden(o.name); setSelectedPallets(new Set()) }}
                >
                  <div>
                    <p className="font-medium text-sm">{o.name}</p>
                    <p className="text-xs text-muted-foreground">{o.producto}</p>
                  </div>
                  <Badge variant={o.estado === 'confirmed' ? 'warning' : o.estado === 'done' ? 'success' : 'default'}>
                    {o.estado}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {selectedOrden && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">Pallets — {selectedOrden}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {loadingPallets ? <LoadingSpinner /> : (
              <>
                <div className="flex flex-wrap items-end gap-3">
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Fecha Elaboración</label>
                    <Input
                      type="date"
                      value={fechaElab}
                      onChange={e => setFechaElab(e.target.value)}
                      className="w-36"
                    />
                  </div>
                  <div className="flex items-center gap-2">
                    <label className="text-sm text-muted-foreground">Cliente</label>
                    <Input
                      placeholder="Nombre del cliente"
                      value={cliente}
                      onChange={e => setCliente(e.target.value)}
                      className="w-48"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <Button variant="outline" size="sm" onClick={selAll}>Sel. todos</Button>
                  <Button variant="outline" size="sm" onClick={selNone}>Desel. todos</Button>
                  <span className="text-xs text-muted-foreground">{selectedPallets.size} de {pallets.length} seleccionados</span>
                </div>

                <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                  {pallets.map(p => (
                    <div
                      key={p.package_id}
                      className={`rounded-lg border p-3 cursor-pointer transition-colors ${
                        selectedPallets.has(p.package_id) ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
                      }`}
                      onClick={() => togglePallet(p.package_id)}
                    >
                      <p className="font-medium text-sm">Pallet #{p.numero_pallet}</p>
                      <p className="text-xs text-muted-foreground">{p.producto}</p>
                      <p className="text-xs text-muted-foreground">Lote: {p.lote} · {formatNumber(p.kg, 1)} kg</p>
                    </div>
                  ))}
                </div>

                <div className="flex justify-end pt-2">
                  <Button
                    onClick={handleDescargar}
                    disabled={selectedPallets.size === 0 || genPDF.isPending}
                  >
                    {genPDF.isPending ? 'Generando PDF...' : `🖨️ Descargar PDF (${selectedPallets.size})`}
                  </Button>
                </div>

                {genPDF.isError && (
                  <p className="text-sm text-destructive">Error al generar PDF. Verifica credenciales.</p>
                )}
              </>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

// ─── Automatización OF Tab ─────────────────────────────────────────────────────

function AutomatizacionOfTab() {
  const [odooUser, setOdooUser] = useState('')
  const [odooKey, setOdooKey] = useState('')
  const [ordenInput, setOrdenInput] = useState('')
  const [ordenBuscar, setOrdenBuscar] = useState('')
  const [tipo, setTipo] = useState<'componentes' | 'subproductos'>('componentes')
  const [palletsTexto, setPalletsTexto] = useState('')
  const [palletsValidados, setPalletsValidados] = useState<PalletValidadoProceso[] | undefined>(undefined)
  const [resultado, setResultado] = useState<{ success: boolean; pallets_agregados: number; kg_total: number; errores: string[]; mensaje?: string } | null>(null)

  const hasCredentials = !!odooUser && !!odooKey

  const { data: orden, isLoading: loadingOrden, error: errorOrden } = useBuscarOrdenProcesos(
    ordenBuscar, odooUser, odooKey, !!ordenBuscar && hasCredentials,
  )
  const validarMut = useValidarPalletsProcesos()
  const agregarMut = useAgregarPalletsProcesos()

  const handleBuscarOrden = () => {
    setOrdenBuscar(ordenInput.trim().toUpperCase())
    setPalletsValidados(undefined)
    setResultado(null)
  }

  const handleValidar = async () => {
    if (!orden) return
    const codigos = palletsTexto.split('\n').map(s => s.trim()).filter(Boolean)
    const result = await validarMut.mutateAsync({
      pallets: codigos, tipo, ordenId: orden.id, odooUser, odooKey,
    })
    setPalletsValidados(result)
    setResultado(null)
  }

  const handleAgregar = async () => {
    if (!orden || !palletsValidados) return
    const validos = palletsValidados.filter(p => p.ok && !p.ya_en_orden)
    const result = await agregarMut.mutateAsync({
      ordenId: orden.id,
      tipo,
      pallets: validos,
      modelo: orden.es_picking ? 'stock.picking' : 'mrp.production',
      odooUser,
      odooKey,
    })
    setResultado(result)
  }

  return (
    <div className="space-y-4">
      <CredentialsForm odooUser={odooUser} odooKey={odooKey} onUser={setOdooUser} onKey={setOdooKey} />

      {hasCredentials && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">1️⃣ Orden de Fabricación</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap items-end gap-3">
              <Input
                placeholder="MO/RF/00123 o solo el número"
                value={ordenInput}
                onChange={e => setOrdenInput(e.target.value)}
                className="w-56"
                onKeyDown={e => e.key === 'Enter' && handleBuscarOrden()}
              />
              <Button onClick={handleBuscarOrden} disabled={!ordenInput || loadingOrden}>
                {loadingOrden ? 'Buscando...' : '🔍 Buscar'}
              </Button>
            </div>

            {errorOrden && (
              <p className="mt-2 text-sm text-destructive">Orden no encontrada. Verifica el nombre y las credenciales.</p>
            )}

            {orden && (
              <div className="mt-3 rounded-lg border bg-muted/30 p-3">
                <p className="font-medium">{orden.nombre}</p>
                <p className="text-sm text-muted-foreground">{orden.producto} · Qty: {formatNumber(orden.cantidad, 0)}</p>
                <Badge variant={orden.estado === 'confirmed' ? 'warning' : orden.estado === 'done' ? 'success' : 'default'} className="mt-1">
                  {orden.estado}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {orden && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">2️⃣ Pallets + Tipo</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-3">
              <label className="text-sm text-muted-foreground">Tipo</label>
              <Select value={tipo} onValueChange={v => setTipo(v as 'componentes' | 'subproductos')}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="componentes">Componentes</SelectItem>
                  <SelectItem value="subproductos">Subproductos</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground block mb-1">Códigos de pallets (uno por línea)</label>
              <textarea
                className="w-full min-h-[120px] rounded-md border border-input bg-background px-3 py-2 text-sm font-mono focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                placeholder="PAL00123\nPAL00124\nPAL00125"
                value={palletsTexto}
                onChange={e => setPalletsTexto(e.target.value)}
              />
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={handleValidar}
                disabled={!palletsTexto.trim() || validarMut.isPending}
              >
                {validarMut.isPending ? 'Validando...' : '✔ Validar Pallets'}
              </Button>
              {palletsValidados && palletsValidados.some(p => p.ok && !p.ya_en_orden) && (
                <Button
                  onClick={handleAgregar}
                  disabled={agregarMut.isPending}
                >
                  {agregarMut.isPending ? 'Agregando...' : '➕ Agregar a Orden'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {palletsValidados && (
        <Card>
          <CardHeader className="py-3">
            <CardTitle className="text-base">3️⃣ Resultado Validación</CardTitle>
          </CardHeader>
          <CardContent>
            <DataTable
              columns={[
                { accessorKey: 'pallet', header: 'Pallet', enableSorting: true },
                { accessorKey: 'producto', header: 'Producto' },
                { accessorKey: 'lote', header: 'Lote' },
                { accessorKey: 'kg', header: 'KG', cell: ({ getValue }) => formatNumber(Number(getValue()), 1), enableSorting: true },
                {
                  accessorKey: 'ok',
                  header: 'Estado',
                  cell: ({ row }) => {
                    if (row.original.ya_en_orden) return <Badge variant="secondary">Ya en orden</Badge>
                    if (row.original.ok) return <Badge variant="success">✓ OK</Badge>
                    return <Badge variant="destructive">{row.original.error ?? 'Error'}</Badge>
                  },
                },
              ]}
              data={palletsValidados}
              loading={false}
              searchPlaceholder="Buscar pallet..."
            />
          </CardContent>
        </Card>
      )}

      {resultado && (
        <Card className={resultado.success ? 'border-green-500/50' : 'border-destructive'}>
          <CardHeader className="py-3">
            <CardTitle className="text-base">
              {resultado.success ? '✅ Operación completada' : '❌ Error'}
            </CardTitle>
          </CardHeader>
          <CardContent>
            {resultado.success ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <KPICard label="Pallets agregados" value={resultado.pallets_agregados} loading={false} />
                <KPICard label="KG totales" value={resultado.kg_total} format="number" loading={false} />
              </div>
            ) : (
              <div className="space-y-1">
                {resultado.errores.map((e, i) => (
                  <p key={i} className="text-sm text-destructive">{e}</p>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  )
}

const fabricacionCols: ColumnDef<FabricacionDetalle>[] = [

  { accessorKey: 'mo_name', header: 'OT', enableSorting: true },

  { accessorKey: 'producto', header: 'Producto' },

  { accessorKey: 'linea', header: 'Línea' },

  {

    accessorKey: 'cantidad',

    header: 'Cantidad (kg)',

    cell: ({ getValue }) => formatNumber(Number(getValue()), 0),

    enableSorting: true,

  },

  {

    accessorKey: 'rendimiento_real',

    header: 'Rend. Real %',

    cell: ({ getValue }) => `${formatNumber(Number(getValue()))}%`,

    enableSorting: true,

  },

  {

    accessorKey: 'rendimiento_teorico',

    header: 'Rend. Teórico %',

    cell: ({ getValue }) => `${formatNumber(Number(getValue()))}%`,

  },

  {

    accessorKey: 'merma',

    header: 'Merma (kg)',

    cell: ({ getValue }) => formatNumber(Number(getValue()), 0),

  },

  { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },

]

type MonitorRow = {

  mo_name: string; producto: string; linea: string; estado: string

  cantidad_planificada: number; cantidad_real: number; avance_pct: number; operario: string

}

const monitorCols: ColumnDef<MonitorRow>[] = [

  { accessorKey: 'mo_name', header: 'OT', enableSorting: true },

  { accessorKey: 'producto', header: 'Producto', enableSorting: true },

  { accessorKey: 'linea', header: 'Línea' },

  { accessorKey: 'operario', header: 'Operario' },

  { accessorKey: 'cantidad_planificada', header: 'Plan (kg)', cell: ({ getValue }) => formatNumber(Number(getValue()), 0) },

  { accessorKey: 'cantidad_real', header: 'Real (kg)', cell: ({ getValue }) => formatNumber(Number(getValue()), 0) },

  {

    accessorKey: 'avance_pct',

    header: 'Avance',

    cell: ({ getValue }) => {

      const v = Number(getValue())

      const variant = v >= 90 ? 'success' : v >= 60 ? 'warning' : 'destructive'

      return <Badge variant={variant}>{v.toFixed(1)}%</Badge>

    },

    enableSorting: true,

  },

  {

    accessorKey: 'estado',

    header: 'Estado',

    cell: ({ getValue }) => {

      const v = String(getValue())

      const variant = v === 'done' ? 'success' : v === 'progress' ? 'warning' : 'default'

      const labels: Record<string, string> = { done: 'Terminada', progress: 'En proceso', pending: 'Pendiente' }

      return <Badge variant={variant}>{labels[v] ?? v}</Badge>

    },

  },

]

type PalletRow = { sala: string; producto: string; cantidad_pallets: number; kg_total: number; temperatura: number; fecha: string }

const palletCols: ColumnDef<PalletRow>[] = [

  { accessorKey: 'sala', header: 'Sala', enableSorting: true },

  { accessorKey: 'producto', header: 'Producto', enableSorting: true },

  { accessorKey: 'cantidad_pallets', header: 'Pallets', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

  { accessorKey: 'kg_total', header: 'Kg Total', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

  { accessorKey: 'temperatura', header: 'Temp (Â°C)', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}Â°` },

  { accessorKey: 'fecha', header: 'Fecha', enableSorting: true },

]

export function ProduccionPage() {

  const [year, setYear] = useState(CURRENT_YEAR)

  const [months, setMonths] = useState<number[]>([])

  const today = new Date().toISOString().slice(0, 10)

  const filters = { year, months: months.length ? months : undefined }

  const { data: kpis, isLoading: loadingKPIs } = useProduccionKPIs(filters)

  const { data: lineas = [], isLoading: loadingLineas } = useProduccionLineas(filters)

  const { data: tuneles = [], isLoading: loadingTuneles } = useProduccionTuneles(filters)

  const { data: fabricaciones = [], isLoading: loadingFab } = useFabricaciones(filters)

  const { data: clasificacion = [], isLoading: loadingClasif } = useClasificacion(filters)

  const { data: monitor = [], isLoading: loadingMonitor } = useMonitorDiario(today)

  const { data: kgLinea = [], isLoading: loadingKgLinea } = useKgPorLinea(filters)

  const { data: pallets = [], isLoading: loadingPallets } = usePalletsProduccion(filters)

  // Aggregate lineas for chart

  const lineasChart = lineas.reduce(

    (acc, row) => {

      const idx = acc.findIndex((x) => x.linea === row.linea)

      if (idx >= 0) acc[idx].cantidad += row.cantidad

      else acc.push({ linea: row.linea, cantidad: row.cantidad })

      return acc

    },

    [] as { linea: string; cantidad: number }[],

  )

  const palletsPorSala = Object.entries(

    pallets.reduce((acc, r) => {

      acc[r.sala] = (acc[r.sala] ?? 0) + r.cantidad_pallets

      return acc

    }, {} as Record<string, number>)

  ).map(([sala, cantidad_pallets]) => ({ sala, cantidad_pallets }))

  return (

    <div className="space-y-4">

      <PageHeader title="Producción" description="Indicadores y detalle de producción por línea, túnel y fabricación">

        <ExportButton data={fabricaciones as unknown as Record<string, unknown>[]} filename="produccion" />

      </PageHeader>

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      {/* KPIs */}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

        <KPICard label="Total Producción (kg)" value={kpis?.total_produccion} loading={loadingKPIs} />

        <KPICard label="Rendimiento Prom." value={kpis?.rendimiento_promedio} unit="%" format="number" loading={loadingKPIs} />

        <KPICard label="Merma Total (kg)" value={kpis?.merma_total} loading={loadingKPIs} />

        <KPICard label="Eficiencia" value={kpis?.eficiencia} unit="%" format="number" loading={loadingKPIs} />

      </div>

      <Tabs defaultValue="monitor">

        <TabsList className="flex-wrap h-auto gap-1">

          <TabsTrigger value="monitor">📏 Monitor Diario</TabsTrigger>

          <TabsTrigger value="lineas">📊 Por Línea</TabsTrigger>

          <TabsTrigger value="kg-linea">⚖️ Kg por Línea</TabsTrigger>

          <TabsTrigger value="tuneles">🏭 Por Túnel</TabsTrigger>

          <TabsTrigger value="pallets">🏠 Pallets por Sala</TabsTrigger>

          <TabsTrigger value="clasificacion">🔄 Clasificación</TabsTrigger>

          <TabsTrigger value="detalle">📋 Detalle OTs</TabsTrigger>

          <TabsTrigger value="etiquetas">🏷️ Etiquetas</TabsTrigger>

          <TabsTrigger value="automatizacion-of">⚙️ Automatización OF</TabsTrigger>

        </TabsList>

        {/* Monitor Diario */}

        <TabsContent value="monitor" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">📏 Monitor de Producción — {today}</CardTitle>

            </CardHeader>

            <CardContent>

              <div className="grid gap-3 sm:grid-cols-3 mb-4">

                <KPICard label="OTs en proceso" value={monitor.filter(r => r.estado === 'progress').length} loading={loadingMonitor} />

                <KPICard label="OTs terminadas" value={monitor.filter(r => r.estado === 'done').length} loading={loadingMonitor} />

                <KPICard label="OTs pendientes" value={monitor.filter(r => r.estado === 'pending').length} loading={loadingMonitor} />

              </div>

            </CardContent>

          </Card>

          <DataTable

            columns={monitorCols}

            data={monitor}

            loading={loadingMonitor}

            searchPlaceholder="Buscar OT, producto o línea..."

          />

        </TabsContent>

        {/* Por Línea */}

        <TabsContent value="lineas" className="mt-4">

          <Card>

            <CardHeader>

              <CardTitle className="text-base">Producción por Línea (kg)</CardTitle>

            </CardHeader>

            <CardContent>

              {loadingLineas ? (

                <LoadingSpinner />

              ) : (

                <BarChart

                  data={lineasChart}

                  xKey="linea"

                  bars={[{ key: 'cantidad', name: 'Kg producidos' }]}

                  yFormatter={(v) => formatNumber(v, 0)}

                  height={350}

                />

              )}

            </CardContent>

          </Card>

        </TabsContent>

        {/* KG por Línea histórico */}

        <TabsContent value="kg-linea" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">Kg Entrada vs Salida por Línea â€” Rendimiento Histórico</CardTitle>

            </CardHeader>

            <CardContent>

              {loadingKgLinea ? <LoadingSpinner /> : (

                <LineChart

                  data={kgLinea}

                  xKey="periodo"

                  lines={[

                    { key: 'kg_entrada', name: 'Kg Entrada' },

                    { key: 'kg_salida', name: 'Kg Salida' },

                    { key: 'rendimiento', name: 'Rendimiento %' },

                  ]}

                  yFormatter={(v) => formatNumber(v, 0)}

                  height={360}

                />

              )}

            </CardContent>

          </Card>

          <div className="mt-4">

            <DataTable

              columns={[

                { accessorKey: 'linea', header: 'Línea', enableSorting: true },

                { accessorKey: 'periodo', header: 'Período', enableSorting: true },

                { accessorKey: 'kg_entrada', header: 'Kg Entrada', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                { accessorKey: 'kg_salida', header: 'Kg Salida', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                { accessorKey: 'rendimiento', header: 'Rendimiento %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },

              ]}

              data={kgLinea}

              loading={loadingKgLinea}

              searchPlaceholder="Buscar línea..."

            />

          </div>

        </TabsContent>

        {/* Túneles */}

        <TabsContent value="tuneles" className="mt-4">

          <Card>

            <CardHeader><CardTitle className="text-base">Producción por Túinel</CardTitle></CardHeader>

            <CardContent>

              {loadingTuneles ? <LoadingSpinner /> : (

                <BarChart

                  data={tuneles}

                  xKey="tunel"

                  bars={[

                    { key: 'cantidad_entrada', name: 'Entrada' },

                    { key: 'cantidad_salida', name: 'Salida' },

                  ]}

                  yFormatter={(v) => formatNumber(v, 0)}

                  height={350}

                />

              )}

            </CardContent>

          </Card>

        </TabsContent>

        {/* Pallets por Sala */}

        <TabsContent value="pallets" className="mt-4">

          <div className="grid gap-4">

            <Card>

              <CardHeader className="py-3">

                <CardTitle className="text-base">Pallets por Sala de Frío</CardTitle>

              </CardHeader>

              <CardContent>

                {loadingPallets ? <LoadingSpinner /> : (

                  <BarChart

                    data={palletsPorSala}

                    xKey="sala"

                    bars={[{ key: 'cantidad_pallets', name: 'Pallets' }]}

                    yFormatter={(v) => formatNumber(v, 0)}

                    height={300}

                  />

                )}

              </CardContent>

            </Card>

            <DataTable

              columns={palletCols}

              data={pallets}

              loading={loadingPallets}

              searchPlaceholder="Buscar sala o producto..."

            />

          </div>

        </TabsContent>

        {/* Clasificación */}

        <TabsContent value="clasificacion" className="mt-4">

          <div className="grid gap-4 lg:grid-cols-2">

            <Card>

              <CardHeader><CardTitle className="text-base">Distribución por Categoría</CardTitle></CardHeader>

              <CardContent>

                {loadingClasif ? <LoadingSpinner /> : (

                  <PieChart

                    data={clasificacion.map((c) => ({ name: c.categoria, value: c.cantidad }))}

                    donut

                    formatter={(v) => formatNumber(v, 0)}

                    height={300}

                  />

                )}

              </CardContent>

            </Card>

            <DataTable

              columns={[

                { accessorKey: 'categoria', header: 'Categoría', enableSorting: true },

                { accessorKey: 'cantidad', header: 'Kg', cell: ({ getValue }) => formatNumber(Number(getValue()), 0), enableSorting: true },

                { accessorKey: 'porcentaje', header: '%', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },

              ]}

              data={clasificacion}

              loading={loadingClasif}

              searchPlaceholder=""

            />

          </div>

        </TabsContent>

        {/* Detalle OTs */}

        <TabsContent value="detalle" className="mt-4">

          <DataTable

            columns={fabricacionCols}

            data={fabricaciones}

            loading={loadingFab}

            searchPlaceholder="Buscar OT o producto..."

          />

        </TabsContent>

        <TabsContent value="etiquetas" className="mt-4">

          <EtiquetasTab />

        </TabsContent>

        <TabsContent value="automatizacion-of" className="mt-4">

          <AutomatizacionOfTab />

        </TabsContent>

      </Tabs>

    </div>

  )

}

export default ProduccionPage
