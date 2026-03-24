# FHIR LLM Clinical Summary System

A clinical data analysis system that uses Large Language Models (LLM) to generate intelligent summaries of patient data from FHIR-compliant databases.

## 🏥 Features

- **Patient Data Analysis**: Extract and analyze patient demographics, conditions, observations, and clinical notes
- **AI-Powered Summaries**: Generate clinical summaries using Llama 3.1 8B model
- **Intelligent Chat Agent**: Natural language queries with RAG-powered responses
- **Smart Visualizations**: 7 built-in visualization types + dynamic category grouping (17 clinical categories)
- **User-Friendly Interaction**: Automatic clarification for vague requests - no technical terms needed
- **Multiple Summary Types**: 
  - Full patient summary
  - Conditions-only summary
  - Observations-only summary
  - Notes-only summary
- **Grouped Observations**: Automatically categorize observations into 17 clinical groups (vital signs, lab values, etc.)
- **Web Interface**: Easy-to-use web interface for selecting patients and generating summaries
- **RESTful API**: Complete API for integration with other systems
- **Elasticsearch Integration**: RAG-powered search and retrieval for enhanced AI responses

## 🚀 Quick Start

### Quick Command (All-in-One)
```bash
cd /home/kchollet/LLM_UA/FHIR_LLM_UA && source venv/bin/activate && cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & cd ../frontend && python server.py & sleep 5 && firefox http://localhost:5173 &
```

### Prerequisites
- Python 3.11+
- MySQL database with FHIR data
- Virtual environment (already set up in this project)

### Running the System

1. **Start both servers** (backend API + frontend web interface):
   ```bash
   ./start_servers.sh
   ```
   OR use the quick command above.

2. **Open your browser** and navigate to: `http://localhost:5173`

3. **Select a patient** from the dropdown - all summaries generate automatically

4. **Wait for AI processing** (30-60 seconds for first generation)

For detailed setup instructions, see **[SETUP.md](SETUP.md)**

## 📊 API Endpoints

### Core Endpoints
- **Health Check**: `GET http://localhost:8000/health`
- **List Patients**: `GET http://localhost:8000/patients`
- **Generate All Summaries**: `GET http://localhost:8000/patients/{patient_id}/all_summaries`
- **Generate Specific Summary**: `GET http://localhost:8000/patients/{patient_id}/llm_summary?category={category}`
- **Clear Cache**: `DELETE http://localhost:8000/patients/{patient_id}/cache`
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)

### Advanced Endpoints (AI Features)
- **Chat Agent Query**: `POST http://localhost:8000/chat-agent/query`
- **Generate Visualization**: `POST http://localhost:8000/chat-agent/visualize`
- **Index Patient Data**: `POST http://localhost:8000/chat-agent/patient/{patient_id}/index`
- **Chat Agent Status**: `GET http://localhost:8000/chat-agent/status`

### Summary Categories

- `patient_summary` - Full clinical summary (default)
- `conditions` - Conditions analysis only
- `observations` - Observations and trends only
- `notes` - Clinical notes summary only

## 🔧 Configuration

### Environment Variables

The system uses the following environment variables (with defaults):

```bash
# Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=llm_ua_clinical
DB_USER=your_username
DB_PASSWORD=your_password

# LLM Configuration
LLM_MODEL_PATH=/home/kchollet/LLM_UA/FHIR_LLM_UA/models/llama31-8b-bnb4
LLM_MAX_NEW_TOKENS=800
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9

# Data Limits
LLM_MAX_CONDITIONS=50        # Normal categories
LLM_MAX_OBSERVATIONS=100     # Normal categories
LLM_MAX_NOTES=3              # Reduced for memory efficiency
LLM_MAX_NOTE_CHARS=2500      # Per note character limit
```

**Note**: Patient Summary and Care Plans use reduced limits (30 conditions, 50 observations, 2 notes, 2000 chars) to prevent memory issues.

For detailed configuration, see **[SETUP.md](SETUP.md)**

### Database Setup

The system expects a MySQL database with the following tables:
- `patients` - Patient demographics
- `conditions` - Medical conditions
- `observations` - Lab results, vitals, etc.
- `notes` - Clinical notes and documentation

## 🧠 AI Model

