import React from 'react'
import { Navigate } from 'react-router-dom'

export default function PrivateRoute({ children }: { children: JSX.Element }) {
  const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  if (!token) return <Navigate to="/login" replace />
  return children
}
