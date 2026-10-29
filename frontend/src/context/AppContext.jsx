import React, { createContext, useContext, useState, useEffect, useMemo, useCallback } from 'react';
import {
  getPatients,
  savePatients,
  saveOrUpdatePatient,
  getQueue,
  saveQueue,
  addToQueue,
  removeFromQueue,
  getConsultations,
  saveConsultation as persistConsultation,
} from '../utils/storage';
import { getTodayDateString, formatDisplayDate } from '../utils/timeUtils';
import { sortQueue, calculateQueueSeverityCounts } from '../utils/queueUtils';
import { evaluateEmergencyIntake } from '../utils/emergencyScreening';
import api from '../services/api';

const AppContext = createContext(null);

export function AppProvider({ children }) {
  const [patients, setPatients] = useState([]);
  const [queue, setQueue] = useState([]);
  const [consultations, setConsultations] = useState([]);
  const [toasts, setToasts] = useState([]);
  const [timeTick, setTimeTick] = useState(0); // Forces re-render for live waiting times

  // Patient Calling / Modal state
  const [callModalOpen, setCallModalOpen] = useState(false);
  const [patientInCall, setPatientInCall] = useState(null);
  const [assignedDoctorPatient, setAssignedDoctorPatient] = useState(null);

  // Sync state from storage
  const refreshFromStorage = useCallback(() => {
    setPatients(getPatients());
    setQueue(getQueue());
    setConsultations(getConsultations());
  }, []);

  // Synchronize with MongoDB Backend Queue so Doctor Queue and Waiting Room Display match
  const syncBackendQueue = useCallback(async () => {
    try {
      const backendItems = await api.getQueue();
      if (Array.isArray(backendItems) && backendItems.length > 0) {
        const localQ = getQueue();
        let changed = false;
        const mergedQ = [...localQ];

        backendItems.forEach((bItem) => {
          if (bItem.queue_status === 'WAITING' || bItem.queue_status === 'CALLED') {
            const matchIndex = mergedQ.findIndex(
              (l) => l.patientId === bItem.patient_code || l.backendEntryId === bItem.entry_id
            );
            if (matchIndex === -1) {
              // Derive severity and score from backend priority tier (1-5).
              // Backend triage_service uses HIGH/MEDIUM/LOW — CRITICAL is not a valid backend tier.
              // Priority 1=Critical/Immediate, 2=Emergent, 3=Urgent, 4=Less Urgent, 5=Non-Urgent
              const prio = bItem.recommended_priority || 3;
              let derivedSeverity, derivedScore;
              if (bItem.is_emergency || prio === 1) {
                derivedSeverity = 'HIGH'; // 'CRITICAL' is not a backend tier; HIGH is the max
                derivedScore = 85;
              } else if (prio === 2) {
                derivedSeverity = 'HIGH';
                derivedScore = 72;
              } else if (prio === 3) {
                derivedSeverity = 'MEDIUM';
                derivedScore = 45;
              } else {
                derivedSeverity = 'LOW';
                derivedScore = 25;
              }
              // Add missing backend entry to local state
              mergedQ.push({
                patientId: bItem.patient_code,
                backendEntryId: bItem.entry_id,
                tokenNumber: bItem.token_number,
                patientName: bItem.patient_name,
                patientType: 'Outpatient',
                symptoms: ['Clinical Intake'],
                priorityScore: derivedScore,
                severity: derivedSeverity,
                emergencyRisk: bItem.is_emergency,
                queueEntryTime: bItem.arrival_time || new Date().toISOString(),
                registrationDate: getTodayDateString(),
                registrationTime: new Date().toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' }),
                status: bItem.queue_status === 'CALLED' ? 'Called' : 'Waiting',
                skippedCount: 0,
              });
              changed = true;
            } else {
              // Ensure backendEntryId and tokenNumber are attached
              if (!mergedQ[matchIndex].backendEntryId || !mergedQ[matchIndex].tokenNumber) {
                mergedQ[matchIndex] = {
                  ...mergedQ[matchIndex],
                  backendEntryId: bItem.entry_id,
                  tokenNumber: bItem.token_number,
                };
                changed = true;
              }
            }
          }
        });

        if (changed) {
          saveQueue(mergedQ);
          setQueue(mergedQ);
        }
      }
    } catch (_) {
      // Backend may be offline or in standalone mode; continue safely
    }
  }, []);

  useEffect(() => {
    refreshFromStorage();
    syncBackendQueue();

    const handleStorageChange = () => {
      refreshFromStorage();
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('medqueue_storage_change', handleStorageChange);

    // Live waiting-time ticker (updates every 15s) and periodically checks backend queue sync
    const interval = setInterval(() => {
      setTimeTick((t) => t + 1);
      syncBackendQueue();
    }, 15000);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('medqueue_storage_change', handleStorageChange);
      clearInterval(interval);
    };
  }, [refreshFromStorage, syncBackendQueue]);

  // Toast Notification System
  const addToast = useCallback((message, type = 'success') => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
    setToasts((prev) => [...prev, { id, message, type }]);

    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4500);
  }, []);

  const removeToast = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  // Today's Date in user local timezone
  const todayDateString = useMemo(() => getTodayDateString(), [timeTick]);
  const formattedTodayDate = useMemo(() => formatDisplayDate(new Date()), [timeTick]);

  // Sorted active queue (Highest priority first)
  const sortedQueue = useMemo(() => {
    return sortQueue(queue, 'priority');
  }, [queue, timeTick]);

  // Current Patient (Front of Queue) and Next Patient
  const currentPatient = useMemo(() => {
    return sortedQueue.length > 0 ? sortedQueue[0] : null;
  }, [sortedQueue]);

  const nextPatient = useMemo(() => {
    return sortedQueue.length > 1 ? sortedQueue[1] : null;
  }, [sortedQueue]);

  // Queue Severity Breakdown
  const queueSeverityCounts = useMemo(() => {
    return calculateQueueSeverityCounts(queue);
  }, [queue]);

  // Daily Statistics (Filtered by Today's Local Registration Date)
  const dailyStats = useMemo(() => {
    // 1. Total Patients registered today
    const todayPatients = patients.filter(
      (p) => p.registrationDate === todayDateString
    );
    const totalCount = todayPatients.length;

    // 2. Waiting Patients: today's patients currently in active queue
    const waitingToday = queue.filter(
      (q) => q.registrationDate === todayDateString
    );
    const waitingCount = waitingToday.length;

    // 3. Emergency Patients: today's waiting patients with CRITICAL / HIGH severity or priorityScore >= 80
    const emergencyCount = waitingToday.filter(
      (q) =>
        String(q.severity).toUpperCase() === 'HIGH' ||
        String(q.severity).toUpperCase() === 'CRITICAL' ||
        (Number(q.priorityScore) || 0) >= 80
    ).length;

    // 4. Consulted Patients: consultations completed today
    const todayConsultations = consultations.filter((c) => {
      const cDate = c.consultationDate || (c.timestamp ? c.timestamp.split('T')[0] : '');
      return cDate === todayDateString;
    });
    const consultedCount = todayConsultations.length;

    return {
      total: totalCount,
      waiting: waitingCount,
      emergency: emergencyCount,
      consulted: consultedCount,
      dateString: todayDateString,
      displayDate: formattedTodayDate,
    };
  }, [patients, queue, consultations, todayDateString, formattedTodayDate]);

  // Register or Add Visit for Patient
  const registerPatientRecord = useCallback((patientData, triageResult) => {
    const registrationTimestamp = new Date().toISOString();
    const registrationDate = getTodayDateString();
    const registrationTime = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });

    // Run synchronous clinical emergency warning screening
    const bpParts = String(patientData.bloodPressure || '120/80').split('/');
    const sbp = parseInt(bpParts[0], 10) || null;
    const dbp = parseInt(bpParts[1], 10) || null;

    const screening = evaluateEmergencyIntake(
      {
        spo2: patientData.spo2,
        systolicBP: sbp,
        diastolicBP: dbp,
        heartRate: patientData.heartRate,
        temperature: patientData.temperature,
      },
      patientData.symptoms || [],
      patientData.chiefComplaint || (patientData.symptoms ? patientData.symptoms.join(', ') : '')
    );

    // Emergency screening provides an independent safety override for life-threatening vitals
    // and red-flag symptoms. It does NOT manufacture a 'CRITICAL' display label — the backend
    // schema only has HIGH / MEDIUM / LOW. Emergencies are shown as HIGH (the maximum tier).
    const isEmergency = screening.isEmergency || triageResult.emergencyRisk === 'YES';
    // Use the ML/triage-calculated severity. If an emergency is detected, cap at HIGH,
    // but never invent a CRITICAL label that inflates the display for non-critical patients.
    const effectiveSeverity = isEmergency
      ? (triageResult.severity === 'LOW' ? 'HIGH' : triageResult.severity)
      : triageResult.severity;

    const visitRecord = {
      visitId: `V_${Date.now()}`,
      visitDate: registrationDate,
      visitTime: registrationTime,
      timestamp: registrationTimestamp,
      symptoms: patientData.symptoms,
      temperature: patientData.temperature,
      heartRate: patientData.heartRate,
      bloodPressure: patientData.bloodPressure,
      spo2: patientData.spo2,
      sugarLevel: patientData.sugarLevel,
      // Use the actual computed score — do NOT force to 90 just because isEmergency.
      // The emergency screening safety net is for clinical escalation, not score inflation.
      priorityScore: triageResult.priorityScore,
      severity: effectiveSeverity,
      emergencyRisk: isEmergency,
      escalationLevel: screening.escalationLevel,
      escalationReasons: screening.reasons,
      actionRequired: screening.actionRequired,
      factors: triageResult.factors,
      status: isEmergency ? 'Escalated Emergency' : 'Waiting',
    };

    const fullPatient = {
      ...patientData,
      registrationDate,
      registrationTime,
      registrationTimestamp,
      currentPriority: visitRecord.priorityScore,
      currentSeverity: effectiveSeverity,
      emergencyRisk: isEmergency,
      escalationReasons: screening.reasons,
      visits: [...(patientData.visits || []), visitRecord],
    };

    // Save/Update patient in storage
    saveOrUpdatePatient(fullPatient);

    // Add to active queue item
    const queueItem = {
      patientId: fullPatient.patientId,
      patientName: fullPatient.patientName,
      age: fullPatient.age,
      gender: fullPatient.gender,
      phoneNumber: fullPatient.phoneNumber,
      patientType: fullPatient.patientType,
      symptoms: fullPatient.symptoms,
      temperature: fullPatient.temperature,
      heartRate: fullPatient.heartRate,
      bloodPressure: fullPatient.bloodPressure,
      spo2: fullPatient.spo2,
      sugarLevel: fullPatient.sugarLevel,
      priorityScore: visitRecord.priorityScore,
      severity: effectiveSeverity,
      emergencyRisk: isEmergency,
      escalationReasons: screening.reasons,
      queueEntryTime: registrationTimestamp,
      registrationDate,
      registrationTime,
      status: isEmergency ? 'Escalated Emergency' : 'Waiting',
      skippedCount: 0,
    };

    addToQueue(queueItem);
    refreshFromStorage();

    // Asynchronously synchronize with MongoDB FastAPI Backend
    api.registerPatient({
      full_name: fullPatient.patientName,
      age: fullPatient.age,
      gender: fullPatient.gender,
      contact: fullPatient.phoneNumber,
    })
      .then((regResp) => {
        const patientCode = regResp.patient_code || fullPatient.patientId;
        return api.createEncounter({
          patient_code: patientCode,
          department: 'General Medicine',
          visit_type: fullPatient.patientType === 'Existing Patient' ? 'RETURNING' : 'NEW',
          chief_complaint: (fullPatient.symptoms && fullPatient.symptoms.length > 0)
            ? fullPatient.symptoms.join(', ')
            : 'Outpatient Clinical Intake',
          symptoms: fullPatient.symptoms || [],
          vitals: {
            temperature: fullPatient.temperature ? Number(fullPatient.temperature) : null,
            heart_rate: fullPatient.heartRate ? Number(fullPatient.heartRate) : null,
            systolic_bp: sbp,
            diastolic_bp: dbp,
            spo2: fullPatient.spo2 ? Number(fullPatient.spo2) : null,
            blood_sugar: fullPatient.sugarLevel ? Number(fullPatient.sugarLevel) : null,
          },
        }).then((encResp) => {
          const encounterId = encResp?.encounter_id;
          if (!encounterId) return;

          // Priority tier: 1 for emergency / critical, 2 for high, 3 for standard outpatient
          const initialPriority = isEmergency || effectiveSeverity === 'CRITICAL' ? 1 : (effectiveSeverity === 'HIGH' ? 2 : 3);
          return api.enqueuePatient({
            patient_code: patientCode,
            encounter_id: encounterId,
            department: 'General Medicine',
            initial_priority: initialPriority,
          }).then((qResp) => {
            if (qResp && qResp.entry_id) {
              const currentQ = getQueue();
              const updatedQ = currentQ.map((item) => {
                if (item.patientId === fullPatient.patientId) {
                  return {
                    ...item,
                    backendEntryId: qResp.entry_id,
                    tokenNumber: qResp.token_number,
                  };
                }
                return item;
              });
              saveQueue(updatedQ);
              refreshFromStorage();
            }
          });
        });
      })
      .catch((err) => {
        // Transparent offline resilience: local storage already preserved the record
        console.info('Backend sync note (offline or local mode):', err.message);
      });

    return fullPatient;
  }, [refreshFromStorage]);

  // Call Patient Flow - Trigger announcement broadcast & backend state update
  const initiateCallPatient = useCallback(async (patient, roomNumber = 'OPD Room 1') => {
    if (!patient) return;

    const patientDisplayName = patient.patientName || 'Patient';
    const cleanId = String(patient.patientId || '').replace(/^Token\s*/i, '');
    const patientTokenDisplay = cleanId.startsWith('P') ? `Token ${cleanId}` : `Token P${cleanId || '1001'}`;

    // 1. Update local queue status to CALLED immediately
    const currentQ = getQueue();
    const updatedQ = currentQ.map((q) => {
      if (q.patientId === patient.patientId) {
        return {
          ...q,
          status: 'CALLED',
          assignedRoom: roomNumber,
          calledAt: new Date().toISOString(),
        };
      }
      return q;
    });
    saveQueue(updatedQ);
    refreshFromStorage();

    // 2. Call backend API to transition status in MongoDB and log announcement event
    const targetId = patient.backendEntryId || patient.entryId || patient.patientId;
    let backendResponse = null;

    try {
      if (targetId) {
        backendResponse = await api.callPatient(targetId, roomNumber);
      } else {
        backendResponse = await api.callNextPatient(roomNumber);
      }
    } catch (err) {
      console.warn('Backend call notice (continuing with synchronized local broadcast):', err.message);
    }

    // 3. Retrieve actual display name and token from response or fallback
    const resolvedName = backendResponse?.patient_name || patientDisplayName;
    const resolvedToken = backendResponse?.token_display || patientTokenDisplay;
    const resolvedRoom = backendResponse?.assigned_room || roomNumber;
    const resolvedDoctor = backendResponse?.called_by || 'Consulting Physician';
    const roomTelugu = resolvedRoom.replace('OPD Room', 'ఓపీడీ రూమ్').replace('Consultation Room', 'కన్సల్టేషన్ రూమ్').replace('Room', 'రూమ్');

    // 4. Create synchronized announcement object for WaitingRoomDisplay
    const announcementEvent = {
      event_id: `EVT_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
      token_number: backendResponse?.token_number || patient.tokenNumber || 1,
      token_display: resolvedToken,
      patient_code: backendResponse?.patient_code || patient.patientId,
      patient_name: resolvedName,
      patient_initials: resolvedName.split(' ').map((n) => n[0]).filter(Boolean).join('. ') + '.',
      room_number: resolvedRoom,
      department: patient.department || 'General Medicine',
      doctor_name: resolvedDoctor,
      timestamp: new Date().toISOString(),
      speech_text_en: `${resolvedToken}. Patient ${resolvedName}, please proceed to ${resolvedRoom}.`,
      speech_text_te: `టోకెన్ ${cleanId || 'P1001'}. ${resolvedName} గారు, దయచేసి ${roomTelugu} కి వెళ్లండి.`,
    };

    // Persist in localStorage for instant multi-tab sync
    localStorage.setItem('medqueue_current_announcement', JSON.stringify(announcementEvent));

    try {
      const recentCalls = JSON.parse(localStorage.getItem('medqueue_recent_calls') || '[]');
      const updatedRecent = [announcementEvent, ...recentCalls.filter((r) => r.patient_code !== announcementEvent.patient_code)].slice(0, 10);
      localStorage.setItem('medqueue_recent_calls', JSON.stringify(updatedRecent));
    } catch (_) {}

    window.dispatchEvent(new CustomEvent('medqueue_announcement', { detail: announcementEvent }));
    window.dispatchEvent(new Event('storage'));

    // 5. Open Call Patient modal for doctor verification
    setPatientInCall({
      ...patient,
      patientName: resolvedName,
      displayName: resolvedName,
      displayToken: resolvedToken,
      assignedRoom: resolvedRoom,
    });
    setCallModalOpen(true);
    addToast(`Called ${resolvedToken} (${resolvedName}) to ${resolvedRoom}.`, 'info');
  }, [refreshFromStorage, addToast]);

  const confirmPatientPresent = useCallback((navigateFn) => {
    if (!patientInCall) return;
    const targetPatient = patientInCall;
    setAssignedDoctorPatient(targetPatient);
    setCallModalOpen(false);
    setPatientInCall(null);
    addToast(`Patient ${targetPatient.patientName} (${targetPatient.patientId}) verified present in consultation room.`, 'success');

    if (navigateFn) {
      navigateFn(`/consultation/${targetPatient.patientId}`);
    }
  }, [patientInCall, addToast]);

  const skipPatient = useCallback((patientId) => {
    const currentQ = getQueue();
    const targetIdx = currentQ.findIndex((p) => p.patientId === patientId);
    if (targetIdx === -1) {
      setCallModalOpen(false);
      return;
    }

    const patient = currentQ[targetIdx];
    const newSkippedCount = (patient.skippedCount || 0) + 1;

    // Reorder: push the skipped patient back 2 spots or towards the end of same severity group
    const remaining = currentQ.filter((p) => p.patientId !== patientId);
    const newInsertIdx = Math.min(remaining.length, targetIdx + 2);
    remaining.splice(newInsertIdx, 0, {
      ...patient,
      skippedCount: newSkippedCount,
      status: 'Skipped',
    });

    saveQueue(remaining);
    refreshFromStorage();
    setCallModalOpen(false);
    setPatientInCall(null);
    addToast('Patient skipped successfully.', 'info');
  }, [refreshFromStorage, addToast]);

  // Complete Consultation Flow
  const completeConsultation = useCallback((consultationData) => {
    const completedTimestamp = new Date().toISOString();
    const today = getTodayDateString();

    const record = {
      id: `C_${Date.now()}`,
      consultationId: `CON-${Date.now().toString().slice(-6)}`,
      patientId: consultationData.patientId,
      patientName: consultationData.patientName,
      doctorName: consultationData.doctorName || 'Attending Physician',
      consultationDate: today,
      timestamp: completedTimestamp,
      diagnosis: consultationData.diagnosis,
      prescription: consultationData.prescription || [],
      doctorNotes: consultationData.doctorNotes,
      followUpDate: consultationData.followUpDate || '',
      vitalsSummary: consultationData.vitalsSummary || {},
    };

    // 1. Save consultation
    persistConsultation(record);

    // 2. Remove patient from waiting queue & notify backend
    const currentQ = getQueue();
    const targetQItem = currentQ.find((q) => q.patientId === consultationData.patientId);
    if (targetQItem?.backendEntryId) {
      api.completeConsultation(targetQItem.backendEntryId).catch(() => {});
    }
    removeFromQueue(consultationData.patientId);

    // 3. Update patient's internal visit history to Consulted
    const allPatients = getPatients();
    const updatedPatients = allPatients.map((p) => {
      if (p.patientId === consultationData.patientId) {
        const updatedVisits = (p.visits || []).map((v, i) => {
          if (i === (p.visits.length - 1)) {
            return {
              ...v,
              status: 'Consulted',
              consultationId: record.consultationId,
              diagnosis: record.diagnosis,
              doctorNotes: record.doctorNotes,
              prescription: record.prescription,
            };
          }
          return v;
        });

        return {
          ...p,
          visits: updatedVisits,
          lastConsultationDate: today,
        };
      }
      return p;
    });
    savePatients(updatedPatients);

    // 4. Clear assigned doctor patient if matched
    if (assignedDoctorPatient && assignedDoctorPatient.patientId === consultationData.patientId) {
      setAssignedDoctorPatient(null);
    }

    refreshFromStorage();
    addToast('Consultation completed successfully.', 'success');
    return record;
  }, [assignedDoctorPatient, refreshFromStorage, addToast]);

  return (
    <AppContext.Provider
      value={{
        patients,
        queue,
        sortedQueue,
        consultations,
        dailyStats,
        currentPatient,
        nextPatient,
        queueSeverityCounts,
        timeTick,
        toasts,
        addToast,
        removeToast,
        registerPatientRecord,
        callModalOpen,
        patientInCall,
        setCallModalOpen,
        initiateCallPatient,
        confirmPatientPresent,
        skipPatient,
        assignedDoctorPatient,
        setAssignedDoctorPatient,
        completeConsultation,
        refreshFromStorage,
      }}
    >
      {children}
    </AppContext.Provider>
  );
}

export function useApp() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useApp must be used within an AppProvider');
  }
  return context;
}
