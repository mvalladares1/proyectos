import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface OrdenCompra {
  id: number
  name: string
  proveedor: string
  fecha: string
  estado: string
  monto_total: number
  producto: string
  cantidad: number
}

export interface ComprasKPI {
  total_ocs: number
  monto_total: number
  ocs_confirmadas: number
  proveedores_activos: number
}

export interface LineaCreditoResumen {
  total_proveedores: number
  total_linea: number
  total_usado: number
  total_disponible: number
  pct_uso_global: number
  sin_cupo: number
  cupo_bajo: number
  disponibles: number
}

export interface LineaCreditoProveedor {
  partner_id: number
  partner_name: string
  linea_total: number
  monto_usado: number
  monto_facturas: number
  monto_recepciones: number
  num_facturas: number
  num_recepciones: number
  disponible: number
  pct_uso: number
  estado: 'Sin cupo' | 'Cupo bajo' | 'Disponible'
  alerta: string
  detalle: {
    tipo: string
    referencia: string
    fecha: string
    monto: number
    descripcion: string
  }[]
}

export function useLineasCreditoResumen(fechaDesde: string, enabled = true) {
  return useQuery<LineaCreditoResumen>({
    queryKey: ['compras', 'lineas-credito-resumen', fechaDesde],
    queryFn: async () => {
      const { data } = await apiClient.get('/compras/lineas-credito/resumen', {
        params: { fecha_desde: fechaDesde },
      })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useLineasCredito(fechaDesde: string, enabled = true) {
  return useQuery<LineaCreditoProveedor[]>({
    queryKey: ['compras', 'lineas-credito', fechaDesde],
    queryFn: async () => {
      const { data } = await apiClient.get('/compras/lineas-credito', {
        params: { fecha_desde: fechaDesde },
      })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCompras(year: number, months: number[]) {
  return useQuery<OrdenCompra[]>({
    queryKey: ['compras', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/compras/', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useComprasKPIs(year: number, months: number[]) {
  return useQuery<ComprasKPI>({
    queryKey: ['compras', 'kpis', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/compras/kpis', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function useComprasPorProveedor(year: number, months: number[]) {
  return useQuery({
    queryKey: ['compras', 'proveedores', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/compras/por-proveedor', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}
