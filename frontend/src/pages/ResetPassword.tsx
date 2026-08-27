import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { resetPassword } from '../api/auth'
import { getErrorMessage } from '../utils/errors'
import { InlineAlert, inputClass } from '../components/ui'
import { Shield } from 'lucide-react'

export default function ResetPassword() {
  const { register: r, handleSubmit, formState: { errors } } = useForm()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const prefillEmail = searchParams.get('email') || ''
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)

  const onSubmit = async (data: any) => {
    setError(null)
    setLoading(true)
    try {
      await resetPassword({ email: data.email, otp: data.otp, new_password: data.new_password })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 1200)
    } catch (e: any) {
      setError(getErrorMessage(e, 'Password reset failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 text-slate-100">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-600 text-white">
            <Shield className="h-7 w-7" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold">Reset password</h1>
          <p className="mt-2 text-sm text-slate-400">Enter the reset code and choose a new password.</p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl sm:p-8">
          {error && (
            <div className="mb-4">
              <InlineAlert>{error}</InlineAlert>
            </div>
          )}
          {success && (
            <div className="mb-4">
              <InlineAlert tone="success">Password reset! Redirecting to login…</InlineAlert>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Email</label>
              <input
                defaultValue={prefillEmail}
                {...r('email', { required: true })}
                className={inputClass}
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Reset code</label>
              <input
                {...r('otp', { required: true })}
                className={inputClass}
                placeholder="123456"
                inputMode="numeric"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">New password</label>
              <input
                type="password"
                autoComplete="new-password"
                {...r('new_password', {
                  required: 'Password is required',
                  minLength: { value: 8, message: 'Password must be at least 8 characters' },
                })}
                className={inputClass}
                placeholder="At least 8 chars, letters + numbers"
              />
              {errors.new_password && <p className="mt-1 text-xs text-rose-300">{String(errors.new_password.message)}</p>}
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-amber-600 px-4 py-3 font-medium text-white hover:bg-amber-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 disabled:opacity-60"
            >
              {loading ? 'Resetting…' : 'Reset password'}
            </button>
          </form>

          <p className="mt-5 text-center text-sm">
            <Link to="/login" className="text-slate-400 hover:text-slate-300">Back to login</Link>
          </p>
        </div>
      </div>
    </div>
  )
}