#!/bin/bash

###############################################################################
# stop_all.sh - Single Command Shutdown Script
# 
# This script stops all services for the FHIR LLM Clinical Dashboard:
# - Backend API (FastAPI)
# - Frontend (Next.js)
# - Express API
#
# Usage: ./stop_all.sh
###############################################################################

# Auto-detect script location and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$SCRIPT_DIR"

# Load environment variables from .env if it exists
if [ -f "$ROOT_DIR/.env" ]; then
    set -a  # Automatically export all variables
    source "$ROOT_DIR/.env"
    set +a
fi

# Set defaults if not in .env
BACKEND_PORT=${BACKEND_PORT:-8001}
FRONTEND_PORT=${FRONTEND_PORT:-3000}

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✅${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}🛑 Stopping FHIR LLM Clinical Dashboard${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Stop Backend (FastAPI)
log_info "Stopping Backend API (port ${BACKEND_PORT})..."
if pkill -f "uvicorn.*${BACKEND_PORT}" 2>/dev/null; then
    sleep 1
    if pgrep -f "uvicorn.*${BACKEND_PORT}" > /dev/null; then
        log_warning "Backend still running, forcing kill..."
        pkill -9 -f "uvicorn.*${BACKEND_PORT}" 2>/dev/null || true
    fi
    log_success "Backend stopped"
else
    log_info "Backend was not running"
fi

# Stop Frontend (Next.js)
log_info "Stopping Frontend (port ${FRONTEND_PORT})..."
if pkill -f "next.*dev" 2>/dev/null; then
    sleep 1
    if pgrep -f "next.*dev" > /dev/null; then
        log_warning "Frontend still running, forcing kill..."
        pkill -9 -f "next.*dev" 2>/dev/null || true
    fi
    log_success "Frontend stopped"
else
    log_info "Frontend was not running"
fi

# Stop Express API
log_info "Stopping Express API..."
if pkill -f "node.*server.js" 2>/dev/null; then
    sleep 1
    if pgrep -f "node.*server.js" > /dev/null; then
        log_warning "Express API still running, forcing kill..."
        pkill -9 -f "node.*server.js" 2>/dev/null || true
    fi
    log_success "Express API stopped"
else
    log_info "Express API was not running"
fi

# Stop any other related processes
log_info "Cleaning up any remaining processes..."
pkill -f "python.*server.py" 2>/dev/null || true
pkill -f "uvicorn.*8000" 2>/dev/null || true

sleep 2

# Verify ports are free
echo ""
log_info "Verifying ports are free..."

if lsof -Pi :${BACKEND_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Port ${BACKEND_PORT} is still in use"
else
    log_success "Port ${BACKEND_PORT} is free"
fi

if lsof -Pi :${FRONTEND_PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
    log_warning "Port ${FRONTEND_PORT} is still in use"
else
    log_success "Port ${FRONTEND_PORT} is free"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✅ All services stopped${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

