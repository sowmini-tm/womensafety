import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import {
  Bell,
  CheckCircle2,
  Home,
  MapPin,
  Navigation,
  Shield,
  User,
  X,
} from 'lucide-react'

/* ------------------------------------------------------------------ */
/* Toast system                                                        */
/* ------------------------------------------------------------------ */

type ToastType = 'success' | 'error' | 'info'
type Toast = { id: number; type: ToastType; message: string }

const ToastContext = createContext<{
  notify: (message: string, type?: ToastType) => void
}>({ notify: () => {} })

export const useToast = () => useContext(ToastContext)

/* ------------------------------------------------------------------ */
/* Navigation                                                          */
/* ------------------------------------------------------------------ */

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Home', icon: Home },
  { to: '/live-tracking', label: 'Tracking', icon: MapPin },
  { to: '/profile', label: 'Profile', icon: User },
]


/* ------------------------------------------------------------------ */
/* AppShell                                                            */
/* ------------------------------------------------------------------ */

export default function AppShell({ children, title }: { children: React.ReactNode; title?: string }) {
  const location = useLocation()
  const navigate = useNavigate()
  const [toasts, setToasts] = useState<Toast[]>([])
  const toastId = useRef(0)
  const [userName, setUserName] = useState<string | null>(null)

  const notify = useCallback((message: string, type: ToastType = 'info') => {
    const id = ++toastId.current
    setToasts((prev) => [...prev, { id, type, message }])
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, 4500)
  }, [])

  const dismissToast = (id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }

  useEffect(() => {
    // Lightweight greeting: fetch the user's profile name if available.
    let active = true
    try {
      const token = localStorage.getItem('access_token')
      if (!token) return
      fetch(`${import.meta.env.VITE_API_BASE_URL ?? ''}/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (active && data?.full_name) setUserName(data.full_name)
        })
        .catch(() => {
          /* ignore — greeting is cosmetic */
        })
    } catch {
      /* ignore */
    }
    return () => {
      active = false
    }
  }, [])

  const pageTitle = title ?? 'Safety Hub'
  const currentPath = location.pathname

  return (
    <ToastContext.Provider value={{ notify }}>
      <div className="min-h-screen bg-slate-950 text-slate-100">
        {/* ---------- Top app bar ---------- */}
        <header className="sticky top-0 z-30 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
            <button
              onClick={() => navigate('/dashboard')}
              className="flex items-center gap-2 rounded-lg focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-400"
            >
              <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-pink-600 text-white">
                <Shield className="h-5 w-5" />
              </span>
              <span className="text-left leading-tight">
                <span className="block text-sm font-semibold">SafeGuard</span>
                <span className="hidden text-[10px] uppercase tracking-[0.2em] text-slate-400 sm:block">
                  Women safety
                </span>
              </span>
            </button>

            <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
              {NAV_ITEMS.map((item) => (
                <button
                  key={item.to}
                  onClick={() => navigate(item.to)}
                  aria-current={currentPath === item.to ? 'page' : undefined}
                  className={`flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-400 ${
                    currentPath === item.to
                      ? 'bg-slate-800 text-white'
                      : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                  }`}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </button>
              ))}
            </nav>

            <div className="flex items-center gap-2">
              <button
                onClick={() => navigate('/live-tracking')}
                className="rounded-full bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400"
              >
                <span className="hidden sm:inline">Live tracking</span>
                <span className="sm:hidden">
                  <MapPin className="h-4 w-4" />
                </span>
              </button>
              <button
                onClick={() => logoutAndRedirect(navigate)}
                title="Log out"
                className="rounded-full bg-slate-800 px-3 py-2 text-sm text-slate-200 hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-400"
              >
                Log out
              </button>
            </div>
          </div>
                </header>

        {/* ---------- Main content ---------- */}
        <main className="mx-auto max-w-7xl px-4 pb-24 pt-5 sm:px-6 md:pb-10">
          <div className="mb-5">
            <h1 className="text-2xl font-semibold tracking-tight">{pageTitle}</h1>
            {userName && <p className="mt-1 text-sm text-slate-400">Welcome back, {userName}.</p>}
          </div>
          {children}
        </main>

        {/* ---------- Mobile bottom navigation ---------- */}
        <nav
          className="fixed inset-x-0 bottom-0 z-30 border-t border-slate-800 bg-slate-950/95 backdrop-blur md:hidden"
          aria-label="Bottom navigation"
        >
          <div className="grid grid-cols-3">
            {NAV_ITEMS.map((item) => (
              <button
                key={item.to}
                onClick={() => navigate(item.to)}
                aria-current={currentPath === item.to ? 'page' : undefined}
                className={`flex flex-col items-center gap-1 py-2.5 text-[10px] font-medium focus:outline-none focus-visible:bg-slate-800 ${
                  currentPath === item.to ? 'text-pink-300' : 'text-slate-400'
                }`}
              >
                <item.icon className="h-5 w-5" />
                {item.label}
              </button>
            ))}
          </div>
        </nav>

        {/* ---------- Toasts ---------- */}
        <div
          className="pointer-events-none fixed inset-x-0 top-16 z-50 flex flex-col items-center gap-2 px-4 sm:left-auto sm:right-4 sm:items-end"
          role="status"
          aria-live="polite"
        >
          {toasts.map((toast) => (
            <div
              key={toast.id}
              className={`pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-lg backdrop-blur ${
                toast.type === 'success'
                  ? 'border-emerald-600/50 bg-emerald-950/90 text-emerald-50'
                  : toast.type === 'error'
                    ? 'border-rose-600/50 bg-rose-950/90 text-rose-50'
                    : 'border-slate-600 bg-slate-900/95 text-slate-50'
              }`}
            >
              {toast.type === 'success' ? (
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
              ) : (
                <Bell className="mt-0.5 h-4 w-4 shrink-0 text-slate-300" />
              )}
              <span className="flex-1">{toast.message}</span>
              <button
                onClick={() => dismissToast(toast.id)}
                aria-label="Dismiss notification"
                className="rounded p-0.5 text-slate-300 hover:text-white focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
            </div>
    </ToastContext.Provider>
  )
}

/** Shared logout: used by the app bar and profile page. */
export function logoutAndRedirect(navigate: ReturnType<typeof useNavigate>) {
  try {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
  } catch {
    // ignore storage errors
  }
  navigate('/login', { replace: true })
}

