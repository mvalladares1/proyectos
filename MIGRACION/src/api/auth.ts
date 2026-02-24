import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import apiClient from './client'
import type { LoginRequest, LoginResponse, User } from '@/types/auth'
import { TOKEN_KEY, USER_KEY } from '@/lib/constants'

// ─── API calls ────────────────────────────────────────────────────

async function login(credentials: LoginRequest): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/login', credentials)
  return data
}

async function logout(): Promise<void> {
  await apiClient.post('/auth/logout').catch(() => {})
}

async function getMe(): Promise<User> {
  const { data } = await apiClient.get<User>('/auth/me')
  return data
}

// ─── Hooks ────────────────────────────────────────────────────────

export function useLogin() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: login,
    onSuccess: (data) => {
      localStorage.setItem(TOKEN_KEY, data.access_token)
      localStorage.setItem(USER_KEY, JSON.stringify(data.user))
      queryClient.setQueryData(['auth', 'me'], data.user)
    },
  })
}

export function useLogout() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: logout,
    onSettled: () => {
      localStorage.removeItem(TOKEN_KEY)
      localStorage.removeItem(USER_KEY)
      queryClient.clear()
      window.location.href = '/login'
    },
  })
}

export function useMe() {
  const token = localStorage.getItem(TOKEN_KEY)

  return useQuery({
    queryKey: ['auth', 'me'],
    queryFn: getMe,
    enabled: !!token,
    staleTime: 5 * 60 * 1000,
    retry: false,
  })
}
