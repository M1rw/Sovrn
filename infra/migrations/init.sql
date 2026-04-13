-- =============================================================================
-- SOVRN Database Initialization
-- =============================================================================
-- PostgreSQL 16 + pgvector
-- =============================================================================

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
    is_admin BOOLEAN DEFAULT FALSE
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_created_at ON users(created_at);

-- =============================================================================
-- SPARKS (MONETIZATION)
-- =============================================================================

CREATE TYPE plan_type AS ENUM ('free', 'freelancer', 'business', 'agency');

CREATE TABLE plans (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(50) UNIQUE NOT NULL,
    type plan_type UNIQUE NOT NULL,
    sparks_included INTEGER NOT NULL,
    price_cents INTEGER NOT NULL,
    features JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default plans
INSERT INTO plans (name, type, sparks_included, price_cents, features) VALUES
    ('Free', 'free', 3, 0, '{"max_projects": 1, "export": false}'),
    ('Freelancer', 'freelancer', 30, 500, '{"max_projects": 5, "export": true}'),
    ('Business', 'business', 100, 1500, '{"max_projects": 20, "export": true, "priority_support": true}'),
    ('Agency', 'agency', -1, 5000, '{"max_projects": -1, "export": true, "priority_support": true, "white_label": true}');

CREATE TABLE accounts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id UUID NOT NULL REFERENCES plans(id),
    sparks_balance INTEGER DEFAULT 0,
    sparks_used_total INTEGER DEFAULT 0,
    plan_started_at TIMESTAMPTZ DEFAULT NOW(),
    plan_expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id)
);

CREATE INDEX idx_accounts_user ON accounts(user_id);

CREATE TYPE ledger_type AS ENUM ('credit', 'debit', 'refund', 'bonus', 'expired');

CREATE TABLE spark_ledger (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    type ledger_type NOT NULL,
    amount INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    description TEXT,
    reference_id UUID,
    reference_type VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

CREATE INDEX idx_spark_ledger_account ON spark_ledger(account_id);
CREATE INDEX idx_spark_ledger_created ON spark_ledger(created_at);

-- =============================================================================
-- INVOICES & PAYMENTS
-- =============================================================================

CREATE TYPE invoice_status AS ENUM ('pending', 'paid', 'cancelled', 'refunded');

CREATE TABLE invoices (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id UUID NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    status invoice_status DEFAULT 'pending',
    plan_id UUID REFERENCES plans(id),
    sparks_amount INTEGER NOT NULL,
    payment_method VARCHAR(50),
    payment_reference TEXT,
    notes TEXT,
    due_date TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_account ON invoices(account_id);
CREATE INDEX idx_invoices_status ON invoices(status);

-- =============================================================================
-- PROJECTS
-- =============================================================================

CREATE TYPE project_status AS ENUM ('draft', 'generating', 'ready', 'deployed', 'archived');

CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255),
    description TEXT,
    status project_status DEFAULT 'draft',
    locale VARCHAR(10) DEFAULT 'en',
    industry VARCHAR(100),
    business_type VARCHAR(100),
    target_audience JSONB DEFAULT '{}',
    goals JSONB DEFAULT '[]',
    brief TEXT,
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    generated_at TIMESTAMPTZ,
    deployed_at TIMESTAMPTZ,
    deploy_url TEXT
);

CREATE INDEX idx_projects_user ON projects(user_id);
CREATE INDEX idx_projects_status ON projects(status);
CREATE INDEX idx_projects_created ON projects(created_at);

-- =============================================================================
-- GENERATION JOBS
-- =============================================================================

CREATE TYPE job_status AS ENUM ('queued', 'processing', 'completed', 'failed', 'cancelled');
CREATE TYPE job_type AS ENUM ('strategy', 'design', 'engineer', 'full');

CREATE TABLE jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    type job_type NOT NULL,
    status job_status DEFAULT 'queued',
    spark_cost INTEGER DEFAULT 1,
    priority INTEGER DEFAULT 0,
    input JSONB DEFAULT '{}',
    output JSONB DEFAULT '{}',
    error TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    worker_id VARCHAR(100)
);

CREATE INDEX idx_jobs_project ON jobs(project_id);
CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_queue ON jobs(status, priority DESC, created_at ASC) WHERE status = 'queued';

-- =============================================================================
-- GENERATED SITES
-- =============================================================================

CREATE TABLE site_generations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    job_id UUID REFERENCES jobs(id),
    version INTEGER DEFAULT 1,
    strategy_output JSONB DEFAULT '{}',
    design_output JSONB DEFAULT '{}',
    code_output JSONB DEFAULT '{}',
    files JSONB DEFAULT '[]',
    lighthouse_scores JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_site_generations_project ON site_generations(project_id);
