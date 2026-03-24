#!/usr/bin/env python3
"""
Backend Management Script - Bypasses shell issues
Run directly: python3 manage_backend.py [start|stop|status|test]
"""

import subprocess
import sys
import time
import requests
import json
import os
from pathlib import Path

BACKEND_DIR = Path(__file__).parent / "FHIR_LLM_UA" / "backend"
BACKEND_PORT = 8001
BACKEND_URL = f"http://localhost:{BACKEND_PORT}"

def run_command(cmd, check=False):
    """Run command without shell (bypasses shell config issues)"""
    try:
        result = subprocess.run(
            cmd,
            shell=False,
            capture_output=True,
            text=True,
            check=check
        )
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)

def stop_backend():
    """Stop backend if running"""
    print("🛑 Stopping backend...")
    cmd = ["pkill", "-9", "-f", "uvicorn.*app.main:app"]
    run_command(cmd)
    time.sleep(2)
    print("✅ Backend stopped")

def start_backend():
    """Start backend"""
    print(f"🚀 Starting backend in {BACKEND_DIR}...")
    
    if not BACKEND_DIR.exists():
        print(f"❌ Backend directory not found: {BACKEND_DIR}")
        return False
    
    # Change to backend directory and start
    log_file = "/tmp/backend_python.log"
    with open(log_file, "w") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app", 
             "--host", "0.0.0.0", "--port", str(BACKEND_PORT)],
            cwd=str(BACKEND_DIR),
            stdout=log,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid  # Create new process group
        )
    
    print(f"✅ Backend started (PID: {process.pid})")
    print(f"📝 Logs: {log_file}")
    return process.pid

def check_backend_status():
    """Check if backend is running"""
    try:
        response = requests.get(f"{BACKEND_URL}/health", timeout=5)
        if response.status_code == 200:
            print("✅ Backend is running and healthy")
            return True
        else:
            print(f"⚠️ Backend responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException:
        print("❌ Backend is not responding")
        return False

def test_query(patient_id="000000500", query="What is the heart rate?"):
    """Test a simple query"""
    print(f"\n🧪 Testing query: '{query}' for patient {patient_id}")
    try:
        response = requests.post(
            f"{BACKEND_URL}/chat-agent/query",
            json={"patient_id": patient_id, "query": query},
            timeout=60
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Query successful")
            print(f"   Response length: {len(data.get('response', ''))} chars")
            print(f"   Has chart: {data.get('chart') is not None}")
            print(f"   Preview: {data.get('response', '')[:150]}...")
            return True
        else:
            print(f"❌ Query failed: {response.status_code}")
            print(f"   {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ Query error: {e}")
        return False

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 manage_backend.py [start|stop|status|restart|test]")
        sys.exit(1)
    
    action = sys.argv[1].lower()
    
    if action == "stop":
        stop_backend()
    
    elif action == "start":
        stop_backend()  # Stop first if running
        time.sleep(1)
        start_backend()
        print("\n⏳ Waiting for backend to start...")
        for i in range(10):
            time.sleep(2)
            if check_backend_status():
                print("\n✅ Backend is ready!")
                break
        else:
            print("\n⚠️ Backend started but not responding yet. Check logs.")
    
    elif action == "restart":
        stop_backend()
        time.sleep(2)
        start_backend()
        print("\n⏳ Waiting for backend to start...")
        for i in range(10):
            time.sleep(2)
            if check_backend_status():
                print("\n✅ Backend is ready!")
                break
    
    elif action == "status":
        check_backend_status()
        # Check process
        success, stdout, stderr = run_command(["pgrep", "-f", "uvicorn.*app.main:app"])
        if success and stdout.strip():
            print(f"✅ Backend process running (PIDs: {stdout.strip()})")
        else:
            print("❌ No backend process found")
    
    elif action == "test":
        if not check_backend_status():
            print("❌ Backend is not running. Start it first with: python3 manage_backend.py start")
            sys.exit(1)
        
        # Test simple query
        test_query()
        
        # Test complex query
        print("\n" + "="*50)
        test_query(query="What are the risk values?")
    
    else:
        print(f"❌ Unknown action: {action}")
        print("Usage: python3 manage_backend.py [start|stop|status|restart|test]")
        sys.exit(1)

if __name__ == "__main__":
    main()

