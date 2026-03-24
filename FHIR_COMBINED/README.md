# FHIR LLM Clinical Dashboard

A clinical dashboard with AI-powered question answering using RAG (Retrieval Augmented Generation).

## 🚀 Quick Start

### Option A: Server Access (Already Set Up)

If you have SSH access to the server where the system is already configured:

```bash
ssh username@server-ip
cd /path/to/FHIR_COMBINED
npm run dev
# OR
./start_all.sh
```

Access: `http://server-ip:3000/generative-ai`

### Option B: Clone from GitHub (New Setup)

```bash
# 1. Clone repository
git clone <repo-url>
cd fhir_karthik/FHIR_COMBINED

# 2. Install dependencies
npm install

# 3. Configure environment
cp .env.example .env
cp FHIR_LLM_UA/backend/.env.example FHIR_LLM_UA/backend/.env
# Edit both .env files with your database credentials

# 4. Download model (first time only)
npm run install-model

# 5. Start system
npm run dev
```

Access: `http://localhost:3000/generative-ai`

---

## 📋 Detailed Setup Instructions

### Prerequisites

- **Node.js 18+** and npm
- **Python 3.11+**
- **MySQL** database server
- **GPU** (recommended) or CPU
- **HuggingFace account** (for model download)

### Step 1: Clone Repository

```bash
git clone <repo-url>
cd fhir_karthik/FHIR_COMBINED
```

### Step 2: Install Dependencies

```bash
npm install
```

This automatically:
- Installs Node.js dependencies (frontend)
- Creates Python virtual environment
- Installs Python dependencies

### Step 3: Configure Environment

**Create your `.env` file from the template:**

```bash
cp .env.example .env
nano .env  # Edit with your configuration
```

**Required changes:**
- `DB_HOST` - Database server (default: localhost)
- `DB_NAME` - Database name
- `DB_USER` - Database username
- `DB_PASSWORD` - Database password
- `ELASTICSEARCH_PASSWORD` - Elasticsearch password
- `BACKEND_PORT` - Backend API port (default: 8001, change if port conflict)
- `FRONTEND_PORT` - Frontend port (default: 3000, change if port conflict)
- `LLM_MODEL_PATH` - Model path (default: `./FHIR_LLM_UA/models/llama31-8b-bnb4`)

**Important:** 
- `.env` is local and not committed to git (it contains secrets)
- Each user creates their own `.env` file after cloning
- Backend code automatically reads from root `.env`

### Step 4: Set Up Database

You will receive the database from the project maintainer. Import it:

```bash
mysql -u your_username -p your_database < FHIR_LLM_UA/sql/schema.sql
# Then import your data dump
mysql -u your_username -p your_database < your_data_dump.sql
```

### Step 5: Download Model (First Time Only)

```bash
npm run install-model
```

**Requirements:**
- HuggingFace account with access to Llama models
- Logged in: `huggingface-cli login`
- ~6GB free disk space

**Alternative:** If you already have the model, point `LLM_MODEL_PATH` in `.env` to your existing model directory.

### Step 6: Start the System

```bash
npm run dev
# OR
./start_all.sh
```

**What starts:**
- Elasticsearch (port 9200)
- Backend API (port 8001)
- Frontend (port 3000)

### Step 7: Access Dashboard

Open browser: `http://localhost:3000/generative-ai`

### Step 8: Stop the System

Press `Ctrl+C` in the terminal, or:

```bash
npm run stop
# OR
./stop_all.sh
```

---

## 🔧 Configuration

All configuration is done via **one root `.env` file**:

- **Root `.env`** - All configuration (ports, database, Elasticsearch, model path, LLM settings)
- Backend code automatically reads from root `.env`

**Setup:**
1. Copy `.env.example` to `.env`: `cp .env.example .env`
2. Edit `.env` with your credentials
3. Run: `npm run dev`

**Important:** 
- `.env` is local and not committed to git (it contains secrets)
- Each user creates their own `.env` file after cloning
- `.env.example` is the template (safe to commit, no secrets)

---

## 📚 Documentation

See **[RUN.md](RUN.md)** for simple instructions on how to run the system.

## Documentation

- **[RUN.md](RUN.md)** - Simple guide to start/stop the system
- **[PROFESSOR_UPDATE_REPORT.md](PROFESSOR_UPDATE_REPORT.md)** - Detailed technical report
- **[CLINICIAN_GUIDE.md](CLINICIAN_GUIDE.md)** - User guide for clinicians
- **[MEETING_DOCUMENT.md](MEETING_DOCUMENT.md)** - Meeting brief

---

## FHIR_COMBINED - Combined Dashboard Project (Technical Details)

## 📁 **Project Structure**

