# SOVRN Build & Deployment Guide
## Complete Implementation & Testing of Three-Agent Pipeline

**Date**: January 3, 2026  
**Status**: Phase 1 - 90% Complete (Designer + Engineer agents now functional)  
**Remaining**: Final integration testing, model deployment

---

## 🎯 Overview

SOVRN is now ready for the complete build. All three AI agents (Strategist, Designer, Engineer) are fully implemented and integrated. This guide walks you through building, testing, and deploying the complete system.

### Current Status

| Component | Status | Notes |
|-----------|--------|-------|
| **Strategist Agent** | ✅ Complete | Analyzes business goals, creates site structure |
| **Designer Agent** | ✅ Complete | Generates design systems with cultural adaptation |
| **Engineer Agent** | ✅ Complete | Produces Next.js code, components, pages |
| **Inference Service** | ✅ Complete | OpenAI-compatible API, model management |
| **API Service** | ✅ Complete | FastAPI with all endpoints, auth, jobs |
| **Web Frontend** | ✅ Basic | Dashboard, auth, project management |
| **Database** | ✅ Complete | PostgreSQL schema with 15+ tables |
| **Docker** | ✅ Complete | Multi-stage builds, production-ready |

---

## 📋 Prerequisites

### System Requirements

```bash
# Minimum specs
- CPU: 4+ cores (8+ recommended for inference)
- RAM: 8GB (16GB recommended for model + services)
- Storage: 50GB (for models + containers + code)
- OS: Linux (Ubuntu 20.04+ or equivalent)

# Or use Dev Container in VS Code
- VS Code with Remote Containers extension
- Docker & Docker Compose installed
```

### Software Requirements

```bash
# Required
- Docker 20.10+
- Docker Compose 2.0+
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend)
- Git 2.0+

# Optional
- Make (for convenient commands)
- CUDA 11.8+ (for GPU acceleration of inference)
```

### Verify Installation

```bash
docker --version        # Should output: Docker version 20.10+
docker-compose --version # Should output: Docker Compose version 2.0+
python3 --version       # Should output: Python 3.11+
node --version          # Should output: v18+
```

---

## 🚀 Quick Start (5 minutes)

### For Development with Dev Container

1. **Open in VS Code**
   ```bash
   git clone https://github.com/Miljte/Sovrn
   cd Sovrn
   # VS Code will suggest opening in Dev Container
   # Click "Reopen in Container"
   ```

2. **Download a Model**
   ```bash
   bash scripts/download-model.sh
   # Choose a model (recommended: Mixtral 8x7B Q4 for balance)
   # Wait for download to complete (5-15 GB)
   ```

3. **Start Services**
   ```bash
   docker-compose up -d
   # Services will start in background
   ```

4. **Verify Health**
   ```bash
   # Check each service
   curl http://localhost:8080/health  # Inference
   curl http://localhost:8000/health  # API
   curl http://localhost:3000 -I      # Web
   ```

5. **Access Dashboard**
   ```
   http://localhost:3000/dashboard
   # Create account → Create project → Generate site
   ```

---

## 🛠️ Complete Build Process

### Step 1: Clone & Setup

```bash
# Clone repository
git clone https://github.com/Miljte/Sovrn
cd Sovrn

# Copy environment configuration
cp services/api/.env.example services/api/.env
cp apps/web/.env.example apps/web/.env

# Review and update .env files as needed
nano services/api/.env
nano apps/web/.env
```

### Step 2: Build Docker Images

```bash
# Build all services (takes 5-15 minutes)
docker-compose build

# Or individual services
docker-compose build api       # Python FastAPI
docker-compose build infer     # Inference server
docker-compose build web       # Next.js frontend
```

### Step 3: Start Services

```bash
# Start all services in background
docker-compose up -d

# Or with logs visible
docker-compose up

# Verify all started successfully
docker-compose ps
# Output should show all containers as "Up"
```

### Step 4: Initialize Database

```bash
# Run migrations (Alembic)
docker-compose exec api alembic upgrade head

# Seed initial data (optional)
docker-compose exec api python -m app.scripts.seed_data
```