CREATE UNIQUE INDEX uq_site_generations_job_id ON site_generations(job_id) WHERE job_id IS NOT NULL;

-- =============================================================================
-- CONVERSATION PERSISTENCE
-- =============================================================================
-- Authoritative state is stored in conversation_threads/conversation_state_snapshots.
-- Summaries are non-authoritative and stored separately in conversation_summaries.

CREATE TABLE conversation_threads (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'active',
    state_version BIGINT NOT NULL DEFAULT 1,
    authoritative_state JSONB NOT NULL DEFAULT '{}',
    locked_constraints JSONB NOT NULL DEFAULT '[]',
    last_turn_index INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_conversation_threads_user ON conversation_threads(user_id);
CREATE INDEX idx_conversation_threads_project ON conversation_threads(project_id);
CREATE INDEX idx_conversation_threads_created ON conversation_threads(created_at);

CREATE TABLE conversation_turns (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    turn_index INTEGER NOT NULL,
    user_message TEXT NOT NULL,
    model_raw_output JSONB,
    server_response JSONB NOT NULL DEFAULT '{}',
    parse_status VARCHAR(30) NOT NULL DEFAULT 'not_attempted',
    provider VARCHAR(50),
    model VARCHAR(100),
    latency_ms INTEGER,
    tokens_used INTEGER,
    idempotency_key VARCHAR(128) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_conversation_turns_thread_turn UNIQUE(thread_id, turn_index),
    CONSTRAINT uq_conversation_turns_thread_idempotency UNIQUE(thread_id, idempotency_key)
);

CREATE INDEX idx_conversation_turns_thread ON conversation_turns(thread_id);
CREATE INDEX idx_conversation_turns_created ON conversation_turns(created_at);
CREATE INDEX idx_conversation_turns_parse_status ON conversation_turns(parse_status);

CREATE TABLE conversation_state_snapshots (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    turn_id UUID REFERENCES conversation_turns(id) ON DELETE SET NULL,
    state_version BIGINT NOT NULL,
    authoritative_state JSONB NOT NULL DEFAULT '{}',
    locked_constraints JSONB NOT NULL DEFAULT '[]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT uq_conversation_state_snapshots_thread_version UNIQUE(thread_id, state_version)
);

CREATE INDEX idx_conversation_state_snapshots_thread ON conversation_state_snapshots(thread_id);
CREATE INDEX idx_conversation_state_snapshots_turn ON conversation_state_snapshots(turn_id);

CREATE TABLE conversation_summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    thread_id UUID NOT NULL REFERENCES conversation_threads(id) ON DELETE CASCADE,
    from_turn_index INTEGER NOT NULL,
    to_turn_index INTEGER NOT NULL,
    summary_json JSONB NOT NULL DEFAULT '{}',
    summarizer_version VARCHAR(50),
    quality_score NUMERIC(5,4),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT chk_conversation_summary_turn_range CHECK (to_turn_index >= from_turn_index)
);

CREATE INDEX idx_conversation_summaries_thread ON conversation_summaries(thread_id);
CREATE INDEX idx_conversation_summaries_to_turn ON conversation_summaries(thread_id, to_turn_index);

-- =============================================================================
-- CULTURAL ADAPTATION RULES
-- =============================================================================

CREATE TABLE locale_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    locale VARCHAR(10) NOT NULL,
    country_code VARCHAR(2),
    region VARCHAR(50),
    rules JSONB NOT NULL DEFAULT '{}',
    payment_methods JSONB DEFAULT '[]',
    legal_requirements JSONB DEFAULT '[]',
    trust_signals JSONB DEFAULT '[]',
    ui_patterns JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(locale, country_code)
);

CREATE INDEX idx_locale_rules_locale ON locale_rules(locale);

