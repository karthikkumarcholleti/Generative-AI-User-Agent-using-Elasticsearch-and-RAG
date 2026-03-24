# 🚀 FHIR LLM Dashboard - Setup & Operations Guide

## ⚡ Quick Start Commands

### **Start Everything (One Command)**
```bash
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "python server.py" 2>/dev/null || true
cd /path/to/elasticsearch && ./bin/elasticsearch -d && sleep 10 && \
cd /home/kchollet/LLM_UA/FHIR_LLM_UA && source venv/bin/activate && \
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
cd ../frontend && python server.py & \
sleep 5 && firefox http://localhost:5173 &
```

> Replace `/path/to/elasticsearch` with the installation directory used on your system.

### **Stop Everything (One Command)**
```bash
pkill -f "uvicorn app.main:app" && pkill -f "python server.py" && echo "✅ All servers stopped"
```

### **Restart Everything**
```bash
pkill -f "uvicorn app.main:app"
pkill -f "python server.py"
sleep 2
cd /path/to/elasticsearch && ./bin/elasticsearch -d && sleep 10 && \
cd /home/kchollet/LLM_UA/FHIR_LLM_UA && source venv/bin/activate && \
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & \
cd ../frontend && python server.py & \
sleep 5 && firefox http://localhost:5173 &
```

> Replace `/path/to/elasticsearch` with the installation directory used on your system.

---

## 📋 Step-by-Step Setup

### **Prerequisites**
- Python 3.11+
- MySQL database with FHIR data
- Virtual environment (already configured)
- ElasticSearch 8.x reachable at `https://localhost:9200`
- Firefox web browser

### **Step 1: Navigate to Project**
```bash
cd /home/kchollet/LLM_UA/FHIR_LLM_UA
```

### **Step 2: Start ElasticSearch**
```bash
cd /path/to/elasticsearch
./bin/elasticsearch -d
sleep 10
curl -k -u elastic:P@ssw0rd https://localhost:9200
```

You should see JSON with `"tagline": "You Know, for Search"`. If ElasticSearch is already running you can skip starting it again, but still verify with the `curl` command.

### **Step 3: Activate Virtual Environment**
```bash
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt.

### **Step 4: Start Backend Server**
```bash
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
```

Expected output:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### **Step 5: Start Frontend Server**
```bash
cd ../frontend
python server.py &
```

Expected output:
```
Serving HTTP on 0.0.0.0 port 5173
```

### **Step 6: Wait for Initialization**
```bash
sleep 5
```

### **Step 7: Open Browser**
```bash
firefox http://localhost:5173 &
```

Or manually open Firefox and navigate to: `http://localhost:5173`

### **Step 8: Index Patient Data for RAG**
- In the dashboard sidebar click `🔄 Index All Patients`
- Or run:
```bash
curl -X POST http://localhost:8000/chat-agent/index-all-patients
```

### **Step 9: Verify RAG Status**
```bash
curl http://localhost:8000/chat-agent/status
```

Expected output includes `"elasticsearch": "connected"` and non-zero `"indexed_patients"`.

---

## 🛑 Step-by-Step Shutdown

### **Step 1: Stop Backend Server**
```bash
pkill -f "uvicorn app.main:app"
```

### **Step 2: Stop Frontend Server**
```bash
pkill -f "python server.py"
```

### **Step 3: Verify Shutdown**
```bash
ps aux | grep -E "uvicorn|server.py" | grep -v grep
```

If this shows nothing, servers are successfully stopped.

### **Step 4: Deactivate Virtual Environment (Optional)**
```bash
deactivate
```

---

## 🔧 Troubleshooting

### **Problem: "Address already in use"**

**Solution:**
```bash
# Kill all existing processes
pkill -f "uvicorn app.main:app"
pkill -f "python server.py"

# Wait 2 seconds
sleep 2

# Check if ports are free
lsof -i :8000
lsof -i :5173

# If nothing shows, restart servers
cd /home/kchollet/LLM_UA/FHIR_LLM_UA
source venv/bin/activate
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
cd ../frontend && python server.py &
```

### **Problem: ElasticSearch not reachable**

**Solution:**
```bash
curl -k -u elastic:P@ssw0rd https://localhost:9200
```

If the curl call fails:
```bash
cd /path/to/elasticsearch
./bin/elasticsearch -d
sleep 10
curl -k -u elastic:P@ssw0rd https://localhost:9200
```

### **Problem: "Unable to connect" in browser**

**Check Frontend:**
```bash
curl -s http://localhost:5173 | head -5
```

**Check Backend:**
```bash
curl -s http://localhost:8000/health
```

