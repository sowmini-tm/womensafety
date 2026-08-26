import api from './client'

export const fetchProfile = async () => {
  const response = await api.get('/profile')
  return response.data
}

export const saveProfile = async (payload: {
  full_name: string
  date_of_birth?: string | null
  gender?: string | null
  city?: string | null
  state?: string | null
  address?: string | null
  profile_image?: string | null
}) => {
  const response = await api.post('/profile', payload)
  return response.data
}

export const fetchMedicalInfo = async () => {
  const response = await api.get('/profile/medical')
  return response.data
}

export const saveMedicalInfo = async (payload: {
  blood_group?: string | null
  allergies?: string | null
  medical_conditions?: string | null
  medications?: string | null
  additional_information?: string | null
}) => {
  const response = await api.post('/profile/medical', payload)
  return response.data
}
