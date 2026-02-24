import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Shield, Users, Check, X, Plus, Trash2, Settings } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/shared/LoadingSpinner'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { NAV_ITEMS } from '@/lib/constants'
import apiClient from '@/api/client'
import {
  useModulosPermisos, usePaginasPermisos, useOverridesOrigen, useMaintenanceConfig,
  useUpdateModuloPermiso, useUpdatePaginaPermiso, useAddOverrideOrigen, useUpdateMaintenanceConfig,
} from '@/api/permissions'
import toast from 'react-hot-toast'
import { cn } from '@/lib/utils'

interface PermisoUsuario {
  username: string
  name: string
  email: string
  dashboards: string[]
  is_admin: boolean
}

interface PermisoOverride {
  id: number
  username: string
  origen: string
  recurso: string
  accion: string
  permitido: boolean
  created_at: string
}

export function PermisosPage() {
  const qc = useQueryClient()
  const [selected, setSelected] = useState<string | null>(null)
  const [newOverride, setNewOverride] = useState({ username: '', origen: '', recurso: '', accion: 'read', permitido: true })

  // Módulos state
  const [selectedModulo, setSelectedModulo] = useState<string | null>(null)
  const [nuevoEmailModulo, setNuevoEmailModulo] = useState('')

  // Páginas state
  const [moduloPaginas, setModuloPaginas] = useState('')
  const [nuevoEmailPagina, setNuevoEmailPagina] = useState<Record<string, string>>({})

  // Override Origen state
  const [newOvOrigen, setNewOvOrigen] = useState({ picking_name: '', origen_override: '' })

  // Configuración state
  const [maintEdit, setMaintEdit] = useState<{ modo_mantenimiento: boolean; mensaje: string; usuarios_excluidos: string[] } | null>(null)
  const [newExcluido, setNewExcluido] = useState('')

  const { data: usuarios = [], isLoading } = useQuery({
    queryKey: ['permisos', 'usuarios'],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/users')
      return data as PermisoUsuario[]
    },
    staleTime: 2 * 60 * 1000,
  })

  const { data: overrides = [], isLoading: loadingOverrides } = useQuery({
    queryKey: ['permisos', 'overrides'],
    queryFn: async () => {
      const { data } = await apiClient.get('/permissions/overrides')
      return data as PermisoOverride[]
    },
    staleTime: 2 * 60 * 1000,
  })

  // New tab hooks
  const { data: modulos = [], isLoading: loadingModulos } = useModulosPermisos()
  const { data: paginas = [], isLoading: loadingPaginas } = usePaginasPermisos(moduloPaginas)
  const { data: overridesOrigen = [], isLoading: loadingOvOrigen } = useOverridesOrigen()
  const { data: maintConfig, isLoading: loadingMaint } = useMaintenanceConfig()
  const updateModuloMut = useUpdateModuloPermiso()
  const updatePaginaMut = useUpdatePaginaPermiso()
  const addOvOrigenMut = useAddOverrideOrigen()
  const updateMaintMut = useUpdateMaintenanceConfig()

  const updateMut = useMutation({
    mutationFn: async ({ username, dashboards }: { username: string; dashboards: string[] }) => {
      await apiClient.put(`/permissions/users/${username}`, { dashboards })
    },
    onSuccess: () => {
      toast.success('Permisos actualizados')
      qc.invalidateQueries({ queryKey: ['permisos'] })
    },
    onError: () => toast.error('Error al actualizar permisos'),
  })

  const addOverrideMut = useMutation({
    mutationFn: async (override: typeof newOverride) => {
      await apiClient.post('/permissions/overrides', override)
    },
    onSuccess: () => {
      toast.success('Override agregado')
      qc.invalidateQueries({ queryKey: ['permisos', 'overrides'] })
      setNewOverride({ username: '', origen: '', recurso: '', accion: 'read', permitido: true })
    },
    onError: () => toast.error('Error al agregar override'),
  })

  const deleteOverrideMut = useMutation({
    mutationFn: async (id: number) => {
      await apiClient.delete(`/permissions/overrides/${id}`)
    },
    onSuccess: () => {
      toast.success('Override eliminado')
      qc.invalidateQueries({ queryKey: ['permisos', 'overrides'] })
    },
    onError: () => toast.error('Error al eliminar override'),
  })

  const selectedUser = usuarios.find((u) => u.username === selected)
  const modules = NAV_ITEMS.filter((m) => !m.adminOnly && m.path !== '/')

  const toggleDashboard = (dashboard: string) => {
    if (!selectedUser) return
    const current = selectedUser.dashboards
    const next = current.includes(dashboard)
      ? current.filter((d) => d !== dashboard)
      : [...current, dashboard]
    updateMut.mutate({ username: selectedUser.username, dashboards: next })
  }

  return (
    <div className="space-y-4">
      <PageHeader
        title="Permisos"
        description="Gestión de accesos por usuario, módulo y overrides"
      />

      <Tabs defaultValue="usuarios">
        <TabsList className="flex-wrap h-auto gap-1">
          <TabsTrigger value="usuarios">👥 Usuarios y Módulos</TabsTrigger>
          <TabsTrigger value="overrides">🔧 Overrides Actuales</TabsTrigger>
          <TabsTrigger value="agregar">➕ Agregar Override</TabsTrigger>
          <TabsTrigger value="modulos">🏛️ Módulos</TabsTrigger>
          <TabsTrigger value="paginas">📄 Páginas</TabsTrigger>
          <TabsTrigger value="override-origen">🔀 Override Origen</TabsTrigger>
          <TabsTrigger value="configuracion">⚙️ Configuración</TabsTrigger>
        </TabsList>

        {/* Usuarios y Módulos tab */}
        <TabsContent value="usuarios" className="mt-4">
          {isLoading ? (
            <LoadingSpinner />
          ) : (
            <div className="grid gap-4 lg:grid-cols-3">
              {/* User list */}
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground flex items-center gap-2">
                  <Users className="h-4 w-4" /> Usuarios ({usuarios.length})
                </h3>
                {usuarios.map((u) => (
                  <button
                    key={u.username}
                    onClick={() => setSelected(u.username)}
                    className={cn(
                      'w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted',
                      selected === u.username && 'border-primary bg-primary/5',
                    )}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm font-medium">{u.name}</p>
                        <p className="text-xs text-muted-foreground">{u.email}</p>
                      </div>
                      {u.is_admin && <Badge variant="info" className="text-xs">Admin</Badge>}
                    </div>
                  </button>
                ))}
              </div>

              {/* Permissions editor */}
              {selectedUser ? (
                <div className="lg:col-span-2">
                  <Card>
                    <CardHeader>
                      <CardTitle className="flex items-center gap-2 text-base">
                        <Shield className="h-4 w-4" />
                        Permisos de {selectedUser.name}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {selectedUser.is_admin ? (
                        <p className="text-sm text-muted-foreground">
                          Este usuario es administrador y tiene acceso a todos los módulos.
                        </p>
                      ) : (
                        <div className="grid gap-2 sm:grid-cols-2">
                          {modules.map((module) => {
                            const hasAccess = selectedUser.dashboards.includes(module.dashboard)
                            return (
                              <button
                                key={module.dashboard}
                                onClick={() => toggleDashboard(module.dashboard)}
                                disabled={updateMut.isPending}
                                className={cn(
                                  'flex items-center justify-between rounded-md border p-3 text-sm transition-colors',
                                  hasAccess
                                    ? 'border-green-500/30 bg-green-500/10 text-green-400'
                                    : 'border-border hover:border-muted-foreground text-muted-foreground',
                                )}
                              >
                                <span>{module.label}</span>
                                {hasAccess ? <Check className="h-4 w-4" /> : <X className="h-4 w-4" />}
                              </button>
                            )
                          })}
                        </div>
                      )}
                    </CardContent>
                  </Card>
                </div>
              ) : (
                <div className="lg:col-span-2 flex items-center justify-center rounded-lg border border-dashed p-12 text-muted-foreground">
                  Selecciona un usuario para editar sus permisos
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* Overrides Actuales tab */}
        <TabsContent value="overrides" className="mt-4">
          {loadingOverrides ? <LoadingSpinner /> : overrides.length === 0 ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              No hay overrides configurados.
            </div>
          ) : (
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">Overrides Activos ({overrides.length})</CardTitle>
              </CardHeader>
              <CardContent className="overflow-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b bg-muted/40">
                      <th className="px-3 py-2 text-left">Usuario</th>
                      <th className="px-3 py-2 text-left">Origen</th>
                      <th className="px-3 py-2 text-left">Recurso</th>
                      <th className="px-3 py-2 text-left">Acción</th>
                      <th className="px-3 py-2 text-center">Permitido</th>
                      <th className="px-3 py-2 text-left">Fecha</th>
                      <th className="px-3 py-2 text-center">Eliminar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {overrides.map((ov) => (
                      <tr key={ov.id} className="border-b hover:bg-muted/20">
                        <td className="px-3 py-2 font-medium">{ov.username}</td>
                        <td className="px-3 py-2 text-muted-foreground">{ov.origen}</td>
                        <td className="px-3 py-2">{ov.recurso}</td>
                        <td className="px-3 py-2">
                          <Badge variant="default">{ov.accion}</Badge>
                        </td>
                        <td className="px-3 py-2 text-center">
                          {ov.permitido
                            ? <Check className="h-4 w-4 text-green-400 inline" />
                            : <X className="h-4 w-4 text-red-400 inline" />}
                        </td>
                        <td className="px-3 py-2 text-muted-foreground text-xs">{ov.created_at}</td>
                        <td className="px-3 py-2 text-center">
                          <button
                            onClick={() => deleteOverrideMut.mutate(ov.id)}
                            disabled={deleteOverrideMut.isPending}
                            className="text-red-400 hover:text-red-300 transition-colors"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Agregar Override tab */}
        <TabsContent value="agregar" className="mt-4">
          <Card className="max-w-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Plus className="h-4 w-4" />
                Agregar Override de Permiso
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid gap-3">
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Usuario</label>
                  <select
                    value={newOverride.username}
                    onChange={e => setNewOverride(p => ({ ...p, username: e.target.value }))}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="">— Seleccionar usuario —</option>
                    {usuarios.map(u => <option key={u.username} value={u.username}>{u.name}</option>)}
                  </select>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Origen</label>
                  <input
                    type="text"
                    value={newOverride.origen}
                    onChange={e => setNewOverride(p => ({ ...p, origen: e.target.value }))}
                    placeholder="ej. proveedor_123"
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Recurso</label>
                  <input
                    type="text"
                    value={newOverride.recurso}
                    onChange={e => setNewOverride(p => ({ ...p, recurso: e.target.value }))}
                    placeholder="ej. recepciones"
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Acción</label>
                  <select
                    value={newOverride.accion}
                    onChange={e => setNewOverride(p => ({ ...p, accion: e.target.value }))}
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  >
                    <option value="read">read</option>
                    <option value="write">write</option>
                    <option value="delete">delete</option>
                    <option value="admin">admin</option>
                  </select>
                </div>
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Permitido</label>
                  <div className="flex gap-3">
                    {[true, false].map(v => (
                      <button
                        key={String(v)}
                        onClick={() => setNewOverride(p => ({ ...p, permitido: v }))}
                        className={cn(
                          'flex-1 rounded border py-2 text-sm transition-colors',
                          newOverride.permitido === v
                            ? v ? 'border-green-500/50 bg-green-500/20 text-green-400' : 'border-red-500/50 bg-red-500/20 text-red-400'
                            : 'border-border text-muted-foreground hover:border-muted-foreground',
                        )}
                      >
                        {v ? '✓ Permitir' : '✗ Denegar'}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
              <Button
                onClick={() => addOverrideMut.mutate(newOverride)}
                disabled={addOverrideMut.isPending || !newOverride.username || !newOverride.recurso}
                className="w-full"
              >
                {addOverrideMut.isPending ? 'Guardando…' : 'Agregar Override'}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ──────────── Módulos tab ──────────── */}
        <TabsContent value="modulos" className="mt-4">
          {loadingModulos ? <LoadingSpinner /> : (
            <div className="grid gap-4 lg:grid-cols-3">
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-muted-foreground mb-2">Módulos ({modulos.length})</h3>
                {modulos.length === 0 && (
                  <p className="text-sm text-muted-foreground p-4 text-center border border-dashed rounded-lg">
                    Sin módulos (API no conectada)
                  </p>
                )}
                {modulos.map(m => (
                  <button
                    key={m.modulo}
                    onClick={() => setSelectedModulo(m.modulo)}
                    className={cn(
                      'w-full rounded-lg border p-3 text-left transition-colors hover:bg-muted',
                      selectedModulo === m.modulo && 'border-primary bg-primary/5',
                    )}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <p className="text-sm font-medium truncate">{m.nombre}</p>
                      <Badge variant={m.es_publico ? 'default' : 'warning'} className="shrink-0 text-xs">
                        {m.es_publico ? 'Público' : 'Restringido'}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground mt-1">{m.emails.length} email(s)</p>
                  </button>
                ))}
              </div>

              {selectedModulo ? (() => {
                const mod = modulos.find(m => m.modulo === selectedModulo)
                return (
                  <div className="lg:col-span-2">
                    <Card>
                      <CardHeader>
                        <CardTitle className="text-base flex items-center gap-2">
                          <Shield className="h-4 w-4" />
                          {mod?.nombre ?? selectedModulo}
                        </CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div>
                          <h4 className="text-sm text-muted-foreground mb-2">Emails con acceso</h4>
                          {(mod?.emails ?? []).length === 0 ? (
                            <p className="text-sm text-muted-foreground italic">Ninguno (módulo público)</p>
                          ) : (
                            <div className="space-y-1">
                              {(mod?.emails ?? []).map(email => (
                                <div key={email} className="flex items-center justify-between rounded border px-3 py-2">
                                  <span className="text-sm">{email}</span>
                                  <button
                                    onClick={() => updateModuloMut.mutate({ accion: 'remove', modulo: selectedModulo, email },
                                      { onSuccess: () => toast.success('Email removido') }
                                    )}
                                    className="text-red-400 hover:text-red-300"
                                  >
                                    <Trash2 className="h-3 w-3" />
                                  </button>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                        <div className="flex gap-2">
                          <input
                            type="email"
                            value={nuevoEmailModulo}
                            onChange={e => setNuevoEmailModulo(e.target.value)}
                            placeholder="nuevo@email.com"
                            className="flex-1 rounded border border-input bg-background px-3 py-2 text-sm"
                          />
                          <Button
                            size="sm"
                            disabled={!nuevoEmailModulo || updateModuloMut.isPending}
                            onClick={() => updateModuloMut.mutate(
                              { accion: 'assign', modulo: selectedModulo, email: nuevoEmailModulo },
                              { onSuccess: () => { toast.success('Email agregado'); setNuevoEmailModulo('') } }
                            )}
                          >
                            <Plus className="h-4 w-4" />
                          </Button>
                        </div>
                      </CardContent>
                    </Card>
                  </div>
                )
              })() : (
                <div className="lg:col-span-2 flex items-center justify-center rounded-lg border border-dashed p-12 text-muted-foreground">
                  Selecciona un módulo para gestionar accesos
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* ──────────── Páginas tab ──────────── */}
        <TabsContent value="paginas" className="mt-4 space-y-4">
          <Card>
            <CardContent className="pt-4">
              <div>
                <label className="text-sm text-muted-foreground block mb-1">Módulo</label>
                <select
                  value={moduloPaginas}
                  onChange={e => setModuloPaginas(e.target.value)}
                  className="w-full max-w-xs rounded border border-input bg-background px-3 py-2 text-sm"
                >
                  <option value="">— Seleccionar módulo —</option>
                  {modulos.map(m => <option key={m.modulo} value={m.modulo}>{m.nombre}</option>)}
                </select>
              </div>
            </CardContent>
          </Card>

          {!moduloPaginas ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              Selecciona un módulo para ver sus páginas y permisos.
            </div>
          ) : loadingPaginas ? <LoadingSpinner /> : (
            <div className="space-y-2">
              {paginas.map(pag => (
                <Card key={pag.slug}>
                  <CardHeader className="py-3">
                    <div className="flex items-center justify-between gap-2">
                      <CardTitle className="text-sm">{pag.name}</CardTitle>
                      <Badge variant={pag.es_publico ? 'default' : 'warning'} className="text-xs">
                        {pag.es_publico ? 'Público' : 'Restringido'}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="pt-0 space-y-2">
                    <div className="flex flex-wrap gap-2">
                      {pag.emails.map(email => (
                        <div key={email} className="flex items-center gap-1 rounded-full border px-2 py-1 text-xs">
                          {email}
                          <button
                            onClick={() => updatePaginaMut.mutate(
                              { accion: 'remove', modulo: moduloPaginas, slug: pag.slug, email },
                              { onSuccess: () => toast.success('Email removido') }
                            )}
                            className="text-red-400 hover:text-red-300 ml-1"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="email"
                        value={nuevoEmailPagina[pag.slug] ?? ''}
                        onChange={e => setNuevoEmailPagina(p => ({ ...p, [pag.slug]: e.target.value }))}
                        placeholder="agregar email…"
                        className="flex-1 rounded border border-input bg-background px-3 py-1.5 text-xs"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!nuevoEmailPagina[pag.slug] || updatePaginaMut.isPending}
                        onClick={() => updatePaginaMut.mutate(
                          { accion: 'assign', modulo: moduloPaginas, slug: pag.slug, email: nuevoEmailPagina[pag.slug] },
                          { onSuccess: () => { toast.success('Email agregado'); setNuevoEmailPagina(p => ({ ...p, [pag.slug]: '' })) } }
                        )}
                      >
                        <Plus className="h-3 w-3" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
              {paginas.length === 0 && (
                <div className="rounded-lg border border-dashed p-8 text-center text-muted-foreground text-sm">
                  No hay páginas configuradas para este módulo.
                </div>
              )}
            </div>
          )}
        </TabsContent>

        {/* ──────────── Override Origen tab ──────────── */}
        <TabsContent value="override-origen" className="mt-4 space-y-4">
          <div className="grid gap-4 lg:grid-cols-2">
            {/* List */}
            <Card>
              <CardHeader className="py-3">
                <CardTitle className="text-base">Overrides de Origen ({overridesOrigen.length})</CardTitle>
              </CardHeader>
              <CardContent className="p-0">
                {loadingOvOrigen ? <div className="p-4"><LoadingSpinner /></div> : overridesOrigen.length === 0 ? (
                  <p className="p-6 text-center text-sm text-muted-foreground">No hay overrides configurados.</p>
                ) : (
                  <div className="overflow-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="border-b bg-muted/40">
                          <th className="px-3 py-2 text-left">Picking</th>
                          <th className="px-3 py-2 text-left">Origen Original</th>
                          <th className="px-3 py-2 text-left">Override</th>
                        </tr>
                      </thead>
                      <tbody>
                        {overridesOrigen.map((ov, i) => (
                          <tr key={i} className="border-b hover:bg-muted/20">
                            <td className="px-3 py-2 font-mono text-xs">{ov.picking_name}</td>
                            <td className="px-3 py-2 text-muted-foreground">{ov.origen_original}</td>
                            <td className="px-3 py-2 font-semibold text-primary">{ov.origen_override}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Add form */}
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Plus className="h-4 w-4" />
                  Agregar Override de Origen
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Nombre del picking</label>
                  <input
                    type="text"
                    value={newOvOrigen.picking_name}
                    onChange={e => setNewOvOrigen(p => ({ ...p, picking_name: e.target.value }))}
                    placeholder="ej. WH/REC/00123"
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm font-mono"
                  />
                </div>
                <div>
                  <label className="text-sm text-muted-foreground block mb-1">Nuevo origen (override)</label>
                  <input
                    type="text"
                    value={newOvOrigen.origen_override}
                    onChange={e => setNewOvOrigen(p => ({ ...p, origen_override: e.target.value }))}
                    placeholder="ej. Proveedor X"
                    className="w-full rounded border border-input bg-background px-3 py-2 text-sm"
                  />
                </div>
                <Button
                  className="w-full"
                  disabled={addOvOrigenMut.isPending || !newOvOrigen.picking_name || !newOvOrigen.origen_override}
                  onClick={() => addOvOrigenMut.mutate(newOvOrigen, {
                    onSuccess: () => {
                      toast.success('Override agregado')
                      setNewOvOrigen({ picking_name: '', origen_override: '' })
                    },
                    onError: () => toast.error('Error al agregar override'),
                  })}
                >
                  {addOvOrigenMut.isPending ? 'Guardando…' : 'Agregar Override'}
                </Button>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* ──────────── Configuración tab ──────────── */}
        <TabsContent value="configuracion" className="mt-4">
          {loadingMaint ? <LoadingSpinner /> : !maintConfig ? (
            <div className="rounded-lg border border-dashed p-12 text-center text-muted-foreground">
              Configuración no disponible (API no conectada).
            </div>
          ) : (() => {
            const cfg = maintEdit ?? maintConfig
            return (
              <Card className="max-w-lg">
                <CardHeader>
                  <CardTitle className="flex items-center gap-2 text-base">
                    <Settings className="h-4 w-4" />
                    Configuración del Sistema
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  {/* Maintenance toggle */}
                  <div className="flex items-center justify-between rounded border p-3">
                    <div>
                      <p className="text-sm font-medium">Modo Mantenimiento</p>
                      <p className="text-xs text-muted-foreground">Bloquea acceso a usuarios no excluidos</p>
                    </div>
                    <button
                      onClick={() => setMaintEdit(p => ({ ...(p ?? maintConfig), modo_mantenimiento: !cfg.modo_mantenimiento }))}
                      className={cn(
                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                        cfg.modo_mantenimiento ? 'bg-primary' : 'bg-muted-foreground/30',
                      )}
                    >
                      <span
                        className={cn(
                          'inline-block h-4 w-4 rounded-full bg-white transition-transform',
                          cfg.modo_mantenimiento ? 'translate-x-6' : 'translate-x-1',
                        )}
                      />
                    </button>
                  </div>

                  {/* Message */}
                  <div>
                    <label className="text-sm text-muted-foreground block mb-1">Mensaje de mantenimiento</label>
                    <textarea
                      rows={2}
                      value={cfg.mensaje}
                      onChange={e => setMaintEdit(p => ({ ...(p ?? maintConfig), mensaje: e.target.value }))}
                      className="w-full rounded border border-input bg-background px-3 py-2 text-sm resize-none"
                    />
                  </div>

                  {/* Excluded users */}
                  <div>
                    <label className="text-sm text-muted-foreground block mb-1">Usuarios excluidos del mantenimiento</label>
                    <div className="space-y-1 mb-2">
                      {cfg.usuarios_excluidos.map(u => (
                        <div key={u} className="flex items-center justify-between rounded border px-3 py-1.5 text-sm">
                          {u}
                          <button
                            onClick={() => setMaintEdit(p => ({
                              ...(p ?? maintConfig),
                              usuarios_excluidos: cfg.usuarios_excluidos.filter(x => x !== u),
                            }))}
                            className="text-red-400 hover:text-red-300"
                          >
                            <X className="h-3 w-3" />
                          </button>
                        </div>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        type="email"
                        value={newExcluido}
                        onChange={e => setNewExcluido(e.target.value)}
                        placeholder="email@ejemplo.com"
                        className="flex-1 rounded border border-input bg-background px-3 py-2 text-sm"
                      />
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={!newExcluido}
                        onClick={() => {
                          setMaintEdit(p => ({
                            ...(p ?? maintConfig),
                            usuarios_excluidos: [...cfg.usuarios_excluidos, newExcluido],
                          }))
                          setNewExcluido('')
                        }}
                      >
                        <Plus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>

                  {/* Save */}
                  <div className="flex gap-2">
                    <Button
                      className="flex-1"
                      disabled={!maintEdit || updateMaintMut.isPending}
                      onClick={() => {
                        if (!maintEdit) return
                        updateMaintMut.mutate(maintEdit, {
                          onSuccess: () => { toast.success('Configuración guardada'); setMaintEdit(null) },
                          onError: () => toast.error('Error al guardar'),
                        })
                      }}
                    >
                      {updateMaintMut.isPending ? 'Guardando…' : 'Guardar cambios'}
                    </Button>
                    {maintEdit && (
                      <Button variant="outline" onClick={() => setMaintEdit(null)}>
                        Descartar
                      </Button>
                    )}
                  </div>
                </CardContent>
              </Card>
            )
          })()}
        </TabsContent>
      </Tabs>
    </div>
  )
}

export default PermisosPage

