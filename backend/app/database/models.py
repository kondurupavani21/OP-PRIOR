"""SQLAlchemy ORM models for MedQueue AI."""
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database.base import Base


def utc_now() -> datetime:
    """Return timezone-aware current UTC time."""
    return datetime.now(timezone.utc)


class User(Base):
    """Staff & Doctor user model."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), default="Doctor", nullable=False)  # Doctor, Receptionist, Admin
    department = Column(String(100), default="General Medicine", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    consultations = relationship("Consultation", back_populates="doctor")


class Patient(Base):
    """Patient master record model."""
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(String(64), unique=True, index=True, nullable=False)  # E.g. PAT-1001
    full_name = Column(String(255), nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String(32), default="Other", nullable=False)
    contact = Column(String(64), nullable=False)
    emergency_contact = Column(String(64), nullable=True)
    blood_group = Column(String(16), nullable=True)
    address = Column(String(255), nullable=True)
    chronic_conditions = Column(Text, nullable=True)  # JSON string or comma-separated
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    visits = relationship("Visit", back_populates="patient", cascade="all, delete-orphan")
    queue_entries = relationship("QueueItem", back_populates="patient", cascade="all, delete-orphan")
    consultations = relationship("Consultation", back_populates="patient", cascade="all, delete-orphan")


class Visit(Base):
    """Individual clinical visit and triage snapshot."""
    __tablename__ = "visits"

    id = Column(Integer, primary_key=True, index=True)
    visit_id = Column(String(64), unique=True, index=True, nullable=False)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    visit_date = Column(String(32), nullable=False)  # YYYY-MM-DD
    visit_time = Column(String(32), nullable=False)  # HH:MM AM/PM
    symptoms = Column(Text, nullable=False)          # JSON array or text
    temperature = Column(Float, default=98.6)        # °F
    heart_rate = Column(Integer, default=75)         # bpm
    spo2 = Column(Integer, default=98)               # %
    blood_pressure = Column(String(32), default="120/80")
    sugar_level = Column(Float, default=100.0)       # mg/dL
    previous_diseases = Column(Text, nullable=True)
    priority_score = Column(Integer, default=20, nullable=False)  # 0 to 100
    severity = Column(String(32), default="LOW", nullable=False)  # HIGH, MEDIUM, LOW
    risk_factors = Column(Text, nullable=True)       # JSON string of factors
    status = Column(String(32), default="WAITING", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="visits")
    queue_item = relationship("QueueItem", back_populates="visit", uselist=False)
    consultation = relationship("Consultation", back_populates="visit", uselist=False)


class QueueItem(Base):
    """Live queue tracking item."""
    __tablename__ = "queue_items"

    id = Column(Integer, primary_key=True, index=True)
    token_number = Column(Integer, nullable=False, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="SET NULL"), nullable=True)
    patient_name = Column(String(255), nullable=False)
    patient_code = Column(String(64), nullable=False)  # PAT-1001 for convenience
    priority_score = Column(Integer, default=20, nullable=False)
    severity = Column(String(32), default="LOW", nullable=False)
    status = Column(String(32), default="WAITING", nullable=False)  # WAITING, WITH_DOCTOR, COMPLETED, CANCELLED
    queue_date = Column(String(32), nullable=False)  # YYYY-MM-DD
    assigned_doctor = Column(String(255), nullable=True)
    assigned_room = Column(String(64), nullable=True)
    estimated_wait_mins = Column(Integer, default=0, nullable=False)
    check_in_time = Column(DateTime, default=utc_now, nullable=False)
    called_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    patient = relationship("Patient", back_populates="queue_entries")
    visit = relationship("Visit", back_populates="queue_item")


class Consultation(Base):
    """Doctor consultation record."""
    __tablename__ = "consultations"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id", ondelete="CASCADE"), nullable=False)
    visit_id = Column(Integer, ForeignKey("visits.id", ondelete="SET NULL"), nullable=True)
    doctor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    doctor_name = Column(String(255), default="Dr. Assigned", nullable=False)
    consultation_date = Column(String(32), nullable=False)  # YYYY-MM-DD
    consultation_time = Column(String(32), nullable=False)  # HH:MM AM/PM
    diagnosis = Column(Text, nullable=False)
    symptoms = Column(Text, nullable=True)
    prescription = Column(Text, nullable=True)
    vital_signs = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    follow_up_date = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    patient = relationship("Patient", back_populates="consultations")
    doctor = relationship("User", back_populates="consultations")
    visit = relationship("Visit", back_populates="consultation")
