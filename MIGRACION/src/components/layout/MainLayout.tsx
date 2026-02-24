import { Outlet } from 'react-router-dom'
import { useState } from 'react'
import { Sidebar } from './Sidebar'
import { Header } from './Header'
import { cn } from '@/lib/utils'

export function MainLayout() {
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false)

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Mobile sidebar overlay */}
      {mobileSidebarOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={() => setMobileSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <Sidebar
        isOpen={sidebarOpen}
        mobileOpen={mobileSidebarOpen}
        onMobileClose={() => setMobileSidebarOpen(false)}
      />

      {/* Main content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        <Header
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          onToggleMobileSidebar={() => setMobileSidebarOpen(!mobileSidebarOpen)}
        />
        <main className="flex-1 overflow-auto p-4 md:p-6">
          <div className={cn('mx-auto max-w-[1600px] animate-fade-in')}>
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  )
}
