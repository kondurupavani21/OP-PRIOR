/**
 * patientUtils.js
 * Helpers for patient ID generation and matching.
 */

// Dynamically generate the next sequential Patient ID based on existing records
export function generateNextPatientId(existingPatients = []) {
  if (!Array.isArray(existingPatients) || existingPatients.length === 0) {
    return 'P1001';
  }

  let maxNum = 1000;
  existingPatients.forEach((patient) => {
    if (patient && patient.patientId) {
      const match = String(patient.patientId).match(/P(\d+)/i);
      if (match && match[1]) {
        const num = parseInt(match[1], 10);
        if (!isNaN(num) && num > maxNum) {
          maxNum = num;
        }
      }
    }
  });

  return `P${maxNum + 1}`;
}

// Clean phone numbers by stripping non-digit characters
export function normalizePhone(phone) {
  if (!phone) return '';
  return String(phone).replace(/\D/g, '');
}

export function findPatientByPhone(patients = [], phone) {
  const cleanTarget = normalizePhone(phone);
  if (!cleanTarget || cleanTarget.length < 5) return null;

  return (
    patients.find((p) => {
      const cleanP = normalizePhone(p.phoneNumber || p.phone);
      if (!cleanP) return false;
      if (cleanP === cleanTarget) return true;
      // Match last 10 digits if numbers have country codes or leading zeros
      if (cleanP.length >= 10 && cleanTarget.length >= 10) {
        return cleanP.slice(-10) === cleanTarget.slice(-10);
      }
      return cleanP.endsWith(cleanTarget) || cleanTarget.endsWith(cleanP);
    }) || null
  );
}
