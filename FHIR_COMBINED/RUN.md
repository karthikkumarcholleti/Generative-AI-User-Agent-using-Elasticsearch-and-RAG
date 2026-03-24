# How to Run the System

## ⚠️ IMPORTANT: Read Before Starting

**Make sure you are in the correct directory and have the right permissions.**

---

## Step-by-Step Instructions

### Step 1: Open Terminal
Open a terminal window on your computer.

### Step 2: Navigate to Project Directory
Copy and paste this command:
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
```

### Step 3: Start All Services
Run this command:
```bash
./start_all.sh
```

**What happens:**
- The script will check/start Elasticsearch (port 9200)
- Start Backend API (port 8001)
- Start Frontend (port 3000)
- Open browser automatically

**Wait for completion:**
- You will see "✅ Setup complete!" message
- The script will keep running (this is normal)
- **DO NOT close the terminal** - keep it open

### Step 4: Verify Services Are Running

**In a NEW terminal window**, run these checks:

```bash
# Check backend health
curl http://localhost:8001/health
```
**Expected:** `{"status":"ok","db":"ok"}`

```bash
# Check if patients endpoint works
curl http://localhost:8001/patients | head -5
```
**Expected:** JSON data with patient information

```bash
# Check frontend proxy
curl http://localhost:3000/api/llm/patients | head -5
```
**Expected:** JSON data with patient information (not an error)

### Step 5: Access the System

**Open your browser and go to:**
```
http://localhost:3000/generative-ai
```

**If you see "Unable to load patients":**
1. Wait 30 seconds (frontend may still be compiling)
2. Press **F5** or **Ctrl+R** to refresh the page
3. Check browser console (F12 → Console tab) for errors
4. Verify backend is running: `curl http://localhost:8001/health`

## Access the System

- **Frontend**: http://localhost:3000/generative-ai
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs

## Stop Everything

### Option 1: Using the Script (Recommended)
In the terminal where you ran `./start_all.sh`, press:
```
Ctrl+C
```

### Option 2: Using Stop Script
In a new terminal:
```bash
cd /mnt/shared/LLM/LLM_UA_karthik_1.0/fhir_karthik/FHIR_COMBINED
./stop_all.sh
```

**Both methods will:**
- Stop Backend API
- Stop Frontend
- Stop Express API
- Free up ports 8001 and 3000

## Check if Services are Running

```
curl http://localhost:8001/health
```

If you see `{"status":"ok","db":"ok"}`, the backend is working.

## View Logs

- Backend: `tail -f FHIR_LLM_UA/backend.log`
- Frontend: `tail -f FHIR_dashboard/nextjs.log`
- Elasticsearch: `tail -f elasticsearch.log`

---

That's it! Simple and easy.

