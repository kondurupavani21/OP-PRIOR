import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { AppProvider } from './context/AppContext';

// Layout
import AppLayout from './components/layout/AppLayout';

// Pages
import Login from './pages/Login';
import Signup from './pages/Signup';
import Dashboard from './pages/Dashboard';
import PatientRegistration from './pages/PatientRegistration';
import PatientDetails from './pages/PatientDetails';
import PatientHistory from './pages/PatientHistory';
import PriorityAssessment from './pages/PriorityAssessment';
import PriorityQueue from './pages/PriorityQueue';
import DoctorDashboard from './pages/DoctorDashboard';
import Consultation from './pages/Consultation';
import Profile from './pages/Profile';
import WaitingRoomDisplay from './pages/WaitingRoomDisplay';

export default function App() {
  return (
    <AuthProvider>
      <AppProvider>
        <Routes>
          {/* Public Authentication Routes & Fullscreen Displays */}
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/waiting-room" element={<WaitingRoomDisplay />} />
          <Route path="/display" element={<WaitingRoomDisplay />} />

          {/* Protected Application Routes under AppLayout */}
          <Route element={<AppLayout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<Dashboard />} />
            <Route path="/patients/register" element={<PatientRegistration />} />
            <Route path="/patients/:id" element={<PatientDetails />} />
            <Route path="/patients/:id/history" element={<PatientHistory />} />
            <Route path="/patients/history" element={<PatientHistory />} />
            <Route path="/priority/:id" element={<PriorityAssessment />} />
            <Route path="/priority-queue" element={<PriorityQueue />} />
            <Route path="/doctor" element={<DoctorDashboard />} />
            <Route path="/consultation" element={<Consultation />} />
            <Route path="/consultation/:id" element={<Consultation />} />
            <Route path="/profile" element={<Profile />} />
          </Route>

          {/* Fallback route */}
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppProvider>
    </AuthProvider>
  );
}
