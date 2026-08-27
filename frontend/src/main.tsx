import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'
import Login from './pages/Login'
import Register from './pages/Register'
import Profile from './pages/Profile'
import Dashboard from './pages/Dashboard'
import LiveTracking from './pages/LiveTracking'
import SharedLocation from './pages/SharedLocation'
import PrivateRoute from './components/PrivateRoute'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<App />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/profile" element={<PrivateRoute><Profile /></PrivateRoute>} />
        <Route path="/dashboard" element={<PrivateRoute><Dashboard /></PrivateRoute>} />
        <Route path="/live-tracking" element={<PrivateRoute><LiveTracking /></PrivateRoute>} />
        <Route path="/shared-location/:token" element={<SharedLocation />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
