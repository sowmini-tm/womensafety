import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fetchEmergencyContacts, fetchLocations } from '../api/safety'

export default function LiveTracking() {
  const navigate = useNavigate()
  const [contacts, setContacts] = useState<any[]>([])
  const [locations, setLocations] = useState<any[]>([])
  const [sharing, setSharing] = useState(true)

  useEffect(() => {
    const load = async () => {
      try {
        const [contactList, locationList] = await Promise.all([
          fetchEmergencyContacts().catch(() => []),
          fetchLocations().catch(() => []),
        ])
        setContacts(contactList)
        setLocations(locationList)
      } catch {
        // ignore missing backend data in local demo mode
      }
    }

    void load()
  }, [])

  const current = locations[0]

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
            <button onClick={() => setSharing((value) => !value)} className={`rounded-full px-4 py-2 text-sm font-medium ${sharing ? 'bg-emerald-600 hover:bg-emerald-500' : 'bg-slate-700 hover:bg-slate-600'}`}>
              {sharing ? 'Stop sharing' : 'Start sharing'}
            </button>
          </div>
        </header>

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
              <div className="absolute left-[20%] top-[30%] h-4 w-4 rounded-full bg-emerald-400 shadow-[0_0_25px_rgba(52,211,153,0.8)]" />
              <div className="absolute left-[54%] top-[52%] h-4 w-4 rounded-full bg-rose-500 shadow-[0_0_25px_rgba(244,63,94,0.8)]" />
              <div className="absolute left-[44%] top-[38%] h-20 w-20 rounded-full border border-dashed border-violet-400/80" />
              <div className="absolute left-[28%] top-[25%] h-60 w-60 rounded-full border border-cyan-500/20" />
              <div className="absolute bottom-4 left-4 rounded-2xl bg-slate-950/80 px-4 py-3">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Current position</p>
                <p className="mt-2 text-lg font-medium text-slate-100">
                  {current ? `${current.latitude.toFixed(4)}, ${current.longitude.toFixed(4)}` : 'No location saved'}
                </p>
              </div>
            </div>
          </div>

          <div className="space-y-6">
            <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-5">
              <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Session</p>
              <div className="mt-4 grid gap-3">
                <div className="rounded-2xl bg-slate-800 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Status</p>
                  <p className="mt-2 text-xl font-semibold text-emerald-300">{sharing ? 'Live' : 'Paused'}</p>
                </div>
                <div className="rounded-2xl bg-slate-800 p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-400">Updated</p>
                  <p className="mt-2 text-base text-slate-100">{current ? new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : 'Waiting for location'}</p>
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
