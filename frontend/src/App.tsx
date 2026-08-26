import { useEffect, useState } from 'react'

function App() {
  const [status, setStatus] = useState('Loading...')

  useEffect(() => {
    fetch(`${import.meta.env.VITE_API_BASE_URL}/health`)
      .then((response) => response.json())
      .then((data) => {
        if (data?.success) {
          setStatus('Backend connected: ' + data.data.status)
        } else {
          setStatus('Backend error')
        }
      })
      .catch(() => setStatus('Failed to connect to backend'))
  }, [])

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 px-4 py-8">
      <div className="max-w-6xl mx-auto">
        <header className="mb-10 flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <p className="text-xs uppercase tracking-[0.35em] text-pink-300">Women safety</p>
            <h1 className="mt-2 text-4xl font-bold">Smart Women Security App</h1>
          </div>
          <nav className="flex flex-wrap gap-3">
            <a href="/" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">Home</a>
            <a href="/login" className="rounded-full bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-500">Login</a>
            <a href="/register" className="rounded-full bg-rose-600 px-4 py-2 text-sm font-medium text-white hover:bg-rose-500">Register</a>
            <a href="/dashboard" className="rounded-full border border-slate-700 px-4 py-2 text-sm text-slate-200 hover:border-slate-500">Dashboard</a>
          </nav>
        </header>

        <section className="grid gap-6 lg:grid-cols-[1.2fr_0.8fr] mb-8">
          <div className="rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
            <p className="text-sm uppercase tracking-[0.26em] text-emerald-300">Safety first</p>
            <h2 className="mt-4 text-4xl font-semibold leading-tight">
              Real-time protection for everyday peace of mind.
            </h2>
            <p className="mt-4 max-w-xl text-slate-300">
              Help women move confidently with emergency alerts, trusted contacts, location tracking,
              safe-route guidance, and quick-response tools built into one app.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <a href="/register" className="rounded-xl bg-rose-600 px-5 py-3 font-medium text-white hover:bg-rose-500">Create account</a>
              <a href="/login" className="rounded-xl border border-slate-600 px-5 py-3 font-medium text-slate-100 hover:border-slate-400">Login</a>
            </div>
          </div>

          <div className="rounded-3xl border border-slate-700 bg-gradient-to-br from-slate-900 via-slate-800 to-rose-950/60 p-6">
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Current status</p>
            <div className="mt-5 rounded-2xl bg-slate-950/60 p-4">
              <p className="text-2xl font-semibold text-emerald-300">{status}</p>
            </div>
            <ul className="mt-6 space-y-3 text-sm text-slate-200">
              <li>• Emergency contact alerts</li>
              <li>• Live location recording</li>
              <li>• SOS and fake-call support</li>
              <li>• Safe route suggestions</li>
            </ul>
          </div>
        </section>

        <section className="grid gap-4 md:grid-cols-3 mb-8">
          <div className="rounded-2xl bg-slate-800 p-5">
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Auth</p>
            <p className="mt-2 text-xl font-medium">JWT protected</p>
          </div>
          <div className="rounded-2xl bg-slate-800 p-5">
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Safety</p>
            <p className="mt-2 text-xl font-medium">SOS + helplines</p>
          </div>
          <div className="rounded-2xl bg-slate-800 p-5">
            <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Smart</p>
            <p className="mt-2 text-xl font-medium">Risk-aware routing</p>
          </div>
        </section>

        <section className="rounded-3xl border border-emerald-500/30 bg-emerald-950/30 p-6 text-emerald-50">
          <p className="font-semibold mb-2">MVP coverage</p>
          <ul className="list-disc pl-5 space-y-1 text-sm">
            <li>User registration, login, and protected profile access</li>
            <li>Emergency contacts, geofences, and location tracking</li>
            <li>Risk assessment, routes, and safety guidance</li>
            <li>Quick emergency tools for immediate assistance</li>
          </ul>
        </section>
      </div>
    </div>
  )
}

export default App
