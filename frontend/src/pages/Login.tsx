import React from 'react'
import { useForm } from 'react-hook-form'
import { login } from '../api/auth'
import { useNavigate } from 'react-router-dom'

export default function Login() {
  const { register: r, handleSubmit } = useForm()
  const navigate = useNavigate()

  const onSubmit = async (data: any) => {
    try {
      const res = await login({ email: data.email, password: data.password })
      localStorage.setItem('access_token', res.access_token)
      localStorage.setItem('refresh_token', res.refresh_token)
      navigate('/dashboard')
    } catch (e: any) {
      alert(e?.response?.data?.detail || 'Login failed')
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 flex items-center justify-center">
      <div className="w-full max-w-md rounded-3xl border border-slate-700 bg-slate-900/90 p-8 shadow-2xl shadow-slate-950/30">
        <p className="text-xs uppercase tracking-[0.28em] text-pink-300">Welcome back</p>
        <h2 className="mt-3 text-3xl font-semibold">Login</h2>
        <p className="mt-2 text-sm text-slate-300">Access your safety dashboard and emergency tools.</p>

        <form onSubmit={handleSubmit(onSubmit)} className="mt-6 space-y-4">
          <div>
            <label className="mb-1 block text-sm text-slate-300">Email</label>
            <input {...r('email')} className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-indigo-500" placeholder="you@example.com" />
          </div>
          <div>
            <label className="mb-1 block text-sm text-slate-300">Password</label>
            <input type="password" {...r('password')} className="w-full rounded-xl border border-slate-700 bg-slate-800 p-3 outline-none focus:border-indigo-500" placeholder="••••••••" />
          </div>
          <button type="submit" className="w-full rounded-xl bg-indigo-600 px-4 py-3 font-medium text-white hover:bg-indigo-500">Login</button>
        </form>

        <p className="mt-5 text-center text-sm text-slate-300">
          Need an account?{' '}
          <a href="/register" className="text-indigo-300 hover:text-indigo-200">Register here</a>
        </p>
        <p className="mt-2 text-center text-sm">
          <a href="/forgot-password" className="text-slate-400 hover:text-slate-300">Forgot password?</a>
          {' · '}
          <a href="/verify-email" className="text-slate-400 hover:text-slate-300">Verify email</a>
        </p>
      </div>
    </div>
  )
}
