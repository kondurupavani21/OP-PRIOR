/**
 * queueUtils.js
 * Sorting, filtering, and metric calculation functions for the outpatient queue.
 */
import { getWaitingMinutes } from './timeUtils.js';

export function sortQueue(queue = [], sortBy = 'priority') {
  const items = [...queue];

  switch (sortBy) {
    case 'priority':
      // Higher priority score first. If tied, earlier queueEntryTime first (FCFS tie-break)
      return items.sort((a, b) => {
        const scoreA = Number(a.priorityScore) || 0;
        const scoreB = Number(b.priorityScore) || 0;
        if (scoreB !== scoreA) {
          return scoreB - scoreA;
        }
        const timeA = new Date(a.queueEntryTime || 0).getTime();
        const timeB = new Date(b.queueEntryTime || 0).getTime();
        return timeA - timeB;
      });

    case 'waitingTime':
      // Longest waiting time first (highest minutes)
      return items.sort((a, b) => {
        const waitA = getWaitingMinutes(a.queueEntryTime);
        const waitB = getWaitingMinutes(b.queueEntryTime);
        return waitB - waitA;
      });

    case 'fcfs':
      // Strictly First-Come-First-Served by queue entry time
      return items.sort((a, b) => {
        const timeA = new Date(a.queueEntryTime || 0).getTime();
        const timeB = new Date(b.queueEntryTime || 0).getTime();
        return timeA - timeB;
      });

    default:
      return items;
  }
}

export function filterQueue(queue = [], { search = '', severity = 'ALL', patientType = 'ALL' } = {}) {
  return queue.filter((item) => {
    // 1. Search filter (Name, ID, Phone)
    if (search && search.trim()) {
      const q = search.toLowerCase().trim();
      const name = String(item.patientName || '').toLowerCase();
      const id = String(item.patientId || '').toLowerCase();
      const phone = String(item.phoneNumber || item.phone || '').toLowerCase();
      if (!name.includes(q) && !id.includes(q) && !phone.includes(q)) {
        return false;
      }
    }

    // 2. Severity filter
    if (severity && severity !== 'ALL') {
      if (String(item.severity).toUpperCase() !== String(severity).toUpperCase()) {
        return false;
      }
    }

    // 3. Patient Type filter
    if (patientType && patientType !== 'ALL') {
      const pType = String(item.patientType || '').toLowerCase();
      const targetType = String(patientType).toLowerCase();
      if (!pType.includes(targetType) && !targetType.includes(pType)) {
        return false;
      }
    }

    return true;
  });
}

// Calculate counts of High, Medium, Low in active queue
export function calculateQueueSeverityCounts(queue = []) {
  let high = 0;
  let medium = 0;
  let low = 0;

  queue.forEach((item) => {
    const sev = String(item.severity || '').toUpperCase();
    if (sev === 'HIGH') high++;
    else if (sev === 'MEDIUM') medium++;
    else if (sev === 'LOW') low++;
  });

  return { high, medium, low, total: queue.length };
}
