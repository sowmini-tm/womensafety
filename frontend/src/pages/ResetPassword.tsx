import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { resetPassword } from '../api/auth'

export default function ResetPassword() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const prefillEmail = searchParams.get('email') || ''
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)

  const onSubmit = async (data: any) => {
    setError(null)
    try {
      await resetPassword({ email: data.email, otp: data.otp, new_password: data.new_password })
      setSuccess(true)
      setTimeout(() => navigate('/login'), 1200)
    } catch (e: any) {
      setError(e?.response?.data?.detail || (e?.response?.data?.detail?.length ? e.response.data.detail[0]?.msg : 'Reset failed'))
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 flex items-center justify-center">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
        <p className="text-xs uppercase tracking-[0.28em] text-amber-300">Password recovery</p>
        <h2 className="mt-3 text-3xl font-semibold">Reset password</h2>
        <p className="mt-2 text-sm text-slate-300">Enter the reset code and choose a new password.</p>

        {error && <p className="mt-4 rounded-xl bg-rose-950/50 px-3 py-2 text-sm text-rose-200">{error}</p>}
        {success && <p className="mt-4 rounded-xl bg-emerald-950/50 px-3 py-2 text-sm text-emerald-200">Password reset! Redirecting to login…</p>}

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Email</label>
            <input
              defaultValue={prefillEmail}
              {...r('email', { required: true })}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-amber-500"
              placeholder="you@example.com"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Reset code</label>
            <input
              {...r('otp', { required: true })}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-amber-500"
              placeholder="123456"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">New password</label>
            <input
              type="password"
              {...r('new_password', { required: true })}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-amber-500"
              placeholder="At least 8 chars, letters + numbers"
            />
          </div>
          <button type="submit" className="w-full rounded-xl bg-amber-600 px-4 py-3 font-medium text-white hover:bg-amber-500">
            Reset password
          </button>
        </form>

        <p className="mt-5 text-center text-sm">
          <a href="/login" className="text-slate-300 hover:text-slate-200">Back to login</a>
        </p>
      </div>
    </div>
  )
}