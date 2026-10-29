# MedQueue AI — Smart Patient Prioritization & OPD Queue Management System

> **An AI-powered clinical triage and outpatient queue orchestration system** integrating FastAPI, MongoDB, scikit-learn ML models, LLM-grounded clinical summaries, OCR-based document verification, bilingual waiting-room announcements, and a React/Vite frontend dashboard.

---

## 📁 Project Structure

```
MedQueue-AI/
├── backend/                    ← FastAPI Python backend (all server logic)
│   ├── app/
│   │   ├── core/               ← Config, security, JWT
│   │   ├── database/           ← MongoDB client, SQLAlchemy session, models
│   │   ├── ml/                 ← ML inference engine, training pipeline, preprocessor
│   │   ├── routers/            ← All REST API endpoint routers (16 modules)
│   │   ├── schemas/            ← Pydantic request/response schemas
│   │   ├── services/           ← Business logic (queue engine, OCR, LLM, triage, etc.)
│   │   ├── simulation/         ← Monte Carlo OPD queue simulation engine
│   │   └── main.py             ← FastAPI application entry point
│   ├── data/
│   │   ├── raw/                ← Raw datasets (triagegeist, Hospital ER — gitignored)
│   │   └── processed/          ← Processed/feature-engineered data
│   ├── models/                 ← Trained ML pipeline .joblib files (6 models + champion)
│   ├── reports/                ← model_evaluation_report.json, simulation_results.json
│   ├── tests/                  ← Full Pytest integration test suite (49 tests)
│   ├── uploads/                ← Uploaded medical documents (OCR processing)
│   ├── .env.example            ← Backend environment variables template
│   ├── requirements.txt        ← Python dependencies
│   ├── run.py                  ← Uvicorn server launcher
│   └── start_backend.bat       ← Windows quick-start script
│
├── frontend/                   ← React + Vite frontend (all UI)
│   ├── src/
│   │   ├── components/         ← Reusable UI components (layout, medical, dashboard)
│   │   ├── context/            ← React context (AuthContext, AppContext)
│   │   ├── pages/              ← Full-page route components (12 pages)
│   │   ├── services/           ← api.js — REST client for all backend endpoints
│   │   └── utils/              ← Helper utilities (queue, triage, time, storage)
│   ├── public/                 ← Static assets (favicon, icons)
│   ├── index.html              ← Root HTML entry point
│   ├── vite.config.js          ← Vite config with dev proxy to backend
│   ├── package.json            ← Node.js dependencies
│   └── .env.example            ← Frontend environment variables template
│
├── docs/                       ← Project documentation
│   ├── architecture.md
│   ├── dataset_audit.md
│   ├── implementation_plan.md
│   ├── limitations.md
│   ├── model_card.md
│   ├── requirements.md
│   └── simulation_protocol.md
│
├── .gitignore
└── README.md                   ← This file
```

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10+ | For FastAPI backend |
| Node.js | 18+ | For React frontend |
| MongoDB | 6.0+ (optional) | Auto-falls back to in-memory mongomock |
| Tesseract OCR | 5.x (optional) | For image document OCR |

---

### 1. Backend Setup (FastAPI + Python)

```bash
# Navigate to the backend folder
cd backend

# Create and activate a virtual environment
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS/Linux
source .venv/bin/activate

# Install all Python dependencies
pip install -r requirements.txt

# Copy environment template and configure
cp .env.example .env
# Edit .env as needed (MongoDB URL, secret key, LLM provider, etc.)

# Start the FastAPI server
python run.py
```

**Backend will be available at:** `http://127.0.0.1:8000`  
**Swagger API Docs:** `http://127.0.0.1:8000/docs`  
**Health Check:** `http://127.0.0.1:8000/health`

> **Windows shortcut:** Double-click `backend/start_backend.bat`

---

### 2. Frontend Setup (React + Vite)

```bash
# Navigate to the frontend folder
cd frontend

# Copy environment template
cp .env.example .env
# Edit VITE_API_URL if your backend runs on a different port

# Install Node.js dependencies
npm install

# Start the development server
npm run dev
```

**Frontend will be available at:** `http://localhost:5173`

