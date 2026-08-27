import React from 'react'

/* Shared minimal UI primitives for consistent, polished styling. */

export function Card({
  children,
  className = '',
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div className={`rounded-2xl border border-slate-800 bg-slate-900/80 p-5 ${className}`}>
      {children}
    </div>
  )
}

export function SectionTitle({
  icon,
  children,
  action,
}: {
  icon?: React.ReactNode
  children: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <div className="mb-4 flex items-center justify-between gap-3">
      <div className="flex items-center gap-2 text-sm font-semibold text-slate-100">
        {icon}
        {children}
      </div>
      {action}
    </div>
  )
}

export function Spinner({ label = 'Loading…' }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 py-10 text-sm text-slate-400">
      <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-600 border-t-pink-400" />
      {label}
    </div>
  )
}

export function EmptyState({
  icon,
  title,
  description,
}: {
  icon?: React.ReactNode
  title: string
  description?: string
}) {
  return (
    <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-900/40 px-6 py-10 text-center">
      {icon && <div className="mb-3 text-slate-500">{icon}</div>}
      <p className="font-medium text-slate-200">{title}</p>
      {description && <p className="mt-1 max-w-xs text-sm text-slate-400">{description}</p>}
    </div>
  )
}

export function StatusBadge({
  tone,
  children,
}: {
  tone: 'success' | 'warning' | 'danger' | 'neutral'
  children: React.ReactNode
}) {
  const tones: Record<string, string> = {
    success: 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30',
    warning: 'bg-amber-500/10 text-amber-300 border-amber-500/30',
    danger: 'bg-rose-500/10 text-rose-300 border-rose-500/30',
    neutral: 'bg-slate-700/40 text-slate-300 border-slate-600/40',
  }
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}
    >
      {children}
    </span>
  )
}

export function Button({
  variant = 'primary',
  className = '',
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'success' | 'outline'
}) {
  const variants: Record<string, string> = {
    primary: 'bg-pink-600 text-white hover:bg-pink-500 focus-visible:ring-pink-400',
    success: 'bg-emerald-600 text-white hover:bg-emerald-500 focus-visible:ring-emerald-400',
    danger: 'bg-rose-600 text-white hover:bg-rose-500 focus-visible:ring-rose-400',
    secondary: 'bg-slate-800 text-slate-100 hover:bg-slate-700 focus-visible:ring-slate-400',
    outline: 'border border-slate-600 text-slate-200 hover:border-slate-400 focus-visible:ring-slate-400',
  }
  return (
    <button
      {...props}
      className={`inline-flex items-center justify-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 disabled:cursor-not-allowed disabled:opacity-60 ${variants[variant]} ${className}`}
    />
  )
}

export function Field({
  label,
  htmlFor,
  children,
  hint,
}: {
  label: string
  htmlFor?: string
  children: React.ReactNode
  hint?: string
}) {
  return (
    <div>
      <label htmlFor={htmlFor} className="mb-1 block text-sm font-medium text-slate-300">
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-slate-500">{hint}</p>}
    </div>
  )
}

export const inputClass =
  'w-full rounded-xl border border-slate-700 bg-slate-800 p-3 text-slate-100 outline-none transition-colors placeholder:text-slate-500 focus:border-pink-500 focus:ring-2 focus:ring-pink-500/30'

export function InlineAlert({
  tone = 'error',
  children,
}: {
  tone?: 'error' | 'success' | 'info'
  children: React.ReactNode
}) {
  const tones = {
    error: 'border-rose-600/50 bg-rose-950/40 text-rose-200',
    success: 'border-emerald-600/50 bg-emerald-950/40 text-emerald-200',
    info: 'border-slate-600/60 bg-slate-800/60 text-slate-200',
  }
  return (
    <div role={tone === 'error' ? 'alert' : 'status'} className={`rounded-xl border px-3 py-2.5 text-sm ${tones[tone]}`}>
      {children}
    </div>
  )
}
