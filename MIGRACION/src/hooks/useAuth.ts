import { useAuthContext } from '@/providers/AuthProvider'
import { useLogin as useLoginMutation, useLogout as useLogoutMutation } from '@/api/auth'
import type { LoginRequest } from '@/types/auth'
import toast from 'react-hot-toast'
import { useNavigate } from 'react-router-dom'

export function useAuth() {
  const { user, token, isAuthenticated, isLoading, setAuth, clearAuth } = useAuthContext()
  const loginMutation = useLoginMutation()
  const logoutMutation = useLogoutMutation()
  const navigate = useNavigate()

  const login = async (credentials: LoginRequest) => {
    const data = await loginMutation.mutateAsync(credentials)
    setAuth(data.user, data.access_token)
    toast.success(`Bienvenido, ${data.user.name}`)
    navigate('/')
  }

  const logout = async () => {
    clearAuth()
    await logoutMutation.mutateAsync()
  }

  return {
    user,
    token,
    isAuthenticated,
    isLoading,
    login,
    logout,
    isLoggingIn: loginMutation.isPending,
    loginError: loginMutation.error,
  }
}
