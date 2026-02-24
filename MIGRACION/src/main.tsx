import React from 'react'
import ReactDOM from 'react-dom/client'
import { Toaster } from 'react-hot-toast'
import App from './App'
import { QueryProvider } from './providers/QueryProvider'
import { AuthProvider } from './providers/AuthProvider'
import './styles/globals.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryProvider>
      <AuthProvider>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 4000,
            style: {
              background: 'hsl(222.2 84% 4.9%)',
              color: 'hsl(210 40% 98%)',
              border: '1px solid hsl(217.2 32.6% 17.5%)',
              borderRadius: '0.5rem',
            },
          }}
        />
      </AuthProvider>
    </QueryProvider>
  </React.StrictMode>,
)
