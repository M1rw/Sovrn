# SOVRN Quick Start Guide

## Current Status: ✅ Running

All services are currently deployed and running!

```bash
# Check service status
docker-compose ps

# Expected output:
# NAME          IMAGE                STATUS
# sovrn-api     sovrn-api            Up (healthy)
# sovrn-infer   sovrn-infer          Up (healthy)
# sovrn-db      pgvector/pgvector    Up (healthy)
# sovrn-redis   redis:7-alpine       Up (healthy)
# sovrn-web     sovrn-web            Up (ready)
```

## Access Services

### API Service (Backend)
- **URL**: http://localhost:8000
- **Health**: `docker exec sovrn-api curl -s http://localhost:8000/health`
- **Docs**: http://localhost:8000/docs (interactive API docs)

### Inference Service (AI Engine)
- **URL**: http://localhost:8080
- **Health**: `docker exec sovrn-infer curl -s http://localhost:8080/health`
- **Status**: ✅ Running (awaiting model download)

### Web Frontend
- **URL**: http://localhost:3000
- **Status**: ✅ Running

### Database
- **Host**: localhost:5432
- **User**: sovrn
- **Database**: sovrn
- **Note**: Needs `.env` file with POSTGRES_PASSWORD

### Redis Cache
- **Host**: localhost:6379
- **Status**: ✅ Healthy

## Initial Setup

### 1. Create Environment File

Create `.env` in project root:
```bash
cat > .env << 'ENVEOF'
# Database
POSTGRES_PASSWORD=sovrn_secure_password_change_this
POSTGRES_USER=sovrn
POSTGRES_DB=sovrn

# JWT & Auth
JWT_SECRET=your_jwt_secret_key_here_minimum_32_chars
NEXTAUTH_SECRET=your_nextauth_secret_here_minimum_32_chars

# API Configuration
ENVIRONMENT=development
LOG_LEVEL=info
LOG_FORMAT=json

# Inference Service
INFERENCE_URL=http://infer:8080
MODEL_PATH=/models/llama-3.2-11b-q4_k_m.gguf
MODEL_THREADS=2
MODEL_GPU_LAYERS=0
ENVEOF
```

### 2. Download AI Model

Download the Llama 3.2 11B Quantized model:
```bash
# Option 1: Use provided script
bash scripts/download-model.sh

# Option 2: Manual download (~7GB)
mkdir -p models
cd models
# Download from: https://huggingface.co/Qwen/Qwen2-7B-Instruct-GGUF
# Or use llama.cpp recommended models
cd ..
```

### 3. Initialize Database

Run migrations to create schema:
```bash
docker-compose exec api alembic upgrade head
```

### 4. Restart Services

After configuration changes:
```bash
docker-compose restart
```

## Testing Services

### Test API Endpoint
```bash
docker exec sovrn-api curl -s http://localhost:8000/health | jq .
```

Output should show:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "service": "sovrn-api"
}
```

### Test Inference Service
```bash
docker exec sovrn-infer curl -s http://localhost:8080/health | jq .
```

Output should show:
```json
{
  "status": "healthy",
  "model_loaded": false,
  "model_info": null
}
```

Once model is loaded, `model_info` will contain model details.

## Common Commands

### Start Services
```bash
docker-compose up -d
```

### Stop Services
```bash
docker-compose down
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f api
docker-compose logs -f infer
docker-compose logs -f web
docker-compose logs -f db
```

### Rebuild Service
```bash
docker-compose build api
docker-compose up -d api
```

### Database Access
```bash
# Connect to PostgreSQL
docker-compose exec db psql -U sovrn -d sovrn

# Within psql, try:
\dt  # List tables
SELECT COUNT(*) FROM users;
```

### View Redis
```bash
docker-compose exec redis redis-cli
> INFO
> KEYS *
```

## File Structure

```
/workspaces/Sovrn/
├── apps/web/                 # Next.js frontend
├── services/
│   ├── api/                  # FastAPI backend
│   ├── infer/                # Inference service
│   └── worker/               # Background jobs
├── models/                   # AI models directory
├── infra/
│   ├── docker/               # Dockerfiles
│   ├── caddy/                # Reverse proxy config
│   └── migrations/           # Database schemas
├── docker-compose.yml        # Production config
├── docker-compose.dev.yml    # Development config
├── .env                      # Environment variables (create this)
└── QUICK_START.md           # This file
```

## Architecture

```
Frontend (Next.js)          API (FastAPI)           AI Engine (llama.cpp)
http://localhost:3000  →    http://localhost:8000  →  http://localhost:8080

              ↓ (database queries) ↓
         PostgreSQL 16 + pgvector
         http://localhost:5432

              ↓ (cache) ↓
          Redis 7.2
          http://localhost:6379
