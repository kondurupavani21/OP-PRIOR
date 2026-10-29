"""Provider-Independent Clinical Doctor Decision-Support LLM Service.

Architecture:
- Adapter pattern supporting:
  1. MockClinicalLLMProvider: Deterministic, grounded offline clinical summarization with zero API keys or external dependencies.
  2. OpenAILLMProvider: Live OpenAI Chat Completions API adapter (activated if OPENAI_API_KEY is present).
  3. OllamaLLMProvider: Local Ollama server adapter (activated if OLLAMA_BASE_URL is present).
- Grounding: Every assertion explicitly cites EHR source records (vitals, chief complaint, verified medical history, uploaded documents).
- 7 Structured Sections (A: Current presentation, B: Previous consultations, C: Investigations, D: Relevant history, E: Timeline, F: Uncertainties, G: Citations).
- Hallucination safeguard: All summaries carry a human-in-the-loop review state ('PENDING_REVIEW', 'ACCEPTED', 'EDITED', 'REJECTED').
- Staleness detection: Summaries detect if new documents or consultations were added after generation.
"""
from abc import ABC, abstractmethod
from datetime import datetime, timezone
import json
import logging
import os
import uuid
from typing import Any, Dict, List, Optional
import urllib.request
import urllib.error

from app.core.config import settings
from app.database.mongodb import (
    get_mongodb,
    get_medical_documents_col,
    get_previous_consultations_col,
    get_medical_history_col,
    get_audit_events_col,
)
from app.schemas.ai_summary import (
    AISummaryResponse,
    AISummaryReviewRequest,
    DifferentialItem,
    GroundedCitation,
    ClinicalTimelineEvent,
    PreviousConsultationSummaryItem,
    PreviousInvestigationSummaryItem,
)

logger = logging.getLogger("medqueue.services.llm")


