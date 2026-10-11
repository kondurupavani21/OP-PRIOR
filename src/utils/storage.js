/**
 * storage.js
 * Centralized LocalStorage wrapper for MedQueue AI.
 * Ensures zero hardcoded records and robust error handling.
 */

const STORAGE_KEYS = {
  USERS: 'medqueue_users',
  CURRENT_USER: 'medqueue_current_user',
  PATIENTS: 'medqueue_patients',
  QUEUE: 'medqueue_queue',
  CONSULTATIONS: 'medqueue_consultations',
};

// Safe JSON parser
function getFromStorage(key, fallback = null) {
  try {
    const raw = localStorage.getItem(key);
    if (!raw) return fallback;
    return JSON.parse(raw);
  } catch (err) {
    console.error(`Error reading ${key} from localStorage:`, err);
    return fallback;
  }
}

// Safe JSON writer
function setToStorage(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    // Dispatch a custom event so other components or tabs can react immediately
    window.dispatchEvent(new Event('medqueue_storage_change'));
    return true;
  } catch (err) {
    console.error(`Error writing ${key} to localStorage:`, err);
    return false;
  }
}

// ==========================================
// USER AUTHENTICATION & PROFILE
// ==========================================

export function getUsers() {
  return getFromStorage(STORAGE_KEYS.USERS, []);
}

export function saveUsers(users) {
  return setToStorage(STORAGE_KEYS.USERS, users);
}

export function getCurrentUser() {
  return getFromStorage(STORAGE_KEYS.CURRENT_USER, null);
}

export function setCurrentUser(user) {
  return setToStorage(STORAGE_KEYS.CURRENT_USER, user);
}

export function removeCurrentUser() {
  localStorage.removeItem(STORAGE_KEYS.CURRENT_USER);
  window.dispatchEvent(new Event('medqueue_storage_change'));
}

// ==========================================
// PATIENTS
// ==========================================

export function getPatients() {
  return getFromStorage(STORAGE_KEYS.PATIENTS, []);
}

export function savePatients(patients) {
  return setToStorage(STORAGE_KEYS.PATIENTS, patients);
}

export function getPatientById(id) {
  const patients = getPatients();
  return patients.find((p) => p.patientId === id || p.id === id) || null;
}

export function saveOrUpdatePatient(patientData) {
  const patients = getPatients();
  const existingIdx = patients.findIndex(
    (p) => p.patientId === patientData.patientId
  );

  let updatedList;
  if (existingIdx >= 0) {
    // Merge existing patient details with new visit records
    const existing = patients[existingIdx];
    const updatedVisits = [
      ...(existing.visits || []),
      ...(patientData.visits ? patientData.visits.filter(v => !(existing.visits || []).some(ev => ev.visitId === v.visitId)) : [])
    ];
    updatedList = [...patients];
    updatedList[existingIdx] = {
      ...existing,
      ...patientData,
      visits: updatedVisits,
      lastVisitDate: patientData.lastVisitDate || new Date().toISOString(),
    };
  } else {
    updatedList = [...patients, patientData];
  }

  savePatients(updatedList);
  return patientData;
}

// ==========================================
// ACTIVE QUEUE
// ==========================================

export function getQueue() {
  return getFromStorage(STORAGE_KEYS.QUEUE, []);
}

export function saveQueue(queue) {
  return setToStorage(STORAGE_KEYS.QUEUE, queue);
}

export function addToQueue(queueItem) {
  const queue = getQueue();
  // Avoid duplicate queue entries for the same active patient
  const exists = queue.some((item) => item.patientId === queueItem.patientId);
  if (!exists) {
    const updated = [...queue, queueItem];
    saveQueue(updated);
    return updated;
  }
  return queue;
}

export function removeFromQueue(patientId) {
  const queue = getQueue();
  const updated = queue.filter((item) => item.patientId !== patientId);
  saveQueue(updated);
  return updated;
}

export function updateQueueItem(patientId, updates) {
  const queue = getQueue();
  const updated = queue.map((item) => {
    if (item.patientId === patientId) {
      return { ...item, ...updates };
    }
    return item;
  });
  saveQueue(updated);
  return updated;
}

// ==========================================
// CONSULTATIONS
// ==========================================

export function getConsultations() {
  return getFromStorage(STORAGE_KEYS.CONSULTATIONS, []);
}

export function saveConsultation(consultation) {
  const consultations = getConsultations();
  const updated = [consultation, ...consultations];
  setToStorage(STORAGE_KEYS.CONSULTATIONS, updated);
  return updated;
}
