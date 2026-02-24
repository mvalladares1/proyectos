import { useState } from 'react'
import { type ColumnDef } from '@tanstack/react-table'
import { Sankey, Tooltip as RcTooltip, Rectangle } from 'recharts'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { PageHeader } from '@/components/layout/PageHeader'
import { DataTable } from '@/components/tables/DataTable'
import { ExportButton } from '@/components/tables/ExportButton'
import { KPICard } from '@/components/shared/KPICard'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { formatNumber } from '@/lib/utils'

import {
  useTrazabilidadInversa,
  useSankeyTrazabilidad,
  type TrazabilidadLoteMP,
} from '@/api/trazabilidad'

// ─── Credentials form ─────────────────────────────────────────────────────────

function CredentialsForm({
  odooUser, odooKey, onUser, onKey,
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

// ─── Trazabilidad Inversa Tab ──────────────────────────────────────────────────

function LotePTTab({ odooUser, odooKey }: { odooUser: string; odooKey: string }) {
  const [loteInput, setLoteInput] = useState('')
  const [lotePT, setLotePT] = useState('')
  const [enabled, setEnabled] = useState(false)

  const { data, isLoading, isError, error } = useTrazabilidadInversa(
    lotePT, odooUser, odooKey, enabled,
  )

  const handleSearch = () => {
    const trimmed = loteInput.trim()
    if (!trimmed) return
    setLotePT(trimmed)
    setEnabled(true)
  }

  const columns: ColumnDef<TrazabilidadLoteMP>[] = [
    { accessorKey: 'lot_name', header: 'Lote MP', cell: ({ row }) => <span className="font-mono text-xs">{row.original.lot_name}</span> },
    { accessorKey: 'product_name', header: 'Producto' },
    { accessorKey: 'proveedor', header: 'Proveedor' },
    { accessorKey: 'kg', header: 'Kg', cell: ({ row }) => formatNumber(row.original.kg, 2) },
    { accessorKey: 'fecha_recepcion', header: 'Fecha Recepción' },
  ]

  const lotes = data?.lotes_mp ?? []

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">🔍 Búsqueda por Lote PT</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-end gap-3">
            <div>
              <label className="text-xs text-muted-foreground">Nombre del Lote PT</label>
              <Input
                placeholder="Ej: LOT-0001, WH/FIN/2024..."
                value={loteInput}
                onChange={e => setLoteInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleSearch()}
                className="w-80"
              />
            </div>
            <Button onClick={handleSearch} disabled={!odooUser || !odooKey || !loteInput.trim()}>
              Buscar Trazabilidad
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading && <LoadingSpinner />}
      {isError && <p className="text-destructive text-sm">Error: {String((error as Error)?.message ?? error)}</p>}

      {data && !isLoading && (
        <>
          {data.error && (
            <Card>
              <CardContent className="pt-4">
                <p className="text-muted-foreground text-sm">⚠️ {data.error}</p>
              </CardContent>
            </Card>
          )}

          {!data.error && (
            <>
              {/* Info del lote PT */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardContent className="pt-4 space-y-1">
                    <p className="text-xs text-muted-foreground">Lote PT</p>
                    <p className="font-mono font-medium">{data.lote_pt}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 space-y-1">
                    <p className="text-xs text-muted-foreground">Producto</p>
                    <p className="text-sm">{data.producto_pt}</p>
                  </CardContent>
                </Card>
                <Card>
                  <CardContent className="pt-4 space-y-1">
                    <p className="text-xs text-muted-foreground">Orden de Producción</p>
                    <p className="font-mono text-sm">{data.mo?.name ?? '—'}</p>
                  </CardContent>
                </Card>
              </div>

              {/* KPIs */}
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <KPICard label="Lotes MP encontrados" value={lotes.length} loading={false} />
                <KPICard label="Kg totales" value={lotes.reduce((s, l) => s + (l.kg ?? 0), 0)} format="number" loading={false} />
                <KPICard label="Proveedores únicos" value={new Set(lotes.map(l => l.proveedor)).size} loading={false} />
              </div>

              {/* Lotes MP table */}
              <Card>
                <CardHeader className="py-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-sm">📦 Lotes MP Utilizados ({lotes.length})</CardTitle>
                  <ExportButton data={lotes} filename={`trazabilidad_${lotePT}`} />
                </CardHeader>
                <CardContent>
                  <DataTable columns={columns} data={lotes} />
                </CardContent>
              </Card>
            </>
          )}
        </>
      )}
    </div>
  )
}

// ─── Sankey Tab ────────────────────────────────────────────────────────────────

function SankeyTab({ odooUser, odooKey }: { odooUser: string; odooKey: string }) {
  const today = new Date().toISOString().slice(0, 10)
  const weekAgo = new Date(Date.now() - 7 * 86400_000).toISOString().slice(0, 10)

  const [startDate, setStartDate] = useState(weekAgo)
  const [endDate, setEndDate] = useState(today)
  const [enabled, setEnabled] = useState(false)

  const { data, isLoading, isError, error } = useSankeyTrazabilidad(
    odooUser, odooKey, { startDate, endDate }, enabled,
  )

  const nodes = data?.nodes ?? []
  const links = data?.links ?? []

  // Recharts Sankey needs numeric source/target
  const safeSankeyData = {
    nodes: nodes.map(n => ({ name: n.name })),
    links: links.map(l => ({
      source: typeof l.source === 'number' ? l.source : nodes.findIndex(n => n.name === l.source),
      target: typeof l.target === 'number' ? l.target : nodes.findIndex(n => n.name === l.target),
      value: l.value > 0 ? l.value : 0.001,
    })).filter(l => l.source >= 0 && l.target >= 0),
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">📊 Diagrama Sankey de Trazabilidad</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label className="text-xs text-muted-foreground">Desde</label>
              <Input type="date" value={startDate} onChange={e => setStartDate(e.target.value)} className="w-36" />
            </div>
            <div>
              <label className="text-xs text-muted-foreground">Hasta</label>
              <Input type="date" value={endDate} onChange={e => setEndDate(e.target.value)} className="w-36" />
            </div>
            <Button onClick={() => setEnabled(true)} disabled={!odooUser || !odooKey}>
              Cargar Diagrama
            </Button>
          </div>
        </CardContent>
      </Card>

      {isLoading && <LoadingSpinner />}
      {isError && <p className="text-destructive text-sm">Error: {String((error as Error)?.message ?? error)}</p>}

      {data && !isLoading && (
        <>
          {nodes.length === 0 ? (
            <Card>
              <CardContent className="pt-4">
                <p className="text-muted-foreground text-sm">Sin datos para el período seleccionado.</p>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">Flujo Pallet → Proceso → Cliente ({nodes.length} nodos, {links.length} conexiones)</CardTitle>
              </CardHeader>
              <CardContent className="overflow-x-auto">
                <Sankey
                  width={900}
                  height={500}
                  data={safeSankeyData}
                  nodePadding={16}
                  margin={{ left: 10, right: 10, top: 10, bottom: 10 }}
                  link={{ stroke: '#d1d5db', strokeOpacity: 0.5 }}
                  node={<SankeyNodeCustom />}
                >
                  <RcTooltip formatter={(v: number) => [`${formatNumber(v, 1)} kg`]} />
                </Sankey>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}

// Custom node renderer for Sankey
function SankeyNodeCustom(props: {
  x?: number; y?: number; width?: number; height?: number; index?: number; payload?: { name: string }
}) {
  const { x = 0, y = 0, width = 10, height = 0, payload } = props
  return (
    <g>
      <Rectangle x={x} y={y} width={width} height={height} fill="#3b82f6" fillOpacity={0.9} radius={2} />
      {height > 12 && (
        <text
          x={x + width + 6}
          y={y + height / 2 + 4}
          fontSize={11}
          fill="currentColor"
          className="fill-foreground"
        >
          {(payload?.name ?? '').slice(0, 22)}
        </text>
      )}
    </g>
  )
}

// ─── Main Page ─────────────────────────────────────────────────────────────────

export default function TrazabilidadPage() {
  const [odooUser, setOdooUser] = useState('')
  const [odooKey, setOdooKey] = useState('')
  const hasCredentials = !!odooUser && !!odooKey

  return (
    <div className="space-y-4 p-4 md:p-6">
      <PageHeader
        title="🔍 Trazabilidad"
        description="Trazabilidad inversa de lotes PT y diagramas de flujo Sankey"
      />

      <CredentialsForm odooUser={odooUser} odooKey={odooKey} onUser={setOdooUser} onKey={setOdooKey} />

      {!hasCredentials && (
        <Card>
          <CardContent className="pt-4">
            <p className="text-muted-foreground text-sm">Ingresa las credenciales Odoo para acceder a los diagramas de trazabilidad.</p>
          </CardContent>
        </Card>
      )}

      {hasCredentials && (
        <Tabs defaultValue="lote-pt">
          <TabsList>
            <TabsTrigger value="lote-pt">📦 Lote PT → Trazabilidad inversa</TabsTrigger>
            <TabsTrigger value="sankey">📊 Diagrama Sankey</TabsTrigger>
          </TabsList>

          <TabsContent value="lote-pt" className="mt-4">
            <LotePTTab odooUser={odooUser} odooKey={odooKey} />
          </TabsContent>

          <TabsContent value="sankey" className="mt-4">
            <SankeyTab odooUser={odooUser} odooKey={odooKey} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}
