import React, { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  createLocation,
  fetchEmergencyContacts,
  fetchSharingStatus,
  startLocationSharing,
  stopLocationSharing,
} from '../api/safety'
import RouteMap from '../components/RouteMap'
import AppShell, { useToast } from '../components/AppShell'
import { getErrorMessage } from '../utils/errors'
import { Card, EmptyState, InlineAlert, Spinner, StatusBadge, Button, SectionTitle, inputClass } from '../components/ui'
import { MapPin, Navigation, Share2, Square, Play } from 'lucide-react'

// Upload roughly every 7 seconds while still receiving watchPosition updates.
const UPLOAD_INTERVAL_MS = 7000

type TrackedPosition = {
  latitude: number
  longitude: number
  accuracy: number | null
  speed: number | null
  at: number
}

type ShareSession = {
  id: string
  is_active: boolean
  share_token?: string | null
  started_at?: string | null
  stopped_at?: string | null
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
  const { notify } = useToast()
  const navigate = useNavigate()
  const [contacts, setContacts] = useState<any[]>([])
  const [sharing, setSharing] = useState(false)
  const [position, setPosition] = useState<TrackedPosition | null>(null)
  const [lastSavedAt, setLastSavedAt] = useState<number | null>(null)
  const [geoError, setGeoError] = useState<string | null>(null)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [geoEvents, setGeoEvents] = useState<Array<{ geofence_id: string; geofence_name: string; event_type: string; distance_meters: number }>>([])
  const [shareSession, setShareSession] = useState<ShareSession | null>(null)
  const [sessionError, setSessionError] = useState<string | null>(null)
  const [showToken, setShowToken] = useState(false)
  const [copied, setCopied] = useState(false)

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

  // Restore server-side sharing state so the UI reflects reality after reloads.
  useEffect(() => {
    const loadStatus = async () => {
      try {
        setShareSession(await fetchSharingStatus())
      } catch {
        // No sessions yet (or backend unreachable) — treat as not sharing.
      }
    }
    void loadStatus()
  }, [])

  const shareLink = shareSession?.share_token
    ? `${window.location.origin}/shared-location/${shareSession.share_token}`
    : null

  const copyShareLink = async () => {
    if (!shareLink) return
    try {
      await navigator.clipboard.writeText(shareLink)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 2500)
    } catch {
      setCopied(false)
    }
  }

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

  const stopSharing = async () => {
    if (watchIdRef.current !== null && 'geolocation' in navigator) {
      navigator.geolocation.clearWatch(watchIdRef.current)
    }
    watchIdRef.current = null
    setSharing(false)
    setShowToken(false)
        try {
      // Deactivate the server-side session so the contact link stops working.
      await stopLocationSharing()
      setShareSession((prev) => (prev ? { ...prev, is_active: false, stopped_at: new Date().toISOString() } : prev))
      setSessionError(null)
      notify('Live location sharing stopped.', 'success')
    } catch (e: any) {
      const msg = getErrorMessage(e, 'Position tracking stopped locally, but the sharing session could not be stopped on the server.')
      setSessionError(msg)
      notify(msg, 'error')
    }
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
      .then((saved) => {
        setLastSavedAt(Date.now())
        setUploadError(null)
        // Surface real geofence entry/exit transitions reported by the backend.
        const events = Array.isArray(saved?.geofence_events) ? saved.geofence_events : []
        if (events.length > 0) setGeoEvents(events)
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
    setSessionError(null)

    // Create the secure server-side sharing session first; GPS watching starts
    // only once the backend confirms the session is active.
    startLocationSharing()
      .then((session) => {
        setShareSession(session)
        setSharing(true)
        setShowToken(true)
        lastUploadRef.current = 0

        // One immediate fix plus the continuous watcher; both funnel through
        // handlePosition, and the throttle keeps the double callback from
        // creating a duplicate record.
        navigator.geolocation.getCurrentPosition(handlePosition, handleGeoError, {
          enableHighAccuracy: true,
          timeout: 15000,
        })
        watchIdRef.current = navigator.geolocation.watchPosition(handlePosition, handleGeoError, {
          enableHighAccuracy: true,
          maximumAge: 5000,
          timeout: 20000,
        })
      })
            .catch((e: any) => {
        const msg = getErrorMessage(e, 'Could not start the secure sharing session. Please try again.')
        setSessionError(msg)
        notify(msg, 'error')
      })
  }

    return (
    <AppShell title="Live Tracking & Sharing">
            <div className="mb-6 flex items-center justify-between gap-4">
        <div>
          <p className="text-sm text-slate-400">{sharing ? 'Tracking is on' : 'Tracking is off'}</p>
        </div>
        <div className="flex items-center gap-3">
          {sharing ? (
            <Button variant="danger" className="h-9" onClick={stopSharing}>
              <Square className="h-4 w-4" /> Stop sharing
            </Button>
          ) : (
            <Button variant="success" className="h-9" onClick={startSharing}>
              <Play className="h-4 w-4" /> Start sharing
            </Button>
          )}
        </div>
      </div>

        {geoError && (
          <div className="mb-4 rounded-2xl border border-rose-700/60 bg-rose-950/40 px-4 py-3 text-sm text-rose-200" role="alert">
            {geoError}
          </div>
        )}

        {sessionError && (
          <div className="mb-4 rounded-2xl border border-amber-700/60 bg-amber-950/40 px-4 py-3 text-sm text-amber-200" role="alert">
            {sessionError}
          </div>
        )}

        {geoEvents.length > 0 && (
          <div className="mb-4 rounded-2xl border border-cyan-700/60 bg-cyan-950/40 px-4 py-3 text-sm text-cyan-100" role="status">
            <p className="text-xs uppercase tracking-[0.2em] text-cyan-300">Geofence activity</p>
            <ul className="mt-2 space-y-1">
              {geoEvents.map((event) => (
                <li key={`${event.geofence_id}-${event.event_type}`}>
                  {event.event_type === 'ENTERED' ? 'Entered' : 'Left'}{' '}
                  <span className="font-medium text-slate-100">{event.geofence_name}</span>{' '}
                  ({Math.round(event.distance_meters)} m from center)
                </li>
              ))}
            </ul>
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
              <RouteMap
                className="h-[420px] w-full"
                userPosition={position ? [position.latitude, position.longitude] : null}
              />
              <div className="pointer-events-none absolute bottom-4 left-4 rounded-2xl bg-slate-950/80 px-4 py-3">
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
                  <p className={`mt-2 text-xl font-semibold ${sharing || shareSession?.is_active ? 'text-emerald-300' : 'text-slate-300'}`}>
                    {sharing || shareSession?.is_active ? 'Live' : 'Paused'}
                  </p>
                  {shareSession && (
                    <p className="mt-1 text-xs text-slate-400">
                      {shareSession.is_active ? 'Contacts can view your location' : 'Sharing session stopped'}
                    </p>
                  )}
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

              {shareSession?.is_active && shareLink && (
                <div className="mt-4 rounded-2xl border border-emerald-800/60 bg-emerald-950/30 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-emerald-300">Emergency contact link</p>
                  <p className="mt-2 break-all text-xs text-slate-300">
                    Anyone with this secure link can see your live position while sharing is active. Stop sharing to revoke it instantly.
                  </p>
                  {showToken ? (
                    <div className="mt-2 space-y-2">
                      <code className="block max-h-20 overflow-y-auto break-all rounded-xl bg-slate-950/70 p-2 text-[11px] text-emerald-200">{shareLink}</code>
                      <div className="flex flex-wrap gap-2">
                        <button onClick={copyShareLink} className="rounded-full bg-cyan-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-cyan-500">
                          {copied ? 'Copied!' : 'Copy link'}
                        </button>
                        <button onClick={() => setShowToken(false)} className="rounded-full border border-slate-600 px-3 py-1.5 text-xs font-medium text-slate-200 hover:border-slate-400">
                          Hide
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button onClick={() => setShowToken(true)} className="mt-2 rounded-full border border-emerald-600 px-3 py-1.5 text-xs font-medium text-emerald-200 hover:border-emerald-400">
                      Show secure contact link
                    </button>
                  )}
                </div>
              )}
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
                      <span className="rounded-full bg-slate-700 px-3 py-1.5 text-xs font-medium text-slate-300">
                        {contact.is_primary ? '★ Primary' : 'On alert list'}
                      </span>
                    </div>
                  ))
                )}
                <button
                  onClick={() => navigate('/dashboard')}
                  className="w-full rounded-2xl bg-cyan-600 px-3 py-2 text-sm font-medium text-white hover:bg-cyan-500"
                >
                  Alert contacts with SOS — open Dashboard
                </button>
              </div>
            </div>
          </div>
              </section>
        </AppShell>
    )
}
