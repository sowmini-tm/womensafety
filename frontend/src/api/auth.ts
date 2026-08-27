import api from './client'

export const register = async (payload: { email: string; mobile_number: string; password: string }) => {
  const res = await api.post('/auth/register', payload)
  return res.data
}

export const login = async (payload: { email: string; password: string }) => {
  const res = await api.post('/auth/login', payload)
  return res.data
}

export const refreshToken = async (refresh_token: string) => {
  const res = await api.post('/auth/refresh', { refresh_token })
  return res.data
}

// --- Phase 12: OTP verification + password recovery ---

export const verifyEmail = async (payload: { email: string; otp: string }) => {
  const res = await api.post('/auth/register/verify', payload)
  return res.data
}

export const resendVerification = async (payload: { email: string }) => {
  const res = await api.post('/auth/register/resend-verification', payload)
  return res.data
}

export const forgotPassword = async (payload: { email: string }) => {
  const res = await api.post('/auth/forgot-password', payload)
  return res.data
}

export const resetPassword = async (payload: { email: string; otp: string; new_password: string }) => {
  const res = await api.post('/auth/reset-password', payload)
  return res.data
}
