# SOVRN System Architecture & Technical Specifications
## Complete Production-Ready Design

**Version**: 2.0  
**Date**: January 3, 2026  
**Status**: Production Architecture

---

## Table of Contents

1. [High-Level Architecture](#1-high-level-architecture)
2. [Service Layer Design](#2-service-layer-design)
3. [Database Schema](#3-database-schema)
4. [AI Pipeline Architecture](#4-ai-pipeline-architecture)
5. [Frontend Architecture](#5-frontend-architecture)
6. [API Design](#6-api-design)
7. [Security Architecture](#7-security-architecture)
8. [Scalability & Performance](#8-scalability--performance)
9. [Deployment Architecture](#9-deployment-architecture)
10. [Monitoring & Observability](#10-monitoring--observability)

---

## 1. High-Level Architecture

### 1.1 System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         CLIENT LAYER                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐            │
│  │   Web App    │  │  Mobile App  │  │   API Clients│            │
│  │  (Next.js)   │  │ (React Native)│  │   (CLI/SDK)  │            │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘            │
└─────────┼──────────────────┼──────────────────┼───────────────────┘
          │                  │                  │
          └──────────────────┴──────────────────┘
                             │
          ┌──────────────────▼───────────────────┐
          │      Caddy Reverse Proxy             │
          │   (HTTPS, Rate Limiting, CORS)       │
          └──────────────────┬───────────────────┘
                             │
          ┌──────────────────┴───────────────────┐
          │                                       │
┌─────────▼──────────┐                 ┌─────────▼──────────┐
│   PRESENTATION     │                 │   API GATEWAY      │
│   Next.js Server   │◄───────────────►│   FastAPI Server   │
│   (Port 3000)      │                 │   (Port 8000)      │
│                    │                 │                    │
│  - SSR/SSG         │                 │  - REST API        │
│  - Auth UI         │                 │  - WebSocket       │
│  - Visual Editor   │                 │  - Auth/AuthZ      │
│  - Asset Upload    │                 │  - Rate Limiting   │
└────────────────────┘                 └─────────┬──────────┘
                                                  │
                      ┌───────────────────────────┼───────────────────────────┐
                      │                           │                           │
          ┌───────────▼──────────┐    ┌──────────▼─────────┐    ┌───────────▼──────────┐
          │   BUSINESS LOGIC     │    │   AI SERVICES      │    │   DATA SERVICES      │
          │                      │    │                    │    │                      │
          │  - Project Service   │    │  - Inference API   │    │  - PostgreSQL 16     │
          │  - User Service      │    │    (llama.cpp)     │    │  - pgvector          │
          │  - Template Service  │    │  - Model Manager   │    │  - Redis Cache       │
          │  - Asset Service     │    │  - Agent Pipeline  │    │  - S3/R2 Storage     │
          │  - Generation Service│    │  - Prompt Manager  │    │                      │
          └──────────────────────┘    └────────────────────┘    └──────────────────────┘
                      │
          ┌───────────▼──────────┐
          │   BACKGROUND JOBS    │
          │                      │
          │  - Celery Workers    │
          │  - Redis Queue       │
          │  - Scheduled Tasks   │
          └──────────────────────┘
                      │
          ┌───────────▼──────────┐
          │   OBSERVABILITY      │
          │                      │
          │  - Prometheus        │
          │  - Grafana          │
          │  - Loki (Logs)      │
          │  - Tempo (Traces)   │
          └──────────────────────┘
```

### 1.2 Design Principles

1. **Offline-First**: All AI computation happens locally (no external API calls)
2. **Self-Contained**: Single VPS deployment for small-scale, Kubernetes for large-scale
3. **Modular**: Each service can be deployed independently
4. **Observable**: Comprehensive logging, metrics, and tracing
5. **Secure**: Zero-trust architecture, defense in depth
6. **Scalable**: Horizontal scaling for all stateless services
7. **Resilient**: Graceful degradation, circuit breakers, retries

### 1.3 Technology Stack

**Frontend:**
- Next.js 14 (App Router)
- React 18 (Server Components + Client Components)
- TypeScript 5.3
- TailwindCSS 3.4 + Radix UI
- TanStack Query (data fetching)
- Zustand (state management)
- GrapesJS (visual editor)
- Socket.io Client (real-time updates)

**Backend:**
- FastAPI 0.109 (async Python)
- SQLAlchemy 2.0 (async ORM)
- Pydantic 2.5 (validation)
- Celery 5.3 (background jobs)
- Redis 7.2 (cache + queue)
- structlog (structured logging)

**AI/ML:**
- llama.cpp (local inference)
- Mixtral 8x7B or Llama 3 70B (primary model)
- Sentence Transformers (embeddings)
- ONNX Runtime (model optimization)

**Data:**
- PostgreSQL 16 + pgvector
- Redis 7.2
- MinIO / S3-compatible storage

**Infrastructure:**
- Docker + Docker Compose
- Caddy 2.8 (reverse proxy)
- Prometheus + Grafana (monitoring)
- Loki (log aggregation)
- Tempo (distributed tracing)

---

## 2. Service Layer Design

### 2.1 API Service (FastAPI)

**Responsibilities:**
- RESTful API endpoints
- WebSocket connections for real-time updates
- Authentication & authorization
- Request validation
- Business logic orchestration
- Rate limiting
- CORS handling

**Structure:**
```
services/api/
├── main.py                    # Application entry point
├── app/
│   ├── __init__.py
│   ├── core/
│   │   ├── config.py         # Settings management
│   │   ├── database.py       # DB connection pool
│   │   ├── security.py       # Auth utilities
│   │   ├── exceptions.py     # Custom exceptions
│   │   └── dependencies.py   # FastAPI dependencies
│   ├── models/               # SQLAlchemy models
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── generation.py
│   │   ├── template.py
│   │   ├── asset.py
│   │   └── analytics.py
│   ├── schemas/              # Pydantic schemas
│   │   ├── user.py
│   │   ├── project.py
│   │   ├── generation.py
│   │   └── api_responses.py
│   ├── api/
│   │   └── v1/
│   │       ├── router.py
│   │       └── endpoints/
│   │           ├── auth.py
│   │           ├── projects.py
│   │           ├── generations.py
│   │           ├── templates.py
│   │           ├── assets.py
│   │           ├── integrations.py
│   │           └── analytics.py
│   ├── services/            # Business logic
│   │   ├── auth_service.py
│   │   ├── project_service.py
│   │   ├── generation_service.py
│   │   ├── template_service.py
│   │   ├── asset_service.py
│   │   └── inference.py
│   ├── agents/              # AI agents
│   │   ├── strategist.py
│   │   ├── designer.py
│   │   ├── engineer.py
│   │   └── base_agent.py
│   ├── middleware/
│   │   ├── logging.py
│   │   ├── rate_limit.py
│   │   ├── auth.py
│   │   └── error_handler.py
│   └── utils/
│       ├── validation.py
│       ├── formatting.py
│       └── helpers.py
├── tests/
│   ├── conftest.py
│   ├── test_agents/
│   ├── test_api/
│   ├── test_services/
│   └── test_integration/
├── requirements.txt
├── requirements-dev.txt
└── Dockerfile
```

**Key Endpoints:**
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/users/me
PATCH  /api/v1/users/me

GET    /api/v1/projects
POST   /api/v1/projects
GET    /api/v1/projects/{id}
PATCH  /api/v1/projects/{id}
DELETE /api/v1/projects/{id}

POST   /api/v1/generations
GET    /api/v1/generations/{id}
GET    /api/v1/generations/{id}/status
GET    /api/v1/generations/{id}/preview
POST   /api/v1/generations/{id}/refine

GET    /api/v1/templates
GET    /api/v1/templates/{id}
POST   /api/v1/templates (admin)

POST   /api/v1/assets/upload
GET    /api/v1/assets/{id}
DELETE /api/v1/assets/{id}

WS     /api/v1/ws/generations/{id}
```

### 2.2 Inference Service (llama.cpp)

**Responsibilities:**
- Load and manage AI models
- Handle inference requests
- Stream responses
- Model quantization
- GPU acceleration (optional)
- Request queuing

**Structure:**
```
services/infer/
├── main.py                   # FastAPI server
├── model_manager.py          # Model loading/unloading
├── inference_engine.py       # llama.cpp wrapper
├── queue_manager.py          # Request queue
├── config.py                 # Model configs
├── utils/
│   ├── prompt_builder.py
│   ├── response_parser.py
│   └── streaming.py
├── models/                   # Model files (gitignored)
│   ├── mixtral-8x7b-q4.gguf
│   └── llama-3-70b-q4.gguf
├── requirements.txt
└── Dockerfile
```

**API:**
```python
POST /v1/chat/completions    # OpenAI-compatible
POST /v1/completions
POST /v1/embeddings
GET  /v1/models
GET  /health
```

**Configuration:**
```python
# Inference settings
MODEL_NAME = "mixtral-8x7b-instruct-q4_K_M.gguf"
CONTEXT_LENGTH = 8192
MAX_TOKENS = 4096
TEMPERATURE = 0.7
TOP_P = 0.95
GPU_LAYERS = 33  # Offload to GPU if available
THREADS = 4
BATCH_SIZE = 512
```

### 2.3 Worker Service (Celery)

**Responsibilities:**
- Process generation jobs asynchronously
- Handle long-running tasks
- Retry failed jobs
- Send notifications
- Scheduled tasks (backups, cleanup)

**Structure:**
```
services/worker/
├── main.py                   # Celery app
├── tasks/
│   ├── generation.py        # Main generation pipeline
│   ├── asset_processing.py  # Image optimization
│   ├── notifications.py     # Email/push notifications
│   ├── analytics.py         # Process analytics events
│   └── maintenance.py       # Cleanup, backups
├── config.py
├── requirements.txt
└── Dockerfile
```

**Tasks:**
```python
@celery_app.task(bind=True, max_retries=3)
def generate_website(self, generation_id: str):
    """
    Main generation pipeline:
    1. Fetch generation request
    2. Run Strategist agent
    3. Run Designer agent
    4. Run Engineer agent
    5. Save artifacts
    6. Update status
    7. Send notification
    """
    pass

@celery_app.task
def process_asset(asset_id: str):
    """Optimize images, generate thumbnails"""
    pass

@celery_app.task
def send_notification(user_id: str, event: str, data: dict):
    """Send email/push notification"""
    pass
```

### 2.4 Web Service (Next.js)

**Responsibilities:**
- Server-side rendering
- Static site generation
- User interface
- Visual editor
- Asset uploads
- Client-side routing

**Structure:**
```
apps/web/
├── src/
│   ├── app/                    # App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── (auth)/
│   │   │   ├── login/
│   │   │   └── register/
│   │   ├── dashboard/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   ├── projects/
│   │   │   ├── templates/
│   │   │   ├── assets/
│   │   │   ├── settings/
│   │   │   └── analytics/
│   │   └── editor/
│   │       └── [projectId]/
│   │           └── page.tsx
│   ├── components/
│   │   ├── ui/              # Radix UI components
│   │   ├── editor/          # Visual editor
│   │   │   ├── Canvas.tsx
│   │   │   ├── Toolbar.tsx
│   │   │   ├── Inspector.tsx
│   │   │   └── ComponentLibrary.tsx
│   │   ├── dashboard/
│   │   ├── generation/
│   │   └── shared/
│   ├── lib/
│   │   ├── api.ts           # API client
│   │   ├── auth.ts          # NextAuth config
│   │   ├── hooks.ts
│   │   └── utils.ts
│   ├── stores/              # Zustand stores
│   │   ├── editor.ts
│   │   ├── user.ts
│   │   └── projects.ts
│   └── types/
│       ├── api.ts
│       ├── editor.ts
│       └── next-auth.d.ts
├── public/
├── next.config.js
├── tailwind.config.ts
└── package.json
```

---

## 3. Database Schema

### 3.1 Complete Schema Definition

```sql
-- Enable extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";

-- =============================================================================
-- USERS & AUTHENTICATION
-- =============================================================================

CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    avatar_url TEXT,
    email_verified BOOLEAN DEFAULT FALSE,
    email_verified_at TIMESTAMPTZ,
    locale VARCHAR(10) DEFAULT 'en',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login_at TIMESTAMPTZ,
    is_active BOOLEAN DEFAULT TRUE,
    is_admin BOOLEAN DEFAULT FALSE,
    
    -- User preferences
    preferences JSONB DEFAULT '{
        "theme": "system",
        "notifications": {
            "email": true,
            "push": true,
            "generation_complete": true
        },
        "editor": {
            "autoSave": true,
            "showGuides": true
        }
    }'::jsonb,
    
    CONSTRAINT email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$')
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);
CREATE INDEX idx_users_is_active ON users(is_active) WHERE is_active = TRUE;

-- =============================================================================
-- WORKSPACES & TEAMS
-- =============================================================================

CREATE TABLE workspaces (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    owner_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    avatar_url TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TYPE workspace_role AS ENUM ('owner', 'admin', 'editor', 'viewer');

CREATE TABLE workspace_members (
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    role workspace_role NOT NULL DEFAULT 'viewer',
    invited_by UUID REFERENCES users(id),
    joined_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (workspace_id, user_id)
);

CREATE INDEX idx_workspace_members_user ON workspace_members(user_id);

-- =============================================================================
-- SUBSCRIPTIONS & BILLING
-- =============================================================================

CREATE TYPE plan_type AS ENUM ('free', 'freelancer', 'business', 'agency', 'enterprise');
CREATE TYPE subscription_status AS ENUM ('active', 'past_due', 'canceled', 'incomplete');

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    type plan_type UNIQUE NOT NULL,
    sparks_included INTEGER NOT NULL,
    sparks_overage_price_cents INTEGER, -- Price per additional Spark
    price_cents INTEGER NOT NULL,
    price_currency VARCHAR(3) DEFAULT 'USD',
    features JSONB DEFAULT '{}',
    limits JSONB DEFAULT '{
        "projects": null,
        "team_members": 1,
        "api_calls_per_day": null,
        "storage_gb": 10
    }',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE subscriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    plan_id UUID REFERENCES plans(id),
    status subscription_status NOT NULL DEFAULT 'active',
    sparks_balance INTEGER DEFAULT 0,
    current_period_start TIMESTAMPTZ,
    current_period_end TIMESTAMPTZ,
    cancel_at_period_end BOOLEAN DEFAULT FALSE,
    canceled_at TIMESTAMPTZ,
    payment_method JSONB, -- Store encrypted payment details
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_subscriptions_user ON subscriptions(user_id);
CREATE INDEX idx_subscriptions_workspace ON subscriptions(workspace_id);
CREATE INDEX idx_subscriptions_status ON subscriptions(status);

CREATE TABLE spark_transactions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    subscription_id UUID REFERENCES subscriptions(id),
    amount INTEGER NOT NULL, -- Negative for usage, positive for purchases
    balance_after INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL, -- 'generation', 'purchase', 'refund', 'adjustment'
    description TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- PROJECTS
-- =============================================================================

CREATE TYPE project_status AS ENUM ('draft', 'generating', 'generated', 'deployed', 'archived', 'failed');

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    created_by UUID REFERENCES users(id),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) NOT NULL,
    description TEXT,
    status project_status DEFAULT 'draft',
    
    -- Project metadata
    locale VARCHAR(10) DEFAULT 'en',
    industry VARCHAR(100),
    business_type VARCHAR(100), -- 'saas', 'ecommerce', 'agency', etc.
    target_audience JSONB,
    business_goals JSONB,
    
    -- Design preferences
    design_preferences JSONB DEFAULT '{
        "colorScheme": "auto",
        "typography": "modern",
        "spacing": "comfortable",
        "animations": "subtle"
    }',
    
    -- SEO
    seo_metadata JSONB DEFAULT '{}',
    
    -- Deployment
    deployment_url TEXT,
    deployment_platform VARCHAR(50), -- 'vercel', 'netlify', 'self-hosted'
    deployment_config JSONB,
    
    -- Statistics
    view_count INTEGER DEFAULT 0,
    last_deployed_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (workspace_id, slug)
);

CREATE INDEX idx_projects_workspace ON projects(workspace_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created_by ON projects(created_by);

-- =============================================================================
-- GENERATIONS
-- =============================================================================

CREATE TYPE generation_status AS ENUM ('queued', 'processing', 'completed', 'failed', 'canceled');
CREATE TYPE generation_step AS ENUM ('strategist', 'designer', 'engineer', 'optimization');

CREATE TABLE generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    status generation_status DEFAULT 'queued',
    current_step generation_step,
    
    -- Input
    brief TEXT NOT NULL,
    additional_context JSONB DEFAULT '{}',
    
    -- Agent outputs
    strategist_output JSONB,
    designer_output JSONB,
    engineer_output JSONB,
    
    -- Generated artifacts
    artifacts_path TEXT, -- Path to generated Next.js project
    preview_url TEXT,
    lighthouse_scores JSONB,
    
    -- Metrics
    generation_time_seconds REAL,
    tokens_used INTEGER,
    sparks_consumed INTEGER DEFAULT 1,
    
    -- Error handling
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    
    UNIQUE (project_id, version)
);

CREATE INDEX idx_generations_project ON generations(project_id);
CREATE INDEX idx_generations_status ON generations(status);
CREATE INDEX idx_generations_created_at ON generations(created_at DESC);

-- Track generation progress in real-time
CREATE TABLE generation_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    generation_id UUID REFERENCES generations(id) ON DELETE CASCADE,
    step generation_step NOT NULL,
    message TEXT NOT NULL,
    level VARCHAR(20) DEFAULT 'info', -- 'debug', 'info', 'warning', 'error'
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_generation_logs_generation ON generation_logs(generation_id, created_at);

-- =============================================================================
-- TEMPLATES
-- =============================================================================

CREATE TYPE template_category AS ENUM (
    'landing_page', 'portfolio', 'ecommerce', 'blog', 'saas',
    'agency', 'restaurant', 'healthcare', 'education', 'finance',
    'real_estate', 'fitness', 'legal', 'nonprofit', 'other'
);

CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    category template_category NOT NULL,
    industry VARCHAR(100),
    tags TEXT[],
    
    -- Visual
    preview_image TEXT NOT NULL,
    preview_images JSONB, -- {'desktop': '...', 'tablet': '...', 'mobile': '...'}
    thumbnail TEXT,
    
    -- Template data
    strategist_template JSONB NOT NULL, -- Pre-filled strategy
    designer_template JSONB NOT NULL,   -- Design tokens
    code_template JSONB NOT NULL,       -- Component structure
    
    -- Metadata
    is_featured BOOLEAN DEFAULT FALSE,
    is_premium BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    rating REAL DEFAULT 0.0,
    
    -- AI generation
    ai_generated BOOLEAN DEFAULT FALSE,
    generated_from UUID REFERENCES projects(id), -- If derived from user project
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_featured ON templates(is_featured) WHERE is_featured = TRUE;
CREATE INDEX idx_templates_usage ON templates(usage_count DESC);

-- =============================================================================
-- ASSETS
-- =============================================================================

CREATE TYPE asset_type AS ENUM ('image', 'video', 'font', 'icon', 'document');

CREATE TABLE assets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    uploaded_by UUID REFERENCES users(id),
    
    -- File info
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255),
    file_size INTEGER NOT NULL, -- bytes
    mime_type VARCHAR(100) NOT NULL,
    type asset_type NOT NULL,
    
    -- Storage
    storage_path TEXT NOT NULL,
    storage_provider VARCHAR(50) DEFAULT 'local', -- 'local', 's3', 'r2'
    cdn_url TEXT,
    
    -- Image-specific
    width INTEGER,
    height INTEGER,
    format VARCHAR(10),
    
    -- Metadata
    alt_text TEXT,
    tags TEXT[],
    metadata JSONB DEFAULT '{}',
    
    -- Optimization
    optimized BOOLEAN DEFAULT FALSE,
    optimization_results JSONB,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    CONSTRAINT positive_file_size CHECK (file_size > 0)
);

CREATE INDEX idx_assets_workspace ON assets(workspace_id);
CREATE INDEX idx_assets_project ON assets(project_id);
CREATE INDEX idx_assets_type ON assets(type);

-- =============================================================================
-- INTEGRATIONS
-- =============================================================================

CREATE TYPE integration_provider AS ENUM (
    'google_analytics', 'google_search_console', 'mailchimp', 'convertkit',
    'stripe', 'paypal', 'hubspot', 'salesforce', 'zapier', 'slack',
    'calendly', 'typeform', 'unsplash', 'pexels'
);

CREATE TABLE integrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workspace_id UUID REFERENCES workspaces(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    provider integration_provider NOT NULL,
    
    -- Credentials (encrypted)
    api_key_encrypted TEXT,
    api_secret_encrypted TEXT,
    access_token_encrypted TEXT,
    refresh_token_encrypted TEXT,
    token_expires_at TIMESTAMPTZ,
    
    -- Configuration
    config JSONB DEFAULT '{}',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    last_sync_at TIMESTAMPTZ,
    sync_status VARCHAR(50),
    error_message TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE (workspace_id, project_id, provider)
);

CREATE INDEX idx_integrations_workspace ON integrations(workspace_id);
CREATE INDEX idx_integrations_project ON integrations(project_id);

-- =============================================================================
-- ANALYTICS
-- =============================================================================

CREATE TYPE analytics_event_type AS ENUM (
    'pageview', 'button_click', 'form_submission', 'link_click',
    'scroll_depth', 'time_on_page', 'conversion', 'custom'
);

CREATE TABLE analytics_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    
    -- Event data
    event_type analytics_event_type NOT NULL,
    event_name VARCHAR(255),
    event_data JSONB DEFAULT '{}',
    
    -- Session
    session_id UUID,
    visitor_id UUID,
    
    -- Page context
    page_url TEXT NOT NULL,
    page_title VARCHAR(500),
    referrer TEXT,
    
    -- Device/Browser
    user_agent TEXT,
    device_type VARCHAR(50), -- 'desktop', 'tablet', 'mobile'
    browser VARCHAR(100),
    os VARCHAR(100),
    
    -- Location
    ip_address INET,
    country VARCHAR(2),
    city VARCHAR(100),
    
    -- Metadata
    metadata JSONB DEFAULT '{}',
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Partitioning by month for performance
CREATE INDEX idx_analytics_project_time ON analytics_events(project_id, created_at DESC);
CREATE INDEX idx_analytics_event_type ON analytics_events(event_type);
CREATE INDEX idx_analytics_session ON analytics_events(session_id);

-- =============================================================================
-- COMMENTS & COLLABORATION
-- =============================================================================

CREATE TABLE comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),
    parent_id UUID REFERENCES comments(id) ON DELETE CASCADE, -- For threading
    
    -- Comment target
    element_selector TEXT, -- CSS selector for the commented element
    page_path VARCHAR(500),
    
    -- Content
    content TEXT NOT NULL,
    mentions UUID[], -- Array of user IDs mentioned
    
    -- Status
    resolved BOOLEAN DEFAULT FALSE,
    resolved_by UUID REFERENCES users(id),
    resolved_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_comments_project ON comments(project_id);
CREATE INDEX idx_comments_user ON comments(user_id);
CREATE INDEX idx_comments_parent ON comments(parent_id);

-- =============================================================================
-- EMBEDDINGS FOR SEMANTIC SEARCH
-- =============================================================================

CREATE TABLE template_embeddings (
    template_id UUID PRIMARY KEY REFERENCES templates(id) ON DELETE CASCADE,
    embedding vector(768), -- Sentence-BERT dimension
    text_content TEXT, -- Combined name + description + tags
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_template_embeddings_vector ON template_embeddings 
USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================

CREATE TYPE audit_action AS ENUM (
    'create', 'update', 'delete', 'login', 'logout',
    'invite', 'remove', 'deploy', 'export', 'import'
);

CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    workspace_id UUID REFERENCES workspaces(id),
    action audit_action NOT NULL,
    resource_type VARCHAR(50) NOT NULL, -- 'project', 'user', 'template', etc.
    resource_id UUID,
    details JSONB DEFAULT '{}',
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_logs_user ON audit_logs(user_id, created_at DESC);
CREATE INDEX idx_audit_logs_workspace ON audit_logs(workspace_id, created_at DESC);
CREATE INDEX idx_audit_logs_resource ON audit_logs(resource_type, resource_id);

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workspaces_updated_at BEFORE UPDATE ON workspaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_templates_updated_at BEFORE UPDATE ON templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subscriptions_updated_at BEFORE UPDATE ON subscriptions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- INITIAL DATA
-- =============================================================================

-- Insert default plans
INSERT INTO plans (name, type, sparks_included, price_cents, features, limits) VALUES
('Free', 'free', 3, 0, 
 '{"templates": "basic", "support": "community"}',
 '{"projects": 3, "team_members": 1, "storage_gb": 1}'
),
('Freelancer', 'freelancer', 25, 1900, 
 '{"templates": "all", "support": "email", "custom_domain": true}',
 '{"projects": 10, "team_members": 1, "storage_gb": 10}'
),
('Business', 'business', 100, 4900, 
 '{"templates": "all", "support": "priority", "custom_domain": true, "white_label": false, "analytics": true}',
 '{"projects": null, "team_members": 5, "storage_gb": 50}'
),
('Agency', 'agency', 500, 9900, 
 '{"templates": "all", "support": "dedicated", "custom_domain": true, "white_label": true, "analytics": true, "api_access": true}',
 '{"projects": null, "team_members": 20, "storage_gb": 200}'
);
```

### 3.2 Migrations Strategy

Use Alembic for version control:

```python
# services/api/alembic/versions/001_initial_schema.py
def upgrade():
    # Create tables
    pass

def downgrade():
    # Drop tables
    pass
```

---

## 4. AI Pipeline Architecture

### 4.1 Three-Agent System

```
┌─────────────────────────────────────────────────────────────┐
│                     GENERATION PIPELINE                      │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  Input: Brief   │
                    │  + Context      │
                    └────────┬────────┘
                             │
                ┌────────────┴────────────┐
                │   STRATEGIST AGENT      │
                │   (Business Analysis)   │
                └────────────┬────────────┘
                             │
                    Output: {
                      business_goal,
                      target_audience,
                      value_proposition,
                      pages[],
                      conversion_funnel
                    }
                             │
                ┌────────────┴────────────┐
                │   DESIGNER AGENT        │
                │   (UI/UX Generation)    │
                └────────────┬────────────┘
                             │
                    Output: {
                      design_system,
                      components[],
                      layouts[],
                      animations
                    }
                             │
                ┌────────────┴────────────┐
                │   ENGINEER AGENT        │
                │   (Code Generation)     │
                └────────────┬────────────┘
                             │
                    Output: {
                      next_js_project,
                      components/,
                      pages/,
                      api/
                    }
                             │
                    ┌────────▼────────┐
                    │  Optimization   │
                    │  - Lighthouse   │
                    │  - Bundle size  │
                    └─────────────────┘
```

### 4.2 Prompt Engineering

**Strategist System Prompt:**
```python
STRATEGIST_SYSTEM_PROMPT = """You are an expert business strategist and conversion optimization specialist.

Your task is to analyze a business brief and create a comprehensive website strategy that maximizes the business's primary goal.

ANALYSIS FRAMEWORK:
1. TRUE GOAL DETECTION: Identify what the business ACTUALLY needs (sales, leads, bookings, awareness)
2. AUDIENCE PSYCHOLOGY: Understand pain points, motivations, objections
3. VALUE PROPOSITION: Craft compelling, differentiated messaging
4. CONVERSION OPTIMIZATION: Design funnel to maximize primary KPI
5. TRUST SIGNALS: Identify required proof points for this industry/audience

OUTPUT REQUIREMENTS:
- Respond ONLY with valid JSON matching the BusinessStrategy schema
- Include 3-7 pages optimized for conversion
- Specify primary and secondary CTAs for each page
- Include at least 5 trust signals specific to the industry
- Design conversion funnel with clear steps

CULTURAL CONSIDERATIONS:
- Adapt trust signals to the target locale (e.g., "As seen on TV" vs "Government certified")
- Consider local payment preferences
- Include region-specific legal requirements
- Adjust tone for cultural norms

EXAMPLES OF GOOD STRATEGY:
{few_shot_examples}
"""
```

**Designer System Prompt:**
```python
DESIGNER_SYSTEM_PROMPT = """You are a world-class UI/UX designer specializing in conversion-optimized web design.

Given a business strategy, create a complete design system and component specifications.

DESIGN PRINCIPLES:
1. CLARITY: Every element serves a purpose
2. HIERARCHY: Guide eye to most important elements
3. CONSISTENCY: Design system with reusable components
4. ACCESSIBILITY: WCAG 2.1 AA compliance minimum
5. PERFORMANCE: Optimize for fast loading

OUTPUT REQUIREMENTS:
- Design tokens (colors, typography, spacing, shadows)
- Component specifications with props and variants
- Layout grids and breakpoints
- Animation/interaction patterns
- Responsive behavior rules

CULTURAL ADAPTATION:
- {locale} typography preferences
- Color psychology for {culture}
- Layout patterns (LTR/RTL)
- Imagery style preferences

TECHNOLOGY CONSTRAINTS:
- TailwindCSS utility classes
- Radix UI primitives
- Framer Motion animations
- Next.js Image optimization

OUTPUT FORMAT: JSON matching DesignSystem schema
"""
```

**Engineer System Prompt:**
```python
ENGINEER_SYSTEM_PROMPT = """You are a senior full-stack engineer specializing in Next.js 14 and modern React patterns.

Given strategy and design specifications, generate production-ready Next.js code.

CODE QUALITY STANDARDS:
1. TypeScript strict mode
2. Server Components by default, Client Components only when needed
3. Proper error boundaries and loading states
4. SEO optimization (metadata, structured data)
5. Performance optimization (code splitting, lazy loading)
6. Accessibility (semantic HTML, ARIA labels)

ARCHITECTURE:
- App Router (not Pages Router)
- Server-side rendering where possible
- API routes for forms/actions
- Proper data fetching patterns
- Environment variable usage

OUTPUT REQUIREMENTS:
Generate complete file tree with:
- app/ (routes and layouts)
- components/ (reusable components)
- lib/ (utilities)
- public/ (static assets)
- types/ (TypeScript definitions)

Each file should be production-ready with:
- Proper imports
- Type safety
- Error handling
- Comments for complex logic
- Responsive design

OUTPUT FORMAT: JSON with file paths and contents
"""
```

### 4.3 Inference Service Implementation

**Key Features:**
- OpenAI-compatible API
- Streaming responses
- Request queuing
- GPU acceleration (optional)
- Model hot-swapping
- Prompt caching

**Performance Targets:**
- First token: < 500ms
- Throughput: 20-30 tokens/second
- Concurrent requests: 4-8 (depending on model size)
- Memory usage: 8-16GB RAM for Q4 quantized 7B-13B models

---

## 5. Frontend Architecture

### 5.1 Component Library Structure

```
src/components/
├── ui/                      # Base UI components (Radix + custom)
│   ├── button.tsx
│   ├── input.tsx
│   ├── dialog.tsx
│   ├── dropdown-menu.tsx
│   └── ...
├── editor/                  # Visual editor components
│   ├── Canvas.tsx           # Main editing surface
│   ├── Toolbar.tsx          # Top toolbar
│   ├── LeftPanel.tsx        # Component library
│   ├── RightPanel.tsx       # Properties inspector
│   ├── LayersPanel.tsx      # Element tree
│   ├── StyleEditor.tsx      # Visual style editing
│   └── ComponentLibrary.tsx # Drag-drop components
├── generation/              # AI generation UI
│   ├── GenerationWizard.tsx
│   ├── ProgressTracker.tsx
│   ├── StrategyPreview.tsx
│   └── RefineDialog.tsx
├── dashboard/               # Dashboard components
│   ├── ProjectCard.tsx
│   ├── ProjectGrid.tsx
│   ├── UsageMetrics.tsx
│   └── ActivityFeed.tsx
└── shared/                  # Shared utilities
    ├── Avatar.tsx
    ├── EmptyState.tsx
    ├── ErrorBoundary.tsx
    └── LoadingSpinner.tsx
```

### 5.2 State Management

**Zustand Stores:**

```typescript
// stores/editor.ts
interface EditorStore {
  // Document state
  elements: Element[];
  selectedElementId: string | null;
  history: HistoryState[];
  historyIndex: number;
  
  // UI state
  mode: 'select' | 'insert' | 'text';
  showGrid: boolean;
  zoom: number;
  
  // Actions
  selectElement: (id: string) => void;
  updateElement: (id: string, props: Partial<Element>) => void;
  deleteElement: (id: string) => void;
  undo: () => void;
  redo: () => void;
  insertComponent: (component: Component, position: Position) => void;
}

// stores/project.ts
interface ProjectStore {
  currentProject: Project | null;
  projects: Project[];
  isLoading: boolean;
  error: string | null;
  
  fetchProjects: () => Promise<void>;
  createProject: (data: CreateProjectInput) => Promise<Project>;
  updateProject: (id: string, data: Partial<Project>) => Promise<void>;
  deleteProject: (id: string) => Promise<void>;
}
```

### 5.3 Real-Time Updates

**WebSocket Connection:**

```typescript
// lib/websocket.ts
export class GenerationSocket {
  private ws: WebSocket | null = null;
  
  connect(generationId: string) {
    this.ws = new WebSocket(
      `${WS_URL}/api/v1/ws/generations/${generationId}`
    );
    
    this.ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      switch (data.type) {
        case 'progress':
          updateProgress(data.step, data.progress);
          break;
        case 'log':
          appendLog(data.message);
          break;
        case 'complete':
          handleComplete(data.result);
          break;
        case 'error':
          handleError(data.error);
          break;
      }
    };
  }
}
```

---

## 6. API Design

### 6.1 RESTful Endpoints

**Authentication:**
```
POST   /api/v1/auth/register
POST   /api/v1/auth/login  
POST   /api/v1/auth/refresh
POST   /api/v1/auth/logout
GET    /api/v1/auth/me
```

**Projects:**
```
GET    /api/v1/projects              # List with pagination
POST   /api/v1/projects              # Create new
GET    /api/v1/projects/{id}         # Get single
PATCH  /api/v1/projects/{id}         # Update
DELETE /api/v1/projects/{id}         # Delete
POST   /api/v1/projects/{id}/duplicate
POST   /api/v1/projects/{id}/export
```

**Generations:**
```
POST   /api/v1/generations           # Start generation
GET    /api/v1/generations/{id}      # Get result
GET    /api/v1/generations/{id}/status
GET    /api/v1/generations/{id}/logs
POST   /api/v1/generations/{id}/refine
DELETE /api/v1/generations/{id}      # Cancel
```

**Templates:**
```
GET    /api/v1/templates             # List with filters
GET    /api/v1/templates/{id}
POST   /api/v1/templates             # Admin only
GET    /api/v1/templates/search?q=saas&category=landing_page
```

**Assets:**
```
POST   /api/v1/assets/upload         # Multipart form
GET    /api/v1/assets                # List user assets
GET    /api/v1/assets/{id}
DELETE /api/v1/assets/{id}
POST   /api/v1/assets/optimize       # Batch optimization
```

### 6.2 Response Format

**Standard Response:**
```json
{
  "success": true,
  "data": { /* ... */ },
  "meta": {
    "timestamp": "2026-01-03T10:00:00Z",
    "request_id": "uuid"
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  },
  "meta": {
    "timestamp": "2026-01-03T10:00:00Z",
    "request_id": "uuid"
  }
}
```

---

## 7. Security Architecture

### 7.1 Authentication Flow

```
User Login
    ↓
Validate credentials (bcrypt)
    ↓
Generate JWT (access + refresh tokens)
    ↓
Access Token: 15 minutes expiry
Refresh Token: 7 days expiry
    ↓
Store refresh token in httpOnly cookie
Return access token in response body
```

### 7.2 Authorization

**Role-Based Access Control (RBAC):**

```python
class Permission(Enum):
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    PROJECT_DELETE = "project:delete"
    ADMIN_ALL = "admin:*"

@require_permission(Permission.PROJECT_WRITE)
async def update_project(project_id: str, user: User):
    # Check ownership or workspace membership
    pass
```

### 7.3 Input Validation

**Pydantic Schemas with strict validation:**

```python
class CreateProjectRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = Field(None, max_length=5000)
    locale: str = Field("en", regex=r"^[a-z]{2}(-[A-Z]{2})?$")
    industry: Optional[str]
    
    @validator('name')
    def validate_name(cls, v):
        # Prevent XSS
        return bleach.clean(v)
```

### 7.4 Rate Limiting

**Redis-based sliding window:**

```python
@rate_limit(requests=100, window=60)  # 100 req/min
async def api_endpoint():
    pass

# Different limits for different endpoints
@rate_limit(requests=10, window=3600)  # 10 generations/hour
async def create_generation():
    pass
```

---

## 8. Scalability & Performance

### 8.1 Caching Strategy

**Multi-Layer Caching:**

```
Browser Cache
    ↓
CDN Cache (static assets)
    ↓
Redis Cache (API responses)
    ↓
Database Query Cache
    ↓
PostgreSQL
```

**Cache Implementation:**

```python
@cache(ttl=300)  # 5 minutes
async def get_templates(category: str):
    return await db.query(templates).filter_by(category=category)

# Invalidation
await cache.delete(f"templates:{category}")
```

### 8.2 Database Optimization

**Indexes:**
- All foreign keys
- Frequently queried fields
- Composite indexes for common queries

**Connection Pooling:**
```python
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)
```

### 8.3 Horizontal Scaling

**Stateless Services:**
- API servers: Scale to N instances
- Worker nodes: Scale based on queue depth
- Inference servers: Dedicated GPU instances

**Load Balancing:**
- Caddy with round-robin
- Sticky sessions for WebSocket
- Health checks every 30s

---

## 9. Deployment Architecture

### 9.1 Production Docker Compose

**Optimized for single VPS:**

```yaml
services:
  caddy:
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
  
  web:
    deploy:
      replicas: 2  # For zero-downtime deploys
      resources:
        limits:
          cpus: '1'
          memory: 1G
  
  api:
    deploy:
      replicas: 2
      resources:
        limits:
          cpus: '2'
          memory: 2G
  
  infer:
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G  # Main memory consumer
```

### 9.2 CI/CD Pipeline

**GitHub Actions Workflow:**

```yaml
name: Deploy Production

on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          npm run test
          cd services/api && pytest
  
  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker images
        run: docker compose build
      - name: Push to registry
        run: docker compose push
  
  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to production
        run: |
          ssh ${{ secrets.PROD_HOST }} "cd /opt/sovrn && docker compose pull && docker compose up -d"
```

---

## 10. Monitoring & Observability

### 10.1 Metrics (Prometheus)

**Key Metrics:**

```python
# Request metrics
http_requests_total = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
http_request_duration_seconds = Histogram('http_request_duration_seconds', 'HTTP request duration')

# Generation metrics
generation_duration_seconds = Histogram('generation_duration_seconds', 'Generation time', ['agent'])
generation_tokens_total = Counter('generation_tokens_total', 'Total tokens generated')
generation_failures_total = Counter('generation_failures_total', 'Failed generations', ['reason'])

# System metrics
inference_queue_length = Gauge('inference_queue_length', 'Inference queue depth')
database_connections = Gauge('database_connections', 'Active DB connections')
```

### 10.2 Logging (Loki)

**Structured Logging:**

```python
logger.info(
    "generation_started",
    generation_id=gen_id,
    user_id=user_id,
    project_id=project_id,
    brief_length=len(brief)
)
```

### 10.3 Grafana Dashboards

**Key Dashboards:**
1. **System Health**: CPU, Memory, Disk, Network
2. **Application Performance**: Request rate, latency, errors
3. **Business Metrics**: Generations/hour, success rate, Spark consumption
4. **User Analytics**: Active users, retention, feature usage

---

## Summary

This architecture provides:

✅ **Scalability**: Horizontal scaling for all stateless services  
✅ **Reliability**: Graceful degradation, retries, circuit breakers  
✅ **Security**: Defense in depth, zero-trust principles  
✅ **Performance**: Multi-layer caching, optimized queries  
✅ **Observability**: Comprehensive metrics, logs, traces  
✅ **Maintainability**: Clean architecture, typed interfaces  

**Production Readiness Checklist:**
- [x] High availability architecture
- [x] Security hardening
- [x] Performance optimization
- [x] Monitoring & alerting
- [x] Backup & disaster recovery
- [x] CI/CD automation
- [ ] Load testing (to be conducted)
- [ ] Security audit (to be conducted)
- [ ] Penetration testing (to be conducted)