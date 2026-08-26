import api from './client'

export const fetchEmergencyContacts = async () => {
  const response = await api.get('/safety/emergency-contacts')
  return response.data
}

export const createEmergencyContact = async (payload: {
  name: string
  phone: string
  email?: string
  relationship_type?: string
  is_primary?: boolean
}) => {
  const response = await api.post('/safety/emergency-contacts', payload)
  return response.data
}

export const updateEmergencyContact = async (
  id: string,
  payload: {
    name?: string
    phone?: string
    email?: string
    relationship_type?: string
    is_primary?: boolean
  },
) => {
  const response = await api.put(`/safety/emergency-contacts/${id}`, payload)
  return response.data
}

export const deleteEmergencyContact = async (id: string) => {
  await api.delete(`/safety/emergency-contacts/${id}`)
}

export const createLocation = async (payload: {
  latitude: number
  longitude: number
  accuracy?: number
  speed?: number
}) => {
  const response = await api.post('/safety/location', payload)
  return response.data
}

export const fetchLocations = async () => {
  const response = await api.get('/safety/location')
  return response.data
}

export const triggerSOS = async (payload: { latitude: number; longitude: number; description?: string }) => {
  const response = await api.post('/safety/sos', payload)
  return response.data
}

export const scheduleFakeCall = async (payload: {
  caller_name: string
  caller_number: string
  delay_seconds?: number
  ringtone?: string
}) => {
  const response = await api.post('/safety/fake-call', payload)
  return response.data
}
