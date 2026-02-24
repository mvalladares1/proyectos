import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Loader2, Lock, User } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useAuth } from '@/hooks/useAuth'

const loginSchema = z.object({
  username: z.string().min(1, 'Usuario requerido'),
  password: z.string().min(1, 'Contraseña requerida'),
})

type LoginFormValues = z.infer<typeof loginSchema>

export function LoginForm() {
  const { login, isLoggingIn } = useAuth()

  const {
    register,
    handleSubmit,
    formState: { errors },
    setError,
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
  })

  const onSubmit = async (data: LoginFormValues) => {
    try {
      await login(data)
    } catch {
      setError('root', { message: 'Credenciales incorrectas. Intenta de nuevo.' })
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-background p-4">
      <div className="w-full max-w-sm">
        {/* Logo */}
        <div className="mb-8 flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary shadow-lg shadow-primary/30">
            <span className="text-xl font-bold text-primary-foreground">RF</span>
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-bold">Rio Futuro</h1>
            <p className="text-sm text-muted-foreground">Dashboard Empresarial</p>
          </div>
        </div>

        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-xl">Iniciar sesión</CardTitle>
            <CardDescription>Ingresa tus credenciales de Odoo</CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="username">Usuario</Label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="username"
                    placeholder="tu.usuario"
                    className="pl-9"
                    autoComplete="username"
                    {...register('username')}
                  />
                </div>
                {errors.username && (
                  <p className="text-xs text-destructive">{errors.username.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="password">Contraseña</Label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
                  <Input
                    id="password"
                    type="password"
                    placeholder="••••••••"
                    className="pl-9"
                    autoComplete="current-password"
                    {...register('password')}
                  />
                </div>
                {errors.password && (
                  <p className="text-xs text-destructive">{errors.password.message}</p>
                )}
              </div>

              {errors.root && (
                <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2">
                  <p className="text-xs text-destructive">{errors.root.message}</p>
                </div>
              )}

              <Button type="submit" className="w-full" disabled={isLoggingIn}>
                {isLoggingIn ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Ingresando...
                  </>
                ) : (
                  'Ingresar'
                )}
              </Button>
            </form>
          </CardContent>
        </Card>

        <p className="mt-4 text-center text-xs text-muted-foreground">
          © {new Date().getFullYear()} Rio Futuro · Dashboard v1.0
        </p>
      </div>
    </div>
  )
}

export default LoginForm
