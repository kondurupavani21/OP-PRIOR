/**
 * api.js
 * Comprehensive Frontend REST API client for MedQueue AI FastAPI Backend.
 * Connects React UI to all backend domains: Patients, Encounters, Queue, Auth,
 * OCR & Verified History, ML Inference, LLM Summaries, Simulation, and Announcements.
 */

const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000/api/v1';

function getAuthHeader() {
  const token = localStorage.getItem('token') || localStorage.getItem('access_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const headers = {
    'Content-Type': 'application/json',
    ...getAuthHeader(),
    ...(options.headers || {}),
  };

  try {
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP Error ${response.status}: ${response.statusText}`);
    }
    return await response.json();
  } catch (err) {
    throw err;
  }
}

export const api = {
  // System Health
  async getHealth() {
    return request('/health');
  },

  // Authentication & RBAC
  async login(email, password) {
    return request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
  },

  async getProfile() {
    return request('/auth/me');
  },

  // Patient Registration & Profiles
  async registerPatient(patientData) {
    return request('/patients', {
      method: 'POST',
      body: JSON.stringify({
        patient_code: patientData.patientId || patientData.patient_code || null,
        full_name: patientData.patientName || patientData.full_name,
        age: Number(patientData.age),
        gender: patientData.gender || 'Other',
        contact: patientData.phoneNumber || patientData.contact,
        emergency_contact: patientData.emergencyContact || null,
        blood_group: patientData.bloodGroup || null,
        preferred_language: patientData.preferredLanguage || 'English',
        accessibility_needs: patientData.accessibilityNeeds || null,
      }),
    });
  },

  async searchPatients(query = '') {
    const q = encodeURIComponent(query);
    return request(`/patients?query=${q}`);
  },

  async getPatient(patientCode) {
    return request(`/patients/${encodeURIComponent(patientCode)}`);
  },

  async getPatientEncounters(patientCode) {
    return request(`/patients/${encodeURIComponent(patientCode)}/encounters`);
  },

  // Encounters & Intake Vitals
  async createEncounter(encounterData) {
    return request('/encounters', {
      method: 'POST',
      body: JSON.stringify(encounterData),
    });
  },

  async getEncounter(encounterId) {
    return request(`/encounters/${encodeURIComponent(encounterId)}`);
  },

  // Active Queue Management & Dispatch Policies
  async getQueue(policy = null) {
    const query = policy ? `?policy=${encodeURIComponent(policy)}` : '';
    return request(`/queue${query}`);
  },

  async enqueuePatient(payload) {
    return request('/queue', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async callNextPatient(roomNumber = 'OPD Room 1') {
    return request(`/queue/call-next?room_number=${encodeURIComponent(roomNumber)}`, {
      method: 'POST',
    });
  },

  async callPatient(entryId, roomNumber = 'OPD Room 1') {
    return request(`/queue/${encodeURIComponent(entryId)}/call?room_number=${encodeURIComponent(roomNumber)}`, {
      method: 'POST',
    });
  },

  async startConsultation(entryId) {
    return request(`/queue/${encodeURIComponent(entryId)}/start`, {
      method: 'POST',
    });
  },

  async completeConsultation(entryId) {
    return request(`/queue/${encodeURIComponent(entryId)}/complete`, {
      method: 'POST',
    });
  },

  async overridePriority(entryId, newPriority, overrideReason, clinicalRationale = '') {
    return request(`/queue/${encodeURIComponent(entryId)}/override`, {
      method: 'POST',
      body: JSON.stringify({
        new_priority: newPriority,
        override_reason: overrideReason,
        clinical_rationale: clinicalRationale,
      }),
    });
  },

  async getQueueConfig() {
    return request('/queue/config');
  },

  async setQueueConfig(config) {
    return request('/queue/config', {
      method: 'POST',
      body: JSON.stringify(config),
    });
  },

  async getQueueSummary() {
    return request('/queue/summary');
  },

  // Medical Document Upload, OCR, Extraction & Verification
  async uploadDocument(patientCode, file, documentType = 'PRESCRIPTION', extra = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('document_type', documentType);
    if (extra.document_category) formData.append('document_category', extra.document_category);
    if (extra.encounter_id) formData.append('encounter_id', extra.encounter_id);
    if (extra.source_facility) formData.append('source_facility', extra.source_facility);
    if (extra.source_doctor) formData.append('source_doctor', extra.source_doctor);

    const tokenHeader = getAuthHeader();
    const url = `${API_BASE}/patients/${encodeURIComponent(patientCode)}/documents`;
    const res = await fetch(url, {
      method: 'POST',
      headers: { ...tokenHeader },
      body: formData,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Document upload failed');
    }
    return await res.json();
  },

  async getPatientDocuments(patientCode) {
    return request(`/patients/${encodeURIComponent(patientCode)}/documents`);
  },

  async getDocumentDetails(documentId) {
    return request(`/documents/${encodeURIComponent(documentId)}`);
  },

  async getDocumentContent(documentId) {
    return request(`/documents/${encodeURIComponent(documentId)}/content`);
  },

  async getDocumentExtraction(documentId) {
    return request(`/documents/${encodeURIComponent(documentId)}/extraction`);
  },

  async reprocessDocument(documentId, ocrMode = 'AUTO') {
    return request(`/documents/${encodeURIComponent(documentId)}/process`, {
      method: 'POST',
      body: JSON.stringify({ ocr_mode: ocrMode }),
    });
  },

  async verifyDocument(documentId, verifiedPayload) {
    return request(`/documents/${encodeURIComponent(documentId)}/verify`, {
      method: 'PATCH',
      body: JSON.stringify(verifiedPayload),
    });
  },

  async rejectDocument(documentId, reviewerNotes = 'Rejected by clinical review') {
    return request(`/documents/${encodeURIComponent(documentId)}/verify`, {
      method: 'PATCH',
      body: JSON.stringify({
        verification_status: 'REJECTED',
        reviewer_notes: reviewerNotes,
      }),
    });
  },

  // Patient Previous Consultations (External Clinic Visits)
  async recordPreviousConsultation(patientCode, payload) {
    return request(`/patients/${encodeURIComponent(patientCode)}/previous-consultations`, {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  },

  async getPatientPreviousConsultations(patientCode) {
    return request(`/patients/${encodeURIComponent(patientCode)}/previous-consultations`);
  },

  async updatePreviousConsultation(consultationId, payload) {
    return request(`/previous-consultations/${encodeURIComponent(consultationId)}`, {
      method: 'PATCH',
      body: JSON.stringify(payload),
    });
  },

  // Verified Medical History
  async getPatientHistory(patientCode) {
    return request(`/patients/${encodeURIComponent(patientCode)}/history`);
  },

  // Machine Learning Triage Acuity
  async getModelsStatus() {
    return request('/models/status');
  },

  async predictTriageAcuity(featurePayload) {
    return request('/models/predict', {
      method: 'POST',
      body: JSON.stringify(featurePayload),
    });
  },

  async getModelEvaluation() {
    return request('/models/evaluation');
  },

  // LLM Grounded Clinical Summaries & Doctor Review
  async generateClinicalSummary(encounterId, providerOverride = null) {
    return request(`/summaries/encounter/${encodeURIComponent(encounterId)}`, {
      method: 'POST',
      body: JSON.stringify({ encounter_id: encounterId, provider_override: providerOverride }),
    });
  },

  async getClinicalSummary(encounterId) {
    return request(`/summaries/encounter/${encodeURIComponent(encounterId)}`);
  },

  async regenerateClinicalSummary(summaryId) {
    return request(`/clinical-summaries/${encodeURIComponent(summaryId)}/regenerate`, {
      method: 'POST',
    });
  },

  async reviewClinicalSummary(encounterId, reviewStatus, doctorNotes = '', editedSummary = null) {
    return request(`/summaries/encounter/${encodeURIComponent(encounterId)}/review`, {
      method: 'PATCH',
      body: JSON.stringify({
        status: reviewStatus,
        doctor_notes: doctorNotes,
        edited_summary_text: editedSummary,
      }),
    });
  },


  // Monte Carlo Queue Simulation
  async runSimulation(params = {}) {
    return request('/simulation/run', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  },

  async getSimulationResults() {
    return request('/simulation/results');
  },

  async getSimulationCalibration() {
    return request('/simulation/calibration');
  },

  // Bilingual Public Waiting Room Announcements
  async getWaitingRoomBoard() {
    return request('/announcements/board');
  },

  async getLatestAnnouncement() {
    return request('/announcements/latest');
  },
};

export default api;
