import React, { useState } from 'react'
import { useForm } from 'react-hook-form'
import { useNavigate } from 'react-router-dom'
import { forgotPassword } from '../api/auth'

export default function ForgotPassword() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()
  const [info, setInfo] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState('')

  const onSubmit = async (data: any) => {
    setError(null)
    setInfo(null)
    try {
      const res = await forgotPassword({ email: data.email })
      setEmail(data.email)
      setInfo(res?.message || 'If the account exists, a reset code has been sent.')
    } catch (e: any) {
      setError(e?.response?.data?.detail || 'Something went wrong')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 flex items-center justify-center">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
        <p className="text-xs uppercase tracking-[0.28em] text-amber-300">Password recovery</p>
        <h2 className="mt-3 text-3xl font-semibold">Forgot password</h2>
        <p className="mt-2 text-sm text-slate-300">We'll send a reset code to your email.</p>

        {error && <p className="mt-4 rounded-xl bg-rose-950/50 px-3 py-2 text-sm text-rose-200">{error}</p>}
        {info && <p className="mt-4 rounded-xl bg-emerald-950/50 px-3 py-2 text-sm text-emerald-200">{info}</p>}

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Email</label>
            <input
              {...r('email', { required: true })}
              className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-amber-500"
              placeholder="you@example.com"
            />
          </div>
          <button type="submit" className="w-full rounded-xl bg-amber-600 px-4 py-3 font-medium text-white hover:bg-amber-500">
            Send reset code
          </button>
        </form>

        {email && info && !error && (
          <button
            onClick={() => navigate(`/reset-password?email=${encodeURIComponent(email)}`)}
            className="mt-4 w-full rounded-xl border border-amber-500 px-4 py-3 text-sm font-medium text-amber-200 hover:border-amber-400"
          >
            I have a code — reset my password
          </button>
        )}

        <p className="mt-5 text-center text-sm">
          <a href="/login" className="text-slate-300 hover:text-slate-200">Back to login</a>
        </p>
      </div>
    </div>
  )
}