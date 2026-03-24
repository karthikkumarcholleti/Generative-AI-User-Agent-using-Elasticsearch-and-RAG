# 🧪 Test Results & Run Instructions

## ✅ Test Results

### 1. Environment Configuration ✅
- **Backend can read from root `.env`**: ✅ PASSED
- **Root `.env` file exists**: ✅ PASSED
- **Script syntax validation**: ✅ PASSED

### 2. GPU Memory Management ✅
- **GPU clearing functions exist**: ✅ PASSED
  - `clear_gpu_memory()` - Regular cleanup after queries
  - `clear_gpu_memory_aggressive()` - Aggressive cleanup on patient switches
- **GPU clearing is called automatically**:
  - ✅ After each LLM query
  - ✅ After patient summary generation
  - ✅ On patient switches
  - ✅ On OOM errors

### 3. Scripts ✅
- **start_all.sh**: ✅ Valid syntax
- **stop_all.sh**: ✅ Valid syntax

---

## 🚀 How to Run

### Option 1: Using npm (Recommended)

```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED

# Start everything
npm run dev

# OR
npm start
```

**What happens:**
- Starts Elasticsearch (port 9200)
- Starts Backend API (port 8001)
- Starts Frontend (port 3000)
- Opens browser automatically

**Access:**
- Frontend: http://localhost:3000/generative-ai
- Backend API: http://localhost:8001
- API Docs: http://localhost:8001/docs

### Option 2: Using Scripts Directly

```bash
cd /home/kchollet/LLM_UA/fhir_karthik/FHIR_COMBINED

# Start everything
./start_all.sh
```

**What happens:** Same as Option 1

---

## 🛑 How to Stop

### Option 1: Press Ctrl+C

In the terminal where you ran `npm run dev` or `./start_all.sh`:
```
Press: Ctrl+C
```

This will:
- Stop Backend API
- Stop Frontend
- Stop Express API
- Stop Elasticsearch (if started by script)

### Option 2: Using npm

```bash
npm run stop
```

### Option 3: Using Stop Script

```bash
./stop_all.sh
```

**What happens:**
- Finds and kills all running services
- Verifies ports are free
- Confirms everything stopped

---

## 🔍 Verify Everything is Running

### Check Services:

```bash
# Check Backend
curl http://localhost:8001/health
# Expected: {"status":"ok","db":"ok"}

# Check Frontend
curl http://localhost:3000
# Expected: HTML response

# Check Elasticsearch
curl http://localhost:9200
# Expected: JSON with cluster info
```

### Check Ports:

```bash
# Check if ports are in use
lsof -i :8001  # Backend
lsof -i :3000  # Frontend
lsof -i :9200  # Elasticsearch
```

---

## 🧠 GPU Memory Management

### Automatic GPU Clearing

GPU memory is **automatically cleared** in these scenarios:

1. **After each LLM query** - `clear_gpu_memory()` is called
2. **After patient summary generation** - Multiple cleanup calls
3. **On patient switches** - `clear_gpu_memory_aggressive()` is called
4. **On OOM errors** - Aggressive cleanup is triggered

### Manual GPU Status Check

You can check GPU memory status via API:

```bash
curl http://localhost:8001/gpu-memory
```

**Response:**
```json
{
  "available": true,
  "device_count": 1,
  "devices": [
    {
      "device_id": 0,
      "name": "NVIDIA GeForce RTX 3090",
      "total_gb": 24.0,
      "allocated_gb": 5.2,
      "reserved_gb": 6.1,
      "free_gb": 17.9,
      "usage_percent": 25.4
    }
  ]
}
```

### GPU Clearing Functions

**Regular Cleanup** (`clear_gpu_memory()`):
- Clears cache on all GPU devices (2 passes)
- Synchronizes all devices
- Clears inter-process cache
- Forces Python garbage collection (2 passes)
- Logs memory status

**Aggressive Cleanup** (`clear_gpu_memory_aggressive()`):
- More thorough cleanup (3 garbage collection passes)
- Used when switching patients
- Used on OOM errors

---

## 📋 Quick Reference

### Start:
```bash
npm run dev
# OR
./start_all.sh
```

### Stop:
```bash
Ctrl+C
# OR
npm run stop
# OR
./stop_all.sh
```

### Check Status:
```bash
curl http://localhost:8001/health
curl http://localhost:8001/gpu-memory
```

### Access:
- Frontend: http://localhost:3000/generative-ai
- Backend: http://localhost:8001
- API Docs: http://localhost:8001/docs

---

## ⚠️ Troubleshooting

### Port Already in Use

If you see "Port XXXX is already in use":

```bash
# Stop everything first
./stop_all.sh

# Or kill specific port
lsof -ti:8001 | xargs kill -9  # Backend
lsof -ti:3000 | xargs kill -9  # Frontend
```

### Backend Not Starting

Check logs:
```bash
tail -f FHIR_LLM_UA/backend.log
```

Common issues:
- Database connection failed → Check `.env` DB credentials
- Model not found → Check `LLM_MODEL_PATH` in `.env`
- Port conflict → Change `BACKEND_PORT` in `.env`

### Frontend Not Starting

Check logs:
```bash
tail -f FHIR_dashboard/nextjs.log
```

Common issues:
- `node_modules` missing → Run `npm install`
- Port conflict → Change `FRONTEND_PORT` in `.env`

### GPU Memory Issues

If you see OOM errors:
- GPU memory is automatically cleared, but if issues persist:
- Check GPU status: `curl http://localhost:8001/gpu-memory`
- Restart the system to clear all GPU memory

---

## ✅ Summary

- ✅ **Configuration**: Root `.env` file (portable)
- ✅ **Start**: `npm run dev` or `./start_all.sh`
- ✅ **Stop**: `Ctrl+C` or `npm run stop` or `./stop_all.sh`
- ✅ **GPU Clearing**: Automatic (after queries, patient switches, OOM)
- ✅ **Status Check**: `curl http://localhost:8001/health`
- ✅ **GPU Status**: `curl http://localhost:8001/gpu-memory`

Everything is ready to run! 🚀