Expected output: `{"status":"ok","db":"ok"}`

**If frontend fails:**
```bash
cd /home/kchollet/LLM_UA/FHIR_LLM_UA/frontend
python server.py &
```

**If backend fails:**
```bash
cd /home/kchollet/LLM_UA/FHIR_LLM_UA/backend
source ../venv/bin/activate
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
```

### **Problem: RAG responses are empty**

**Solution:**
```bash
curl http://localhost:8000/chat-agent/status
```

If `indexed_patients` is `0`, re-index:
```bash
curl -X POST http://localhost:8000/chat-agent/index-all-patients
```

### **Problem: Database connection error**

**Check MySQL is running:**
```bash
sudo systemctl status mysql
```

**Start MySQL if needed:**
```bash
sudo systemctl start mysql
```

---

## 🌐 Important URLs

| Service | URL |
|---------|-----|
| Dashboard | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Documentation | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |
| Chat Agent Status | http://localhost:8000/chat-agent/status |
| Index All Patients (POST) | http://localhost:8000/chat-agent/index-all-patients |

---

## 🧪 Verification Commands

### **Check Backend Health**
```bash
curl http://localhost:8000/health
```

Expected: `{"status":"ok","db":"ok"}`

### **Check Frontend**
```bash
curl http://localhost:5173 | head -c 100
```

Expected: HTML content

### **Check ElasticSearch**
```bash
curl -k -u elastic:P@ssw0rd https://localhost:9200
```

### **Check RAG Status**
```bash
curl http://localhost:8000/chat-agent/status
```

### **List Patients**
```bash
curl http://localhost:8000/patients | head -c 200
```

### **Check Running Servers**
```bash
ps aux | grep -E "uvicorn|server.py" | grep -v grep
```

### **Check Port Usage**
```bash
netstat -tlnp | grep -E "(8000|5173)"
```

---

## 📅 Daily Workflow

### **Morning (Start Work):**
1. Open terminal in Cursor (Ctrl + `)
2. Run one command:
   ```bash
   pkill -f "uvicorn app.main:app" 2>/dev/null || true
   pkill -f "python server.py" 2>/dev/null || true
   cd /path/to/elasticsearch && ./bin/elasticsearch -d && sleep 10
   cd /home/kchollet/LLM_UA/FHIR_LLM_UA && source venv/bin/activate
   cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
   cd ../frontend && python server.py &
   sleep 5 && firefox http://localhost:5173 &
   ```
3. Dashboard opens in Firefox
4. Start working!

### **Evening (End Work):**
1. Close Firefox (Alt + F4)
2. Stop servers:
   ```bash
   pkill -f "uvicorn app.main:app" && pkill -f "python server.py"
   ```

---

## 💡 Pro Tips

### **Create Shortcut Aliases**

Add to `~/.bashrc`:
```bash
alias start-dashboard='pkill -f "uvicorn app.main:app" 2>/dev/null || true; pkill -f "python server.py" 2>/dev/null || true; cd /path/to/elasticsearch && ./bin/elasticsearch -d && sleep 10; cd /home/kchollet/LLM_UA/FHIR_LLM_UA && source venv/bin/activate && cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 & cd ../frontend && python server.py & sleep 5 && firefox http://localhost:5173 &'

alias stop-dashboard='pkill -f "uvicorn app.main:app" && pkill -f "python server.py"'
```

Replace `/path/to/elasticsearch` with the actual installation directory on your machine.

Reload:
```bash
source ~/.bashrc
```

Now you can use:
- `start-dashboard` to start everything
- `stop-dashboard` to stop everything

---

## ⚙️ Configuration

### **Environment Variables**

Create or edit `.env` in project root:

```bash
# Database Configuration
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=llm_ua_clinical
DB_USER=your_username
DB_PASSWORD=your_password

# ElasticSearch Configuration
ELASTICSEARCH_HOST=localhost
ELASTICSEARCH_PORT=9200
ELASTICSEARCH_USERNAME=elastic
ELASTICSEARCH_PASSWORD=P@ssw0rd

# LLM Configuration
LLM_MODEL_PATH=/home/kchollet/LLM_UA/FHIR_LLM_UA/models/llama31-8b-bnb4
LLM_MAX_NEW_TOKENS=800
LLM_TEMPERATURE=0.3
LLM_TOP_P=0.9

# Data Limits
LLM_MAX_CONDITIONS=50
LLM_MAX_OBSERVATIONS=100
LLM_MAX_NOTES=3
LLM_MAX_NOTE_CHARS=2500
```

---

**Last Updated:** November 11, 2025

