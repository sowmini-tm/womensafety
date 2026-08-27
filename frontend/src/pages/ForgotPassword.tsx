import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, Link } from 'react-router-dom'
import { forgotPassword } from '../api/auth'
import { getErrorMessage } from '../utils/errors'
import { InlineAlert, inputClass } from '../components/ui'
import { Shield } from 'lucide-react'

export default function ForgotPassword() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()
  const [info, setInfo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  const onSubmit = async (data: any) => {
    setError(null)
    setInfo(null)
    setLoading(true)
    try {
      const res = await forgotPassword({ email: data.email })
      setEmail(data.email)
      setInfo(res?.message || 'If the account exists, a reset code has been sent.')
    } catch (e: any) {
      setError(getErrorMessage(e, 'Something went wrong'))
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
          <h1 className="mt-4 text-3xl font-semibold">Forgot password</h1>
          <p className="mt-2 text-sm text-slate-400">We'll send a reset code to your email.</p>
        </div>

        <div className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-xl sm:p-8">
          {error && (
            <div className="mb-4">
              <InlineAlert>{error}</InlineAlert>
            </div>
          )}
          {info && (
            <div className="mb-4">
              <InlineAlert tone="success">{info}</InlineAlert>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4" noValidate>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Email</label>
              <input
                {...r('email', { required: true })}
                className={inputClass}
                placeholder="you@example.com"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-amber-600 px-4 py-3 font-medium text-white hover:bg-amber-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-400 disabled:opacity-60"
            >
              {loading ? 'Sending…' : 'Send reset code'}
            </button>
          </form>

          {email && info && !error && (
            <button
              onClick={() => navigate(`/reset-password?email=${encodeURIComponent(email)}`)}
              className="mt-4 w-full rounded-full border border-amber-500 px-4 py-3 text-sm font-medium text-amber-200 hover:border-amber-400"
            >
              I have a code — reset my password
            </button>
          )}

          <p className="mt-5 text-center text-sm">
            <Link to="/login" className="text-slate-400 hover:text-slate-300">Back to login</Link>
          </p>
        </div>
      </div>
    </div>
  )
}