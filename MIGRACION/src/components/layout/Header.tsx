import { Menu, LogOut, User, ChevronDown } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/hooks/useAuth'
import { useAuthContext } from '@/providers/AuthProvider'
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem,
  DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger,
} from './DropdownMenu'

interface HeaderProps {
  onToggleSidebar: () => void
  onToggleMobileSidebar: () => void
}

export function Header({ onToggleSidebar, onToggleMobileSidebar }: HeaderProps) {
  const { user } = useAuthContext()
  const { logout } = useAuth()

  return (
    <header className="flex h-14 shrink-0 items-center border-b bg-card px-4 gap-3">
      {/* Desktop sidebar toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="hidden lg:flex"
        onClick={onToggleSidebar}
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Mobile sidebar toggle */}
      <Button
        variant="ghost"
        size="icon"
        className="lg:hidden"
        onClick={onToggleMobileSidebar}
      >
        <Menu className="h-5 w-5" />
      </Button>

      {/* Spacer */}
      <div className="flex-1" />

      {/* User menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="flex items-center gap-2 h-9 px-3">
            <div className="flex h-7 w-7 items-center justify-center rounded-full bg-primary/20 text-primary">
              <User className="h-4 w-4" />
            </div>
            <span className="hidden text-sm font-medium md:block">{user?.name ?? 'Usuario'}</span>
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-48">
          <DropdownMenuLabel>
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium">{user?.name}</p>
              <p className="text-xs text-muted-foreground">{user?.email}</p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={logout} className="text-destructive focus:text-destructive">
            <LogOut className="mr-2 h-4 w-4" />
            Cerrar sesión
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  )
}
