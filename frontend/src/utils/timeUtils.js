/**
 * timeUtils.js
 * Handles accurate local date calculation (avoiding UTC timezone drift)
 * and dynamic elapsed wait time formatting.
 */

// Returns local date string in YYYY-MM-DD format based on the browser's local timezone
export function getTodayDateString(date = new Date()) {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

// Returns formatted human-readable date, e.g. "21 September 2026"
export function formatDisplayDate(dateStrOrObj = new Date()) {
  const d = typeof dateStrOrObj === 'string' ? new Date(dateStrOrObj.includes('T') ? dateStrOrObj : `${dateStrOrObj}T00:00:00`) : dateStrOrObj;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleDateString('en-US', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
}

// Returns formatted time e.g. "02:45 PM"
export function formatDisplayTime(isoStringOrDate = new Date()) {
  const d = typeof isoStringOrDate === 'string' ? new Date(isoStringOrDate) : isoStringOrDate;
  if (isNaN(d.getTime())) return '';
  return d.toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    hour12: true,
  });
}

// Calculates dynamic waiting time from queue entry time to now
export function calculateWaitingTime(queueEntryTime) {
  if (!queueEntryTime) return '0 min';
  const entry = new Date(queueEntryTime).getTime();
  const now = Date.now();
  const diffMs = Math.max(0, now - entry);
  const totalMinutes = Math.floor(diffMs / (1000 * 60));

  if (totalMinutes < 1) {
    return '< 1 min';
  }
  if (totalMinutes < 60) {
    return `${totalMinutes} min`;
  }
  const hours = Math.floor(totalMinutes / 60);
  const remainingMins = totalMinutes % 60;
  return remainingMins > 0 ? `${hours} hr ${remainingMins} min` : `${hours} hr`;
}

// Returns total minutes elapsed for numeric sorting
export function getWaitingMinutes(queueEntryTime) {
  if (!queueEntryTime) return 0;
  const entry = new Date(queueEntryTime).getTime();
  const now = Date.now();
  return Math.max(0, Math.floor((now - entry) / (1000 * 60)));
}
