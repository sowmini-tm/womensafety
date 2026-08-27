import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'
import RouteMap from '../components/RouteMap'

// Refresh shared location every 7 seconds while the session is active.
const REFRESH_INTERVAL_MS = 7000

type SharedLocation = {
  latitude: number
  longitude: number
  accuracy: number | null
  speed: number | null
  timestamp: string | null
  session_status: string
}

type ViewerState =
  | { status: 'loading' }
  | { status: 'live'; data: SharedLocation }
  | { status: 'unavailable' }

// Plain axios instance WITHOUT the shared client interceptors: the share token
// in the URL is the only authorization this contact needs, so no JWT should
// ever be attached to (or embedded in) these requests.
const sharedApi = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '',
  headers: { 'Content-Type': 'application/json' },
})

const sharedLocationUrl = (token: string) =>
  `/safety/shared-location/${encodeURIComponent(token)}`

export default function SharedLocation() {
  const { token = '' } = useParams<{ token: string }>()
  const [viewer, setViewer] = useState<ViewerState>({ status: 'loading' })
  const activeRef = useRef(true)

  const fetchOnce = async () => {
    if (!token || !activeRef.current) return
    try {
      const response = await sharedApi.get<SharedLocation>(sharedLocationUrl(token))
      if (!activeRef.current) return
      setViewer({ status: 'live', data: response.data })
    } catch {
      if (activeRef.current) setViewer({ status: 'unavailable' })
    }
  }

  useEffect(() => {
    activeRef.current = true
    setViewer({ status: 'loading' })
    void fetchOnce()
    return () => {
      activeRef.current = false
    }
    // token captured on mount; changing it remounts via route
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  // Single polling interval, guarded by activeRef so it stops on unmount and
  // once the session is unavailable.
  useEffect(() => {
    if (!activeRef.current) return
    const interval = window.setInterval(() => {
      void fetchOnce()
    }, REFRESH_INTERVAL_MS)
    return () => {
      window.clearInterval(interval)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  if (viewer.status === 'loading') {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <div className="mx-auto max-w-3xl px-4 py-10 text-center">
          <p className="text-sm uppercase tracking-[0.3em] text-cyan-300">Shared live location</p>
          <h1 className="mt-3 text-2xl font-semibold">Loading live location…</h1>
          <p className="mt-2 text-slate-400">Please wait while we verify the secure link.</p>
        </div>
      </div>
    )
  }

  if (viewer.status === 'unavailable') {
    return (
      <div className="min-h-screen bg-slate-950 text-slate-100">
        <div className="mx-auto max-w-3xl px-4 py-10">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-8 text-center">
            <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-slate-800 text-2xl">🛡️</div>
            <h1 className="mt-4 text-2xl font-semibold">Shared location is no longer available.</h1>
            <p className="mt-3 text-slate-400">
              This may happen because the person sharing their location stopped the session, or the secure link expired.
            </p>
          </div>
        </div>
      </div>
    )
  }

  const { data } = viewer
  const position: [number, number] = [data.latitude, data.longitude]
  const lastUpdated = data.timestamp ? new Date(data.timestamp).toLocaleString() : 'Unknown'

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-3xl px-4 py-8 sm:px-6">
        <header className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5 sm:p-6">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Trusted contact view</p>
              <h1 className="mt-2 text-2xl font-semibold">Shared Live Location</h1>
            </div>
            <span className="inline-flex items-center gap-2 self-start rounded-full bg-slate-950/80 px-3 py-1.5 text-xs font-medium text-emerald-300">
              <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" />
              {data.session_status === 'active' ? 'Live · updating automatically' : 'Session ended'}
            </span>
          </div>
          <p className="mt-3 text-sm text-slate-400">
            This location may update automatically while the person is sharing it.
          </p>
        </header>

        <section className="mt-6 overflow-hidden rounded-3xl border border-slate-800">
          <RouteMap className="h-[380px] w-full sm:h-[440px]" userPosition={position} />
        </section>

        <section className="mt-6 rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
          <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Current position</p>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <div className="rounded-2xl bg-slate-800 p-3">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Coordinates</p>
              <p className="mt-2 font-mono text-sm text-slate-100">
                {data.latitude.toFixed(5)}, {data.longitude.toFixed(5)}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-800 p-3">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">GPS accuracy</p>
              <p className="mt-2 text-sm text-slate-100">
                {data.accuracy != null ? `±${Math.round(data.accuracy)} m` : 'Not available'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-800 p-3">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Speed</p>
              <p className="mt-2 text-sm text-slate-100">
                {data.speed != null ? `${(data.speed * 3.6).toFixed(1)} km/h` : 'Not available'}
              </p>
            </div>
            <div className="rounded-2xl bg-slate-800 p-3">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Last updated</p>
              <p className="mt-2 text-sm text-slate-100">{lastUpdated}</p>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}