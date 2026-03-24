#!/bin/bash

echo "🛑 Stopping all servers..."

# Stop backend (uvicorn)
echo "Stopping backend server (port 8000)..."
pkill -f "uvicorn app.main:app"

# Stop frontend (python server)
echo "Stopping frontend server (port 5173)..."
pkill -f "python server.py"

# Wait a moment
sleep 2

# Verify they're stopped
BACKEND_RUNNING=$(ps aux | grep "uvicorn app.main:app" | grep -v grep | wc -l)
FRONTEND_RUNNING=$(ps aux | grep "python server.py" | grep -v grep | wc -l)

if [ $BACKEND_RUNNING -eq 0 ] && [ $FRONTEND_RUNNING -eq 0 ]; then
    echo "✅ All servers stopped successfully!"
else
    echo "⚠️  Some processes may still be running. Force killing..."
    pkill -9 -f "uvicorn app.main:app"
    pkill -9 -f "python server.py"
    sleep 1
    echo "✅ Force kill complete!"
fi

echo ""
echo "📋 Server Status:"
echo "Backend (port 8000): $(lsof -ti:8000 | wc -l) processes"
echo "Frontend (port 5173): $(lsof -ti:5173 | wc -l) processes"
echo ""
echo "✅ Safe to exit now!"

















