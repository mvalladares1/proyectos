// Generic API response wrapper
export interface ApiResponse<T> {
  data: T
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ApiError {
  detail: string
  status_code?: number
}

// Common filter types
export interface DateRangeFilter {
  start_date?: string
  end_date?: string
}

export interface YearMonthFilter {
  year?: number
  months?: number[]
}

export interface KPIMetric {
  label: string
  value: number
  unit?: string
  change?: number
  change_type?: 'increase' | 'decrease' | 'neutral'
  format?: 'currency' | 'number' | 'percent'
}
