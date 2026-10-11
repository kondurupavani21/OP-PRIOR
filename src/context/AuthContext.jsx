import React, { createContext, useContext, useState, useEffect } from 'react';
import {
  getUsers,
  saveUsers,
  getCurrentUser,
  setCurrentUser,
  removeCurrentUser,
} from '../utils/storage';

const AuthContext = createContext(null);

// Default demo staff accounts for instant testing if desired
const DEMO_STAFF = [
  {
    id: 'usr_doc_1',
    name: 'Dr. Sarah Jenkins',
    email: 'doctor@medqueue.ai',
    password: 'password123',
    role: 'Doctor',
    department: 'Emergency & Triage',
    licenseId: 'MED-78291',
  },
  {
    id: 'usr_rec_1',
    name: 'Alex Rivera',
    email: 'reception@medqueue.ai',
    password: 'password123',
    role: 'Receptionist',
    department: 'OP Registration Desk',
    licenseId: 'ADM-41022',
  },
  {
    id: 'usr_adm_1',
    name: 'Chief Admin Vance',
    email: 'admin@medqueue.ai',
    password: 'password123',
    role: 'Admin',
    department: 'Clinical Operations',
    licenseId: 'OPS-10001',
  },
];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Initialize and ensure default demo accounts exist in medqueue_users
  useEffect(() => {
    let existingUsers = getUsers();
    if (!existingUsers || existingUsers.length === 0) {
      saveUsers(DEMO_STAFF);
      existingUsers = DEMO_STAFF;
    }

    const current = getCurrentUser();
    if (current) {
      setUser(current);
    }
    setLoading(false);
  }, []);

  const login = (email, password) => {
    const users = getUsers();
    const found = users.find(
      (u) =>
        u.email.toLowerCase().trim() === email.toLowerCase().trim() &&
        u.password === password
    );

    if (found) {
      setCurrentUser(found);
      setUser(found);
      return { success: true, user: found };
    }
    return { success: false, error: 'Invalid email address or password.' };
  };

  const signup = ({ name, email, password, role = 'Doctor' }) => {
    const users = getUsers();
    const emailLower = email.toLowerCase().trim();

    if (users.some((u) => u.email.toLowerCase().trim() === emailLower)) {
      return { success: false, error: 'An account with this email already exists.' };
    }

    const newUser = {
      id: `usr_${Date.now()}`,
      name: name.trim(),
      email: emailLower,
      password,
      role,
      department: role === 'Doctor' ? 'General Medicine' : 'Outpatient Department',
      licenseId: `ID-${Math.floor(10000 + Math.random() * 90000)}`,
      createdAt: new Date().toISOString(),
    };

    const updated = [...users, newUser];
    saveUsers(updated);
    setCurrentUser(newUser);
    setUser(newUser);
    return { success: true, user: newUser };
  };

  const logout = () => {
    removeCurrentUser();
    setUser(null);
  };

  const updateProfile = (updates) => {
    if (!user) return { success: false, error: 'No active session.' };
    const users = getUsers();
    const updatedUser = { ...user, ...updates };

    const updatedUsers = users.map((u) => (u.id === user.id ? updatedUser : u));
    saveUsers(updatedUsers);
    setCurrentUser(updatedUser);
    setUser(updatedUser);
    return { success: true, user: updatedUser };
  };

  const quickDemoLogin = (role = 'Doctor') => {
    const target = DEMO_STAFF.find((s) => s.role === role) || DEMO_STAFF[0];
    setCurrentUser(target);
    setUser(target);
    return target;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated: !!user,
        loading,
        login,
        signup,
        logout,
        updateProfile,
        quickDemoLogin,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