### Step 5: Download AI Model

```bash
# Interactive model selection & download
bash scripts/download-model.sh

# Or specify directly
bash scripts/download-model.sh --model "mistral-7b-v0.1.Q4_K_M.gguf"

# Models stored in: /models directory (mounted in containers)
```

### Step 6: Test Services

```bash
# Test inference service health
curl http://localhost:8080/health

# Test inference API
curl -X POST http://localhost:8080/v1/chat/completions \
  -H 'Content-Type: application/json' \
  -d '{
    "messages": [{"role": "user", "content": "Hello, tell me about web design"}],
    "max_tokens": 100
  }'

# Test API health
curl http://localhost:8000/health

# Access API docs
open http://localhost:8000/docs

# Test web frontend
open http://localhost:3000
```

---

## 🧪 Testing the Three-Agent Pipeline

### Automated Test

```bash
# Run full generation pipeline test
python3 services/api/tests/test_generation_pipeline.py

# Expected output:
# ✓ Strategist: Analyzed business goals
# ✓ Designer: Created design system
# ✓ Engineer: Generated code
# ✓ Complete site generation successful
```

### Manual End-to-End Test

#### 1. Create Account & Project

```bash
# Open dashboard
open http://localhost:3000

# Sign up or login
# Create new project
# Fill in project details
```

#### 2. Generate Site

```bash
# In project, click "Generate Site"
# Enter business brief (example):
"""
We run a sustainable coffee shop in Portland and want to increase online orders.
Target: Health-conscious customers aged 20-50.
We need: Product showcase, order system, about us, contact.
"""

# Select locale: English
# Click "Generate"
# Watch progress: Strategy → Design → Code
# Wait 5-10 minutes (depending on model speed)
```

#### 3. Review Generated Site

```bash
# Once complete:
# - Strategy: View business analysis
# - Design: Review color scheme, layouts
# - Code: Download Next.js project
# - Preview: Live preview of generated site
```

#### 4. Export & Deploy

```bash
# Download generated Next.js project
# From dashboard: Project → Download Code

# Deploy to Vercel (easiest):
# cd downloaded-project
# npm install
# git init && git add . && git commit -m "init"
# vercel deploy

# Or self-host:
# npm install
# npm run build
# npm start
```

---

## 📊 Generation Pipeline Details

### Agent 1: Strategist
**Purpose**: Business analysis and site structure  
**Input**: Business brief, industry, locale  
**Output**: Site strategy with pages, CTAs, KPIs

```python
strategy = await strategist_agent.analyze(
    brief="...",
    locale="en",
    industry="ecommerce"
)
# Returns: SiteStrategy with business_goal, pages, conversion_funnel
```

### Agent 2: Designer
**Purpose**: Design system and visual language  
**Input**: Strategy, brand guidelines, locale rules  
**Output**: Complete design system with tokens and page layouts

```python
design = await designer_agent.design(
    strategy=strategy,
    locale="en",
    brand_guidelines={"colors": ["green"], "style": "modern"}
)
# Returns: DesignSystem with colors, typography, components
```

### Agent 3: Engineer
**Purpose**: Next.js code generation  
**Input**: Strategy + Design  
**Output**: Complete, deployable Next.js project

```python
code = await engineer_agent.generate(
    strategy=strategy,
    design=design,
    project_name="my-site"
)
# Returns: GeneratedSite with files, pages, components
```

### Full Pipeline

```python
# Orchestrated by GenerationService
from app.services.generation import generation_service

# One call runs all three agents in sequence
project = await generation_service.generate(
    request=GenerationRequest(
        brief="Business brief...",
        project_name="my-project",
        locale="en",
        industry="tech"
    )
)
# Returns: GeneratedProject with strategy, design, code
```

---

## 🔧 Troubleshooting

### Inference Service Won't Start

