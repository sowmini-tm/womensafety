import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, Link } from 'react-router-dom'
import { resendVerification, verifyEmail } from '../api/auth'
import { getErrorMessage } from '../utils/errors'
import { InlineAlert, inputClass } from '../components/ui'
import { Shield } from 'lucide-react'

export default function VerifyEmail() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()
  const [info, setInfo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')
  const [loading, setLoading] = useState(false)

  const onResend = async (data: any) => {
    setError(null)
    setInfo(null)
    setLoading(true)
    try {
      const res = await resendVerification({ email: data.email })
      setEmail(data.email)
      setInfo(res?.message || 'If the email exists, a verification code has been sent.')
    } catch (e: any) {
      setError(getErrorMessage(e, 'Could not send verification code'))
    } finally {
      setLoading(false)
    }
  }

  const onVerify = async (data: any) => {
    setError(null)
    setInfo(null)
    setLoading(true)
    try {
      await verifyEmail({ email: email || data.email, otp: data.otp })
      setInfo('Email verified. You can now sign in.')
      navigate('/login')
    } catch (e: any) {
      setError(getErrorMessage(e, 'Verification failed'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 px-4 py-10 text-slate-100">
      <div className="w-full max-w-md">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="flex h-14 w-14 items-center justify-center rounded-2xl bg-cyan-600 text-white">
            <Shield className="h-7 w-7" />
          </span>
          <h1 className="mt-4 text-3xl font-semibold">Verify your email</h1>
          <p className="mt-2 text-sm text-slate-400">Enter the 6-digit code sent to your email.</p>
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

          <form onSubmit={handleSubmit(onVerify)} className="space-y-4" noValidate>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Email</label>
              <input
                defaultValue={email}
                {...r('email', { required: true })}
                className={inputClass}
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-slate-300">Verification code</label>
              <input
                {...r('otp', { required: true })}
                className={inputClass}
                placeholder="123456"
                inputMode="numeric"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-full bg-cyan-600 px-4 py-3 font-medium text-white hover:bg-cyan-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400 disabled:opacity-60"
            >
              {loading ? 'Verifying…' : 'Verify email'}
            </button>
          </form>

          <div className="mt-5 text-center text-sm">
            <span className="text-slate-400">Didn't receive a code? </span>
            <button onClick={handleSubmit(onResend)} disabled={loading} className="font-medium text-cyan-300 hover:text-cyan-200">
              Resend code
            </button>
          </div>
          <p className="mt-3 text-center text-sm">
            <Link to="/login" className="text-slate-400 hover:text-slate-300">Back to login</Link>
          </p>
        </div>
      </div>
    </div>
  )
}