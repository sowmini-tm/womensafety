import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createLocation, fetchEmergencyContacts } from '../api/safety'

// Upload roughly every 7 seconds while still receiving watchPosition updates.
const UPLOAD_INTERVAL_MS = 7000

type TrackedPosition = {
  latitude: number
  longitude: number
  accuracy: number | null
  speed: number | null
  at: number
}

const describeGeolocationError = (error: GeolocationPositionError): string => {
  switch (error.code) {
    case error.PERMISSION_DENIED:
      return 'Permission denied — allow location access for this site to share your live position.'
    case error.POSITION_UNAVAILABLE:
      return 'Your device could not determine its position. Keeping the watcher active.'
    case error.TIMEOUT:
      return 'Timed out waiting for a GPS fix. Retrying…'
    default:
      return 'Unexpected geolocation error while tracking your position.'
  }
}

export default function LiveTracking() {
  const navigate = useNavigate()
  const [contacts, setContacts] = useState<any[]>([])
  const [sharing, setSharing] = useState(false)
  const [position, setPosition] = useState<TrackedPosition | null>(null)
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null)
  const [geoError, setGeoError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)

  const watchIdRef = useRef<number | null>(null)
  const lastUploadRef = useRef(0)

  useEffect(() => {
    const load = async () => {
      try {
        setContacts(await fetchEmergencyContacts())
      } catch {
        // ignore missing backend data in local demo mode
      }
    }

    void load()
  }, [])

  // Clear any active watcher when navigating away.
  useEffect(
    () => () => {
      if (watchIdRef.current !== null && typeof navigator !== 'undefined' && 'geolocation' in navigator) {
        navigator.geolocation.clearWatch(watchIdRef.current)
        watchIdRef.current = null
      }
    },
    [],
  )

  const stopSharing = () => {
    if (watchIdRef.current !== null && 'geolocation' in navigator) {
      navigator.geolocation.clearWatch(watchIdRef.current)
    }
    watchIdRef.current = null
    setSharing(false)
  }

  const handlePosition = (pos: GeolocationPosition) => {
    const tracked: TrackedPosition = {
      latitude: pos.coords.latitude,
      longitude: pos.coords.longitude,
      accuracy: Number.isFinite(pos.coords.accuracy) ? pos.coords.accuracy : null,
      speed: pos.coords.speed != null && Number.isFinite(pos.coords.speed) ? pos.coords.speed : null,
      at: pos.timestamp || Date.now(),
    }
    setGeoError(null)
    setPosition(tracked)

    // Throttled upload; the very first fix is sent immediately via lastUploadRef reset.
    const now = Date.now()
    if (now - lastUploadRef.current < UPLOAD_INTERVAL_MS) return
    lastUploadRef.current = now
    createLocation({
      latitude: tracked.latitude,
      longitude: tracked.longitude,
      accuracy: tracked.accuracy ?? undefined,
      speed: tracked.speed ?? undefined,
    })
      .then(() => {
        setLastSavedAt(Date.now())
        setUploadError(null)
      })
      .catch(() => {
        setUploadError('Could not save the last position to the server. Will retry on the next update.')
      })
  }

  const handleGeoError = (error: GeolocationPositionError) => {
    setGeoError(describeGeolocationError(error))
    if (error.code === error.PERMISSION_DENIED) {
      // Denial keeps firing on the watcher; stop cleanly instead of spamming errors.
      stopSharing()
    }
  }

  const startSharing = () => {
    if (!('geolocation' in navigator)) {
      setGeoError('Geolocation is not supported by this browser.')
      return
    }
    if (watchIdRef.current !== null) return // already watching — never spawn duplicate watchers

    setGeoError(null)
    setSharing(true)
    lastUploadRef.current = 0

    // One immediate fix plus the continuous watcher; both funnel through handlePosition,
    // and the throttle keeps the double callback from creating a duplicate record.
    navigator.geolocation.getCurrentPosition(handlePosition, handleGeoError, {
      enableHighAccuracy: true,
      timeout: 15000,
    })
    watchIdRef.current = navigator.geolocation.watchPosition(handlePosition, handleGeoError, {
      enableHighAccuracy: true,
      maximumAge: 5000,
      timeout: 20000,
    })
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/80 p-5 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-cyan-300">Live tracking</p>
            <h1 className="mt-2 text-3xl font-semibold">Location sharing</h1>
          </div>
          <div className="flex gap-3">
            <button onClick={() => navigate('/dashboard')} className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">Dashboard</button>
            {sharing ? (
              <button onClick={stopSharing} className="rounded-full bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500">Stop sharing</button>
            ) : (
              <button onClick={startSharing} className="rounded-full bg-emerald-600 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-500">Start sharing</button>
            )}
          </div>
        </header>

        {geoError && (
          <div className="mb-4 rounded-2xl border border-rose-700/60 bg-rose-950/40 px-4 py-3 text-sm text-rose-200" role="alert">
            {geoError}
          </div>
        )}

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Active route</p>
              <span className={`rounded-full px-2 py-1 text-[10px] uppercase tracking-[0.2em] ${sharing ? 'bg-emerald-500/10 text-emerald-300' : 'bg-slate-700 text-slate-300'}`}>
                {sharing ? 'sharing' : 'paused'}
              </span>
            </div>

            <div className="relative h-[420px] overflow-hidden rounded-3xl border border-slate-700 bg-gradient-to-br from-slate-800 via-slate-900 to-indigo-950">
              <div className="absolute inset-0 opacity-30" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)', backgroundSize: '24px 24px' }} />
              <div className={`absolute inset-x-10 bottom-10 rounded-full border border-dashed transition-all duration-500 ${sharing ? 'h-48 border-emerald-400/60' : 'h-32 border-slate-500/40'}`} />
              <div className="absolute bottom-4 left-4 rounded-2xl bg-slate-950/80 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Current position</p>
                <p className="mt-2 text-lg font-medium text-slate-100">
                  {position
                    ? `${position.latitude.toFixed(5)}, ${position.longitude.toFixed(5)}`
                    : sharing
                      ? 'Acquiring GPS fix…'
                      : 'Start sharing to track your live position'}
                </p>
                {position?.accuracy != null && (
                  <p className="mt-1 text-xs text-slate-300">
                    Accuracy ±{Math.round(position.accuracy)} m
                    {position.speed != null ? ` · ${(position.speed * 3.6).toFixed(1)} km/h` : ''}
                  </p>
                )}
              </div>
              {sharing && (
                <span className="absolute right-4 top-4 flex items-center gap-2 rounded-full bg-slate-950/80 px-3 py-1 text-xs font-medium text-emerald-300">
                  <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-400" /> live
                </span>
              )}
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Session</p>
              <div className="mt-4 grid gap-3">
                <div className="rounded-2xl bg-slate-800 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Status</p>
                  <p className={`mt-2 text-xl font-semibold ${sharing ? 'text-emerald-300' : 'text-slate-300'}`}>{sharing ? 'Live' : 'Paused'}</p>
                </div>
                <div className="rounded-2xl bg-slate-800 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Updated</p>
                  <p className="mt-2 text-base text-slate-100">
                    {position
                      ? new Date(position.at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                      : 'Waiting for location'}
                  </p>
                </div>
                <div className="rounded-2xl bg-slate-800 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Last saved to server</p>
                  <p className="mt-2 text-base text-slate-100">{lastSavedAt ? new Date(lastSavedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : 'Not yet'}</p>
                  {uploadError && <p className="mt-2 text-xs text-amber-300">{uploadError}</p>}
                </div>
              </div>
            </div>

            <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Trusted circle</p>
              <div className="mt-4 space-y-3">
                {contacts.length === 0 ? (
                  <p className="text-slate-300">No trusted contacts added yet.</p>
                ) : (
                  contacts.map((contact) => (
                    <div key={contact.id} className="flex items-center justify-between rounded-2xl bg-slate-800 px-3 py-2">
                      <div>
                        <p className="font-medium text-slate-100">{contact.name}</p>
                        <p className="text-sm text-slate-300">{contact.phone}</p>
                      </div>
                      <button className="rounded-full bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-500">Notify</button>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}
