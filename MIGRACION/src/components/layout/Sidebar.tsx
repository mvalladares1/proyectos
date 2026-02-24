import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard, Truck, Factory, Package, Warehouse,
  ShoppingCart, BarChart2, TrendingUp, ShoppingBag,
  Handshake, RefreshCw, Bot, Shield, X, ChevronLeft,
} from 'lucide-react'
import { cn } from '@/lib/utils'
import { NAV_ITEMS } from '@/lib/constants'
import { usePermissions } from '@/hooks/usePermissions'
import { useAuthContext } from '@/providers/AuthProvider'

const ICON_MAP: Record<string, React.ElementType> = {
  LayoutDashboard, Truck, Factory, Package, Warehouse,
  ShoppingCart, BarChart2, TrendingUp, ShoppingBag,
  Handshake, RefreshCw, Bot, Shield,
}

interface SidebarProps {
  isOpen: boolean
  mobileOpen: boolean
  onMobileClose: () => void
}

export function Sidebar({ isOpen, mobileOpen, onMobileClose }: SidebarProps) {
  const location = useLocation()
  const { canAccess } = usePermissions()
  const { user } = useAuthContext()

  const visibleItems = NAV_ITEMS.filter((item) => {
    if (item.adminOnly && !user?.is_admin) return false
    return true
  })

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          'hidden lg:flex flex-col border-r bg-card transition-all duration-300 shrink-0',
          isOpen ? 'w-60' : 'w-16',
        )}
      >
        <SidebarContent isOpen={isOpen} items={visibleItems} canAccess={canAccess} location={location.pathname} />
      </aside>

      {/* Mobile sidebar drawer */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r bg-card transition-transform duration-300 lg:hidden',
          mobileOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="flex h-14 items-center justify-between border-b px-4">
          <span className="font-semibold">Rio Futuro</span>
          <button onClick={onMobileClose} className="rounded-md p-1 hover:bg-muted">
            <X className="h-5 w-5" />
          </button>
        </div>
        <SidebarContent isOpen={true} items={visibleItems} canAccess={canAccess} location={location.pathname} />
      </aside>
    </>
  )
}

interface SidebarContentProps {
  isOpen: boolean
  items: typeof NAV_ITEMS[number][]
  canAccess: (dashboard: string) => boolean
  location: string
}

function SidebarContent({ isOpen, items, canAccess, location }: SidebarContentProps) {
  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      {/* Logo */}
      <div className="flex h-14 items-center border-b px-4">
        {isOpen ? (
          <div className="flex items-center gap-2">
            <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-xs font-bold text-primary-foreground">RF</span>
            </div>
            <span className="font-semibold text-sm">Rio Futuro</span>
          </div>
        ) : (
          <div className="h-7 w-7 rounded-lg bg-primary flex items-center justify-center mx-auto">
            <span className="text-xs font-bold text-primary-foreground">RF</span>
          </div>
        )}
      </div>

      {/* Nav links */}
      <nav className="flex-1 overflow-y-auto py-3 scrollbar-none">
        <ul className="space-y-0.5 px-2">
          {items.map((item) => {
            const Icon = ICON_MAP[item.icon] ?? LayoutDashboard
            const accessible = canAccess(item.dashboard)
            const isActive = location === item.path || (item.path !== '/' && location.startsWith(item.path))

            return (
              <li key={item.path}>
                <NavLink
                  to={accessible ? item.path : '#'}
                  className={cn(
                    'flex items-center gap-3 rounded-md px-2 py-2 text-sm transition-colors',
                    isActive
                      ? 'bg-primary/10 text-primary font-medium'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                    !accessible && 'opacity-40 cursor-not-allowed',
                  )}
                  title={!isOpen ? item.label : undefined}
                >
                  <Icon className="h-4 w-4 shrink-0" />
                  {isOpen && <span>{item.label}</span>}
                </NavLink>
              </li>
            )
          })}
        </ul>
      </nav>
    </div>
  )
}
