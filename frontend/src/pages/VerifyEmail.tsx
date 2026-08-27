import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { resendVerification, verifyEmail } from '../api/auth'

export default function VerifyEmail() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()
  const [info, setInfo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')

  const onResend = async (data: any) => {
    setError(null)
    setInfo(null)
    try {
      const res = await resendVerification({ email: data.email })
      setEmail(data.email)
      setInfo(res?.message || 'If the email exists, a verification code has been sent.')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Could not send verification code')
    }
  }

  const onVerify = async (data: any) => {
    setError(null)
    try {
      await verifyEmail({ email: email || data.email, otp: data.otp })
      setInfo('Email verified. You can now sign in.')
      navigate('/login')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Verification failed')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 flex items-center justify-center">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
        <p className="text-xs uppercase tracking-[0.28em] text-cyan-300">Verify email</p>
        <h2 className="mt-3 text-3xl font-semibold">Verify your email</h2>
        <p className="mt-2 text-sm text-slate-300">Enter the 6-digit code sent to your email.</p>

        {error && <p className="mt-4 rounded-xl bg-rose-950/50 px-3 py-2 text-sm text-rose-200">{error}</p>}
        {info && <p className="mt-4 rounded-xl bg-emerald-950/50 px-3 py-2 text-sm text-emerald-200">{info}</p>}

        <form onSubmit={handleSubmit(onVerify)} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Email</label>
            <input
              defaultValue={email}
              {...r('email', { required: true })}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-cyan-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Verification code</label>
            <input
              {...r('otp', { required: true })}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-cyan-500"
              placeholder="123456"
            />
          </div>
          <button type="submit" className="w-full rounded-xl bg-cyan-600 px-4 py-3 font-medium text-white hover:bg-cyan-500">
            Verify email
          </button>
        </form>

        <div className="mt-5 text-center text-sm">
          <span className="text-slate-300">Didn't receive a code? </span>
          <button onClick={handleSubmit(onResend)} className="text-cyan-300 hover:text-cyan-200">
            Resend code
          </button>
        </div>
      </div>
    </div>
  )
}