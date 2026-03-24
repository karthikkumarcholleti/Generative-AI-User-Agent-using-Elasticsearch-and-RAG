#!/bin/bash

###############################################################################
# start_all.sh - Single Command Startup Script
# 
# This script starts all services needed for the FHIR LLM Clinical Dashboard:
# - Elasticsearch (port 9200) - if not already running
# - Backend API (FastAPI on port 8001)
# - Frontend (Next.js on port 3000)
# - Express API (if needed)
#
# Usage: ./start_all.sh
###############################################################################

set -e  # Exit on error (but we handle Elasticsearch gracefully)

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages (defined early so we can use them)
log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

log_error() {
    echo -e "${RED}❌${NC} $1"
}

log_step() {
    echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}$1${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}\n"
}

# Auto-detect script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Load environment variables from .env if it exists
if [ -f "$ROOT_DIR/.env" ]; then
    log_info "Loading configuration from .env..."
    set -a  # Automatically export all variables
    source "$ROOT_DIR/.env"
    set +a
else
    log_warning ".env file not found. Using defaults. Copy .env.example to .env to configure."
fi

# Set defaults if not in .env
BACKEND_PORT=${BACKEND_PORT:-8001}
FRONTEND_PORT=${FRONTEND_PORT:-3000}
ELASTICSEARCH_PORT=${ELASTICSEARCH_PORT:-9200}
ELASTICSEARCH_HOST=${ELASTICSEARCH_HOST:-localhost}
BACKEND_URL=${BACKEND_URL:-http://localhost:8001}
FRONTEND_URL=${FRONTEND_URL:-http://localhost:3000}

# Project paths (relative to ROOT_DIR)
BACKEND_DIR="$ROOT_DIR/FHIR_LLM_UA/backend"
FRONTEND_DIR="$ROOT_DIR/FHIR_dashboard/backend/frontend"
EXPRESS_DIR="$ROOT_DIR/FHIR_dashboard/backend"
VENV_DIR="$ROOT_DIR/FHIR_LLM_UA/venv"
ELASTICSEARCH_DIR="$ROOT_DIR/elasticsearch-8.14.0"

# Log files
BACKEND_LOG="$ROOT_DIR/FHIR_LLM_UA/backend.log"
NEXTJS_LOG="$ROOT_DIR/FHIR_dashboard/nextjs.log"
EXPRESS_LOG="$ROOT_DIR/FHIR_dashboard/express.log"
ELASTICSEARCH_LOG="$ROOT_DIR/elasticsearch.log"

# Function to check if a service is running
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=30
    local attempt=0
    
    log_info "Waiting for $service_name to be ready..."
    
    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log_success "$service_name is ready!"
            return 0
        fi
        attempt=$((attempt + 1))
        sleep 1
    done
    
    log_warning "$service_name did not become ready after ${max_attempts} seconds"
    return 1
}

# Cleanup function for graceful shutdown
cleanup_on_exit() {
    echo ""
    log_step "🛑 Shutting down services..."
    
    # Load .env if available for port numbers
    if [ -f "$ROOT_DIR/.env" ]; then
        set -a
        source "$ROOT_DIR/.env"
        set +a
    fi
    BACKEND_PORT=${BACKEND_PORT:-8001}
    FRONTEND_PORT=${FRONTEND_PORT:-3000}
    
    # Kill processes if they exist
    if [ -n "${BACKEND_PID:-}" ]; then
        log_info "Stopping Backend API..."
        kill "$BACKEND_PID" 2>/dev/null || pkill -f "uvicorn.*${BACKEND_PORT}" 2>/dev/null || true
    fi
    
    if [ -n "${NEXT_PID:-}" ]; then
        log_info "Stopping Frontend..."
        kill "$NEXT_PID" 2>/dev/null || pkill -f "next.*dev" 2>/dev/null || true
    fi
    
    if [ -n "${EXPRESS_PID:-}" ]; then
        log_info "Stopping Express API..."
        kill "$EXPRESS_PID" 2>/dev/null || pkill -f "node.*server.js" 2>/dev/null || true
    fi
    
    # Only stop Elasticsearch if we started it
    if [ -n "${ES_PID:-}" ]; then
        log_info "Stopping Elasticsearch..."
        kill "$ES_PID" 2>/dev/null || true
    fi
    
    sleep 2
    log_success "All services stopped"
    exit 0
}

# Set trap for Ctrl+C
trap cleanup_on_exit SIGINT SIGTERM

# Cleanup function for initial cleanup
cleanup() {
    log_info "Cleaning up..."
    # Load .env if available for port numbers
    if [ -f "$ROOT_DIR/.env" ]; then
        set -a
        source "$ROOT_DIR/.env"
        set +a
    fi
    BACKEND_PORT=${BACKEND_PORT:-8001}
    # Kill processes if they exist
    pkill -f "uvicorn.*${BACKEND_PORT}" 2>/dev/null || true
    pkill -f "next.*dev" 2>/dev/null || true
    pkill -f "node.*server.js" 2>/dev/null || true
    # Note: We don't kill Elasticsearch here as it may be used by other services
    sleep 2
}

###############################################################################
# MAIN SCRIPT
###############################################################################

log_step "🚀 Starting FHIR LLM Clinical Dashboard"

# Step 1: Stop existing processes
log_step "Step 1: Stopping existing processes"
cleanup
log_success "Existing processes stopped"

# Step 1.5: Start Elasticsearch
log_step "Step 1.5: Starting Elasticsearch"

# Check if Elasticsearch is already running
if curl -s "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}" > /dev/null 2>&1; then
    log_success "Elasticsearch is already running"
    ES_STATUS=$(curl -s "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}/_cluster/health" 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    log_info "Cluster status: $ES_STATUS"
    ES_RUNNING=true
else
    ES_RUNNING=false
    # Check if Elasticsearch directory exists
    if [ ! -d "$ELASTICSEARCH_DIR" ]; then
        log_warning "Elasticsearch directory not found: $ELASTICSEARCH_DIR"
        log_info "Skipping Elasticsearch startup (assuming external instance)"
    elif [ ! -f "$ELASTICSEARCH_DIR/bin/elasticsearch" ]; then
        log_warning "Elasticsearch binary not found"
        log_info "Skipping Elasticsearch startup (assuming external instance)"
    else
        log_info "Starting Elasticsearch..."
        cd "$ELASTICSEARCH_DIR"
        nohup ./bin/elasticsearch > "$ELASTICSEARCH_LOG" 2>&1 &
        ES_PID=$!
        log_success "Elasticsearch started (PID: $ES_PID)"
        log_info "Logs: $ELASTICSEARCH_LOG"
        
        # Wait for Elasticsearch to be ready
        log_info "Waiting for Elasticsearch to be ready (this may take 10-30 seconds)..."
        ES_READY=false
        for i in {1..30}; do
            if curl -s "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}" > /dev/null 2>&1; then
                ES_READY=true
                ES_RUNNING=true
                break
            fi
            sleep 1
        done
        
        if [ "$ES_READY" = true ]; then
            ES_STATUS=$(curl -s "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}/_cluster/health" 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
            log_success "Elasticsearch is ready! (Status: $ES_STATUS)"
        else
            log_warning "Elasticsearch may not be fully ready yet. Check logs: $ELASTICSEARCH_LOG"
        fi
        cd "$ROOT_DIR"
    fi
fi

# Step 2: Pre-flight checks
log_step "Step 2: Pre-flight checks"

# Check backend directory
if [ ! -d "$BACKEND_DIR" ]; then
    log_error "Backend directory not found: $BACKEND_DIR"
    exit 1
fi
log_success "Backend directory found"

# Check virtual environment
if [ ! -d "$VENV_DIR" ] || [ ! -f "$VENV_DIR/bin/activate" ]; then
    log_error "Virtual environment not found: $VENV_DIR"
    log_info "Please create it first: python -m venv $VENV_DIR"
    exit 1
fi
log_success "Virtual environment found"

# Check frontend directory
if [ ! -d "$FRONTEND_DIR" ]; then
    log_error "Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi
log_success "Frontend directory found"

# Check if node_modules exists
if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
    log_warning "node_modules not found. Run 'npm install' in $FRONTEND_DIR first"
    log_info "Attempting to install dependencies..."
    cd "$FRONTEND_DIR"
    npm install || {
        log_error "Failed to install dependencies"
        exit 1
    }
    log_success "Dependencies installed"
fi

# Check ports
if check_port $BACKEND_PORT; then
    # Check if backend is healthy before killing it
    if curl -s "http://localhost:${BACKEND_PORT}/health" 2>/dev/null | grep -q '"status":"ok"'; then
        log_success "Backend is already running and healthy on port ${BACKEND_PORT} - keeping it running"
        SKIP_BACKEND_START=true
    else
        log_warning "Port ${BACKEND_PORT} is in use but backend is not healthy. Attempting to free it..."
        pkill -f "uvicorn.*${BACKEND_PORT}" 2>/dev/null || true
        sleep 2
        SKIP_BACKEND_START=false
    fi
else
    SKIP_BACKEND_START=false
fi

if check_port $FRONTEND_PORT; then
    log_warning "Port ${FRONTEND_PORT} is already in use. Attempting to free it..."
    pkill -f "next.*dev" 2>/dev/null || true
    sleep 2
fi

# Step 3: Start Backend
if [ "${SKIP_BACKEND_START:-false}" = true ]; then
    log_step "Step 3: Backend API (port ${BACKEND_PORT}) - Already Running"
    log_success "Backend is already running and healthy - skipping startup"
    BACKEND_PID=$(pgrep -f "uvicorn.*${BACKEND_PORT}" | head -1)
    log_info "Backend PID: $BACKEND_PID"
else
    log_step "Step 3: Starting Backend API (port ${BACKEND_PORT})"

    cd "$BACKEND_DIR"
    source "$VENV_DIR/bin/activate"

    log_info "Starting FastAPI backend..."
    nohup python -m uvicorn app.main:app --host 0.0.0.0 --port ${BACKEND_PORT} > "$BACKEND_LOG" 2>&1 &
    BACKEND_PID=$!

    log_success "Backend started (PID: $BACKEND_PID)"
    log_info "Logs: $BACKEND_LOG"
fi

# Wait for backend to be ready with extended timeout
log_info "Waiting for backend to start (this may take 15-30 seconds)..."
BACKEND_READY=false
for i in {1..30}; do
    if curl -s "http://localhost:${BACKEND_PORT}/health" > /dev/null 2>&1; then
        # Verify health response is correct
        HEALTH_RESPONSE=$(curl -s "http://localhost:${BACKEND_PORT}/health" 2>/dev/null)
        if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
            BACKEND_READY=true
            log_success "Backend is healthy!"
            break
        fi
    fi
    sleep 1
done

if [ "$BACKEND_READY" = false ]; then
    log_error "Backend failed to start or is not healthy!"
    log_info "Checking backend logs..."
    tail -20 "$BACKEND_LOG" 2>/dev/null | head -10
    log_error "Please check the logs: $BACKEND_LOG"
    log_warning "Continuing anyway, but backend may not be working..."
fi

# Verify patients endpoint works
if [ "$BACKEND_READY" = true ]; then
    log_info "Verifying patients endpoint..."
    PATIENTS_TEST=$(curl -s "http://localhost:${BACKEND_PORT}/patients" 2>/dev/null | head -1)
    if echo "$PATIENTS_TEST" | grep -q "patientId\|patient_id"; then
        PATIENT_COUNT=$(curl -s "http://localhost:${BACKEND_PORT}/patients" 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(len(d))" 2>/dev/null || echo "?")
        log_success "Patients endpoint working ($PATIENT_COUNT patients available)"
    else
        log_warning "Patients endpoint may not be working correctly"
    fi
fi

# Step 4: Start Express API (if needed)
log_step "Step 4: Starting Express API (if needed)"

if [ -f "$EXPRESS_DIR/server.js" ]; then
    cd "$EXPRESS_DIR"
    log_info "Starting Express API..."
    nohup node server.js > "$EXPRESS_LOG" 2>&1 &
    EXPRESS_PID=$!
    log_success "Express API started (PID: $EXPRESS_PID)"
    log_info "Logs: $EXPRESS_LOG"
    sleep 2
else
    log_info "Express API not found, skipping..."
fi

# Step 5: Start Frontend
log_step "Step 5: Starting Frontend (port ${FRONTEND_PORT})"

cd "$FRONTEND_DIR"
log_info "Starting Next.js frontend..."
# Set PORT environment variable for Next.js
PORT=${FRONTEND_PORT} nohup npm run dev > "$NEXTJS_LOG" 2>&1 &
NEXT_PID=$!

log_success "Frontend started (PID: $NEXT_PID)"
log_info "Logs: $NEXTJS_LOG"

# Wait for frontend to be ready
log_info "Waiting for frontend to compile (this may take 30-60 seconds)..."
sleep 10

# Try to check if frontend is responding
if wait_for_service "http://localhost:${FRONTEND_PORT}" "Frontend"; then
    log_success "Frontend is ready!"
else
    log_warning "Frontend may still be compiling. Check logs: $NEXTJS_LOG"
fi

# Step 6: Display status
log_step "✅ All Services Started!"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📊 Service Status${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Elasticsearch:${NC}"
if [ "${ES_RUNNING:-false}" = true ] || curl -s "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}" > /dev/null 2>&1; then
    ES_STATUS=$(curl -s "http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}/_cluster/health" 2>/dev/null | python3 -c "import sys, json; d=json.load(sys.stdin); print(d.get('status', 'unknown'))" 2>/dev/null || echo "unknown")
    echo "   URL:      http://${ELASTICSEARCH_HOST}:${ELASTICSEARCH_PORT}"
    echo "   Status:   $ES_STATUS"
    if [ -n "${ES_PID:-}" ]; then
        echo "   PID:      $ES_PID"
    fi
    echo "   Logs:     $ELASTICSEARCH_LOG"
else
    echo "   Status:   Not running (or external instance)"
fi
echo ""

echo -e "${BLUE}Backend API:${NC}"
echo "   URL:      http://localhost:${BACKEND_PORT}"
echo "   Health:   http://localhost:${BACKEND_PORT}/health"
echo "   Docs:     http://localhost:${BACKEND_PORT}/docs"
echo "   PID:      $BACKEND_PID"
echo "   Logs:     $BACKEND_LOG"
echo ""

if [ -n "${EXPRESS_PID:-}" ]; then
    echo -e "${BLUE}Express API:${NC}"
    echo "   PID:      $EXPRESS_PID"
    echo "   Logs:     $EXPRESS_LOG"
    echo ""
fi

echo -e "${BLUE}Frontend:${NC}"
echo "   URL:      http://localhost:${FRONTEND_PORT}"
echo "   PID:      $NEXT_PID"
echo "   Logs:     $NEXTJS_LOG"
echo ""

echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 7: Verify everything and open browser
log_step "Step 7: Final verification and opening browser"

# Final backend health check before opening browser
log_info "Performing final backend health check..."
FINAL_HEALTH_CHECK=false
for i in {1..5}; do
    HEALTH_RESPONSE=$(curl -s "http://localhost:${BACKEND_PORT}/health" 2>/dev/null)
    if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
        FINAL_HEALTH_CHECK=true
        break
    fi
    sleep 1
done

if [ "$FINAL_HEALTH_CHECK" = true ]; then
    log_success "✅ Backend confirmed healthy!"
    log_info "Health response: $HEALTH_RESPONSE"
    
    # Test patients endpoint one more time
    PATIENTS_RESPONSE=$(curl -s "http://localhost:${BACKEND_PORT}/patients" 2>/dev/null | head -1)
    if echo "$PATIENTS_RESPONSE" | grep -q "patientId\|patient_id"; then
        log_success "✅ Patients endpoint confirmed working!"
        
        # Now open browser to dashboard (full-stack work)
        log_info "Opening browser to Dashboard..."
        DASHBOARD_URL="http://localhost:${FRONTEND_PORT}"
        if command -v firefox > /dev/null 2>&1; then
            firefox "$DASHBOARD_URL" 2>/dev/null &
            log_success "Browser opened to Dashboard!"
        elif command -v google-chrome > /dev/null 2>&1; then
            google-chrome "$DASHBOARD_URL" 2>/dev/null &
            log_success "Browser opened to Dashboard!"
        elif command -v chromium-browser > /dev/null 2>&1; then
            chromium-browser "$DASHBOARD_URL" 2>/dev/null &
            log_success "Browser opened to Dashboard!"
        else
            log_warning "No browser found. Please open manually:"
            echo "   $DASHBOARD_URL"
        fi
    else
        log_error "❌ Patients endpoint not working - NOT opening browser"
        log_warning "Please check backend logs: $BACKEND_LOG"
        log_info "You can manually test: curl http://localhost:${BACKEND_PORT}/patients"
    fi
else
    log_error "❌ Backend health check failed - NOT opening browser"
    log_error "Backend is not responding correctly"
    log_warning "Please check backend logs: $BACKEND_LOG"
    log_info "You can manually test: curl http://localhost:${BACKEND_PORT}/health"
fi

echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}📋 Test Queries${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "1. What is the patient's creatinine level?"
echo "2. What is the patient's heart rate?"
echo "3. Is the patient diabetic?"
echo "4. Show me all vitals"
echo "5. What are the patient's conditions?"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${YELLOW}💡 To stop all services:${NC}"
echo -e "${YELLOW}   • Press Ctrl+C (in this terminal)${NC}"
echo -e "${YELLOW}   • Or run: ./stop_all.sh${NC}"
echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Services are running in the background.${NC}"
echo -e "${BLUE}Press Ctrl+C to stop all services...${NC}"
echo ""

# Keep script running so Ctrl+C can be caught
wait

