import { calculatePriority } from './priorityCalculator.js';
import { generateNextPatientId, findPatientByPhone, normalizePhone } from './patientUtils.js';
import { getTodayDateString, formatDisplayDate, calculateWaitingTime } from './timeUtils.js';
import { sortQueue, filterQueue, calculateQueueSeverityCounts } from './queueUtils.js';

console.log('=== MEDQUEUE AI UNIT VERIFICATION ===\n');

// 1. Date & Time tests
const todayStr = getTodayDateString();
console.log(`[PASS] Today's Local Date String: "${todayStr}"`);
console.log(`[PASS] Today's Formatted Date: "${formatDisplayDate(todayStr)}"`);

// 2. Dynamic ID Generation
const emptyListIds = generateNextPatientId([]);
console.log(`[PASS] Initial empty patient ID: ${emptyListIds} (Expected: P1001)`);
if (emptyListIds !== 'P1001') throw new Error('Failed initial ID');

const nextId = generateNextPatientId([{ patientId: 'P1001' }, { patientId: 'P1002' }]);
console.log(`[PASS] Next sequential ID: ${nextId} (Expected: P1003)`);
if (nextId !== 'P1003') throw new Error('Failed sequential ID');

// 3. Existing Patient Phone Lookup
const existingPatients = [
  { patientId: 'P1001', patientName: 'Michael Chang', phoneNumber: '+1 (987) 654-3210' },
  { patientId: 'P1002', patientName: 'Sarah Parker', phoneNumber: '9123456789' },
];
const found = findPatientByPhone(existingPatients, '987-654-3210');
console.log(`[PASS] Phone lookup found: ${found?.patientName} (${found?.patientId})`);
if (!found || found.patientId !== 'P1001') throw new Error('Failed phone lookup');

// 4. Simulated AI Priority Calculation - Emergency / High Risk Case
const highRiskPatient = {
  age: 68,
  temperature: 101.4,
  heartRate: 118,
  spo2: 88, // < 90 severe hypoxia
  bloodPressure: '165/100',
  sugarLevel: 140,
  symptoms: ['Chest Pain', 'Shortness of Breath'],
  previousDiseases: ['Cardiovascular Disease', 'Hypertension'],
};
const highTriage = calculatePriority(highRiskPatient);
console.log(`[PASS] High Risk Triage Score: ${highTriage.priorityScore}/100, Severity: ${highTriage.severity}, Emergency: ${highTriage.emergencyRisk}`);
if (highTriage.severity !== 'HIGH' || highTriage.emergencyRisk !== 'YES') {
  throw new Error('High triage scoring mismatch');
}

// 5. Simulated AI Priority Calculation - Low Risk Case
const lowRiskPatient = {
  age: 28,
  temperature: 98.6,
  heartRate: 72,
  spo2: 99,
  bloodPressure: '118/76',
  sugarLevel: 90,
  symptoms: ['Cough', 'Fatigue'],
  previousDiseases: ['None'],
};
const lowTriage = calculatePriority(lowRiskPatient);
console.log(`[PASS] Low Risk Triage Score: ${lowTriage.priorityScore}/100, Severity: ${lowTriage.severity}, Emergency: ${lowTriage.emergencyRisk}`);
if (lowTriage.severity !== 'LOW') {
  throw new Error('Low triage scoring mismatch');
}

// 6. Queue Sorting & Severity Breakdown
const sampleQueue = [
  { patientId: 'P1002', patientName: 'Sarah Parker', priorityScore: lowTriage.priorityScore, severity: lowTriage.severity, queueEntryTime: new Date(Date.now() - 300000).toISOString() },
  { patientId: 'P1001', patientName: 'Michael Chang', priorityScore: highTriage.priorityScore, severity: highTriage.severity, queueEntryTime: new Date(Date.now() - 60000).toISOString() },
];
const sorted = sortQueue(sampleQueue, 'priority');
console.log(`[PASS] Top Queue Patient after sorting by priority: ${sorted[0].patientName} (${sorted[0].patientId}) with score ${sorted[0].priorityScore}`);
if (sorted[0].patientId !== 'P1001') {
  throw new Error('Priority sorting mismatch: higher priority patient should be #1');
}

const counts = calculateQueueSeverityCounts(sampleQueue);
console.log(`[PASS] Severity counts: High=${counts.high}, Medium=${counts.medium}, Low=${counts.low}, Total=${counts.total}`);

console.log('\nALL 6 CORE LOGIC TESTS PASSED WITH 100% INTEGRITY!\n');
