import React, { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client'
import { fetchMedicalInfo, fetchProfile, saveMedicalInfo, saveProfile } from '../api/profile'

export default function Profile() {
  const [user, setUser] = useState<any | null>(null)
  const [profile, setProfile] = useState<any>({})
  const [medical, setMedical] = useState<any>({})
  const [status, setStatus] = useState('Loading profile...')
  const navigate = useNavigate()

  const loadProfile = async () => {
    try {
      const [authUser, savedProfile, savedMedical] = await Promise.all([
        api.get('/auth/me'),
        fetchProfile().catch(() => null),
        fetchMedicalInfo().catch(() => null),
      ])
      setUser(authUser.data)
      setProfile(savedProfile ?? {})
      setMedical(savedMedical ?? {})
      setStatus('Profile loaded')
    } catch {
      localStorage.removeItem('access_token')
      localStorage.removeItem('refresh_token')
      setUser(null)
      navigate('/login')
    }
  }

  useEffect(() => {
    void loadProfile()
  }, [navigate])

  const handleSaveProfile = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const payload = {
      full_name: String(formData.get('full_name') || profile.full_name || user?.email || 'User'),
      date_of_birth: formData.get('date_of_birth') ? String(formData.get('date_of_birth')) : null,
      gender: String(formData.get('gender') || profile.gender || 'female'),
      city: String(formData.get('city') || profile.city || ''),
      state: String(formData.get('state') || profile.state || ''),
      address: String(formData.get('address') || profile.address || ''),
      profile_image: formData.get('profile_image') ? String(formData.get('profile_image')) : null,
    }

    try {
      const result = await saveProfile(payload)
      setProfile(result)
      setStatus('Profile saved successfully')
    } catch {
      setStatus('Profile save failed')
    }
  }

  const handleSaveMedical = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const formData = new FormData(event.currentTarget)
    const payload = {
      blood_group: formData.get('blood_group') ? String(formData.get('blood_group')) : medical.blood_group || null,
      allergies: formData.get('allergies') ? String(formData.get('allergies')) : medical.allergies || null,
      medical_conditions: formData.get('medical_conditions') ? String(formData.get('medical_conditions')) : medical.medical_conditions || null,
      medications: formData.get('medications') ? String(formData.get('medications')) : medical.medications || null,
      additional_information: formData.get('additional_information') ? String(formData.get('additional_information')) : medical.additional_information || null,
    }

    try {
      const result = await saveMedicalInfo(payload)
      setMedical(result)
      setStatus('Medical info saved successfully')
    } catch {
      setStatus('Medical info save failed')
    }
  }

  const logout = () => {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    navigate('/login')
  }

  if (!user) return <div className="p-6">Not authenticated or loading...</div>

  return (
    <div className="p-6 max-w-4xl mx-auto text-slate-100">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-3xl font-semibold">Profile</h2>
        <button onClick={logout} className="bg-red-600 hover:bg-red-500 px-4 py-2 rounded-lg">Logout</button>
      </div>

      <div className="rounded-xl bg-slate-800 p-4 mb-6">
        <p className="text-sm uppercase tracking-[0.2em] text-slate-400">Status</p>
        <p className="mt-2 text-lg">{status}</p>
      </div>

      <div className="grid md:grid-cols-2 gap-6 mb-6">
        <div className="rounded-xl bg-slate-800 p-5 space-y-2">
          <p><strong>ID:</strong> {user.id}</p>
          <p><strong>Email:</strong> {user.email}</p>
          <p><strong>Mobile:</strong> {user.mobile_number}</p>
        </div>

        <div className="rounded-xl bg-slate-800 p-5">
          <p className="font-semibold mb-2">Profile summary</p>
          <p>{profile.full_name || 'No full name set yet.'}</p>
          <p>{profile.city && profile.state ? `${profile.city}, ${profile.state}` : 'Location not set.'}</p>
        </div>
      </div>

      <div className="grid md:grid-cols-2 gap-6">
        <form onSubmit={handleSaveProfile} className="rounded-xl bg-slate-800 p-5 space-y-4">
          <h3 className="text-xl font-semibold">Personal Details</h3>
          <input name="full_name" defaultValue={profile.full_name || ''} placeholder="Full name" className="w-full rounded p-2 bg-slate-700" />
          <input name="date_of_birth" type="date" defaultValue={profile.date_of_birth || ''} className="w-full rounded p-2 bg-slate-700" />
          <select name="gender" defaultValue={profile.gender || 'female'} className="w-full rounded p-2 bg-slate-700">
            <option value="female">Female</option>
            <option value="male">Male</option>
            <option value="other">Other</option>
          </select>
          <input name="city" defaultValue={profile.city || ''} placeholder="City" className="w-full rounded p-2 bg-slate-700" />
          <input name="state" defaultValue={profile.state || ''} placeholder="State" className="w-full rounded p-2 bg-slate-700" />
          <textarea name="address" defaultValue={profile.address || ''} placeholder="Address" className="w-full rounded p-2 bg-slate-700" rows={3} />
          <button type="submit" className="bg-indigo-600 hover:bg-indigo-500 px-4 py-2 rounded-lg">Save profile</button>
        </form>

        <form onSubmit={handleSaveMedical} className="rounded-xl bg-slate-800 p-5 space-y-4">
          <h3 className="text-xl font-semibold">Medical Info</h3>
          <input name="blood_group" defaultValue={medical.blood_group || ''} placeholder="Blood group" className="w-full rounded p-2 bg-slate-700" />
          <textarea name="allergies" defaultValue={medical.allergies || ''} placeholder="Allergies" className="w-full rounded p-2 bg-slate-700" rows={2} />
          <textarea name="medical_conditions" defaultValue={medical.medical_conditions || ''} placeholder="Medical conditions" className="w-full rounded p-2 bg-slate-700" rows={2} />
          <textarea name="medications" defaultValue={medical.medications || ''} placeholder="Medications" className="w-full rounded p-2 bg-slate-700" rows={2} />
          <textarea name="additional_information" defaultValue={medical.additional_information || ''} placeholder="Additional information" className="w-full rounded p-2 bg-slate-700" rows={3} />
          <button type="submit" className="bg-emerald-600 hover:bg-emerald-500 px-4 py-2 rounded-lg">Save Medical info</button>
        </form>
      </div>
    </div>
  )
}
