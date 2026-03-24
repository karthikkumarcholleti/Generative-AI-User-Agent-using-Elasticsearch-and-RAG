# 🚀 Installation Guide - Setting Up on a New System

This guide explains how to set up the entire project on a new system after cloning from GitHub.

## 📦 What Gets Pushed to GitHub

✅ **Pushed to GitHub:**
- All source code (`.py`, `.tsx`, `.ts`, `.js` files)
- Configuration templates (`.env.template`)
- Documentation (`.md` files)
- Scripts (`start_all.sh`, etc.)
- `package.json` and `requirements.txt` (dependency lists)
- Project structure

❌ **NOT Pushed (excluded by .gitignore):**
- `venv/` - Python virtual environment (recreated)
- `node_modules/` - Node.js dependencies (recreated)
- `models/` - LLM model files (downloaded separately)
- `.env` - Environment files with secrets (created from templates)
- Log files, cache, build artifacts

---

## 🔧 Step-by-Step Installation

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** and npm
- **MySQL** database server
- **Git**
- **GPU** (recommended for LLM inference, but CPU works too)

---

### Step 1: Clone the Repository

```bash
git clone <your-github-repo-url>
cd fhir_karthik/FHIR_COMBINED
```

---

### Step 2: Set Up Python Backend

#### 2.1 Create Virtual Environment

```bash
cd FHIR_LLM_UA
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 2.2 Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
# If requirements.txt doesn't exist, install manually:
pip install fastapi uvicorn sqlalchemy pymysql python-dotenv transformers sentence-transformers torch elasticsearch
```

#### 2.3 Download LLM Model

The model files are too large for GitHub. You need to download them separately:

**Option A: Download from HuggingFace (Recommended)**
```bash
cd ../models
# Download Llama 3.1 8B quantized model
# You'll need HuggingFace CLI or manual download
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --local-dir llama31-8b-bnb4
```

**Option B: Copy from Original System**
If you have access to the original system:
```bash
# On original system:
cd FHIR_COMBINED/FHIR_LLM_UA/models
tar -czf llama31-8b-bnb4.tar.gz llama31-8b-bnb4/

# Transfer to new system, then:
cd FHIR_COMBINED/FHIR_LLM_UA/models
tar -xzf llama31-8b-bnb4.tar.gz
```

**Option C: Use Different Model Path**
Edit `.env` file to point to a different model location if you have it elsewhere.

---

### Step 3: Set Up Frontend

#### 3.1 Install Node.js Dependencies

```bash
cd ../../FHIR_dashboard/backend/frontend
npm install
```

This will recreate `node_modules/` based on `package.json`.

---

### Step 4: Set Up Elasticsearch

#### Option A: Use Bundled Elasticsearch (if included)

```bash
cd ../../elasticsearch-8.14.0
# Elasticsearch should be included in the repo
# If not, download from https://www.elastic.co/downloads/elasticsearch
```

#### Option B: Install Elasticsearch Separately

Download Elasticsearch 8.14.0 from [elastic.co](https://www.elastic.co/downloads/elasticsearch) and extract it.

---

### Step 5: Configure Environment Variables

#### 5.1 Backend Configuration

```bash
cd FHIR_COMBINED/FHIR_LLM_UA/backend
cp ../../config/llm_backend.env.template .env
```

Edit `.env` with your settings:
```bash
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=your_database_name
DB_USER=your_username
DB_PASSWORD=your_password

LLM_MODEL_PATH=/path/to/FHIR_COMBINED/FHIR_LLM_UA/models/llama31-8b-bnb4
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
```

#### 5.2 Frontend Configuration (if needed)

```bash
cd FHIR_COMBINED/FHIR_dashboard/backend/frontend
# Check if .env.local is needed
```

---

### Step 6: Set Up Database

1. **Create MySQL Database:**
```sql
CREATE DATABASE your_database_name;
```

2. **Import Schema:**
```bash
cd FHIR_COMBINED/FHIR_LLM_UA
mysql -u your_username -p your_database_name < sql/schema.sql
```

3. **Load Patient Data:**
   - You'll need to provide FHIR data files (ADT, CCDA, ORU)
   - Or use existing database dump

---

### Step 7: Start the System

```bash
cd FHIR_COMBINED
./start_all.sh
```

This will:
- Start Elasticsearch
- Start Backend API (port 8001)
- Start Frontend (port 3000)

---

## 📋 Quick Checklist

- [ ] Cloned repository
- [ ] Created Python venv and installed dependencies
- [ ] Downloaded LLM model (or configured path)
- [ ] Installed Node.js dependencies (`npm install`)
- [ ] Set up Elasticsearch
- [ ] Created `.env` files from templates
- [ ] Set up MySQL database
- [ ] Started all services

---

## 🔍 Troubleshooting

### Model Not Found
- Check `LLM_MODEL_PATH` in `.env` file
- Ensure model files are in the correct location
- Model should be ~5.4GB when extracted

### Dependencies Missing
- Python: `pip install -r requirements.txt`
- Node: `npm install` in frontend directory

### Database Connection Error
- Check `.env` file has correct database credentials
- Ensure MySQL is running
- Verify database exists

### Elasticsearch Not Starting
- Check if port 9200 is available
- Verify Elasticsearch installation
- Check logs in `elasticsearch-8.14.0/logs/`

---

## 💡 Key Points

1. **Source code is pushed** - All your code is in GitHub
2. **Dependencies are recreated** - Using `requirements.txt` and `package.json`
3. **Models downloaded separately** - Too large for GitHub (5.4GB)
4. **Configuration from templates** - Copy `.env.template` to `.env` and edit
5. **Data needs to be provided** - Database and patient data separately

---

## 📝 Notes

- The `.gitignore` ensures only essential code is pushed
- Large files (models, dependencies) are recreated on the new system
- This keeps the repository clean and fast to clone
- Follow the steps above to restore everything

---

**Last Updated:** January 2025

