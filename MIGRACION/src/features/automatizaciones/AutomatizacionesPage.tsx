import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Play, RefreshCw, CheckCircle, XCircle, Clock, ToggleLeft, ToggleRight } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { KPICard } from '@/components/shared/KPICard'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { cn, formatDateTime, formatNumber } from '@/lib/utils'
import {
  useAutomatizaciones, useEjecutarAutomatizacion,
  useTuneles, useCrearOrdenFabricacion,
  useMovimientosStock, useProcesosAutomatizacion, useToggleProcesoActivo,
  usePreviewRevertirConsumo, useRevertirConsumo,
  type ComponentePreview, type SubproductoPreview, type RevertirPreviewResult, type RevertirConsumoResult,
} from '@/api/automatizaciones'
import toast from 'react-hot-toast'

// ─── Revertir Consumo Tab ────────────────────────────────────────────────────

function RevertirConsumoTab() {
  const [odooUser, setOdooUser] = useState('')
  const [odooKey, setOdooKey] = useState('')
  const [odfName, setOdfName] = useState('')
  const [preview, setPreview] = useState<RevertirPreviewResult | null>(null)
  const [result, setResult] = useState<RevertirConsumoResult | null>(null)
  const [confirmado, setConfirmado] = useState(false)

  const previewMut = usePreviewRevertirConsumo()
  const revertirMut = useRevertirConsumo()

  const hasCredentials = !!odooUser && !!odooKey
  const odfTrimmed = odfName.trim()

  const handlePreview = () => {
    setPreview(null)
    setResult(null)
    setConfirmado(false)
    previewMut.mutate(
      { odfName: odfTrimmed, odooUser, odooKey },
      {
        onSuccess: (data) => {
          setPreview(data)
          if (!data.success) toast.error(data.message)
        },
        onError: () => toast.error('Error al obtener preview'),
      },
    )
  }

  const handleRevertir = () => {
    revertirMut.mutate(
      { odfName: odfTrimmed, odooUser, odooKey },
      {
        onSuccess: (data) => {
          setResult(data)
          setConfirmado(false)
          if (data.success) toast.success(data.message)
          else toast.error(data.message)
        },
        onError: () => toast.error('Error al revertir consumo'),
      },
    )
  }

  return (
    <div className="space-y-4">
      {/* Credentials */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">🔑 Credenciales Odoo</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">Usuario (email)</label>
              <Input type="email" placeholder="usuario@riofuturo.cl" value={odooUser} onChange={e => setOdooUser(e.target.value)} className="w-56" />
            </div>
            <div className="flex items-center gap-2">
              <label className="text-sm text-muted-foreground">API Key</label>
              <Input type="password" placeholder="Odoo API key" value={odooKey} onChange={e => setOdooKey(e.target.value)} className="w-56" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Paso 1: ODF input */}
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-base">🔄 Revertir Consumo de ODF</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            Recupera componentes (MP) a sus paquetes originales y elimina subproductos de una orden de desmontaje.
          </p>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <label className="text-xs text-muted-foreground block mb-1">Código de la ODF</label>
              <Input
                placeholder="VLK/CongTE109"
                value={odfName}
                onChange={e => setOdfName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && odfTrimmed && hasCredentials && handlePreview()}
              />
            </div>
            <Button
              variant="secondary"
              onClick={handlePreview}
              disabled={!odfTrimmed || !hasCredentials || previewMut.isPending}
            >
              {previewMut.isPending ? <><RefreshCw className="mr-2 h-3 w-3 animate-spin" />Analizando…</> : '🔍 Ver Detalle'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Paso 2: Preview */}
      {previewMut.isPending && <LoadingSpinner />}

      {preview && preview.success && (
        <div className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Componentes a recuperar */}
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">📦 Componentes a Recuperar ({preview.componentes_preview.length})</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {preview.componentes_preview.length === 0 ? (
                  <p className="text-xs text-muted-foreground">Sin componentes</p>
                ) : preview.componentes_preview.map((c, i) => (
                  <div key={i} className="rounded border p-2 text-xs space-y-0.5">
                    <p className="font-medium">{c.paquete}</p>
                    <p className="text-muted-foreground">{c.producto} · Lote: {c.lote}</p>
                    <p className="text-blue-400">{formatNumber(c.cantidad, 2)} kg · {c.ubicacion}</p>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Subproductos a eliminar */}
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-sm">🧊 Subproductos a Eliminar ({preview.subproductos_preview.length})</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {preview.subproductos_preview.length === 0 ? (
                  <p className="text-xs text-muted-foreground">Sin subproductos</p>
                ) : preview.subproductos_preview.map((s, i) => (
                  <div key={i} className="rounded border border-red-500/20 bg-red-500/5 p-2 text-xs space-y-0.5">
                    <p className="font-medium">{s.producto}</p>
                    <p className="text-muted-foreground">{formatNumber(s.cantidad_actual, 2)} kg → 0 · {s.ubicacion}</p>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Paso 3: Confirmar */}
          {!result && (
            <Card className="border-orange-500/30">
              <CardContent className="pt-4 space-y-3">
                <div className="rounded bg-orange-500/10 border border-orange-500/30 p-3 text-sm">
                  <p className="font-medium text-orange-400">⚠️ Confirmación requerida</p>
                  <ul className="mt-1 text-xs text-muted-foreground list-disc list-inside space-y-0.5">
                    <li>Esta acción NO se puede deshacer automáticamente</li>
                    <li>Se crearán transferencias reales en Odoo</li>
                    <li>Revisa el detalle antes de continuar</li>
                  </ul>
                </div>
                {!confirmado ? (
                  <Button variant="destructive" className="w-full" onClick={() => setConfirmado(true)}>
                    Entiendo — Mostrar botón de Reversión
                  </Button>
                ) : (
                  <Button
                    variant="destructive"
                    className="w-full"
                    disabled={revertirMut.isPending}
                    onClick={handleRevertir}
                  >
                    {revertirMut.isPending
                      ? <><RefreshCw className="mr-2 h-4 w-4 animate-spin" />Revirtiendo…</>
                      : '🔄 CONFIRMAR Y REVERTIR'}
                  </Button>
                )}
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {preview && !preview.success && (
        <Card className="border-red-500/30">
          <CardContent className="pt-4">
            <p className="text-destructive text-sm">❌ {preview.message}</p>
          </CardContent>
        </Card>
      )}

      {/* Resultado */}
      {result && (
        <Card className={result.success ? 'border-green-500/30 bg-green-500/5' : 'border-red-500/30'}>
          <CardHeader className="py-3">
            <CardTitle className={`text-base ${result.success ? 'text-green-400' : 'text-destructive'}`}>
              {result.success ? '✅' : '❌'} {result.message}
            </CardTitle>
          </CardHeader>
          {result.success && (
            <CardContent className="space-y-3">
              <div className="grid grid-cols-3 gap-3 text-sm">
                <div className="rounded border p-2 text-center">
                  <p className="text-xs text-muted-foreground">Componentes revertidos</p>
                  <p className="font-bold text-lg">{result.componentes_revertidos.length}</p>
                </div>
                <div className="rounded border p-2 text-center">
                  <p className="text-xs text-muted-foreground">Subproductos eliminados</p>
                  <p className="font-bold text-lg">{result.subproductos_eliminados.length}</p>
                </div>
                <div className="rounded border p-2 text-center">
                  <p className="text-xs text-muted-foreground">Transferencias creadas</p>
                  <p className="font-bold text-lg">{result.transferencias_creadas.length}</p>
                </div>
              </div>
              {result.transferencias_creadas.length > 0 && (
                <div className="text-xs space-y-1">
                  {result.transferencias_creadas.map(t => (
                    <p key={t.id} className="font-mono text-green-400">• {t.name} (ID: {t.id})</p>
                  ))}
                </div>
              )}
              {result.errores && result.errores.length > 0 && (
                <div className="text-xs space-y-0.5">
                  <p className="font-medium text-orange-400">Advertencias:</p>
                  {result.errores.map((e, i) => <p key={i} className="text-muted-foreground">• {e}</p>)}
                </div>
              )}
              <Button variant="outline" size="sm" className="w-full" onClick={() => { setResult(null); setPreview(null); setOdfName(''); setConfirmado(false) }}>
                Nueva reversión
              </Button>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  )
}

// ─────────────────────────────────────────────────────────────────────────────

const estadoConfig: Record<string, { color: string; icon: React.ElementType; badge: 'success' | 'warning' | 'destructive' | 'default' }> = {
  activo:     { color: 'text-green-400',           icon: CheckCircle, badge: 'success'     },
  inactivo:   { color: 'text-muted-foreground',    icon: Clock,       badge: 'default'     },
  error:      { color: 'text-red-400',             icon: XCircle,     badge: 'destructive' },
  ejecutando: { color: 'text-blue-400',            icon: RefreshCw,   badge: 'default'     },
}

export function AutomatizacionesPage() {
  const qc = useQueryClient()

  // Monitor state
  const { data: automatizaciones = [], isLoading } = useAutomatizaciones()
  const ejecutarMut = useEjecutarAutomatizacion()

  // Crear estado
  const [tunelSel, setTunelSel] = useState('')
  const [palletsText, setPalletsText] = useState('')
  const [crearResult, setCrearResult] = useState<Record<string, unknown> | null>(null)
  const { data: tuneles = [], isLoading: loadingTuneles } = useTuneles()
  const crearMut = useCrearOrdenFabricacion()

  // Movimientos estado
  const today = new Date().toISOString().slice(0, 10)
  const [movFechaIni, setMovFechaIni] = useState(today)
  const [movFechaFin, setMovFechaFin] = useState(today)
  const [movEnabled, setMovEnabled] = useState(false)
  const { data: movimientos = [], isLoading: loadingMov } = useMovimientosStock(movFechaIni, movFechaFin, movEnabled)
  // Monitor Movimientos — auto-load today
  const { data: todayMov = [], isLoading: loadingTodayMov } = useMovimientosStock(today, today, true)

  // Procesos estado
  const { data: procesos = [], isLoading: loadingProcesos } = useProcesosAutomatizacion()
  const toggleProcesoMut = useToggleProcesoActivo()

  const handleCrear = () => {
    const pallets = palletsText.split(/[\n,]+/).map(p => p.trim().toUpperCase()).filter(Boolean)
    if (!tunelSel || pallets.length === 0) {
      toast.error('Selecciona un túnel e ingresa al menos un pallet')
      return
    }
    crearMut.mutate(
      { tunel: tunelSel, pallets },
      {
        onSuccess: (data) => {
          setCrearResult(data as Record<string, unknown>)
          toast.success('Orden de fabricación creada')
          setPalletsText('')
        },
        onError: () => toast.error('Error al crear la orden'),
      },
    )
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Automatizaciones"
        description="Monitor y control de automatizaciones del sistema"
      >
        <Button variant="outline" size="sm" onClick={() => qc.invalidateQueries({ queryKey: ['automatizaciones'] })}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Actualizar
        </Button>
      </PageHeader>

      <Tabs defaultValue="monitor">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="monitor">📊 Monitor</TabsTrigger>
          <TabsTrigger value="crear">➕ Crear Orden</TabsTrigger>
          <TabsTrigger value="movimientos">📦 Movimientos</TabsTrigger>
          <TabsTrigger value="monitor-mov">📈 Monitor Mov.</TabsTrigger>
          <TabsTrigger value="procesos">⚙️ Procesos</TabsTrigger>
          <TabsTrigger value="revertir">🔄 Revertir Consumo</TabsTrigger>
        </TabsList>

        {/* Monitor tab */}
        <TabsContent value="monitor" className="mt-4">
          {isLoading ? (
            <LoadingSpinner />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {automatizaciones.map((auto) => {
                const cfg = estadoConfig[auto.estado] ?? estadoConfig.inactivo
                const Icon = cfg.icon
                return (
                  <Card key={auto.id} className="hover:shadow-md transition-shadow">
                    <CardHeader className="pb-2">
                      <div className="flex items-start justify-between gap-2">
                        <CardTitle className="text-base">{auto.nombre}</CardTitle>
                        <Badge variant={cfg.badge as 'default' | 'success' | 'warning' | 'destructive' | 'info'} className="shrink-0">
                          <Icon className={cn('mr-1 h-3 w-3', auto.estado === 'ejecutando' && 'animate-spin')} />
                          {auto.estado}
                        </Badge>
                      </div>
                      <CardDescription className="text-xs">{auto.descripcion}</CardDescription>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {auto.ultimo_run && (
                        <p className="text-xs text-muted-foreground">Último run: {formatDateTime(auto.ultimo_run)}</p>
                      )}
                      {auto.proximo_run && (
                        <p className="text-xs text-muted-foreground">Próximo: {formatDateTime(auto.proximo_run)}</p>
                      )}
                      {auto.resultado && (
                        <p className="text-xs text-muted-foreground truncate">{auto.resultado}</p>
                      )}
                      <Button
                        size="sm"
                        variant="outline"
                        className="w-full"
                        disabled={auto.estado === 'ejecutando' || ejecutarMut.isPending}
                        onClick={() => ejecutarMut.mutate(auto.id)}
                      >
                        <Play className="mr-2 h-3 w-3" />
                        Ejecutar ahora
                      </Button>
                    </CardContent>
                  </Card>
                )
              })}
              {automatizaciones.length === 0 && !isLoading && (
                <div className="col-span-full rounded-lg border border-dashed p-12 text-center text-muted-foreground">
                  No hay automatizaciones configuradas.
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* Crear Orden tab */}
        <TabsContent value="crear" className="mt-4">
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Crear Orden de Fabricación</CardTitle>
                <CardDescription>Selecciona el túnel e ingresa los pallets a consumir</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                {/* Tunnel selector */}
                <div>
                  <label className="text-sm font-medium block mb-2">Túnel</label>
                  {loadingTuneles ? <LoadingSpinner /> : (
                    <div className="flex flex-wrap gap-2">
                      {tuneles.map(t => (
                        <button
                          key={t.codigo}
                          onClick={() => setTunelSel(t.codigo)}
                          className={cn(
                            'rounded-md border px-3 py-2 text-sm transition-colors',
                            tunelSel === t.codigo
                              ? 'border-primary bg-primary/10 text-primary'
                              : 'border-border hover:border-muted-foreground text-muted-foreground',
                          )}
                        >
                          <span className="font-mono font-semibold">{t.codigo}</span>
                          <span className="ml-1 text-xs">{t.sucursal}</span>
                        </button>
                      ))}
                      {tuneles.length === 0 && (
                        <p className="text-sm text-muted-foreground">No hay túneles disponibles (API no conectada)</p>
                      )}
                    </div>
                  )}
                </div>

                {/* Pallet input */}
                <div>
                  <label className="text-sm font-medium block mb-1">
                    Pallets <span className="text-xs text-muted-foreground">(uno por línea o separados por coma)</span>
                  </label>
                  <textarea
                    rows={6}
                    value={palletsText}
                    onChange={e => setPalletsText(e.target.value.toUpperCase())}
                    placeholder="PAL-0001&#10;PAL-0002&#10;PAL-0003"
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm font-mono resize-y"
                  />
                  <p className="text-xs text-muted-foreground mt-1">
                    {palletsText.split(/[\n,]+/).filter(p => p.trim()).length} pallets ingresados
                  </p>
                </div>

                <Button
                  className="w-full"
                  onClick={handleCrear}
                  disabled={crearMut.isPending || !tunelSel}
                >
                  {crearMut.isPending ? (
                    <><RefreshCw className="mr-2 h-4 w-4 animate-spin" />Creando…</>
                  ) : (
                    <><Play className="mr-2 h-4 w-4" />Crear Orden</>
                  )}
                </Button>
              </CardContent>
            </Card>

            {/* Result */}
            {crearResult && (
              <Card className="border-green-500/30 bg-green-500/5">
                <CardHeader>
                  <CardTitle className="text-base text-green-400 flex items-center gap-2">
                    <CheckCircle className="h-4 w-4" />
                    Orden Creada
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <pre className="text-xs text-muted-foreground overflow-auto whitespace-pre-wrap">
                    {JSON.stringify(crearResult, null, 2)}
                  </pre>
                  <Button
                    variant="outline"
                    size="sm"
                    className="mt-3 w-full"
                    onClick={() => setCrearResult(null)}
                  >
                    Limpiar resultado
                  </Button>
                </CardContent>
              </Card>
            )}
          </div>
        </TabsContent>

        {/* Movimientos tab */}
        <TabsContent value="movimientos" className="mt-4 space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div className="flex flex-wrap items-end gap-3">
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Desde</label>
                  <input
                    type="date"
                    value={movFechaIni}
                    onChange={e => setMovFechaIni(e.target.value)}
                    className="rounded border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground block mb-1">Hasta</label>
                  <input
                    type="date"
                    value={movFechaFin}
                    onChange={e => setMovFechaFin(e.target.value)}
                    className="rounded border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <button
                  onClick={() => setMovEnabled(true)}
                  className="rounded bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
                >
                  Cargar movimientos
                </button>
              </div>
            </CardContent>
          </Card>

          {!movEnabled ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              Selecciona un rango de fechas y presiona "Cargar movimientos".
            </div>
          ) : loadingMov ? (
            <LoadingSpinner />
          ) : movimientos.length === 0 ? (
            <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground">
              No hay movimientos en el rango seleccionado.
            </div>
          ) : (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">Movimientos de Stock ({movimientos.length})</CardTitle>
              </CardHeader>
              <CardContent className="overflow-auto p-0">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/40">
                      <th className="px-3 py-2 text-left">Referencia</th>
                      <th className="px-3 py-2 text-left">Producto</th>
                      <th className="px-3 py-2 text-left">Origen → Destino</th>
                      <th className="px-3 py-2 text-right">Cantidad</th>
                      <th className="px-3 py-2 text-left">Fecha</th>
                      <th className="px-3 py-2 text-left">Estado</th>
                    </tr>
                  </thead>
                  <tbody>
                    {movimientos.map(m => (
                      <tr key={m.id} className="border-b hover:bg-muted/20">
                        <td className="px-3 py-2 font-mono text-xs">{m.referencia}</td>
                        <td className="px-3 py-2">{m.producto}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">
                          {m.origen} → {m.destino}
                        </td>
                        <td className="px-3 py-2 text-right font-semibold">{m.cantidad}</td>
                        <td className="px-3 py-2 text-xs text-muted-foreground">{m.fecha}</td>
                        <td className="px-3 py-2">
                          <Badge variant="default">{m.estado}</Badge>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Monitor Movimientos tab */}
        <TabsContent value="monitor-mov" className="mt-4 space-y-4">
          {loadingTodayMov ? (
            <LoadingSpinner />
          ) : (() => {
            const totalPallets = todayMov.reduce((s, m) => s + (m.cantidad ?? 0), 0)
            const exitosos = todayMov.filter(m => m.estado && m.estado !== 'cancel').length
            const fallidos = todayMov.filter(m => m.estado === 'cancel').length
            const tasaExito = (exitosos + fallidos) > 0 ? Math.round(exitosos / (exitosos + fallidos) * 100) : null

            return (
              <>
                <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
                  <KPICard label="Movimientos Hoy" value={todayMov.length} />
                  <KPICard label="Pallets Movidos" value={totalPallets} />
                  <KPICard label="Exitosos" value={exitosos} />
                  <KPICard label="Tasa Éxito" value={tasaExito ?? 0} unit="%" />
                </div>

                {todayMov.length === 0 ? (
                  <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
                    📭 No hay movimientos registrados hoy.
                  </div>
                ) : (
                  <Card>
                    <CardHeader className="py-3">
                      <CardTitle className="text-base">Historial de Hoy ({todayMov.length})</CardTitle>
                    </CardHeader>
                    <CardContent className="p-0 space-y-2 pb-4 px-4">
                      {todayMov.map(m => {
                        const ok = m.estado !== 'cancel'
                        return (
                          <div
                            key={m.id}
                            className={`flex items-center justify-between rounded-lg border p-3 ${ok ? 'border-green-500/20 bg-green-500/5' : 'border-red-500/20 bg-red-500/5'}`}
                          >
                            <div className="space-y-0.5">
                              <p className="text-sm font-medium">
                                {ok ? '✅' : '⚠️'} {m.destino}
                              </p>
                              <p className="text-xs text-muted-foreground">
                                {m.referencia} · {m.origen} → {m.destino}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm font-semibold text-blue-400">{m.cantidad} uds</p>
                              <p className="text-xs text-muted-foreground">{m.fecha}</p>
                            </div>
                          </div>
                        )
                      })}
                    </CardContent>
                  </Card>
                )}
              </>
            )
          })()}
        </TabsContent>

        {/* Procesos tab */}
        <TabsContent value="procesos" className="mt-4">
          {loadingProcesos ? (
            <LoadingSpinner />
          ) : procesos.length === 0 ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              No hay procesos configurados (API no conectada).
            </div>
          ) : (
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {procesos.map(p => (
                <Card key={p.id} className={cn('transition-all', p.activo ? 'border-green-500/20' : 'opacity-70')}>
                  <CardHeader className="pb-2">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-sm">{p.nombre}</CardTitle>
                      <Badge variant={p.activo ? 'success' : 'default'}>{p.estado}</Badge>
                    </div>
                    <CardDescription className="text-xs">{p.descripcion}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="text-xs text-muted-foreground space-y-1">
                      <p>Intervalo: cada {p.intervalo_minutos} min</p>
                      {p.ultimo_run && <p>Último run: {formatDateTime(p.ultimo_run)}</p>}
                      {p.proximo_run && <p>Próximo: {formatDateTime(p.proximo_run)}</p>}
                    </div>
                    <Button
                      size="sm"
                      variant={p.activo ? 'destructive' : 'outline'}
                      className="w-full"
                      disabled={toggleProcesoMut.isPending}
                      onClick={() => toggleProcesoMut.mutate({ id: p.id, activo: !p.activo })}
                    >
                      {p.activo
                        ? <><ToggleLeft className="mr-2 h-3 w-3" />Desactivar</>
                        : <><ToggleRight className="mr-2 h-3 w-3" />Activar</>
                      }
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* Revertir Consumo tab */}
        <TabsContent value="revertir" className="mt-4">
          <RevertirConsumoTab />
        </TabsContent>

      </Tabs>
    </div>
  )
}

export default AutomatizacionesPage
