import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createEmergencyContact, createLocation, deleteEmergencyContact, fetchEmergencyContacts, fetchLocations, scheduleFakeCall, triggerSOS, updateEmergencyContact } from '../api/safety'
import { createGeofence, createRoutePlan, deleteGeofence, fetchGeofences, fetchNotifications, fetchSafetyActivity, updateGeofence } from '../api/safetyExtra'

export default function Dashboard() {
  const navigate = useNavigate()
  const [contacts, setContacts] = useState<any[]>([])
  const [locations, setLocations] = useState<any[]>([])
  const [geofences, setGeofences] = useState<any[]>([])
  const [status, setStatus] = useState('Ready')
  const [helplines, setHelplines] = useState<any[]>([])
  const [chatbotReply, setChatbotReply] = useState('Ask for safety guidance or route help.')
  const [routeResult, setRouteResult] = useState<any>(null)
  const [activity, setActivity] = useState<any[]>([])
  const [notifications, setNotifications] = useState<any[]>([])
  const [contactForm, setContactForm] = useState({ name: '', phone: '', email: '', relationship_type: 'Friend', is_primary: false })
  const [editingContactId, setEditingContactId] = useState<string | null>(null)
  const [geofenceForm, setGeofenceForm] = useState({ name: '', latitude: '', longitude: '', radius: '' })
  const [editingGeofenceId, setEditingGeofenceId] = useState<string | null>(null)

  const resetContactForm = () => {
    setContactForm({ name: '', phone: '', email: '', relationship_type: 'Friend', is_primary: false })
    setEditingContactId(null)
  }

  const resetGeofenceForm = () => {
    setGeofenceForm({ name: '', latitude: '', longitude: '', radius: '' })
    setEditingGeofenceId(null)
  }

  useEffect(() => {
    void loadData()
  }, [])

  const loadData = async () => {
    try {
      const [contactList, locationList, geofenceList, activityList, notificationList] = await Promise.all([
        fetchEmergencyContacts(),
        fetchLocations(),
        fetchGeofences().catch(() => []),
        fetchSafetyActivity().catch(() => []),
        fetchNotifications().catch(() => []),
      ])
      setContacts(contactList)
      setLocations(locationList)
      setGeofences(geofenceList)
      setActivity(activityList)
      setNotifications(notificationList)
      setHelplines([
        { name: 'National Women Helpline', number: '1091', type: 'women_safety' },
        { name: 'Police Emergency', number: '112', type: 'police' },
        { name: 'Women in Distress', number: '181', type: 'women_safety' },
      ])
    } catch {
      setStatus('Not authenticated or backend unavailable')
    }
  }

  const handleLocation = async () => {
    if (!navigator.geolocation) {
      setStatus('Geolocation is not supported in this browser')
      return
    }

    navigator.geolocation.getCurrentPosition(async (position) => {
      try {
        const payload = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          accuracy: position.coords.accuracy,
          speed: position.coords.speed ?? 0,
        }
        await createLocation(payload)
        setStatus('Location saved successfully')
        await loadData()
      } catch {
        setStatus('Location save failed')
      }
    }, () => setStatus('Location permission denied'))
  }

  const handleSOS = async () => {
    if (!navigator.geolocation) {
      setStatus('Geolocation is not supported in this browser - SOS not sent')
      return
    }

    navigator.geolocation.getCurrentPosition(
      async (position) => {
        try {
          const payload = {
            latitude: position.coords.latitude,
            longitude: position.coords.longitude,
            description: 'SOS triggered from dashboard',
          }
          const response = await triggerSOS(payload)
          setStatus(`SOS triggered at your current location: ${response.id}`)
        } catch {
          setStatus('SOS trigger failed')
        }
      },
      (error) => {
        if (error.code === error.PERMISSION_DENIED) {
          setStatus('Location permission denied - SOS was NOT sent. Enable location access and try again.')
        } else {
          setStatus('Could not determine your current location - SOS was NOT sent.')
        }
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 0 },
    )
  }

  const handleFakeCall = async () => {
    try {
      const response = await scheduleFakeCall({
        caller_name: 'Trusted Contact',
        caller_number: '+15551234567',
        delay_seconds: 10,
      })
      setStatus(`Fake call scheduled: ${response.id}`)
    } catch {
      setStatus('Fake call scheduling failed')
    }
  }

  const handleContactSubmit = async () => {
    if (!contactForm.name.trim() || !contactForm.phone.trim()) {
      setStatus('Contact name and phone are required')
      return
    }
    try {
      const payload = {
        name: contactForm.name.trim(),
        phone: contactForm.phone.trim(),
        email: contactForm.email.trim() || undefined,
        relationship_type: contactForm.relationship_type.trim() || undefined,
        is_primary: contactForm.is_primary,
      }
      if (editingContactId) {
        await updateEmergencyContact(editingContactId, payload)
        setStatus('Emergency contact updated')
      } else {
        await createEmergencyContact(payload)
        setStatus('Emergency contact added')
      }
      resetContactForm()
      await loadData()
    } catch {
      setStatus(editingContactId ? 'Emergency contact update failed' : 'Emergency contact creation failed')
    }
  }

  const handleContactEdit = (contact: any) => {
    setEditingContactId(contact.id)
    setContactForm({
      name: contact.name ?? '',
      phone: contact.phone ?? '',
      email: contact.email ?? '',
      relationship_type: contact.relationship_type ?? '',
      is_primary: Boolean(contact.is_primary),
    })
  }

  const handleContactDelete = async (id: string) => {
    try {
      await deleteEmergencyContact(id)
      setStatus('Emergency contact deleted')
      if (editingContactId === id) resetContactForm()
      await loadData()
    } catch {
      setStatus('Emergency contact deletion failed')
    }
  }

  const handleGeofenceSubmit = async () => {
    if (!geofenceForm.name.trim() || !geofenceForm.latitude.trim() || !geofenceForm.longitude.trim() || !geofenceForm.radius.trim()) {
      setStatus('Zone name, latitude, longitude and radius are required')
      return
    }
    const latitude = Number(geofenceForm.latitude)
    const longitude = Number(geofenceForm.longitude)
    const radius = Number(geofenceForm.radius)
    if (Number.isNaN(latitude) || Number.isNaN(longitude) || Number.isNaN(radius)) {
      setStatus('Latitude, longitude and radius must be numbers')
      return
    }
    try {
      const payload = { name: geofenceForm.name.trim(), latitude, longitude, radius, is_active: true }
      if (editingGeofenceId) {
        await updateGeofence(editingGeofenceId, payload)
        setStatus('Safe zone updated')
      } else {
        await createGeofence(payload)
        setStatus(`Geofence created: ${payload.name}`)
      }
      resetGeofenceForm()
      await loadData()
    } catch {
      setStatus(editingGeofenceId ? 'Safe zone update failed' : 'Safe zone creation failed')
    }
  }

  const handleGeofenceEdit = (zone: any) => {
    setEditingGeofenceId(zone.id)
    setGeofenceForm({
      name: zone.name ?? '',
      latitude: zone.latitude != null ? String(zone.latitude) : '',
      longitude: zone.longitude != null ? String(zone.longitude) : '',
      radius: zone.radius != null ? String(zone.radius) : '',
    })
  }

  const handleGeofenceDelete = async (id: string) => {
    try {
      await deleteGeofence(id)
      setStatus('Safe zone deleted')
      if (editingGeofenceId === id) resetGeofenceForm()
      await loadData()
    } catch {
      setStatus('Safe zone deletion failed')
    }
  }

  const handleRoutePlan = async () => {
    try {
      const payload = {
        start_latitude: 12.97,
        start_longitude: 77.59,
        destination_latitude: 12.975,
        destination_longitude: 77.6,
        route_type: 'safe',
      }
      const result = await createRoutePlan(payload)
      setRouteResult(result)
      setStatus('Safe route plan generated')
    } catch {
      setStatus('Route plan failed')
    }
  }

  const handleAssistant = async () => {
    try {
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL}/safety/chatbot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: 'I feel unsafe while travelling at night.' }),
      })
      const payload = await response.json()
      setChatbotReply(payload.response || 'No guidance available.')
      setStatus('Safety guidance received')
    } catch {
      setStatus('Safety guidance unavailable')
    }
  }

  const handleLogout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
        <header className="mb-6 flex flex-col gap-4 rounded-3xl border border-slate-800 bg-slate-900/80 p-5 shadow-2xl shadow-slate-950/30 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.3em] text-pink-300">Women safety</p>
            <h2 className="mt-2 text-3xl font-semibold">Safety dashboard</h2>
          </div>
          <div className="flex items-center gap-3">
            <button onClick={() => navigate('/profile')} className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">Profile</button>
            <button onClick={() => navigate('/live-tracking')} className="rounded-full bg-cyan-600 px-4 py-2 text-sm font-medium text-white hover:bg-cyan-500">Live tracking</button>
            <button onClick={handleLogout} className="rounded-full bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500">Logout</button>
          </div>
        </header>

        <section className="mb-6 grid gap-6 lg:grid-cols-[1.3fr_0.7fr]">
          <div className="rounded-3xl border border-slate-800 bg-gradient-to-br from-slate-900 via-slate-800 to-indigo-950/60 p-6">
            <div className="mb-5 flex items-center justify-between">
              <div>
                <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Overview</p>
                <h3 className="mt-2 text-2xl font-semibold">Protection status</h3>
              </div>
              <span className="rounded-full border border-emerald-500/50 bg-emerald-500/10 px-3 py-1 text-xs font-medium text-emerald-300">Safe mode</span>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="rounded-2xl bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Contacts</p>
                <p className="mt-2 text-2xl font-semibold">{contacts.length}</p>
              </div>
              <div className="rounded-2xl bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Safe zones</p>
                <p className="mt-2 text-2xl font-semibold">{geofences.length}</p>
              </div>
              <div className="rounded-2xl bg-slate-950/60 p-4">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Activity</p>
                <p className="mt-2 text-2xl font-semibold">{activity.length}</p>
              </div>
            </div>

            <div className="mt-6 rounded-3xl border border-slate-700 bg-slate-950/60 p-4">
              <div className="mb-3 flex items-center justify-between">
                <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Live safety map</p>
                <span className="text-xs text-emerald-300">tracking on</span>
              </div>
              <div className="relative h-52 overflow-hidden rounded-2xl bg-gradient-to-br from-slate-800 via-slate-900 to-blue-950">
                <div className="absolute inset-0 opacity-30" style={{ backgroundImage: 'linear-gradient(rgba(255,255,255,0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.08) 1px, transparent 1px)', backgroundSize: '22px 22px' }} />
                <div className="absolute left-[18%] top-[30%] h-4 w-4 rounded-full bg-emerald-400 shadow-[0_0_20px_rgba(52,211,153,0.8)]" />
                <div className="absolute left-[55%] top-[55%] h-4 w-4 rounded-full bg-amber-400 shadow-[0_0_20px_rgba(251,191,36,0.7)]" />
                <div className="absolute left-[37%] top-[42%] h-16 w-16 rounded-full border-2 border-dashed border-violet-400/80" />
                <div className="absolute left-[50%] top-[50%] h-2 w-2 rounded-full bg-rose-500 shadow-[0_0_18px_rgba(244,63,94,0.8)]" />
                <div className="absolute bottom-4 left-4 rounded-xl bg-slate-900/80 px-3 py-2 text-xs text-slate-200">Current location: {locations[0] ? `${locations[0].latitude.toFixed(4)}, ${locations[0].longitude.toFixed(4)}` : 'Not saved yet'} </div>
              </div>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
            <div className="mb-4 flex items-center justify-between">
              <p className="text-xs uppercase tracking-[0.25em] text-slate-400">Quick actions</p>
              <span className="rounded-full bg-indigo-500/10 px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-indigo-300">Ready</span>
            </div>
            <div className="space-y-3">
              <button onClick={handleLocation} className="w-full rounded-2xl bg-indigo-600 px-4 py-3 text-left font-medium text-white hover:bg-indigo-500">Save my location</button>
              <button onClick={handleSOS} className="w-full rounded-2xl bg-red-600 px-4 py-3 text-left font-medium text-white hover:bg-red-500">Trigger SOS</button>
              <button onClick={handleFakeCall} className="w-full rounded-2xl bg-amber-600 px-4 py-3 text-left font-medium text-white hover:bg-amber-500">Schedule fake call</button>
              <button onClick={handleRoutePlan} className="w-full rounded-2xl bg-cyan-600 px-4 py-3 text-left font-medium text-white hover:bg-cyan-500">Plan safe route</button>
            </div>
          </div>
        </section>

        <div className="rounded-2xl bg-slate-800 p-4 mb-6">
          <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Status</p>
          <p className="mt-2 text-lg text-slate-100">{status}</p>
        </div>

        <div className="grid gap-6 md:grid-cols-3 mb-6">
          <div className="rounded-2xl bg-slate-800 p-4">
            <h3 className="text-xl font-semibold mb-3">Emergency Contacts</h3>
            <form
              className="mb-4 space-y-2"
              onSubmit={(e) => {
                e.preventDefault()
                void handleContactSubmit()
              }}
            >
              <input value={contactForm.name} onChange={(e) => setContactForm({ ...contactForm, name: e.target.value })} placeholder="Name" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
              <input value={contactForm.phone} onChange={(e) => setContactForm({ ...contactForm, phone: e.target.value })} placeholder="Phone (+15551234567)" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
              <input value={contactForm.email} onChange={(e) => setContactForm({ ...contactForm, email: e.target.value })} placeholder="Email (optional)" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
              <div className="flex items-center gap-2">
                <input value={contactForm.relationship_type} onChange={(e) => setContactForm({ ...contactForm, relationship_type: e.target.value })} placeholder="Relationship" className="min-w-0 flex-1 rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
                <label className="flex shrink-0 items-center gap-1 text-xs text-slate-300">
                  <input type="checkbox" checked={contactForm.is_primary} onChange={(e) => setContactForm({ ...contactForm, is_primary: e.target.checked })} />
                  Primary
                </label>
              </div>
              <div className="flex gap-2">
                <button type="submit" className="rounded-lg bg-emerald-600 px-3 py-2 text-sm font-medium text-white hover:bg-emerald-500">{editingContactId ? 'Save changes' : 'Add contact'}</button>
                {editingContactId && (
                  <button type="button" onClick={resetContactForm} className="rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:border-slate-400">Cancel</button>
                )}
              </div>
            </form>
            {contacts.length === 0 ? <p>No contacts yet.</p> : contacts.map((contact) => (
              <div key={contact.id} className="border-b border-slate-700 py-2 last:border-b-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium">{contact.is_primary ? '★ ' : ''}{contact.name}</p>
                    <p className="truncate text-sm text-slate-300">{contact.phone}{contact.relationship_type ? ` · ${contact.relationship_type}` : ''}</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <button onClick={() => handleContactEdit(contact)} className="rounded-md border border-slate-600 px-2 py-1 text-xs hover:border-slate-400">Edit</button>
                    <button onClick={() => void handleContactDelete(contact.id)} className="rounded-md bg-rose-700 px-2 py-1 text-xs hover:bg-rose-600">Delete</button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-2xl bg-slate-800 p-4">
            <h3 className="text-xl font-semibold mb-3">Recent Locations</h3>
            {locations.length === 0 ? <p>No location records yet.</p> : locations.map((location) => (
              <div key={location.id} className="border-b border-slate-700 py-2">
                <p className="text-sm text-slate-300">{location.latitude}, {location.longitude}</p>
                <p className="text-xs text-slate-400">Accuracy: {location.accuracy ?? 'n/a'}</p>
              </div>
            ))}
          </div>

          <div className="rounded-2xl bg-slate-800 p-4">
            <h3 className="text-xl font-semibold mb-3">Emergency Help</h3>
            {helplines.length === 0 ? <p>No helpline data available.</p> : helplines.map((item) => (
              <div key={`${item.name}-${item.number}`} className="border-b border-slate-700 py-2">
                <p className="font-medium">{item.name}</p>
                <p className="text-sm text-slate-300">{item.number}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="grid gap-6 md:grid-cols-2 mb-6">
          <div className="rounded-2xl bg-slate-800 p-4">
            <h3 className="text-xl font-semibold mb-3">Safe Zones</h3>
            <form
              className="mb-4 space-y-2"
              onSubmit={(e) => {
                e.preventDefault()
                void handleGeofenceSubmit()
              }}
            >
              <input value={geofenceForm.name} onChange={(e) => setGeofenceForm({ ...geofenceForm, name: e.target.value })} placeholder="Zone name" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
              <div className="grid grid-cols-2 gap-2">
                <input value={geofenceForm.latitude} onChange={(e) => setGeofenceForm({ ...geofenceForm, latitude: e.target.value })} placeholder="Latitude" inputMode="decimal" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
                <input value={geofenceForm.longitude} onChange={(e) => setGeofenceForm({ ...geofenceForm, longitude: e.target.value })} placeholder="Longitude" inputMode="decimal" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
              </div>
              <input value={geofenceForm.radius} onChange={(e) => setGeofenceForm({ ...geofenceForm, radius: e.target.value })} placeholder="Radius in meters" inputMode="decimal" className="w-full rounded-lg border border-slate-700 bg-slate-900 px-3 py-2 text-sm" />
              <div className="flex gap-2">
                <button type="submit" className="rounded-lg bg-violet-600 px-3 py-2 text-sm font-medium text-white hover:bg-violet-500">{editingGeofenceId ? 'Save changes' : 'Create zone'}</button>
                {editingGeofenceId && (
                  <button type="button" onClick={resetGeofenceForm} className="rounded-lg border border-slate-600 px-3 py-2 text-sm text-slate-200 hover:border-slate-400">Cancel</button>
                )}
              </div>
            </form>
            {geofences.length === 0 ? <p>No safe zones yet.</p> : geofences.map((zone) => (
              <div key={zone.id} className="border-b border-slate-700 py-2 last:border-b-0">
                <div className="flex items-center justify-between gap-2">
                  <div className="min-w-0">
                    <p className="font-medium">{zone.name}</p>
                    <p className="truncate text-sm text-slate-300">{zone.latitude}, {zone.longitude} · radius {zone.radius}m</p>
                  </div>
                  <div className="flex shrink-0 gap-1">
                    <button onClick={() => handleGeofenceEdit(zone)} className="rounded-md border border-slate-600 px-2 py-1 text-xs hover:border-slate-400">Edit</button>
                    <button onClick={() => void handleGeofenceDelete(zone.id)} className="rounded-md bg-rose-700 px-2 py-1 text-xs hover:bg-rose-600">Delete</button>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-2xl bg-slate-800 p-4">
            <h3 className="text-xl font-semibold mb-3">Recommended Route</h3>
            {routeResult ? (
              <div>
                <p className="text-sm text-slate-300">Distance: {routeResult.results?.[0]?.distance ?? 'n/a'} m</p>
                <p className="text-sm text-slate-300">Duration: {routeResult.results?.[0]?.estimated_duration ?? 'n/a'} min</p>
                <p className="text-sm text-slate-300">Risk score: {routeResult.results?.[0]?.risk_score ?? 'n/a'}</p>
              </div>
            ) : <p>No route planned yet.</p>}
          </div>
        </div>

        <div className="rounded-2xl bg-slate-800 p-4 mb-6">
          <h3 className="text-xl font-semibold mb-3">Recent Activity</h3>
          {activity.length === 0 ? <p>No recent activity yet.</p> : activity.map((item) => (
            <div key={`${item.type}-${item.id}`} className="border-b border-slate-700 py-3 last:border-b-0">
              <div className="flex items-center justify-between gap-4">
                <p className="font-medium capitalize">{item.title}</p>
                <span className="rounded-full bg-slate-700 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-200">{item.severity}</span>
              </div>
              <p className="text-sm text-slate-300 mt-1">{item.message}</p>
              <p className="text-xs text-slate-400 mt-1">{item.timestamp ? new Date(item.timestamp).toLocaleString() : 'Just now'}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl bg-slate-800 p-4 mb-6">
          <h3 className="text-xl font-semibold mb-3">Notifications</h3>
          {notifications.length === 0 ? <p>No notifications yet.</p> : notifications.map((item) => (
            <div key={item.id} className="border-b border-slate-700 py-3 last:border-b-0">
              <div className="flex items-center justify-between gap-4">
                <p className="font-medium capitalize">{item.type}</p>
                <span className="rounded-full bg-slate-700 px-2 py-1 text-[10px] uppercase tracking-wide text-slate-200">{item.status}</span>
              </div>
              <p className="text-sm text-slate-300 mt-1">{item.message}</p>
              <p className="text-xs text-slate-400 mt-1">{item.created_at ? new Date(item.created_at).toLocaleString() : 'Just now'}</p>
            </div>
          ))}
        </div>

        <div className="rounded-2xl bg-slate-800 p-4">
          <div className="mb-3 flex items-center justify-between">
            <h3 className="text-xl font-semibold">Safety Assistant</h3>
            <button onClick={handleAssistant} className="rounded-lg bg-sky-600 px-3 py-2 text-sm hover:bg-sky-500">Get guidance</button>
          </div>
          <p className="text-slate-200">{chatbotReply}</p>
        </div>
      </div>
    </div>
  )
}