```bash
# Check logs
docker-compose logs infer

# Common issues:
# 1. Model not found
#    → Run: bash scripts/download-model.sh
#
# 2. Out of memory
#    → Reduce max_gpu_layers in .env or use smaller model
#
# 3. Port 8080 already in use
#    → Change port in docker-compose.yml or stop other services
```

### API Service Connection Errors

```bash
# Check API logs
docker-compose logs api

# Common issues:
# 1. Database not ready
#    → Wait 10 seconds and restart: docker-compose restart api
#
# 2. Inference service not responding
#    → Check inference service is healthy
#    → Update INFERENCE_URL in .env
#
# 3. Redis not available
#    → Restart Redis: docker-compose restart redis
```

### Generation Fails

```bash
# Check error in logs
docker-compose logs api | grep -i error

# Common issues:
# 1. Model not loaded
#    → Check inference service health: curl http://localhost:8080/health
#
# 2. Out of memory during generation
#    → Reduce max_tokens in request
#    → Use smaller model
#
# 3. JSON parsing error
#    → Model output not valid JSON
#    → Try different model or adjust temperature (lower = more structured)
```

### Database Connection Issues

```bash
# Reset database
docker-compose exec postgres dropdb -U sovrn sovrn_dev
docker-compose exec postgres createdb -U sovrn sovrn_dev
docker-compose exec api alembic upgrade head
```

---

## 📈 Performance Tuning

### Inference Speed

```bash
# For faster inference (CPU):
# 1. Use smaller model (7B instead of 13B)
# 2. Reduce context window: max_context_length in .env
# 3. Increase threads: inference_threads in .env
# 4. Enable GPU if available

# Expected performance:
# CPU (4 cores): 15-25 tokens/sec
# CPU (8 cores): 25-35 tokens/sec
# GPU (RTX 3080): 100-200 tokens/sec
```

### API Response Time

```bash
# Typical generation timeline:
# Strategy:  60-90 seconds
# Design:    60-120 seconds
# Engineer:  120-180 seconds
# Total:     240-390 seconds (4-6.5 minutes)

# To optimize:
# 1. Use faster model (Mistral instead of Mixtral)
# 2. Reduce output tokens (shorter code)
# 3. Use parallel processing for components
```

### Database Optimization

```bash
# Enable slow query logging
docker-compose exec postgres psql -U sovrn -d sovrn_dev
# ALTER DATABASE sovrn_dev SET log_min_duration_statement = 100;

# Monitor queries
docker-compose exec postgres psql -U sovrn -d sovrn_dev
# SELECT query FROM pg_stat_statements WHERE mean_time > 100;
```

---

## 🌍 Deployment

### Production Checklist

```bash
☐ Environment variables configured
☐ Database backups enabled
☐ Inference model cached/optimized
☐ SSL certificates generated
☐ Rate limiting configured
☐ Monitoring alerts set up
☐ Logging aggregation enabled
☐ Secrets management in place
☐ Docker images scanned for vulnerabilities
☐ Load testing completed
```

### Docker Compose Production

```bash
# Use production config
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# With Caddy reverse proxy
# (Already configured in docker-compose.yml)
# Access via: https://yourdomain.com
```

### Kubernetes Deployment

```bash
# Create Kubernetes manifests from docker-compose
# kubectl apply -f k8s/manifests/

# Or use Helm charts (future release)
helm install sovrn ./charts/sovrn
```

### Cloud Deployment

#### Heroku
```bash
heroku create my-sovrn-app
heroku addons:create heroku-postgresql:standard-0
heroku config:set INFERENCE_URL=https://inference.example.com
git push heroku main
```

#### AWS
```bash
# Use ECS/Fargate with RDS PostgreSQL
# ECR for image registry
# ElastiCache for Redis
# See: docs/DEPLOYMENT.md
```

#### DigitalOcean
```bash
# Use App Platform + Managed Database
# droplet OR App Platform recommended
# See deployment guide in docs/
```

---

## 📚 Next Steps

### Phase 2: Feature Parity (Weeks 2-4)

```
[ ] Advanced Visual Editor (GrapesJS integration)
[ ] Template Library (20+ pre-built templates)
[ ] Asset Management (image upload, CDN integration)
[ ] Enhanced Dashboard (drag-drop, live preview)
[ ] Generation History & Versioning
```