```

## Three-Agent Pipeline

The system uses three specialized AI agents:

1. **Strategist Agent** - Analyzes business goals, creates site strategy
2. **Designer Agent** - Designs visual layouts and components
3. **Engineer Agent** - Writes production-ready code

Full pipeline flow:
```
User Brief
   ↓
Strategist (understand goals)
   ↓
Designer (create layouts)
   ↓
Engineer (write code)
   ↓
Complete Website
```

## API Routes

### Authentication
- `POST /v1/auth/register` - Register new user
- `POST /v1/auth/login` - Login user
- `POST /v1/auth/logout` - Logout

### Projects
- `POST /v1/projects` - Create new project
- `GET /v1/projects` - List user projects
- `GET /v1/projects/{id}` - Get project details
- `PUT /v1/projects/{id}` - Update project
- `DELETE /v1/projects/{id}` - Delete project

### Generation
- `POST /v1/projects/{id}/generate` - Start generation pipeline
- `GET /v1/projects/{id}/generation-status` - Check generation progress

### Inference (OpenAI-compatible)
- `POST /v1/chat/completions` - Chat completion
- `POST /v1/completions` - Text completion
- `GET /v1/models` - List available models
- `POST /admin/load-model` - Load a model

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| POSTGRES_PASSWORD | ✅ Yes | - | Database password |
| JWT_SECRET | ✅ Yes | - | JWT signing key (32+ chars) |
| NEXTAUTH_SECRET | ✅ Yes | - | NextAuth session secret |
| ENVIRONMENT | ❌ No | development | production/development |
| LOG_LEVEL | ❌ No | info | debug/info/warning/error |
| INFERENCE_URL | ❌ No | http://infer:8080 | Inference service URL |
| MODEL_PATH | ❌ No | /models/llama-3.2-11b-q4_k_m.gguf | Path to AI model |

## Troubleshooting

### Services not starting?
```bash
# Clean restart
docker-compose down
docker-compose up -d

# Check logs
docker-compose logs
```

### API database errors?
```bash
# Verify database is running and healthy
docker-compose ps db

# Check database logs
docker-compose logs db

# Try to connect directly
docker-compose exec db psql -U sovrn -d sovrn
```

### Inference service slow?
```bash
# Check if model is loaded
docker exec sovrn-infer curl http://localhost:8080/health

# If model_loaded is false, download and load model
# Check available models
docker exec sovrn-infer curl http://localhost:8080/v1/models
```

### Web frontend not loading?
```bash
# Check web logs
docker-compose logs web

# Restart web service
docker-compose restart web

# Check API connectivity from web
docker-compose exec web curl http://api:8000/health
```

## Performance Tips

1. **For Development**
   - Use `docker-compose.dev.yml` for faster builds
   - Mount volumes for live code reloading

2. **For Production**
   - Use `docker-compose.yml`
   - Configure SSL/TLS via Caddy
   - Set resource limits appropriately

3. **For Inference Speed**
   - Download quantized models (faster, smaller)
   - Enable GPU layers if GPU available (`MODEL_GPU_LAYERS=30`)
   - Increase threads if CPU cores available (`MODEL_THREADS=8`)

## Getting Help

- **API Docs**: http://localhost:8000/docs
- **Service Logs**: `docker-compose logs [service-name]`
- **Database Issues**: `docker-compose exec db psql -U sovrn`
- **Code Issues**: Check console errors in `docker-compose logs`

## Next Steps

1. ✅ Services running - **Current Status**
2. ⏳ Download model - See "Download AI Model" section
3. ⏳ Initialize database - See "Initialize Database" section  
4. ⏳ Run integration tests
5. ⏳ Test generation pipeline end-to-end
6. ⏳ Deploy to production

---

**SOVRN is ready for development and testing!**

Last updated: January 3, 2026
