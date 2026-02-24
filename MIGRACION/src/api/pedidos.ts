import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface PedidoVenta {
  id: number
  name: string
  cliente: string
  fecha: string
  estado: string
  monto_total: number
  lineas: number
}

export interface PedidosKPI {
  total_pedidos: number
  monto_total: number
  pedidos_confirmados: number
  clientes_activos: number
}

export interface ProyeccionVenta {
  id: number
  name: string
  cliente: string
  fecha_entrega: string
  estado: string
  especie: string
  kg_comprometidos: number
  monto_total: number
  dias_para_entrega: number
}

export interface CalendarioEntrega {
  fecha: string
  pedidos: {
    name: string
    cliente: string
    especie: string
    kg: number
    monto: number
    estado: string
  }[]
  total_kg: number
  total_monto: number
  num_pedidos: number
}

export interface ProgresoVenta {
  cliente: string
  pedidos_total: number
  pedidos_confirmados: number
  pedidos_entregados: number
  monto_total: number
  monto_facturado: number
  avance_pct: number
}

export function usePedidosVenta(year: number, months: number[]) {
  return useQuery<PedidoVenta[]>({
    queryKey: ['pedidos-venta', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/pedidos-venta/', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePedidosKPIs(year: number, months: number[]) {
  return useQuery<PedidosKPI>({
    queryKey: ['pedidos-venta', 'kpis', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/pedidos-venta/kpis', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}

export function usePedidoDetalle(id: number | null) {
  return useQuery<PedidoVenta>({
    queryKey: ['pedidos-venta', 'detalle', id],
    queryFn: async () => {
      const { data } = await apiClient.get(`/pedidos-venta/${id}`)
      return data
    },
    enabled: id !== null,
    staleTime: 2 * 60 * 1000,
  })
}

export function useProyeccionVentas(fechaInicio: string, fechaFin: string, estado?: string, enabled = true) {
  return useQuery<ProyeccionVenta[]>({
    queryKey: ['pedidos-venta', 'proyeccion', fechaInicio, fechaFin, estado],
    queryFn: async () => {
      const { data } = await apiClient.get('/containers/proyecciones', {
        params: { start_date: fechaInicio, end_date: fechaFin, state: estado || undefined },
      })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useCalendarioVentas(fechaInicio: string, fechaFin: string, enabled = true) {
  return useQuery<CalendarioEntrega[]>({
    queryKey: ['pedidos-venta', 'calendario', fechaInicio, fechaFin],
    queryFn: async () => {
      const { data } = await apiClient.get('/containers/calendario', {
        params: { start_date: fechaInicio, end_date: fechaFin },
      })
      return data
    },
    enabled,
    staleTime: 5 * 60 * 1000,
  })
}

export function useProgresoVentas(year: number, months: number[]) {
  return useQuery<ProgresoVenta[]>({
    queryKey: ['pedidos-venta', 'progreso', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/containers/progreso-ventas', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 5 * 60 * 1000,
  })
}
