import React from 'react'
import { useForm } from 'react-hook-form'
import { register as apiRegister } from '../api/auth'
import { useNavigate } from 'react-router-dom'

export default function Register() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()

  const onSubmit = async (data: any) => {
    try {
      const mobileNumber = data.mobile_number ?? data.mobile
      await apiRegister({ email: data.email, mobile_number: mobileNumber, password: data.password })
      alert('Registered — you can now login')
      navigate('/login')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Register failed')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 flex items-center justify-center">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
        <p className="text-xs uppercase tracking-[0.28em] text-emerald-300">Create account</p>
        <h2 className="mt-3 text-3xl font-semibold">Register</h2>
        <p className="mt-2 text-sm text-slate-300">Set up your account and start using the safety tools.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Email</label>
            <input {...r('email')} className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-emerald-500" placeholder="you@example.com" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Mobile</label>
            <input {...r('mobile_number')} className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-emerald-500" placeholder="+1234567890" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Password</label>
            <input type="password" {...r('password')} className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-emerald-500" placeholder="••••••••" />
          </div>
          <button type="submit" className="w-full rounded-xl bg-emerald-600 px-4 py-3 font-medium text-white hover:bg-emerald-500">Register</button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-300">
          Already have an account?{' '}
          <a href="/login" className="text-emerald-300 hover:text-emerald-200">Login</a>
        </p>
      </div>
    </div>
  )
}
