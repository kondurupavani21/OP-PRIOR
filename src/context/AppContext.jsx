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

  useEffect(() => {
    refreshFromStorage();

    const handleStorageChange = () => {
      refreshFromStorage();
    };

    window.addEventListener('storage', handleStorageChange);
    window.addEventListener('medqueue_storage_change', handleStorageChange);

    // Live waiting-time ticker (updates every 15s)
    const interval = setInterval(() => {
      setTimeTick((t) => t + 1);
    }, 15000);

    return () => {
      window.removeEventListener('storage', handleStorageChange);
      window.removeEventListener('medqueue_storage_change', handleStorageChange);
      clearInterval(interval);
    };
  }, [refreshFromStorage]);

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

    // 3. Emergency Patients: today's waiting patients with HIGH severity or priorityScore >= 80
    const emergencyCount = waitingToday.filter(
      (q) =>
        String(q.severity).toUpperCase() === 'HIGH' ||
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
      priorityScore: triageResult.priorityScore,
      severity: triageResult.severity,
      emergencyRisk: triageResult.emergencyRisk,
      factors: triageResult.factors,
      status: 'Waiting',
    };

    const fullPatient = {
      ...patientData,
      registrationDate,
      registrationTime,
      registrationTimestamp,
      currentPriority: triageResult.priorityScore,
      currentSeverity: triageResult.severity,
      emergencyRisk: triageResult.emergencyRisk,
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
      priorityScore: triageResult.priorityScore,
      severity: triageResult.severity,
      emergencyRisk: triageResult.emergencyRisk,
      queueEntryTime: registrationTimestamp,
      registrationDate,
      registrationTime,
      status: 'Waiting',
      skippedCount: 0,
    };

    addToQueue(queueItem);
    refreshFromStorage();

    return fullPatient;
  }, [refreshFromStorage]);

  // Call Patient Flow
  const initiateCallPatient = useCallback((patient) => {
    if (!patient) return;
    setPatientInCall(patient);
    setCallModalOpen(true);
  }, []);

  const confirmPatientPresent = useCallback((navigateFn) => {
    if (!patientInCall) return;
    const targetPatient = patientInCall;
    setAssignedDoctorPatient(targetPatient);
    setCallModalOpen(false);
    setPatientInCall(null);
    addToast(`Patient ${targetPatient.patientName} (${targetPatient.patientId}) called to consultation room.`, 'success');

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

    // 2. Remove patient from waiting queue
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