This system uses **Llama 3.1 8B Instruct** model with:
- 4-bit quantization for memory efficiency
- BitsAndBytesConfig for optimal performance
- Clinical-specific prompting for accurate medical summaries

## 📁 Project Structure

```
FHIR_LLM_UA/
├── backend/
│   ├── app/
│   │   ├── api/           # API endpoints
│   │   ├── core/          # Core functionality (LLM, database, prompts)
│   │   └── main.py        # FastAPI application
├── frontend/
│   ├── index.html         # Web interface
│   └── server.py          # Simple HTTP server
├── models/
│   └── llama31-8b-bnb4/   # AI model files
├── sql/
│   └── schema.sql         # Database schema
├── venv/                  # Python virtual environment
├── start_servers.sh       # Startup script
├── README.md             # This file (main documentation)
├── SETUP.md              # Setup and operations guide
├── USAGE.md              # User guide and features
├── DASHBOARD_README.md    # Dashboard features documentation
└── STEPS_TO_RUN.txt      # Quick reference cheat sheet
```

## 🔍 Troubleshooting

### Common Issues

1. **"Patient not found" error**: Ensure the database contains patient data and the patient ID exists
2. **Slow response times**: The LLM model takes 30-60 seconds for complex patients - this is normal
3. **Connection refused**: Make sure both servers are running on the correct ports (8000 for backend, 5173 for frontend)
4. **Database connection errors**: Check your database credentials and ensure MySQL is running
5. **"Summary temporarily unavailable"**: GPU memory constraints - wait and try again
6. **Address already in use**: Kill existing processes: `pkill -f "uvicorn" && pkill -f "python server.py"`

### Quick Fixes

**Restart servers:**
```bash
pkill -f "uvicorn app.main:app" && pkill -f "python server.py" && sleep 2 && cd /home/kchollet/LLM_UA/FHIR_LLM_UA && source venv/bin/activate && cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & cd ../frontend && python server.py &
```

**Check server status:**
```bash
curl http://localhost:8000/health  # Backend
curl http://localhost:5173          # Frontend
ps aux | grep -E "uvicorn|server.py" | grep -v grep  # Running processes
```

For detailed troubleshooting, see **[SETUP.md](SETUP.md)**

## 🛡️ Security Notes

- This is a development/demo system
- Database credentials should be properly secured in production
- Consider implementing authentication and authorization for production use
- The web interface is served over HTTP (not HTTPS) for simplicity

## 📝 License

This project is for educational and research purposes. Please ensure compliance with the Llama 3.1 Community License for the AI model components.

## 📚 Additional Documentation

- **[SETUP.md](SETUP.md)** - Complete setup and operations guide
- **[USAGE.md](USAGE.md)** - User guide and dashboard features
- **[DASHBOARD_README.md](DASHBOARD_README.md)** - Dashboard features documentation
- **[STEPS_TO_RUN.txt](STEPS_TO_RUN.txt)** - Quick reference cheat sheet
- **[HOW_TO_USE_GROUPED_VISUALIZATIONS.md](HOW_TO_USE_GROUPED_VISUALIZATIONS.md)** - Guide to grouped visualization feature
- **[CLARIFICATION_FEATURE.md](CLARIFICATION_FEATURE.md)** - Automatic clarification for non-technical users
- **[OBSERVATION_CATEGORIES_LIST.md](OBSERVATION_CATEGORIES_LIST.md)** - Complete list of 17 observation categories
- **[GROUPED_VISUALIZATION_GUIDE.md](GROUPED_VISUALIZATION_GUIDE.md)** - Technical documentation for grouped visualizations

## 🤝 Contributing

This is a demonstration system. For production use, consider:
- Adding authentication and authorization
- Implementing proper error handling and logging
- Adding unit tests
- Optimizing the LLM inference pipeline
- Adding more sophisticated clinical data validation

## 📝 Recent Updates

**December 2024:**
- ✅ Adaptive memory management for complex categories
- ✅ Batch summary generation (all 6 categories at once)
- ✅ In-memory caching system
- ✅ Generative AI chat interface
- ✅ Visual chart generation
- ✅ Patient search with auto-expand dropdown
- ✅ Grouped observation visualizations (17 clinical categories)
- ✅ Automatic clarification feature for non-technical users
- ✅ RAG-powered Elasticsearch integration
- ✅ Smart intent detection for visualization requests