> The Vite dev server proxies all `/api/*` requests to `http://127.0.0.1:8000` automatically.

---

### 3. Running Both Together

Open two terminal windows:

**Terminal 1 — Backend:**
```bash
cd backend
.venv\Scripts\activate    # Windows
python run.py
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

Then open `http://localhost:5173` in your browser.

---

## 🧪 Running the Test Suite

```bash
cd backend

# Run all 49 integration tests
.venv\Scripts\python.exe -m pytest tests/ -v

# Run a specific test file
.venv\Scripts\python.exe -m pytest tests/test_queue.py -v

# Run with short traceback on failures
.venv\Scripts\python.exe -m pytest tests/ -v --tb=short
```

**Expected result: 49 passed, 0 failed** ✅

> Tests use in-memory mongomock automatically — no MongoDB installation required for testing.

---

## 🔑 Default Login Credentials

| Role | Email | Password |
|---|---|---|
| Doctor | `doctor@medqueue.org` | `doctor123` |
| Receptionist | `receptionist@medqueue.org` | `receptionist123` |
| Admin | `admin@medqueue.org` | `admin123` |

> Change these in production via the `.env` file and the admin panel.

---

## ⚙️ Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|---|---|---|
| `PROJECT_NAME` | `MedQueue AI Backend` | Service name |
| `HOST` | `127.0.0.1` | Bind address |
| `PORT` | `8000` | Bind port |
| `MONGODB_URL` | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB_NAME` | `medqueue_ai` | Database name |
| `USE_MONGOMOCK` | `False` | Force in-memory mock (for CI/testing) |
| `SECRET_KEY` | *(change me)* | JWT signing secret |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | Token lifetime (24h) |
| `LLM_PROVIDER` | `mock` | `mock`, `openai`, or `ollama` |
| `OPENAI_API_KEY` | *(blank)* | OpenAI API key (if using OpenAI) |
| `MAX_UPLOAD_SIZE_MB` | `15` | Max medical document size |
| `BACKEND_CORS_ORIGINS` | `http://localhost:5173,...` | Comma-separated allowed origins |

### Frontend (`frontend/.env`)

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://127.0.0.1:8000/api/v1` | FastAPI backend base URL |

---

## 🏗️ Key Features

| Feature | Details |
|---|---|
| **Patient Registration** | Identity verification, duplicate detection, demographic capture |
| **Encounter Intake** | Vitals recording, symptom capture, chief complaint |
| **Emergency Screening** | Synchronous rule-based flagging (SpO2, BP, HR, shock index) |
| **ML Triage Acuity** | 6 trained models (LR, RF, MLP × Model A/B), champion Random Forest |
| **Queue Management** | FCFS, Conventional Priority, Dynamic Hybrid policies |
| **Doctor Overrides** | Audited priority escalation with mandatory clinical rationale |
| **Document OCR** | PDF direct extraction (pypdf) + image OCR (pytesseract), identity match |
| **LLM Clinical Summary** | 7-section grounded summary with source citations (mock/OpenAI/Ollama) |
| **Waiting Room Display** | Live token board with bilingual (English/Telugu) Web Speech API announcements |
| **Monte Carlo Simulation** | Policy A/B/C comparative OPD queue simulation with starvation metrics |
| **RBAC Auth** | JWT-based role-based access (doctor, receptionist, admin, nurse) |

---

## 🤖 Machine Learning — Datasets and Model Evaluation

### Datasets

| Dataset | Location | Purpose | License |
|---|---|---|---|
| **Triagegeist** (`train.csv`) | `backend/data/raw/triagegeist/` | Primary training + validation | Kaggle (research) |
| **Triagegeist** (`patient_history.csv`) | `backend/data/raw/triagegeist/` | Longitudinal comorbidity history (Model B) | Kaggle (research) |
| **Hospital ER** (`Hospital_ER_Data.csv`) | `backend/data/raw/hospital_er/` | Monte Carlo calibration baseline only | Public |

- **Target variable**: `triage_acuity` (1–5 ESI-scale integer)
- **Class labels**: 1 = Critical/Immediate, 2 = Emergent, 3 = Urgent, 4 = Less Urgent, 5 = Non-Urgent
- **Leakage blacklist**: `disposition`, `ed_los_hours` (post-arrival outcomes — strictly excluded)
- **Split**: 80/20 stratified train/validation, no data used for model selection from validation

