#!/bin/bash

# FHIR LLM Clinical Summary - Startup Script
# This script starts both the backend API server and frontend web server

echo "🏥 Starting FHIR LLM Clinical Summary System"
echo "=============================================="

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first."
    exit 1
fi

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Function to cleanup background processes
cleanup() {
    echo ""
    echo "🛑 Shutting down servers..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Set trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start backend server in background
echo "🚀 Starting backend API server on port 8000..."
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 3

# Start frontend server in background
echo "🌐 Starting frontend web server on port 5173..."
cd frontend
python server.py &
FRONTEND_PID=$!
cd ..

# Wait a moment for frontend to start
sleep 2

echo ""
echo "✅ Both servers are running!"
echo ""
echo "📊 Backend API: http://localhost:8000"
echo "   - Health check: http://localhost:8000/health"
echo "   - API docs: http://localhost:8000/docs"
echo ""
echo "🖥️  Frontend UI: http://localhost:5173"
echo ""
echo "💡 Open your browser and go to http://localhost:5173 to use the interface"
echo ""
echo "Press Ctrl+C to stop both servers"

# Wait for user interrupt
wait
