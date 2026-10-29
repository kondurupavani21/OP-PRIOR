import React, { useState, useEffect, useRef } from 'react';
import {
  Upload,
  FileText,
  CheckCircle2,
  AlertTriangle,
  Clock,
  RotateCcw,
  Eye,
  Download,
  Check,
  X,
  ShieldCheck,
  ShieldAlert,
  HelpCircle,
  Pill,
  Activity,
  Calendar,
  Building2,
  User,
  AlertCircle,
} from 'lucide-react';
import api from '../../services/api';

const DOCUMENT_CATEGORIES = [
  { value: 'PRESCRIPTION', label: '1. Prescription' },
  { value: 'LAB_REPORT', label: '2. Laboratory Report' },
  { value: 'RADIOLOGY_REPORT', label: '3. Radiology / Imaging Report' },
  { value: 'DISCHARGE_SUMMARY', label: '4. Discharge Summary' },
  { value: 'CONSULTATION_NOTE', label: '5. Consultation Notes' },
  { value: 'EMR_EXPORT', label: '6. Electronic Medical Record (EMR) Export' },
  { value: 'OTHER', label: '7. Other Medical Document' },
];

export default function MedicalDocumentUpload({
  patientCode,
  encounterId = null,
  readOnly = false,
  canVerify = false,
  onDocumentUploaded = null,
  onDocumentVerified = null,
}) {
  const fileInputRef = useRef(null);

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState(null);
  const [category, setCategory] = useState('PRESCRIPTION');
  const [sourceFacility, setSourceFacility] = useState('');
  const [sourceDoctor, setSourceDoctor] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState('');
  const [uploadSuccess, setUploadSuccess] = useState('');

  // Patient Document List State
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(false);

  // Preview & Verification Modal State
  const [previewDoc, setPreviewDoc] = useState(null);
  const [previewContent, setPreviewContent] = useState(null);
  const [isLoadingPreview, setIsLoadingPreview] = useState(false);
  const [verificationNotes, setVerificationNotes] = useState('');
  const [isVerifying, setIsVerifying] = useState(false);

  // Load documents for target patient
  const loadDocuments = async () => {
    if (!patientCode) return;
    setIsLoadingDocs(true);
    try {
      const docs = await api.getPatientDocuments(patientCode);
      setDocuments(Array.isArray(docs) ? docs : []);
    } catch (err) {
      console.warn('Failed to fetch patient documents:', err.message);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  useEffect(() => {
    loadDocuments();
  }, [patientCode]);

  // Handle Drag & Drop
  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFileSelected(e.target.files[0]);
    }
  };

  const handleFileSelected = (file) => {
    setUploadError('');
    setUploadSuccess('');

    // Client-side extension validation
    const allowed = ['.pdf', '.png', '.jpg', '.jpeg', '.txt'];
    const name = file.name.toLowerCase();
    const isAllowed = allowed.some((ext) => name.endsWith(ext));
    if (!isAllowed) {
      setUploadError('Unsupported file format. Please upload a PDF, PNG, JPG/JPEG, or TXT file.');
      return;
    }

    // Size limit check (15 MB)
    if (file.size > 15 * 1024 * 1024) {
      setUploadError('File size exceeds the 15 MB maximum limit.');
      return;
    }

    setSelectedFile(file);
  };

  const handleUploadSubmit = async (e) => {
    e?.preventDefault();
    if (!selectedFile || !patientCode) return;

    setIsUploading(true);
    setUploadError('');
    setUploadSuccess('');

    try {
      const resp = await api.uploadDocument(patientCode, selectedFile, category, {
        document_category: category,
        encounter_id: encounterId,
        source_facility: sourceFacility.trim() || null,
        source_doctor: sourceDoctor.trim() || null,
      });

      setUploadSuccess(`Successfully uploaded and processed "${selectedFile.name}" with OCR!`);
      setSelectedFile(null);
      setSourceFacility('');
      setSourceDoctor('');
      if (fileInputRef.current) fileInputRef.current.value = '';

      await loadDocuments();
      if (onDocumentUploaded) onDocumentUploaded(resp);
    } catch (err) {
      setUploadError(err.message || 'Document upload and OCR processing failed.');
    } finally {
      setIsUploading(false);
    }
  };

  // Inspect & Preview Document
  const handleOpenPreview = async (doc) => {
    setPreviewDoc(doc);
    setIsLoadingPreview(true);
    setVerificationNotes(doc.reviewer_notes || '');
    try {
      const content = await api.getDocumentContent(doc.document_id);
      setPreviewContent(content);
    } catch (err) {
      setPreviewContent({
        extracted_text: doc.extracted_text || 'Content preview could not be loaded.',
        extracted_fields: doc.extracted_fields || [],
        extracted_labs: doc.extracted_labs || [],
        extracted_medications: doc.extracted_medications || [],
      });
    } finally {
      setIsLoadingPreview(false);
    }
  };

  // Verify Document Action
  const handleVerify = async (status) => {
    if (!previewDoc) return;
    setIsVerifying(true);
    try {
      const confirmedConditions = (previewDoc.extracted_fields || [])
        .filter((f) => f.field_name === 'condition')
        .map((f) => f.corrected_value || f.extracted_value);

      const confirmedMeds = (previewDoc.extracted_medications || []).map(
        (m) => m.medicine_name
      );

      const confirmedAllergies = (previewDoc.extracted_fields || [])
        .filter((f) => f.field_name === 'allergy')
        .map((f) => f.corrected_value || f.extracted_value);

      await api.verifyDocument(previewDoc.document_id, {
        verification_status: status,
        reviewer_notes: verificationNotes.trim() || (status === 'VERIFIED' ? 'Approved by attending clinician' : 'Rejected upon review'),
        verified_conditions: confirmedConditions,
        verified_medications: confirmedMeds,
        verified_allergies: confirmedAllergies,
        confirm_patient_identity: true,
      });

      await loadDocuments();
      setPreviewDoc(null);
      if (onDocumentVerified) onDocumentVerified(previewDoc.document_id, status);
    } catch (err) {
      alert(`Verification failed: ${err.message}`);
    } finally {
      setIsVerifying(false);
    }
  };

  // Reprocess / Retry OCR
  const handleReprocess = async (docId) => {
    try {
      await api.reprocessDocument(docId, 'AUTO');
      await loadDocuments();
    } catch (err) {
      alert(`Retry OCR failed: ${err.message}`);
    }
  };

  return (
    <div className="space-y-6">
      {/* SECTION 1: UPLOAD CARD */}
      {!readOnly && (
        <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100">
            <Upload className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              Upload Previous Medical Records (Prescriptions, Labs, Scans)
            </h3>
          </div>

          <p className="text-xs text-slate-500">
            Upload patient-carried records from external clinics or hospitals. The system automatically performs direct text extraction and OCR, flags uncertain handwriting, and drafts structured clinical findings for doctor review.
          </p>

          {uploadError && (
            <div className="p-3.5 rounded-xl bg-rose-50 border border-rose-200 flex items-center gap-2 text-rose-700 text-xs font-semibold animate-in fade-in">
              <AlertCircle className="w-4 h-4 shrink-0 text-rose-500" />
              <span>{uploadError}</span>
            </div>
          )}

          {uploadSuccess && (
            <div className="p-3.5 rounded-xl bg-emerald-50 border border-emerald-200 flex items-center gap-2 text-emerald-800 text-xs font-semibold animate-in fade-in">
              <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-600" />
              <span>{uploadSuccess}</span>
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {/* Category Selector */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Document Category *
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500 bg-white"
              >
                {DOCUMENT_CATEGORIES.map((c) => (
                  <option key={c.value} value={c.value}>
                    {c.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Source Hospital / Clinic */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Previous Hospital / Clinic (Optional)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <Building2 className="w-3.5 h-3.5" />
                </div>
                <input
                  type="text"
                  value={sourceFacility}
                  onChange={(e) => setSourceFacility(e.target.value)}
                  placeholder="e.g. City Care Hospital"
                  className="w-full pl-8 pr-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>

            {/* Source Doctor */}
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Previous Doctor Name (Optional)
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                  <User className="w-3.5 h-3.5" />
                </div>
                <input
                  type="text"
                  value={sourceDoctor}
                  onChange={(e) => setSourceDoctor(e.target.value)}
                  placeholder="e.g. Dr. Verma"
                  className="w-full pl-8 pr-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500"
                />
              </div>
            </div>
          </div>

          {/* Drag & Drop Box */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition ${
              isDragging
                ? 'border-blue-500 bg-blue-50/50'
                : 'border-slate-300 hover:border-blue-400 bg-slate-50/50'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".pdf,.png,.jpg,.jpeg,.txt"
              className="hidden"
            />
            <div className="w-10 h-10 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center mx-auto mb-2">
              <Upload className="w-5 h-5" />
            </div>
            {selectedFile ? (
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-800">{selectedFile.name}</p>
                <p className="text-[11px] text-slate-400">
                  {(selectedFile.size / 1024).toFixed(1)} KB • Click or drag to replace
                </p>
              </div>
            ) : (
              <div className="space-y-1">
                <p className="text-xs font-bold text-slate-700">
                  Click to select or drag and drop medical document
                </p>
                <p className="text-[11px] text-slate-400">
                  Supports PDF (scanned & text-based), JPEG/JPG, PNG, TXT (Max 15 MB)
                </p>
              </div>
            )}
          </div>

          {selectedFile && (
            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={() => setSelectedFile(null)}
                className="px-4 py-2 rounded-xl border border-slate-300 text-slate-600 hover:bg-slate-100 text-xs font-semibold cursor-pointer"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleUploadSubmit}
                disabled={isUploading}
                className="px-5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold shadow-md shadow-blue-500/20 transition cursor-pointer flex items-center gap-1.5 disabled:opacity-50"
              >
                {isUploading ? (
                  <>
                    <RotateCcw className="w-3.5 h-3.5 animate-spin" />
                    <span>Processing Document OCR...</span>
                  </>
                ) : (
                  <>
                    <Upload className="w-3.5 h-3.5" />
                    <span>Upload & Process with OCR</span>
                  </>
                )}
              </button>
            </div>
          )}
        </div>
      )}

      {/* SECTION 2: UPLOADED DOCUMENTS TABLE / CARDS */}
      <div className="bg-white rounded-2xl p-6 border border-slate-200/90 shadow-xs space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <FileText className="w-4 h-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900">
              Attached Medical Records ({documents.length})
            </h3>
          </div>
          <button
            type="button"
            onClick={loadDocuments}
            disabled={isLoadingDocs}
            className="text-xs text-blue-600 hover:text-blue-700 font-semibold flex items-center gap-1 cursor-pointer"
          >
            <RotateCcw className={`w-3 h-3 ${isLoadingDocs ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {documents.length === 0 ? (
          <div className="text-center py-8 bg-slate-50/70 rounded-xl border border-dashed border-slate-200">
            <FileText className="w-8 h-8 text-slate-300 mx-auto mb-2" />
            <p className="text-xs font-semibold text-slate-600">No medical documents attached yet.</p>
            <p className="text-[11px] text-slate-400 mt-0.5">
              Patient registration and queue prioritization proceed smoothly with or without documents.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {documents.map((doc) => {
              const isVerified = doc.verification_status === 'VERIFIED';
              const isNeedsReview = doc.verification_status === 'NEEDS_REVIEW';
              const isRejected = doc.verification_status === 'REJECTED';
              const isMatchUncertain = doc.identity_match_status === 'UNCERTAIN' || doc.identity_match_status === 'MISMATCH';

              return (
                <div
                  key={doc.document_id}
                  className="p-4 rounded-xl border border-slate-200 bg-slate-50/50 hover:bg-white transition flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs"
                >
                  <div className="space-y-1.5 flex-1 min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="font-bold text-slate-900 truncate">
                        {doc.filename}
                      </span>
                      <span className="px-2 py-0.5 rounded-md font-mono text-[10px] font-bold bg-blue-100/70 text-blue-700">
                        {doc.document_category || doc.document_type}
                      </span>

                      {/* Verification Status Badge */}
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${
                          isVerified
                            ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                            : isNeedsReview
                            ? 'bg-amber-100 text-amber-800 border border-amber-300'
                            : isRejected
                            ? 'bg-rose-100 text-rose-800 border border-rose-300'
                            : 'bg-blue-100 text-blue-800 border border-blue-300'
                        }`}
                      >
                        {doc.verification_status}
                      </span>

                      {/* Patient Identity Matching Warning Badge */}
                      {isMatchUncertain && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-amber-50 text-amber-800 border border-amber-300 flex items-center gap-1">
                          <AlertTriangle className="w-3 h-3 text-amber-600" />
                          <span>Identity Check: {doc.identity_match_status}</span>
                        </span>
                      )}

                      {/* Uncertain Fields Badge */}
                      {doc.has_uncertain_fields && (
                        <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-purple-50 text-purple-700 border border-purple-200">
                          Uncertain Fields Flagged
                        </span>
                      )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3 text-[11px] text-slate-500">
                      <span>Doc ID: <strong className="font-mono text-slate-700">{doc.document_id}</strong></span>
                      {doc.document_date && <span>Date: <strong>{doc.document_date}</strong></span>}
                      {doc.source_facility && <span>Facility: <strong>{doc.source_facility}</strong></span>}
                      <span>Engine: <strong className="text-slate-600">{doc.ocr_engine}</strong></span>
                    </div>

                    {/* Extracted items summary */}
                    <div className="flex flex-wrap gap-1.5 pt-1">
                      {(doc.extracted_fields || [])
                        .filter((f) => f.field_name === 'condition')
                        .map((f, fi) => (
                          <span key={fi} className="px-2 py-0.5 rounded bg-slate-200/70 text-slate-700 text-[10px] font-medium">
                            Dx: {f.extracted_value}
                          </span>
                        ))}
                      {(doc.extracted_medications || []).map((m, mi) => (
                        <span key={mi} className="px-2 py-0.5 rounded bg-blue-50 text-blue-800 border border-blue-100 text-[10px] font-medium">
                          Rx: {m.medicine_name} {m.dosage || ''}
                        </span>
                      ))}
                      {(doc.extracted_labs || []).map((l, li) => (
                        <span key={li} className={`px-2 py-0.5 rounded text-[10px] font-medium ${l.is_abnormal ? 'bg-rose-50 text-rose-800 border border-rose-200 font-bold' : 'bg-slate-100 text-slate-700'}`}>
                          Lab: {l.test_name} ({l.result_value} {l.unit || ''})
                        </span>
                      ))}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-2 shrink-0 pt-2 md:pt-0">
                    <button
                      type="button"
                      onClick={() => handleOpenPreview(doc)}
                      className="px-3 py-1.5 rounded-lg bg-blue-50 text-blue-700 hover:bg-blue-100 text-xs font-semibold transition flex items-center gap-1 cursor-pointer"
                      title="Inspect extracted text, labs, and verify fields"
                    >
                      <Eye className="w-3.5 h-3.5" />
                      <span>Inspect</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleReprocess(doc.document_id)}
                      className="p-1.5 rounded-lg text-slate-500 hover:text-slate-700 hover:bg-slate-100 transition cursor-pointer"
                      title="Retry OCR extraction"
                    >
                      <RotateCcw className="w-3.5 h-3.5" />
                    </button>

                    <a
                      href={`http://127.0.0.1:8000/api/v1/documents/${doc.document_id}/download`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="p-1.5 rounded-lg text-slate-500 hover:text-blue-600 hover:bg-blue-50 transition"
                      title="Download original file"
                    >
                      <Download className="w-3.5 h-3.5" />
                    </a>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* SECTION 3: INSPECTION & VERIFICATION MODAL */}
      {previewDoc && (
        <div className="fixed inset-0 z-50 bg-slate-900/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-3xl w-full max-h-[90vh] overflow-hidden flex flex-col shadow-2xl border border-slate-200 animate-in zoom-in-95">
            {/* Modal Header */}
            <div className="p-5 border-b border-slate-100 flex items-center justify-between bg-slate-50">
              <div className="space-y-0.5">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                    {previewDoc.document_id}
                  </span>
                  <span className="text-xs font-bold text-slate-800">{previewDoc.filename}</span>
                </div>
                <p className="text-[11px] text-slate-500">
                  Category: {previewDoc.document_category} • Engine: {previewDoc.ocr_engine}
                </p>
              </div>

              <button
                type="button"
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 rounded-xl text-slate-400 hover:text-slate-600 hover:bg-slate-200/50 cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="p-6 overflow-y-auto space-y-5 text-xs flex-1">
              {/* Patient Identity Check Alert */}
              {previewDoc.identity_match_status !== 'MATCHED' && (
                <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 space-y-1">
                  <div className="flex items-center gap-1.5 font-bold">
                    <ShieldAlert className="w-4 h-4 text-amber-600" />
                    <span>Identity Verification Warning ({previewDoc.identity_match_status})</span>
                  </div>
                  <p className="text-[11px] text-amber-800">
                    {previewDoc.identity_match_details || 'Detected patient identity printed on document requires clinician confirmation.'}
                  </p>
                </div>
              )}

              {/* Extracted Labs & Findings */}
              {previewDoc.extracted_labs && previewDoc.extracted_labs.length > 0 && (
                <div className="space-y-2">
                  <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider block">
                    Extracted Laboratory Investigations
                  </span>
                  <div className="border border-slate-200 rounded-xl overflow-hidden">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-50 border-b border-slate-200 text-[10px] text-slate-500 uppercase font-semibold">
                        <tr>
                          <th className="p-2.5">Test Name</th>
                          <th className="p-2.5">Observed Result</th>
                          <th className="p-2.5">Ref Range</th>
                          <th className="p-2.5">Flag</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-100">
                        {previewDoc.extracted_labs.map((lab, i) => (
                          <tr key={i} className={lab.is_abnormal ? 'bg-rose-50/40' : ''}>
                            <td className="p-2.5 font-semibold text-slate-800">{lab.test_name}</td>
                            <td className="p-2.5 font-bold">{lab.result_value} {lab.unit || ''}</td>
                            <td className="p-2.5 text-slate-500">{lab.reference_range || 'N/A'}</td>
                            <td className="p-2.5">
                              {lab.flag ? (
                                <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-rose-100 text-rose-800">
                                  {lab.flag}
                                </span>
                              ) : (
                                <span className="text-slate-400">Normal</span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Extracted Medications */}
              {previewDoc.extracted_medications && previewDoc.extracted_medications.length > 0 && (
                <div className="space-y-2">
                  <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider block">
                    Extracted Prescribed Medications
                  </span>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {previewDoc.extracted_medications.map((m, i) => (
                      <div key={i} className="p-2.5 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between">
                        <div>
                          <strong className="text-slate-800 block">💊 {m.medicine_name}</strong>
                          <span className="text-[11px] text-slate-500">
                            {m.dosage || 'Dosage uncertain'} • {m.frequency || 'Freq unspecified'} {m.duration ? `(${m.duration})` : ''}
                          </span>
                        </div>
                        {m.is_uncertain && (
                          <span className="px-1.5 py-0.5 rounded text-[9px] font-bold bg-amber-100 text-amber-800">
                            Uncertain Dose
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Raw Extracted Text Stream */}
              <div className="space-y-1.5">
                <span className="font-bold text-slate-800 uppercase text-[10px] tracking-wider block">
                  Extracted OCR Document Text
                </span>
                <pre className="p-3.5 rounded-xl bg-slate-900 text-slate-200 font-mono text-[11px] overflow-x-auto max-h-48 whitespace-pre-wrap leading-relaxed border border-slate-800">
                  {isLoadingPreview ? 'Loading document text...' : previewDoc.extracted_text || 'No text extracted.'}
                </pre>
              </div>

              {/* Clinician Review Notes */}
              {canVerify && (
                <div className="space-y-1.5 pt-2 border-t border-slate-100">
                  <label className="block text-xs font-semibold text-slate-700">
                    Clinician Review / Correction Notes
                  </label>
                  <textarea
                    rows="2"
                    value={verificationNotes}
                    onChange={(e) => setVerificationNotes(e.target.value)}
                    placeholder="Document verified by attending physician. Chronic condition confirmed..."
                    className="w-full px-3 py-2 rounded-xl border border-slate-200 text-xs text-slate-800 focus:outline-hidden focus:border-blue-500"
                  />
                </div>
              )}
            </div>

            {/* Modal Footer */}
            <div className="p-4 border-t border-slate-100 flex items-center justify-between bg-slate-50">
              <a
                href={`http://127.0.0.1:8000/api/v1/documents/${previewDoc.document_id}/download`}
                target="_blank"
                rel="noopener noreferrer"
                className="px-3.5 py-2 rounded-xl border border-slate-300 text-slate-700 text-xs font-semibold hover:bg-slate-100 transition flex items-center gap-1.5"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Original</span>
              </a>

              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setPreviewDoc(null)}
                  className="px-4 py-2 rounded-xl border border-slate-300 text-slate-600 hover:bg-slate-100 text-xs font-semibold cursor-pointer"
                >
                  Close
                </button>

                {canVerify && (
                  <>
                    <button
                      type="button"
                      disabled={isVerifying}
                      onClick={() => handleVerify('REJECTED')}
                      className="px-4 py-2 rounded-xl bg-rose-50 text-rose-700 hover:bg-rose-100 border border-rose-200 text-xs font-semibold transition cursor-pointer"
                    >
                      Reject Document
                    </button>
                    <button
                      type="button"
                      disabled={isVerifying}
                      onClick={() => handleVerify('VERIFIED')}
                      className="px-5 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold shadow-md shadow-emerald-600/20 transition cursor-pointer flex items-center gap-1.5"
                    >
                      <ShieldCheck className="w-4 h-4" />
                      <span>Verify & Commit to History</span>
                    </button>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