```
FHIR_COMBINED/
├── FHIR_dashboard/              ← Full-stack team's work
│   └── backend/
│       ├── frontend/            ← Next.js/React frontend
│       │   ├── pages/
│       │   │   └── generative-ai.tsx  ← Generative AI page (integrated)
│       │   ├── components/
│       │   │   ├── PremiumChartCard.tsx
│       │   │   ├── RechartsVisualization.tsx
│       │   │   ├── PatientSearch.tsx
│       │   │   └── Sidebar.tsx  ← Updated with Generative AI link
│       │   └── services/
│       │       └── llmApi.ts    ← API client for LLM backend
│       ├── api/                 ← Express.js API
│       │   └── search.js        ← ElasticSearch search endpoints
│       └── services/
│           └── elasticsearch.js ← ElasticSearch service
│
├── FHIR_LLM_UA/                 ← LLM work (connected with full-stack)
│   └── backend/
│       └── app/
│           ├── api/
│           │   ├── rag_service.py          ← RAG service
│           │   ├── chat_agent.py           ← Chat API endpoints
│           │   ├── condition_categorizer.py ← Condition categorization
│           │   ├── intelligent_visualization.py ← Auto-visualization
│           │   ├── summary.py              ← Summary generation
│           │   └── ...
│           └── core/
│               ├── prompts.py              ← LLM prompts
│               └── llm.py                  ← LLM generation
│
├── elasticsearch-8.14.0/        ← ElasticSearch instance
├── config/                      ← Configuration templates
├── start_combined.sh            ← Startup script
└── [Documentation files]        ← All .md documentation
```

---

## 🎯 **What's Where**

### **FHIR_dashboard/** (Full-stack team's work)
- ✅ Original full-stack dashboard
- ✅ **Plus:** Generative AI integration
  - `generative-ai.tsx` page
  - `PremiumChartCard.tsx` component
  - `RechartsVisualization.tsx` component
  - `PatientSearch.tsx` component
  - Updated `Sidebar.tsx` with Generative AI link
  - `llmApi.ts` service
  - ElasticSearch search endpoints

### **FHIR_LLM_UA/** (Your LLM work)
- ✅ Complete LLM backend
- ✅ RAG service
- ✅ Condition categorization
- ✅ Intelligent visualization
- ✅ All improvements and enhancements

### **FHIR_COMBINED/** (Root)
- ✅ ElasticSearch instance
- ✅ Configuration files
- ✅ Startup scripts
- ✅ All documentation

---

## 🔗 **How They Connect**

### **Architecture:**

```
┌─────────────────────────────────────────┐
│  FHIR_dashboard/backend/frontend/      │
│  (Next.js/React)                        │
│  ─────────────────────────────────────  │
│  • Generative AI page                   │
│  • Makes API calls →                    │
└──────────────┬──────────────────────────┘
               │
               │ HTTP (http://localhost:8000)
               ▼
┌─────────────────────────────────────────┐
│  FHIR_LLM_UA/backend/                  │
│  (FastAPI)                              │
│  ─────────────────────────────────────  │
│  • RAG service                          │
│  • LLM generation                       │
│  • Returns JSON ←                       │
└─────────────────────────────────────────┘
```

---

## 🚀 **Getting Started**

### **1. Start ElasticSearch:**
```bash
cd FHIR_COMBINED/elasticsearch-8.14.0
./bin/elasticsearch
```

### **2. Start LLM Backend:**
```bash
cd FHIR_COMBINED/FHIR_LLM_UA/backend
source venv/bin/activate  # or activate your virtual environment
python -m uvicorn app.main:app --reload --port 8000
```

### **3. Start Full-Stack Dashboard:**
```bash
cd FHIR_COMBINED/FHIR_dashboard/backend
npm install  # if needed
npm run dev   # Starts Next.js frontend
node server.js  # Starts Express.js backend (in another terminal)
```

### **Or use the startup script:**
```bash
cd FHIR_COMBINED
./start_combined.sh
```

---

## 📊 **Features**

### **Full-Stack Dashboard:**
- ✅ Original dashboard features
- ✅ Generative AI integration
- ✅ Patient search with ElasticSearch
- ✅ Professional visualizations
- ✅ Category-based condition display

### **LLM Backend:**
- ✅ RAG (Retrieval Augmented Generation)
- ✅ Condition categorization
- ✅ Intelligent visualization
- ✅ Live terminal logging
- ✅ Source verification

---

## 📝 **Documentation**

See individual documentation files in `FHIR_COMBINED/`:
- `HOW_LLM_HANDLES_QUESTIONS.md` - How RAG works
- `LLM_QUESTION_EXAMPLES.md` - Example questions
- `ORGANIZATION_STRUCTURE.md` - Detailed structure
- And many more...

---

## ✅ **Summary**

- ✅ `FHIR_dashboard/` = Full-stack team's work + Generative AI integration
- ✅ `FHIR_LLM_UA/` = Your LLM work (complete backend)
- ✅ `FHIR_COMBINED/` = Combined workspace with all documentation
- ✅ Clean, professional organization
- ✅ Ready for submission

---

**Everything is properly organized and ready to use!** 🎯