### Phase 3: Quality & Testing (Weeks 5-6)

```
[ ] Unit Tests (backend, frontend)
[ ] Integration Tests (pipeline)
[ ] E2E Tests (Playwright)
[ ] CI/CD Pipeline (GitHub Actions)
[ ] Performance Testing
```

### Phase 4: Production Ready (Weeks 7-8)

```
[ ] Monitoring & Alerting (Prometheus, Grafana)
[ ] Security Hardening
[ ] Performance Optimization
[ ] Documentation
[ ] Public Launch
```

---

## 💡 Tips & Tricks

### Quick Development Loop

```bash
# Watch mode for API
docker-compose exec api watchmedo auto-restart -d app -p '*.py' -- \
  uvicorn main:app --reload

# Watch mode for web
docker-compose exec web npm run dev

# Or in separate terminals:
npm run dev  # From apps/web directory
python -m uvicorn app.main:app --reload  # From services/api
```

### Testing Specific Agents

```bash
# Test only Strategist
python3 -c "
import asyncio
from app.agents.strategist import strategist_agent
asyncio.run(strategist_agent.analyze('Test brief'))
"

# Test Designer
python3 -c "
import asyncio
from app.agents.designer import designer_agent
# Need strategy first, see examples
"
```

### Debugging Generation

```bash
# Set debug logging
export LOG_LEVEL=DEBUG
docker-compose up api

# Monitor inference service
watch -n 1 'curl http://localhost:8080/stats | jq .'

# Watch database queries
docker-compose exec postgres psql -U sovrn -d sovrn_dev -c \
  "SELECT * FROM pg_stat_statements ORDER BY calls DESC LIMIT 10;"
```

### Model Selection Guide

```
Use this matrix to choose the right model:

Size     | Quality | Speed | Memory | Recommended
---------|---------|-------|--------|---------------
3B       | Fair    | Fast  | 4GB    | Demo, testing
7B       | Good    | Med   | 6GB    | Most use cases
13B      | Better  | Slow  | 10GB   | High quality output
70B      | Best    | Very Slow | 48GB | Enterprise
Mixtral  | Excellent | Fast  | 24GB   | Best balance

For SOVRN: Recommend 7B or Mixtral 8x7B Q4
```

---

## 📞 Support & Resources

### Documentation
- [API.md](docs/API.md) - Complete API documentation
- [DEPLOYMENT.md](docs/DEPLOYMENT.md) - Deployment guides
- [SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) - Architecture details
- [QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) - Commands and troubleshooting

### Community
- GitHub Issues: Report bugs and request features
- Discussions: Ask questions and share ideas
- Contributing: See CONTRIBUTING.md

### Professional Support
- Email: support@sovrn.ai
- Discord: [Join our community](https://discord.gg/sovrn)
- Enterprise: contact@sovrn.ai

---

## ✅ Verification Checklist

After completing the build, verify everything works:

```bash
# Health checks
☐ Inference service responding (http://localhost:8080/health)
☐ API service responding (http://localhost:8000/health)
☐ Web frontend accessible (http://localhost:3000)
☐ Database connected
☐ Redis connected

# Functionality tests
☐ Can create account
☐ Can create project
☐ Can start generation
☐ All three agents execute
☐ Code is generated successfully
☐ Can download generated site

# Performance baselines
☐ Strategy generation: < 90 seconds
☐ Design generation: < 120 seconds
☐ Code generation: < 180 seconds
☐ Total pipeline: < 400 seconds
☐ API response time: < 100ms (excluding generation)

# Production readiness
☐ All environment variables set
☐ Database backups configured
☐ Monitoring enabled
☐ Logging aggregated
☐ Security hardened
☐ Rate limiting active
```

---

**🎉 You're ready to generate AI websites!**

For the latest updates, visit: https://github.com/Miljte/Sovrn

---

*Last Updated: January 3, 2026*  
*Version: 1.0.0*
