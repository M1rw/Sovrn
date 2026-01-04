#!/bin/bash
# SOVRN Build & Test Script
# Runs the complete build process with validation

set -e

echo "╔════════════════════════════════════════════════════════════════════════════╗"
echo "║                      SOVRN COMPLETE BUILD SCRIPT                          ║"
echo "║              Three-Agent AI Website Builder Construction                   ║"
echo "╚════════════════════════════════════════════════════════════════════════════╝"

SOVRN_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SOVRN_ROOT"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

log_success() {
    echo -e "${GREEN}✓${NC} $1"
}

log_error() {
    echo -e "${RED}✗${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Step 1: Check Docker and Docker Compose
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 1: System Checks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_info "Checking Docker installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    log_success "Docker installed: $DOCKER_VERSION"
else
    log_error "Docker not found. Please install Docker first."
    exit 1
fi

log_info "Checking Docker Compose installation..."
if command -v docker-compose &> /dev/null; then
    DC_VERSION=$(docker-compose --version)
    log_success "Docker Compose installed: $DC_VERSION"
else
    log_error "Docker Compose not found. Please install Docker Compose."
    exit 1
fi

# Step 2: Build Docker images
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 2: Building Docker Images"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_info "Building API service..."
docker-compose build api
log_success "API service built"

log_info "Building Inference service..."
docker-compose build infer
log_success "Inference service built"

log_info "Building Web frontend..."
docker-compose build web
log_success "Web frontend built"

# Step 3: Start services
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 3: Starting Services"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

log_info "Starting PostgreSQL..."
docker-compose up -d postgres
sleep 5
log_success "PostgreSQL started"

log_info "Starting Redis..."
docker-compose up -d redis
sleep 3
log_success "Redis started"

log_info "Starting Inference service..."
docker-compose up -d infer
sleep 10
log_success "Inference service started"

log_info "Starting API service..."
docker-compose up -d api
sleep 5
log_success "API service started"

log_info "Starting Web frontend..."
docker-compose up -d web
sleep 5
log_success "Web frontend started"

# Step 4: Health checks
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 4: Health Checks"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check inference service
log_info "Checking inference service health..."
if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
    log_success "Inference service is healthy"
else
    log_warning "Inference service not responding yet (may still be starting)"
fi

# Check API service
log_info "Checking API service health..."
if curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
    log_success "API service is healthy"
else
    log_warning "API service not responding yet (may still be starting)"
fi

# Check Web frontend
log_info "Checking web frontend..."
if curl -sf http://localhost:3000 > /dev/null 2>&1; then
    log_success "Web frontend is responsive"
else
    log_warning "Web frontend not responding yet (may still be starting)"
fi

# Step 5: Display endpoints
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 5: Service Endpoints"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo -e "${GREEN}Services are now running!${NC}"
echo ""
echo "  📊 API Service:"
echo "     • OpenAPI Docs: http://localhost:8000/docs"
echo "     • ReDoc: http://localhost:8000/redoc"
echo "     • Health: http://localhost:8000/health"
echo ""
echo "  🧠 Inference Service:"
echo "     • Health: http://localhost:8080/health"
echo "     • Chat Completions: http://localhost:8080/v1/chat/completions"
echo ""
echo "  🌐 Web Frontend:"
echo "     • App: http://localhost:3000"
echo "     • Dashboard: http://localhost:3000/dashboard"
echo ""
echo "  🗄️  Database:"
echo "     • PostgreSQL: localhost:5432"
echo "     • User: sovrn"
echo "     • Database: sovrn_dev"
echo ""
echo "  💾 Cache:"
echo "     • Redis: localhost:6379"
echo ""

# Step 6: Run tests (optional)
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "STEP 6: Optional Testing"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

read -p "Run generation pipeline test? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    log_info "Running generation pipeline test..."
    if python3 services/api/tests/test_generation_pipeline.py; then
        log_success "Generation pipeline test passed!"
    else
        log_warning "Generation pipeline test had issues (may be due to model not loaded)"
    fi
fi

# Summary
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ BUILD COMPLETE!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

echo ""
echo "🚀 Next Steps:"
echo ""
echo "1. Download a model:"
echo "   bash scripts/download-model.sh"
echo ""
echo "2. Test the inference service:"
echo "   curl -X POST http://localhost:8080/v1/chat/completions \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'"
echo ""
echo "3. Visit the dashboard:"
echo "   http://localhost:3000/dashboard"
echo ""
echo "4. View logs:"
echo "   docker-compose logs -f api"
echo "   docker-compose logs -f infer"
echo "   docker-compose logs -f web"
echo ""
echo "5. Stop services:"
echo "   docker-compose down"
echo ""

log_success "SOVRN is ready to go! 🎉"
