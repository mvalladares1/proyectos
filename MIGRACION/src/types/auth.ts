export interface User {
  id: number
  name: string
  email: string
  username: string
  roles: string[]
  is_admin: boolean
}

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

export interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  isLoading: boolean
}

export interface PermissionCheckRequest {
  username: string
  dashboard: string
  page?: string
}

export interface PermissionCheckResponse {
  allowed: boolean
  reason?: string
}

export interface DashboardPermissions {
  dashboards: string[]
  pages: Record<string, string[]>
}