### Current Evaluation Results (retrained with scikit-learn 1.9.1)

| Model | Feature Set | Macro F1 | Balanced Acc | Accuracy |
|---|---|---|---|---|
| Logistic Regression | Model A (Current Only) | 0.8102 | 0.8313 | 0.7840 |
| Random Forest | Model A (Current Only) | 0.8394 | 0.8598 | 0.8161 |
| MLP | Model A (Current Only) | 0.8383 | 0.8401 | 0.8203 |
| Logistic Regression | Model B (History-Aware) | 0.8279 | 0.8463 | 0.8044 |
| **Random Forest** ⭐ | **Model B (History-Aware)** | **0.8550** | **0.8663** | **0.8319** |
| MLP | Model B (History-Aware) | 0.8477 | 0.8439 | 0.8290 |

**Champion**: `model_b_random_forest` — selected on highest Macro F1 (0.855) across minority classes.

### Training

```bash
cd backend

# Retrain all 6 models and regenerate evaluation report
.venv\Scripts\python.exe -c "from app.ml.train_pipeline import run_full_training_pipeline; run_full_training_pipeline(max_rows=35000)"

# Or via the API (server must be running):
curl -X POST "http://127.0.0.1:8000/api/v1/models/train"
```

> **Limitation**: The Triagegeist dataset uses a 5-level ESI acuity scale (1–5), not the 4-tier Critical/High/Medium/Low labeling. The inference engine maps these as: Acuity 1–2 → HIGH urgency tier, Acuity 3 → MEDIUM, Acuity 4–5 → LOW. The emergency safety screening layer runs *independently of* the ML prediction and can override any acuity score.

---

## 📚 Documentation

All project documentation lives in [`docs/`](docs/):

- [`architecture.md`](docs/architecture.md) — System architecture and data flow
- [`dataset_audit.md`](docs/dataset_audit.md) — Dataset schemas, distributions, class imbalance
- [`model_card.md`](docs/model_card.md) — ML model training, evaluation, and comparison
- [`requirements.md`](docs/requirements.md) — Functional and safety requirements
- [`limitations.md`](docs/limitations.md) — Known limitations and risk log
- [`implementation_plan.md`](docs/implementation_plan.md) — Phase-by-phase roadmap
- [`simulation_protocol.md`](docs/simulation_protocol.md) — Monte Carlo simulation protocol

---

## 🛡️ Safety Disclaimer

> **MedQueue AI is a research and academic demonstration system.** It is not a certified medical device and must not be used for actual clinical triage decisions without qualified clinical oversight. All AI predictions and priority suggestions are advisory only. The attending clinician retains full authority over all patient care decisions.

---

## 🔧 Audit Changelog (October 2026)

The following fixes were applied during the full audit pass:

| # | File(s) Changed | Issue Fixed |
|---|---|---|
| 1 | `backend/requirements.txt` | Added missing ML dependencies (`scikit-learn>=1.9.1`, `numpy`, `pandas`, `joblib`) |
| 2 | `backend/app/schemas/patient.py` | Replaced Pydantic v1 `class Config` with `model_config = ConfigDict(from_attributes=True)` (eliminates deprecation warning) |
| 3 | `backend/app/schemas/consultation.py` | Same Pydantic v2 `ConfigDict` migration |
| 4 | `backend/models/*.joblib` | All 6 models retrained with scikit-learn 1.9.1 (eliminates `InconsistentVersionWarning`) |
| 5 | `backend/reports/model_evaluation_report.json` | Regenerated with fresh training run — metrics correspond to current saved models |
| 6 | `backend/models/pipeline_metadata.json` | Updated `trained_at` timestamp after retraining |
| 7 | `backend/pytest.ini` | Created: sets `asyncio_mode = auto`, `asyncio_default_fixture_loop_scope = function` (eliminates pytest-asyncio deprecation warning) |
| 8 | `README.md` | Added ML metrics table, dataset sources, training command, and this changelog |
