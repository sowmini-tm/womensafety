import api from './client'

export const createGeofence = async (payload: {
  name: string
  latitude: number
  longitude: number
  radius: number
  is_active?: boolean
}) => {
  const response = await api.post('/safety/geofences', payload)
  return response.data
}

export const fetchGeofences = async () => {
  const response = await api.get('/safety/geofences')
  return response.data
}

export const fetchSafetyActivity = async () => {
  const response = await api.get('/safety/activity')
  return response.data
}

export const fetchNotifications = async () => {
  const response = await api.get('/safety/notifications')
  return response.data
}

export const createRoutePlan = async (payload: {
  start_latitude: number
  start_longitude: number
  destination_latitude: number
  destination_longitude: number
  route_type?: string
}) => {
  const response = await api.post('/safety/route-plan', payload)
  return response.data
}
