import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { register as apiRegister } from '../api/auth'
import { useNavigate, Link } from 'react-router-dom'
import { getErrorMessage } from '../utils/errors'
import { InlineAlert, inputClass } from '../components/ui'
import { Shield } from 'lucide-react'

export default function Register() {
  const { register: r, handleSubmit, formState: { errors } } = useForm()
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const onSubmit = async (data: any) => {
    setError(null)
    setLoading(true)
    try {
      const mobileNumber = data.mobile_number ?? data.mobile
      await apiRegister({ email: data.email, mobile_number: mobileNumber, password: data.password })
      navigate('/login', { state: { registered: true } })
    } catch (e: any) {
      setError(getErrorMessage(e, 'Registration failed'))
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
          <h1 className="mt-4 text-3xl font-semibold">Create your account</h1>
          <p className="mt-2 text-sm text-slate-400">Set up your safety tools in under a minute.</p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl sm:p-8">
          {error && (
            <div className="mb-4">
              <InlineAlert>{error}</InlineAlert>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label htmlFor="reg-email" className="mb-1 block text-sm font-medium text-slate-300">Email</label>
              <input
                id="reg-email"
                type="email"
                autoComplete="email"
                {...r('email', { required: 'Email is required' })}
                className={inputClass}
                placeholder="you@example.com"
              />
              {errors.email && <p className="mt-1 text-xs text-rose-300">{String(errors.email.message)}</p>}
            </div>
            <div>
              <label htmlFor="reg-mobile" className="mb-1 block text-sm font-medium text-slate-300">Mobile</label>
              <input
                id="reg-mobile"
                autoComplete="tel"
                {...r('mobile_number', { required: 'Mobile number is required' })}
                className={inputClass}
                placeholder="+1234567890"
              />
              {errors.mobile_number && <p className="mt-1 text-xs text-rose-300">{String(errors.mobile_number.message)}</p>}
            </div>
            <div>
              <label htmlFor="reg-password" className="mb-1 block text-sm font-medium text-slate-300">Password</label>
              <input
                id="reg-password"
                type="password"
                autoComplete="new-password"
                {...r('password', {
                  required: 'Password is required',
                  minLength: { value: 8, message: 'Password must be at least 8 characters' },
                })}
                className={inputClass}
                placeholder="At least 8 characters"
              />
              {errors.password ? (
                <p className="mt-1 text-xs text-rose-300">{String(errors.password.message)}</p>
              ) : (
                <p className="mt-1 text-xs text-slate-500">Use at least 8 characters with letters and numbers.</p>
              )}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-pink-600 px-4 py-3 font-medium text-white hover:bg-pink-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-400 disabled:opacity-60"
            >
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>

          <p className="mt-5 text-center text-sm text-slate-400">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-pink-300 hover:text-pink-200">Log in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}

