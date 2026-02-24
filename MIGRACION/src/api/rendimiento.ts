import { useQuery } from '@tanstack/react-query'
import apiClient from './client'

export interface RendimientoData {
  periodo: string
  rendimiento: number
  merma: number
  eficiencia: number
}

export interface RendimientoKPI {
  rendimiento_promedio: number
  merma_promedio: number
  eficiencia_promedio: number
  mejor_mes: string
}

export function useRendimiento(year: number, months: number[]) {
  return useQuery<RendimientoData[]>({
    queryKey: ['rendimiento', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useRendimientoKPIs(year: number, months: number[]) {
  return useQuery<RendimientoKPI>({
    queryKey: ['rendimiento', 'kpis', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/kpis', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useRendimientoPorLinea(year: number, months: number[]) {
  return useQuery({
    queryKey: ['rendimiento', 'lineas', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/por-linea', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useRendimientoVentas(year: number, months: number[]) {
  return useQuery({
    queryKey: ['rendimiento', 'ventas', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/ventas', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useRendimientoStockRotacion(year: number, months: number[]) {
  return useQuery({
    queryKey: ['rendimiento', 'stock-rotacion', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/stock-rotacion', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useRendimientoCompras(year: number, months: number[]) {
  return useQuery({
    queryKey: ['rendimiento', 'compras-analisis', year, months],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/compras', {
        params: { year, months: months.length ? months : undefined },
      })
      return data
    },
    staleTime: 10 * 60 * 1000,
  })
}

export function useStockTeoricoAnual(fechaDesde: string, fechaHasta: string, enabled = true) {
  return useQuery({
    queryKey: ['rendimiento', 'stock-teorico', fechaDesde, fechaHasta],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/stock-teorico', {
        params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
      })
      return data
    },
    enabled,
    staleTime: 10 * 60 * 1000,
  })
}

export interface InventarioTrazabilidadData {
  total_comprado_kg: number
  total_comprado_monto: number
  total_comprado_precio_promedio: number
  total_vendido_kg: number
  total_vendido_monto: number
  total_vendido_precio_promedio: number
  fecha_desde: string
  fecha_hasta: string
  por_tipo_fruta: {
    tipo_fruta: string
    manejo: string
    comprado_kg: number
    comprado_monto: number
    vendido_kg: number
    vendido_monto: number
  }[]
}

export function useInventarioTrazabilidad(fechaDesde: string, fechaHasta: string, enabled = true) {
  return useQuery<InventarioTrazabilidadData>({
    queryKey: ['rendimiento', 'inventario-trazabilidad', fechaDesde, fechaHasta],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/inventario-trazabilidad', {
        params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
      })
      return data
    },
    enabled,
    staleTime: 10 * 60 * 1000,
  })
}

export interface ProduccionRendimientoData {
  resumen: {
    kg_consumido: number
    kg_producido: number
    rendimiento_pct: number
    merma_pct: number
    merma_kg: number
    ordenes_total: number
  }
  rendimientos_por_tipo: {
    tipo_fruta: string
    kg_consumido: number
    kg_producido: number
    rendimiento_pct: number
    merma_pct: number
  }[]
  detalle_ordenes: {
    fecha: string
    orden: string
    tipo_fruta: string
    estado: string
    kg_consumido: number
    kg_producido: number
    rendimiento_pct: number
    merma_pct: number
  }[]
}

export function useProduccionRendimiento(fechaDesde: string, fechaHasta: string, enabled = true) {
  return useQuery<ProduccionRendimientoData>({
    queryKey: ['rendimiento', 'produccion-rendimiento', fechaDesde, fechaHasta],
    queryFn: async () => {
      const { data } = await apiClient.get('/rendimiento/produccion-data', {
        params: { fecha_desde: fechaDesde, fecha_hasta: fechaHasta },
      })
      return data
    },
    enabled,
    staleTime: 10 * 60 * 1000,
  })
}
