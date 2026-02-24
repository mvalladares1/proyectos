import { useState } from 'react'

import { type ColumnDef } from '@tanstack/react-table'

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

import { PageHeader } from '@/components/layout/PageHeader'

import { FilterBar } from '@/components/forms/FilterBar'

import { DataTable } from '@/components/tables/DataTable'

import { KPICard } from '@/components/shared/KPICard'

import { BarChart } from '@/components/charts/BarChart'

import { LineChart } from '@/components/charts/LineChart'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

import { LoadingSpinner } from '@/components/shared/LoadingSpinner'

import { CURRENT_YEAR } from '@/lib/constants'

import { formatCurrency } from '@/lib/utils'

import { useClientes, useComercialKPIs, useVentasMensuales, type ClienteData } from '@/api/comercial'

const columns: ColumnDef<ClienteData>[] = [

  { accessorKey: 'cliente', header: 'Cliente', enableSorting: true },

  { accessorKey: 'pedidos', header: 'Pedidos', enableSorting: true },

  { accessorKey: 'ventas', header: 'Ventas', cell: ({ getValue }) => formatCurrency(Number(getValue())), enableSorting: true },

  { accessorKey: 'margen', header: 'Margen %', cell: ({ getValue }) => `${Number(getValue()).toFixed(1)}%`, enableSorting: true },

  { accessorKey: 'tendencia', header: 'Tendencia', cell: ({ getValue }) => {

    const v = Number(getValue()); return <span className={v >= 0 ? 'text-green-400' : 'text-red-400'}>{v >= 0 ? 'â–²' : 'â–¼'} {Math.abs(v).toFixed(1)}%</span>

  }},

]

export function RelacionComercialPage() {

  const [year, setYear] = useState(CURRENT_YEAR)

  const [months, setMonths] = useState<number[]>([])

  const { data: clientes = [], isLoading } = useClientes(year, months)

  const { data: kpis, isLoading: loadingKPIs } = useComercialKPIs(year, months)

  const { data: ventasMensuales = [], isLoading: loadingVentas } = useVentasMensuales(year)

  const totalVentas = clientes.reduce((s, r) => s + r.ventas, 0)

  const margenProm = clientes.length ? clientes.reduce((s, r) => s + r.margen, 0) / clientes.length : 0

  return (

    <div className="space-y-4">

      <PageHeader title="Relación Comercial" description="Análisis de clientes, ventas y métricas comerciales" />

      <FilterBar year={year} onYearChange={setYear} months={months} onMonthsChange={setMonths} />

      {/* KPIs */}

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">

        <KPICard label="Clientes Activos" value={kpis?.clientes_activos ?? clientes.length} loading={loadingKPIs} />

        <KPICard label="Ventas Totales" value={kpis?.ventas_totales ?? totalVentas} format="currency" loading={loadingKPIs} />

        <KPICard label="Margen Promedio" value={kpis?.margen_promedio ?? margenProm} unit="%" format="number" loading={loadingKPIs} />

        <Card className="p-4">

          <p className="text-sm text-muted-foreground">Cliente Top</p>

          {loadingKPIs ? <div className="h-7 w-32 rounded bg-muted animate-pulse mt-1" /> : (

            <p className="text-base font-bold mt-1 truncate">{kpis?.cliente_top ?? 'â€”'}</p>

          )}

        </Card>

      </div>

      <Tabs defaultValue="tendencia">

        <TabsList>

          <TabsTrigger value="tendencia">📈 Ventas Mensuales</TabsTrigger>

          <TabsTrigger value="tabla">📋 Clientes</TabsTrigger>

          <TabsTrigger value="grafico">📊 Análisis</TabsTrigger>

        </TabsList>

        {/* Ventas Mensuales */}

        <TabsContent value="tendencia" className="mt-4">

          <Card>

            <CardHeader className="py-3">

              <CardTitle className="text-base">Evolución Mensual de Ventas — {year}</CardTitle>

            </CardHeader>

            <CardContent>

              {loadingVentas ? <LoadingSpinner /> : (

                <LineChart

                  data={ventasMensuales as { mes: string; monto: number; pedidos: number }[]}

                  xKey="mes"

                  lines={[

                    { key: 'monto', name: 'Ventas ($)' },

                  ]}

                  yFormatter={(v) => formatCurrency(v)}

                  height={340}

                />

              )}

            </CardContent>

          </Card>

        </TabsContent>

        {/* Tabla Clientes */}

        <TabsContent value="tabla" className="mt-4">

          <DataTable

            columns={columns}

            data={clientes}

            loading={isLoading}

            searchPlaceholder="Buscar cliente..."

          />

        </TabsContent>

        {/* Gráfico por cliente */}

        <TabsContent value="grafico" className="mt-4">

          <Card>

            <CardHeader><CardTitle className="text-base">Ventas por Cliente (Top 15)</CardTitle></CardHeader>

            <CardContent>

              {isLoading ? <LoadingSpinner /> : (

                <BarChart

                  data={clientes.slice(0, 15)}

                  xKey="cliente"

                  bars={[{ key: 'ventas', name: 'Ventas' }, { key: 'margen', name: 'Margen %' }]}

                  yFormatter={(v) => formatCurrency(v)}

                  horizontal

                  height={400}

                />

              )}

            </CardContent>

          </Card>

        </TabsContent>

      </Tabs>

    </div>

  )

}

export default RelacionComercialPage
