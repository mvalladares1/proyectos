import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'
import toast from 'react-hot-toast'
import { TOKEN_KEY } from '@/lib/constants'

const isDev = import.meta.env.DEV

export const apiClient = axios.create({
  baseURL: isDev ? '/api' : import.meta.env.VITE_API_URL_PROD,
  timeout: 30_000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor: attach token
apiClient.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const token = localStorage.getItem(TOKEN_KEY)
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor: handle errors globally
apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError<{ detail: string }>) => {
    const status = error.response?.status
    const message = error.response?.data?.detail ?? error.message

    if (status === 401) {
      localStorage.removeItem(TOKEN_KEY)
      window.location.href = '/login'
    } else if (status === 403) {
      toast.error('No tienes permisos para realizar esta acción')
    } else if (status === 500) {
      toast.error(`Error del servidor: ${message}`)
    }

    return Promise.reject(error)
  },
)

export default apiClient
