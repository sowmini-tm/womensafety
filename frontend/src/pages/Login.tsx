import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { login } from '../api/auth'
import { useNavigate, Link, useLocation } from 'react-router-dom'
import { getErrorMessage } from '../utils/errors'
import { InlineAlert, inputClass } from '../components/ui'
import { Shield } from 'lucide-react'

export default function Login() {
  const { register: r, handleSubmit, formState: { errors } } = useForm()
  const navigate = useNavigate()
  const location = useLocation()
  const justRegistered = Boolean((location.state as { registered?: boolean } | null)?.registered)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (data: any) => {
    setError(null)
    setLoading(true)
    try {
      const res = await login({ email: data.email, password: data.password })
      try {
        localStorage.setItem('access_token', res.access_token)
        localStorage.setItem('refresh_token', res.refresh_token)
      } catch {
        // ignore storage errors
      }
      navigate('/dashboard')
    } catch (e: any) {
      setError(getErrorMessage(e, 'Login failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 text-slate-100">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-pink-600 text-white">
            <Shield className="h-7 w-7" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold">Back to safety</h1>
          <p className="mt-2 text-sm text-slate-400">Log in to your safety dashboard.</p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl sm:p-8">
          {error && (
            <div className="mb-4">
              <InlineAlert>{error}</InlineAlert>
            </div>
          )}
          {justRegistered && !error && (
            <div className="mb-4">
              <InlineAlert tone="success">Account created! You can now log in.</InlineAlert>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-medium text-slate-300">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                {...r('email', { required: 'Email is required' })}
                className={inputClass}
                placeholder="you@example.com"
              />
              {errors.email && <p className="mt-1 text-xs text-rose-300">{String(errors.email.message)}</p>}
            </div>
            <div>
              <label htmlFor="password" className="mb-1 block text-sm font-medium text-slate-300">Password</label>
              <input
                id="password"
                type="password"
                autoComplete="current-password"
                {...r('password', { required: 'Password is required' })}
                className={inputClass}
                placeholder="••••••••"
              />
              {errors.password && <p className="mt-1 text-xs text-rose-300">{String(errors.password.message)}</p>}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-pink-600 px-4 py-3 font-medium text-white hover:bg-pink-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-400 disabled:opacity-60"
            >
              {loading ? 'Logging in…' : 'Log in'}
            </button>
          </form>

          <div className="mt-5 space-y-1 text-center text-sm">
            <p className="text-slate-400">
              Need an account?{' '}
              <Link to="/register" className="font-medium text-pink-300 hover:text-pink-200">Register here</Link>
            </p>
            <p>
              <Link to="/forgot-password" className="text-slate-400 hover:text-slate-300">Forgot password?</Link>
              {' · '}
              <Link to="/verify-email" className="text-slate-400 hover:text-slate-300">Verify email</Link>
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