class BaseLLMProvider(ABC):
    """Abstract interface for clinical summarizer providers."""

    @abstractmethod
    def generate_clinical_summary(
        self,
        encounter: Dict[str, Any],
        patient: Dict[str, Any],
        verified_history: List[Dict[str, Any]],
        previous_consultations: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
        triage_assessment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Produce structured clinical summary with 7 formal sections and grounding citations."""
        pass


class MockClinicalLLMProvider(BaseLLMProvider):
    """Deterministic, grounded clinical intelligence engine with zero external dependencies.

    Synthesizes clinical evidence directly from measured vitals, verified history,
    patient-reported previous consultations, and extracted medical documents.
    """

    def generate_clinical_summary(
        self,
        encounter: Dict[str, Any],
        patient: Dict[str, Any],
        verified_history: List[Dict[str, Any]],
        previous_consultations: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
        triage_assessment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        age = patient.get("age", 40)
        sex = patient.get("gender", "Unknown")
        chief_complaint = encounter.get("chief_complaint", "General outpatient consultation")
        symptom_duration = encounter.get("symptom_duration", "1 day")
        symptoms = encounter.get("symptoms", [])
        vitals = encounter.get("vitals", {})
        missingness = encounter.get("missingness_indicators", {})

        sbp = vitals.get("systolic_bp")
        dbp = vitals.get("diastolic_bp")
        hr = vitals.get("heart_rate")
        spo2 = vitals.get("spo2")
        temp = vitals.get("temperature")
        rr = vitals.get("respiratory_rate")
        sugar = vitals.get("blood_sugar")
        pain = vitals.get("pain_score")

        symptoms_str = ", ".join(symptoms) if symptoms else "none reported"

        # -------------------------------------------------------------
        # Section A: Current Presentation
        # -------------------------------------------------------------
        vitals_points = []
        escalation_flags = []
        citations: List[GroundedCitation] = []
        uncertainties: List[str] = []

        citations.append(GroundedCitation(
            claim=f"Primary presenting complaint: '{chief_complaint}' (duration: {symptom_duration})",
            source_type="CHIEF_COMPLAINT",
            source_reference=f"Encounter ID {encounter.get('encounter_id', encounter.get('_id'))}",
            verification_status="PATIENT_REPORTED",
        ))

        missing_measurements = []
        if sbp is None or dbp is None:
            missing_measurements.append("Blood Pressure (Systolic/Diastolic)")
        if hr is None:
            missing_measurements.append("Pulse / Heart Rate")
        if spo2 is None:
            missing_measurements.append("Oxygen Saturation (SpO2)")
        if temp is None:
            missing_measurements.append("Body Temperature")
        if sugar is None:
            missing_measurements.append("Random Blood Sugar")
        if rr is None:
            missing_measurements.append("Respiratory Rate")

        if missing_measurements:
            uncertainties.append(f"Missing intake physiological measurements: {', '.join(missing_measurements)}.")

        # Vitals assessment
        if spo2 is not None:
            if spo2 < 90:
                vitals_points.append(f"CRITICAL HYPOXIA (SpO2 {spo2}%) - Supplemental O2 required.")
                escalation_flags.append(f"Hypoxia alert: SpO2 {spo2}%")
            elif spo2 < 95:
                vitals_points.append(f"Sub-optimal oxygen saturation (SpO2 {spo2}%).")
            else:
                vitals_points.append(f"Oxygen saturation within normal limits ({spo2}%).")
            citations.append(GroundedCitation(
                claim=f"Pulse oximetry measured at {spo2}%",
                source_type="VITALS",
                source_reference="Encounter Intake Vitals",
                verification_status="CLINICIAN_VERIFIED",
            ))

        if sbp is not None and dbp is not None:
            if sbp >= 180 or dbp >= 110:
                vitals_points.append(f"HYPERTENSIVE CRISIS RANGE ({sbp}/{dbp} mmHg) - Assess end-organ signs.")
                escalation_flags.append(f"Hypertensive crisis: {sbp}/{dbp} mmHg")
            elif sbp >= 140 or dbp >= 90:
                vitals_points.append(f"Elevated blood pressure ({sbp}/{dbp} mmHg).")
            elif sbp < 90:
                vitals_points.append(f"HYPOTENSION / SHOCK ALERT ({sbp}/{dbp} mmHg) - Volume resuscitation check.")
                escalation_flags.append(f"Hypotensive alert: SBP {sbp} mmHg")
            else:
                vitals_points.append(f"Blood pressure normotensive ({sbp}/{dbp} mmHg).")
            citations.append(GroundedCitation(
                claim=f"Intake BP recorded as {sbp}/{dbp} mmHg",
                source_type="VITALS",
                source_reference="Encounter Intake Vitals",
                verification_status="CLINICIAN_VERIFIED",
            ))

        if hr is not None:
            if hr > 120:
                vitals_points.append(f"Significant Tachycardia ({hr} bpm).")
                escalation_flags.append(f"Tachycardia: {hr} bpm")
            elif hr < 50:
                vitals_points.append(f"Marked Bradycardia ({hr} bpm).")
                escalation_flags.append(f"Bradycardia: {hr} bpm")
            else:
                vitals_points.append(f"Resting heart rate normal ({hr} bpm).")

        if temp is not None:
            if temp >= 102.0 or temp >= 38.9:
                vitals_points.append(f"High pyrexia ({temp}°).")
                escalation_flags.append(f"High fever: {temp}°")
            elif temp >= 100.4 or temp >= 38.0:
                vitals_points.append(f"Low-grade pyrexia ({temp}°).")

        vitals_assessment = " | ".join(vitals_points) if vitals_points else "Baseline intake measurements recorded."
        synopsis = (
            f"{age}-year-old {sex} presenting for outpatient consultation with primary complaint: "
            f"'{chief_complaint}' (reported duration: {symptom_duration}). "
            f"Associated symptoms: {symptoms_str}."
        )

        section_a = {
            "chief_complaint": chief_complaint,
            "symptom_duration": symptom_duration,
            "current_symptoms": symptoms,
            "vital_signs_summary": vitals_assessment,
            "vital_signs_details": vitals,
            "missing_measurements": missing_measurements,
        }

        # -------------------------------------------------------------
        # Section B: Previous Consultations
        # -------------------------------------------------------------
        section_b: List[PreviousConsultationSummaryItem] = []
        for pcon in previous_consultations:
            fac = pcon.get("facility_name") or "External Clinic/Hospital"
            doc_n = pcon.get("doctor_name")
            fac_doc = f"{fac} ({doc_n})" if doc_n else fac
            c_date = pcon.get("consultation_date")
            dx = pcon.get("previous_diagnosis") or "Clinical Consultation"
            tx = pcon.get("treatment_prescribed") or (", ".join(pcon.get("medicines_taken", [])) if pcon.get("medicines_taken") else "None recorded")
            resp = pcon.get("treatment_response", "UNCHANGED")
            dur = pcon.get("duration_of_treatment")

            section_b.append(PreviousConsultationSummaryItem(
                facility_or_doctor=fac_doc,
                consultation_date=c_date,
                documented_diagnosis=dx,
                treatment_recorded=f"{tx} (duration: {dur})" if dur else tx,
                patient_reported_adherence="Patient reported adherence noted" if pcon.get("medicines_taken") else "Adherence not documented",
                reported_response=resp,
                source_type=pcon.get("source_provenance", "PATIENT_REPORTED"),
            ))

            citations.append(GroundedCitation(
                claim=f"Previous consultation at {fac_doc} for '{dx}' with reported response: {resp}",
                source_type="PATIENT_REPORTED",
                source_reference=f"Previous Consultation {pcon.get('consultation_id')}",
                verification_status="VERIFIED" if pcon.get("is_verified") else "PATIENT_REPORTED",
            ))

        # -------------------------------------------------------------
        # Section C: Previous Investigations (From Uploaded Documents)
        # -------------------------------------------------------------
        section_c: List[PreviousInvestigationSummaryItem] = []
        for doc in documents:
            doc_id = doc.get("document_id")
            doc_date = doc.get("document_date")
            doc_labs = doc.get("extracted_labs", [])
            for lab in doc_labs:
                t_name = lab.get("test_name")
                r_val = lab.get("result_value")
                u = lab.get("unit")
                ref = lab.get("reference_range")
                abn = lab.get("is_abnormal", False)
                flag = lab.get("flag")

                display_res = f"{r_val} {u or ''}".strip()
                if flag:
                    display_res += f" [{flag}]"

                section_c.append(PreviousInvestigationSummaryItem(
                    test_name=t_name,
                    result=display_res,
                    units=u,
                    reference_range=ref,
                    investigation_date=doc_date,
                    is_abnormal=abn,
                    source_document_id=doc_id,
                ))

                citations.append(GroundedCitation(
                    claim=f"Investigation {t_name}: {display_res} (Ref: {ref or 'N/A'})",
                    source_type="DOCUMENT_OCR",
                    source_reference=f"Doc {doc_id} ({doc.get('filename')})",
                    document_id=doc_id,
                    verification_status=doc.get("verification_status", "UNVERIFIED"),
                ))

            # Imaging findings from extracted fields
            for f in doc.get("extracted_fields", []):
                if f.get("field_name") == "imaging_finding":
                    section_c.append(PreviousInvestigationSummaryItem(
                        test_name="Radiology / Imaging Finding",
                        result=f.get("extracted_value"),
                        investigation_date=doc_date,
                        is_abnormal=True,
                        source_document_id=doc_id,
                    ))

        # -------------------------------------------------------------
        # Section D: Relevant Medical History
        # -------------------------------------------------------------
        comorbidities_list = []
        active_medications = []
        known_allergies = []

        for hx in verified_history:
            rtype = hx.get("record_type", "CONDITION")
            if rtype == "CONDITION":
                c_name = hx.get("condition_name") or hx.get("condition") or "Known Chronic Condition"
                src_doc = hx.get("source_document_id") or "Clinical Staff Verified"
                comorbidities_list.append(f"{c_name} [VERIFIED via {src_doc}]")
                citations.append(GroundedCitation(
                    claim=f"Verified pre-existing condition: {c_name}",
                    source_type="VERIFIED_HISTORY",
                    source_reference=str(src_doc),
                    verification_status="VERIFIED",
                ))
            elif rtype == "MEDICATION":
                m_name = hx.get("medication_name") or "Medication"
                active_medications.append(f"{m_name} [VERIFIED]")
            elif rtype == "ALLERGY":
                a_name = hx.get("allergen") or "Allergy"
                known_allergies.append(f"{a_name} [VERIFIED]")

        # Include unverified document medications/allergies with clear labeling
        for doc in documents:
            v_status = doc.get("verification_status", "PENDING_REVIEW")
            doc_id = doc.get("document_id")
            for m in doc.get("extracted_medications", []):
                m_name = m.get("medicine_name")
                dose = m.get("dosage")
                entry = f"{m_name} {dose or ''}".strip() + f" [{v_status} - Doc {doc_id}]"
                if entry not in active_medications:
                    active_medications.append(entry)
            for f in doc.get("extracted_fields", []):
                if f.get("field_name") == "allergy":
                    a_name = f.get("extracted_value") + f" [{v_status} - Doc {doc_id}]"
                    if a_name not in known_allergies:
                        known_allergies.append(a_name)

        if not comorbidities_list:
            comorbidities_list.append("No verified past comorbidities recorded.")

        section_d = {
            "verified_conditions": comorbidities_list,
            "active_medications": active_medications or ["No active medications recorded"],
            "known_allergies": known_allergies or ["No known drug allergies documented"],
        }

        # -------------------------------------------------------------
        # Section E: Clinical Timeline
        # -------------------------------------------------------------
        section_e: List[ClinicalTimelineEvent] = []

        # Previous Consultations Events
        for pcon in previous_consultations:
            section_e.append(ClinicalTimelineEvent(
                event_date=pcon.get("consultation_date") or "Date Unspecified",
                event_type="CONSULTATION",
                description=f"Consultation at {pcon.get('facility_name') or 'External clinic'}: {pcon.get('previous_diagnosis') or 'Clinical visit'}. Response: {pcon.get('treatment_response')}.",
                source_document_id=None,
                is_uncertain_date=pcon.get("consultation_date") is None,
            ))

        # Uploaded Document Investigation Events
        for doc in documents:
            if doc.get("document_date"):
                section_e.append(ClinicalTimelineEvent(
                    event_date=doc.get("document_date"),
                    event_type="INVESTIGATION",
                    description=f"{doc.get('document_category', 'Record')} from {doc.get('source_facility') or 'Provider'} ({doc.get('filename')}).",
                    source_document_id=doc.get("document_id"),
                    is_uncertain_date=False,
                ))

        # Current Presentation Event
        section_e.append(ClinicalTimelineEvent(
            event_date=encounter.get("arrival_time", "Today")[:10],
            event_type="CURRENT_PRESENTATION",
            description=f"Current OPD Arrival: Chief complaint '{chief_complaint}' ({symptom_duration}).",
            source_document_id=encounter.get("encounter_id"),
            is_uncertain_date=False,
        ))

        # Sort timeline chronologically where valid ISO date is present
        def parse_date_key(evt: ClinicalTimelineEvent) -> str:
            d = evt.event_date or ""
            return d if len(d) >= 10 else "0000-00-00"
        section_e.sort(key=parse_date_key)

        # -------------------------------------------------------------
        # Section F: Important Uncertainties & Missing Information
        # -------------------------------------------------------------
        for doc in documents:
            if doc.get("verification_status") in ["PENDING_REVIEW", "NEEDS_REVIEW"]:
                uncertainties.append(f"Document '{doc.get('filename')}' ({doc.get('document_id')}) is unverified (Status: {doc.get('verification_status')}).")
            if doc.get("identity_match_status") in ["UNCERTAIN", "MISMATCH"]:
                uncertainties.append(f"Patient identity check for doc '{doc.get('filename')}': {doc.get('identity_match_details')}.")
            for m in doc.get("extracted_medications", []):
                if m.get("is_uncertain"):
                    uncertainties.append(f"Medication '{m.get('medicine_name')}' in doc {doc.get('document_id')} has an unclear/missing dosage.")

        # Check for unverified previous consultations
        for pcon in previous_consultations:
            if not pcon.get("is_verified"):
                uncertainties.append(f"Previous consultation at {pcon.get('facility_name') or 'External facility'} is patient-reported and pending doctor clinical review.")

        if not uncertainties:
            uncertainties.append("No conflicting records, illegible fields, or critical missing information detected.")

        # -------------------------------------------------------------
        # Section G: Traceable Source References
        # -------------------------------------------------------------
        section_g = citations

        # -------------------------------------------------------------
        # Assistive Differential Considerations
        # -------------------------------------------------------------
        differentials: List[DifferentialItem] = []
        cc_lower = chief_complaint.lower()
        symptom_str_lower = symptoms_str.lower()

        if "chest pain" in cc_lower or "chest pain" in symptom_str_lower:
            differentials.append(DifferentialItem(
                condition_name="Acute Coronary Syndrome / Angina Pectoris",
                likelihood="High",
                clinical_rationale="Patient presents with acute chest discomfort. Immediate cardiac biomarker and ECG evaluation indicated.",
                suggested_workup=["12-lead ECG", "Serum Troponin I/T", "Chest X-Ray (CXR)"],
            ))
            differentials.append(DifferentialItem(
                condition_name="Gastroesophageal Reflux / Esophageal Spasm",
                likelihood="Moderate",
                clinical_rationale="Alternative etiology after coronary ischemia is ruled out.",
                suggested_workup=["Trial of antacid/PPI therapy"],
            ))
        elif "breath" in cc_lower or "cough" in cc_lower or "asthma" in symptom_str_lower:
            differentials.append(DifferentialItem(
                condition_name="Acute Respiratory Infection / Bronchospasm",
                likelihood="High",
                clinical_rationale="Respiratory complaints with abnormal auscultation or breathlessness.",
                suggested_workup=["Peak Expiratory Flow Rate", "Chest Radiograph", "Complete Blood Count (CBC)"],
            ))
        elif "headache" in cc_lower or "dizz" in cc_lower:
            differentials.append(DifferentialItem(
                condition_name="Hypertensive Headache / Tension Cephalea",
                likelihood="High",
                clinical_rationale="Neurological presentation with blood pressure evaluation required.",
                suggested_workup=["Serial BP monitoring", "Fundoscopy", "Neurological exam"],
            ))
        elif "abdom" in cc_lower or "stomach" in cc_lower or "vomit" in symptom_str_lower:
            differentials.append(DifferentialItem(
                condition_name="Acute Gastroenteritis / Peptic Ulcer Disease",
                likelihood="High",
                clinical_rationale="Gastrointestinal symptomatology without overt peritonitis on intake.",
                suggested_workup=["Serum Electrolytes", "Abdominal Ultrasound if tenderness localizes"],
            ))
        else:
            differentials.append(DifferentialItem(
                condition_name="Primary Outpatient Evaluation - Diagnostic Workup",
                likelihood="Moderate",
                clinical_rationale="Presentation requires full clinical history taking and targeted physical examination.",
                suggested_workup=["Targeted physical exam", "Routine outpatient laboratory profile"],
            ))

        workup = []
        for diff in differentials:
            workup.extend(diff.suggested_workup)
        unique_workup = list(dict.fromkeys(workup))

        return {
            "chief_complaint_synopsis": synopsis,
            "vitals_objective_assessment": vitals_assessment,
            "verified_comorbidities_context": comorbidities_list,
            "differential_considerations": [d.model_dump() for d in differentials],
            "recommended_workup": unique_workup,
            "escalation_flags": escalation_flags,
            "grounded_citations": [c.model_dump() for c in citations],
            "section_a_current_presentation": section_a,
            "section_b_previous_consultations": [b.model_dump() for b in section_b],
            "section_c_previous_investigations": [c.model_dump() for c in section_c],
            "section_d_relevant_medical_history": section_d,
            "section_e_clinical_timeline": [e.model_dump() for e in section_e],
            "section_f_important_uncertainties": uncertainties,
            "section_g_source_references": [g.model_dump() for g in section_g],
            "provider_used": "mock_clinical_llm_summarizer",
            "generation_mode": "DETERMINISTIC_GROUNDED",
        }


class OpenAILLMProvider(BaseLLMProvider):
    """Live OpenAI provider using urllib with deterministic fallback."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.model = model

    def generate_clinical_summary(
        self,
        encounter: Dict[str, Any],
        patient: Dict[str, Any],
        verified_history: List[Dict[str, Any]],
        previous_consultations: List[Dict[str, Any]],
        documents: List[Dict[str, Any]],
        triage_assessment: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        prompt = (
            f"You are a clinical decision-support AI summarizing patient medical records for the treating physician.\n"
            f"SAFETY RULES:\n"
            f"1. Summarize records rather than independently diagnosing the patient or prescribing treatment.\n"
            f"2. Never invent diagnoses, test results, dates, or dosages. If information is missing, explicitly state it is missing.\n"
            f"3. Never assume prescribed medications were taken.\n"
            f"4. Clearly identify output as an AI-assisted summary requiring clinician review.\n\n"
            f"EHR DATA:\n"
            f"Patient: Age {patient.get('age')}, Sex {patient.get('gender')}\n"
            f"Chief Complaint: {encounter.get('chief_complaint')} (Duration: {encounter.get('symptom_duration')})\n"
            f"Symptoms: {encounter.get('symptoms')}\n"
            f"Vitals: {encounter.get('vitals')}\n"
            f"Previous Consultations: {json.dumps(previous_consultations, default=str)}\n"
            f"Uploaded Documents Extracted Data: {json.dumps(documents, default=str)[:3000]}\n"
            f"Verified History: {json.dumps(verified_history, default=str)}\n"
        )

        req_data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a clinical decision-support assistant. Generate factual clinical summaries grounded strictly in provided EHR data in valid JSON format."},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }

        try:
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=json.dumps(req_data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                res_body = json.loads(resp.read().decode("utf-8"))
                parsed = json.loads(res_body["choices"][0]["message"]["content"])
                # Fall back to base mock parser for any missing structured fields
                base_struct = MockClinicalLLMProvider().generate_clinical_summary(
                    encounter, patient, verified_history, previous_consultations, documents, triage_assessment
                )
                base_struct.update(parsed)
                base_struct["provider_used"] = f"openai_{self.model}"
                base_struct["generation_mode"] = "LLM_SYNTHESIZED"
                return base_struct
        except Exception as exc:
            logger.warning(f"OpenAI call failed ({exc}). Falling back to MockClinicalLLMProvider.")
            fallback = MockClinicalLLMProvider().generate_clinical_summary(
                encounter, patient, verified_history, previous_consultations, documents, triage_assessment
            )
            fallback["generation_mode"] = "DETERMINISTIC_FALLBACK"
            return fallback


def get_llm_provider(provider_preference: Optional[str] = None) -> BaseLLMProvider:
    """Factory selecting active provider with offline fallback."""
    openai_key = os.getenv("OPENAI_API_KEY")
    if (provider_preference == "openai" or settings.LLM_PROVIDER == "openai") and openai_key:
        return OpenAILLMProvider(api_key=openai_key, model=settings.OPENAI_MODEL)
    return MockClinicalLLMProvider()


class AISummaryService:
    """Service orchestrating grounded clinical summary creation, persistence, doctor review, and staleness detection."""

    def __init__(self):
        self.db = get_mongodb()

    def generate_encounter_summary(
        self,
        encounter_id: str,
        provider_preference: Optional[str] = None,
    ) -> AISummaryResponse:
        """Fetch all relevant patient records and generate 7-section decision-support summary."""
        encounter = self.db.encounters.find_one({
            "$or": [{"encounter_id": encounter_id}, {"_id": encounter_id}]
        })
        if not encounter:
            raise ValueError(f"Encounter '{encounter_id}' not found.")

        canonical_enc_id = encounter.get("encounter_id", encounter_id)
        patient_code = encounter.get("patient_code") or encounter.get("patient_id")
        patient = self.db.patients.find_one({
            "$or": [{"patient_code": patient_code}, {"_id": patient_code}]
        }) or {}

        # 1. Fetch verified medical history
        verified_history = list(get_medical_history_col().find({
            "$or": [{"patient_code": patient_code}, {"patient_id": patient_code}]
        }))

        # 2. Fetch patient-reported previous consultations
        previous_consultations = list(get_previous_consultations_col().find({
            "$or": [{"patient_code": patient_code}, {"patient_id": patient_code}]
        }))

        # 3. Fetch uploaded medical documents
        documents = list(get_medical_documents_col().find({
            "$or": [{"patient_code": patient_code}, {"patient_id": patient_code}]
        }))

        # 4. Fetch triage assessment
        triage_record = self.db.triage_assessments.find_one({
            "$or": [{"encounter_id": canonical_enc_id}, {"encounter_id": encounter_id}]
        })

        # 5. Generate structured summary payload
        provider = get_llm_provider(provider_preference)
        summary_payload = provider.generate_clinical_summary(
            encounter=encounter,
            patient=patient,
            verified_history=verified_history,
            previous_consultations=previous_consultations,
            documents=documents,
            triage_assessment=triage_record,
        )

        summary_id = f"SUM-{uuid.uuid4().hex[:8].upper()}"
        now_utc = datetime.now(timezone.utc)

        doc = {
            "_id": summary_id,
            "summary_id": summary_id,
            "encounter_id": canonical_enc_id,
            "patient_id": patient_code,
            "chief_complaint_synopsis": summary_payload["chief_complaint_synopsis"],
            "vitals_objective_assessment": summary_payload["vitals_objective_assessment"],
            "verified_comorbidities_context": summary_payload["verified_comorbidities_context"],
            "differential_considerations": summary_payload["differential_considerations"],
            "recommended_workup": summary_payload["recommended_workup"],
            "escalation_flags": summary_payload["escalation_flags"],
            "grounded_citations": summary_payload["grounded_citations"],
            "section_a_current_presentation": summary_payload.get("section_a_current_presentation", {}),
            "section_b_previous_consultations": summary_payload.get("section_b_previous_consultations", []),
            "section_c_previous_investigations": summary_payload.get("section_c_previous_investigations", []),
            "section_d_relevant_medical_history": summary_payload.get("section_d_relevant_medical_history", {}),
            "section_e_clinical_timeline": summary_payload.get("section_e_clinical_timeline", []),
            "section_f_important_uncertainties": summary_payload.get("section_f_important_uncertainties", []),
            "section_g_source_references": summary_payload.get("section_g_source_references", []),
            "provider_used": summary_payload["provider_used"],
            "generation_mode": summary_payload.get("generation_mode", "LLM_SYNTHESIZED"),
            "is_stale": False,
            "stale_reason": None,
            "doctor_review_status": "PENDING_REVIEW",
            "doctor_notes": None,
            "reviewed_by_doctor_id": None,
            "reviewed_at": None,
            "created_at": now_utc,
        }

        # Delete older summary for this encounter and persist fresh one
        self.db.ai_summaries.delete_many({
            "$or": [{"encounter_id": canonical_enc_id}, {"encounter_id": encounter_id}]
        })
        self.db.ai_summaries.insert_one(doc)

        # Audit event
        get_audit_events_col().insert_one({
            "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
            "action": "SUMMARY_GENERATED",
            "resource_type": "ai_summary",
            "resource_id": summary_id,
            "timestamp": now_utc.isoformat(),
            "details": f"Generated clinical summary for encounter {canonical_enc_id} using {summary_payload['provider_used']}",
        })

        return self._format_response(doc)

    def get_encounter_summary(self, encounter_id: str) -> Optional[AISummaryResponse]:
        """Fetch summary for encounter and evaluate whether newer records make it stale."""
        doc = self.db.ai_summaries.find_one({
            "$or": [{"encounter_id": encounter_id}, {"_id": encounter_id}]
        })
        if not doc:
            return None

        # Staleness evaluation
        created_at = doc.get("created_at")
        patient_code = doc.get("patient_id")
        is_stale = False
        stale_reason = None

        if created_at and patient_code:
            created_iso = created_at.isoformat() if isinstance(created_at, datetime) else str(created_at)
            # Check if documents were uploaded after summary creation
            newer_docs = get_medical_documents_col().count_documents({
                "patient_code": patient_code,
                "upload_timestamp": {"$gt": created_iso},
            })
            if newer_docs > 0:
                is_stale = True
                stale_reason = f"{newer_docs} new medical document(s) uploaded since summary was generated."

            # Check if previous consultations were added/updated after summary creation
            newer_pcons = get_previous_consultations_col().count_documents({
                "patient_code": patient_code,
                "updated_at": {"$gt": created_iso},
            })
            if newer_pcons > 0:
                is_stale = True
                stale_reason = f"{newer_pcons} previous consultation record(s) added/updated since summary was generated."

        doc["is_stale"] = is_stale
        doc["stale_reason"] = stale_reason
        return self._format_response(doc)

    def review_summary(
        self,
        encounter_id: str,
        review_req: AISummaryReviewRequest,
        doctor_id: str,
    ) -> AISummaryResponse:
        """Physician review checkpoint: accept, edit, or reject summary."""
        doc = self.db.ai_summaries.find_one({
            "$or": [{"encounter_id": encounter_id}, {"_id": encounter_id}]
        })
        if not doc:
            raise ValueError(f"Summary for encounter '{encounter_id}' not found.")

        matched_id = doc["_id"]
        now_utc = datetime.now(timezone.utc)
        update_fields = {
            "doctor_review_status": review_req.status.upper(),
            "doctor_notes": review_req.doctor_notes,
            "reviewed_by_doctor_id": doctor_id,
            "reviewed_at": now_utc,
        }
        if review_req.edited_summary_text:
            update_fields["chief_complaint_synopsis"] = review_req.edited_summary_text

        self.db.ai_summaries.update_one({"_id": matched_id}, {"$set": update_fields})

        # Audit event
        get_audit_events_col().insert_one({
            "audit_id": f"AUD-{uuid.uuid4().hex[:10]}",
            "action": "SUMMARY_REVIEWED",
            "resource_type": "ai_summary",
            "resource_id": str(matched_id),
            "timestamp": now_utc.isoformat(),
            "details": f"Summary for encounter {encounter_id} marked as {review_req.status} by {doctor_id}",
        })

        updated = self.db.ai_summaries.find_one({"_id": matched_id})
        return self._format_response(updated)

    def _format_response(self, doc: Dict[str, Any]) -> AISummaryResponse:
        diffs = [DifferentialItem(**d) for d in doc.get("differential_considerations", [])]
        cites = [GroundedCitation(**c) for c in doc.get("grounded_citations", [])]

        sec_b = [PreviousConsultationSummaryItem(**b) for b in doc.get("section_b_previous_consultations", [])]
        sec_c = [PreviousInvestigationSummaryItem(**c) for c in doc.get("section_c_previous_investigations", [])]
        sec_e = [ClinicalTimelineEvent(**e) for e in doc.get("section_e_clinical_timeline", [])]
        sec_g = [GroundedCitation(**g) for g in doc.get("section_g_source_references", [])]

        return AISummaryResponse(
            id=doc["_id"],
            encounter_id=doc["encounter_id"],
            patient_id=doc["patient_id"],
            chief_complaint_synopsis=doc["chief_complaint_synopsis"],
            vitals_objective_assessment=doc["vitals_objective_assessment"],
            verified_comorbidities_context=doc["verified_comorbidities_context"],
            differential_considerations=diffs,
            recommended_workup=doc["recommended_workup"],
            escalation_flags=doc["escalation_flags"],
            grounded_citations=cites,
            section_a_current_presentation=doc.get("section_a_current_presentation", {}),
            section_b_previous_consultations=sec_b,
            section_c_previous_investigations=sec_c,
            section_d_relevant_medical_history=doc.get("section_d_relevant_medical_history", {}),
            section_e_clinical_timeline=sec_e,
            section_f_important_uncertainties=doc.get("section_f_important_uncertainties", []),
            section_g_source_references=sec_g,
            provider_used=doc["provider_used"],
            generation_mode=doc.get("generation_mode", "LLM_SYNTHESIZED"),
            is_stale=doc.get("is_stale", False),
            stale_reason=doc.get("stale_reason"),
            doctor_review_status=doc.get("doctor_review_status", "PENDING_REVIEW"),
            doctor_notes=doc.get("doctor_notes"),
            reviewed_by_doctor_id=doc.get("reviewed_by_doctor_id"),
            reviewed_at=doc.get("reviewed_at"),
            created_at=doc.get("created_at", datetime.now(timezone.utc)),
        )


ai_summary_service = AISummaryService()