-- Insert common locale rules
INSERT INTO locale_rules (locale, country_code, region, payment_methods, legal_requirements, ui_patterns) VALUES
    ('en', 'US', 'North America', '["stripe", "paypal", "apple_pay", "google_pay"]', '["ccpa", "ada"]', '{"direction": "ltr", "mobile_first": true}'),
    ('en', 'GB', 'Europe', '["stripe", "paypal", "apple_pay"]', '["gdpr", "cookie_consent"]', '{"direction": "ltr", "mobile_first": true}'),
    ('de', 'DE', 'Europe', '["stripe", "paypal", "klarna", "giropay"]', '["gdpr", "impressum", "cookie_consent"]', '{"direction": "ltr", "formal_tone": true}'),
    ('fr', 'FR', 'Europe', '["stripe", "paypal", "carte_bancaire"]', '["gdpr", "mentions_legales", "cookie_consent"]', '{"direction": "ltr"}'),
    ('ar', 'SA', 'Middle East', '["mada", "stc_pay", "apple_pay"]', '["local_entity"]', '{"direction": "rtl", "mobile_first": true}'),
    ('ar', 'EG', 'Middle East', '["fawry", "vodafone_cash", "instapay"]', '[]', '{"direction": "rtl", "mobile_first": true}'),
    ('hi', 'IN', 'South Asia', '["upi", "razorpay", "paytm", "phonepe"]', '["gst_compliance"]', '{"direction": "ltr", "mobile_first": true}'),
    ('pt', 'BR', 'South America', '["pix", "boleto", "mercadopago"]', '["lgpd"]', '{"direction": "ltr", "mobile_first": true}'),
    ('sw', 'KE', 'Africa', '["mpesa", "airtel_money"]', '[]', '{"direction": "ltr", "mobile_first": true, "low_bandwidth": true}'),
    ('ja', 'JP', 'East Asia', '["stripe", "paypay", "rakuten_pay", "konbini"]', '["act_protection_personal_info"]', '{"direction": "ltr", "vertical_text_support": true}'),
    ('zh', 'CN', 'East Asia', '["alipay", "wechat_pay", "unionpay"]', '["icp_license", "data_localization"]', '{"direction": "ltr"}');

-- =============================================================================
-- EMBEDDINGS (for RAG)
-- =============================================================================

CREATE TABLE embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    content_type VARCHAR(50) NOT NULL,
    content_id UUID NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    content TEXT NOT NULL,
    embedding vector(384),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_embeddings_type ON embeddings(content_type);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =============================================================================
-- TEMPLATES
-- =============================================================================

CREATE TABLE templates (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(100),
    industry VARCHAR(100),
    preview_url TEXT,
    thumbnail_url TEXT,
    config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    is_premium BOOLEAN DEFAULT FALSE,
    usage_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_templates_category ON templates(category);
CREATE INDEX idx_templates_industry ON templates(industry);

-- =============================================================================
-- AUDIT LOG
-- =============================================================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_created ON audit_log(created_at);

-- =============================================================================
-- FUNCTIONS & TRIGGERS
-- =============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER accounts_updated_at BEFORE UPDATE ON accounts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER invoices_updated_at BEFORE UPDATE ON invoices
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER locale_rules_updated_at BEFORE UPDATE ON locale_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER conversation_threads_updated_at BEFORE UPDATE ON conversation_threads
    FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Spark balance update function
CREATE OR REPLACE FUNCTION update_spark_balance()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.type IN ('credit', 'bonus', 'refund') THEN
        UPDATE accounts SET sparks_balance = sparks_balance + NEW.amount WHERE id = NEW.account_id;
    ELSIF NEW.type = 'debit' THEN
        UPDATE accounts SET 
            sparks_balance = sparks_balance - NEW.amount,
            sparks_used_total = sparks_used_total + NEW.amount
        WHERE id = NEW.account_id;
    ELSIF NEW.type = 'expired' THEN
        UPDATE accounts SET sparks_balance = sparks_balance - NEW.amount WHERE id = NEW.account_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER spark_ledger_balance AFTER INSERT ON spark_ledger
    FOR EACH ROW EXECUTE FUNCTION update_spark_balance();

-- Generate invoice number
CREATE OR REPLACE FUNCTION generate_invoice_number()
RETURNS TRIGGER AS $$
BEGIN
    NEW.invoice_number = 'INV-' || TO_CHAR(NOW(), 'YYYYMM') || '-' || LPAD(nextval('invoice_seq')::TEXT, 6, '0');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE SEQUENCE invoice_seq START 1;

CREATE TRIGGER invoices_number BEFORE INSERT ON invoices
    FOR EACH ROW EXECUTE FUNCTION generate_invoice_number();

-- =============================================================================
-- DEFAULT ADMIN USER (change password immediately!)
-- =============================================================================

INSERT INTO users (email, password_hash, name, email_verified, is_admin)
VALUES (
    'admin@sovrn.local',
    -- Password: changeme123 (bcrypt hash)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G5PGgkmJQOJkXe',
    'Admin',
    TRUE,
    TRUE
);

-- Create admin account with agency plan
INSERT INTO accounts (user_id, plan_id, sparks_balance)
SELECT u.id, p.id, 1000
FROM users u, plans p
WHERE u.email = 'admin@sovrn.local' AND p.type = 'agency';
