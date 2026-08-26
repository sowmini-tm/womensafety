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
