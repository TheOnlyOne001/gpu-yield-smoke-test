#!/bin/bash
# Step 1: Environment Setup Guide

echo "🚀 GPU Yield Calculator - Step 1: Environment Setup"

# First, let's create the enhanced .env file
cat > .env << 'EOF'
# GPU Yield Calculator Environment Configuration

# === CORE INFRASTRUCTURE ===
REDIS_URL=redis://redis:6379
POSTGRES_URL=postgresql://postgres:password@postgres:5432/gpu_yield_db

# === API CONFIGURATION ===
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000
ENVIRONMENT=development

# === SECURITY ===
JWT_SECRET=your-super-secret-jwt-key-change-in-production
API_SECRET_KEY=your-api-secret-key
HCAPTCHA_SECRET_KEY=your-hcaptcha-secret-key

# === EMAIL CONFIGURATION ===
SENDGRID_API_KEY=your-sendgrid-api-key
FROM_EMAIL=alerts@gpuyield.com

# === STRIPE CONFIGURATION ===
STRIPE_SECRET_KEY=sk_test_your-stripe-secret-key
STRIPE_WEBHOOK_SECRET=whsec_your-webhook-secret
STRIPE_PRICE_ID=price_your-price-id

# === MONITORING ===
SENTRY_DSN=your-sentry-dsn

# === APPLICATION SETTINGS ===
LOG_LEVEL=INFO
MAX_WORKERS=4
SCRAPE_INTERVAL_SECONDS=120
CACHE_TTL_SECONDS=30
RATE_LIMIT_PER_MINUTE=60

# === DATA SETTINGS ===
MAX_STREAM_LENGTH=10000
DATA_RETENTION_DAYS=7
BATCH_SIZE=1000

# === EXTERNAL APIS (Optional) ===
VAST_AI_API_KEY=optional
RUNPOD_API_KEY=optional
IONET_API_KEY=optional
EOF

echo "✅ Created .env file"

# Create enhanced docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  # Redis for caching and job queues
  redis:
    image: redis:7-alpine
    container_name: gpu-yield-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
      - ./config/redis.conf:/usr/local/etc/redis/redis.conf
    command: redis-server /usr/local/etc/redis/redis.conf
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # PostgreSQL for persistent data
  postgres:
    image: postgres:15-alpine
    container_name: gpu-yield-postgres
    environment:
      POSTGRES_DB: gpu_yield_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./database/init.sql:/docker-entrypoint-initdb.d/01-init.sql
      - ./database/migrations:/docker-entrypoint-initdb.d/migrations
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # FastAPI Backend
  api:
    build:
      context: ./api
      dockerfile: Dockerfile
    container_name: gpu-yield-api
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://postgres:password@postgres:5432/gpu_yield_db
    env_file:
      - .env
    volumes:
      - ./api:/app
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

  # Next.js Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: gpu-yield-frontend
    ports:
      - "3000:3000"
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    env_file:
      - .env
    volumes:
      - ./frontend:/app
      - /app/node_modules
      - /app/.next
    depends_on:
      - api
    restart: unless-stopped
    command: npm run dev

  # Background Worker
  worker:
    build:
      context: ./worker
      dockerfile: Dockerfile
    container_name: gpu-yield-worker
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://postgres:password@postgres:5432/gpu_yield_db
    env_file:
      - .env
    volumes:
      - ./worker:/app
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    restart: unless-stopped
    command: python alerts.py

  # Price Scraper
  scraper:
    build:
      context: ./scrapper
      dockerfile: Dockerfile
    container_name: gpu-yield-scraper
    environment:
      - REDIS_URL=redis://redis:6379
      - POSTGRES_URL=postgresql://postgres:password@postgres:5432/gpu_yield_db
    env_file:
      - .env
    volumes:
      - ./scrapper:/app
      - ./logs:/app/logs
    depends_on:
      redis:
        condition: service_healthy
      postgres:
        condition: service_healthy
    restart: unless-stopped
    command: python main.py

  # Database Admin (Optional - for development)
  pgadmin:
    image: dpage/pgadmin4:latest
    container_name: gpu-yield-pgadmin
    environment:
      PGADMIN_DEFAULT_EMAIL: admin@gpuyield.com
      PGADMIN_DEFAULT_PASSWORD: admin123
    ports:
      - "5050:80"
    volumes:
      - pgadmin_data:/var/lib/pgadmin
    depends_on:
      - postgres
    restart: unless-stopped
    profiles: ["dev"]  # Only start with --profile dev

volumes:
  redis_data:
  postgres_data:
  pgadmin_data:

networks:
  default:
    name: gpu_yield_network
EOF

echo "✅ Created docker-compose.yml file"

# Create Redis configuration
mkdir -p config
cat > config/redis.conf << 'EOF'
# Redis Configuration for GPU Yield Calculator
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
appendonly yes
appendfsync everysec
auto-aof-rewrite-percentage 100
auto-aof-rewrite-min-size 64mb
EOF

echo "✅ Created Redis configuration"

# Create database initialization script
mkdir -p database/migrations
cat > database/init.sql << 'EOF'
-- GPU Yield Calculator Database Schema
-- This script initializes the database with all required tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users/Signups table
CREATE TABLE IF NOT EXISTS signups (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    signup_date TIMESTAMPTZ DEFAULT NOW(),
    stripe_customer_id VARCHAR(255),
    trial_start_date TIMESTAMPTZ,
    trial_end_date TIMESTAMPTZ,
    subscription_status VARCHAR(50) DEFAULT 'trial',
    gpu_models_interested TEXT[],
    min_profit_threshold DECIMAL(10,2) DEFAULT 0.00,
    alert_frequency_minutes INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT true,
    api_key VARCHAR(255),
    is_admin BOOLEAN DEFAULT false,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Price data table
CREATE TABLE IF NOT EXISTS prices (
    id BIGSERIAL PRIMARY KEY,
    cloud VARCHAR(50) NOT NULL,
    gpu_model VARCHAR(100) NOT NULL,
    region VARCHAR(100) NOT NULL,
    price_usd_hr DECIMAL(10,6) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    availability_count INTEGER DEFAULT 1,
    source_record_id VARCHAR(255),
    data_quality_score DECIMAL(3,2) DEFAULT 1.0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint for deduplication
    UNIQUE(cloud, gpu_model, region, date_trunc('minute', timestamp))
);

-- Alert rules table
CREATE TABLE IF NOT EXISTS alert_rules (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES signups(id) ON DELETE CASCADE,
    gpu_model VARCHAR(100) NOT NULL,
    min_profit_threshold DECIMAL(10,2) NOT NULL,
    max_price_threshold DECIMAL(10,6),
    preferred_regions TEXT[],
    alert_frequency_minutes INTEGER DEFAULT 30,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Alert log table
CREATE TABLE IF NOT EXISTS alerts_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES signups(id) ON DELETE CASCADE,
    alert_rule_id UUID REFERENCES alert_rules(id) ON DELETE CASCADE,
    gpu_model VARCHAR(100) NOT NULL,
    triggered_price DECIMAL(10,6) NOT NULL,
    cloud VARCHAR(50) NOT NULL,
    sent_at TIMESTAMPTZ DEFAULT NOW(),
    email_status VARCHAR(50) DEFAULT 'sent',
    profit_margin DECIMAL(10,2),
    metadata JSONB DEFAULT '{}'
);

-- Analytics events table
CREATE TABLE IF NOT EXISTS analytics_events (
    id BIGSERIAL PRIMARY KEY,
    event_name VARCHAR(100) NOT NULL,
    user_id UUID REFERENCES signups(id) ON DELETE SET NULL,
    session_id VARCHAR(255),
    event_data JSONB DEFAULT '{}',
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    ip_address INET,
    user_agent TEXT
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_prices_timestamp ON prices(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_prices_gpu_model ON prices(gpu_model);
CREATE INDEX IF NOT EXISTS idx_prices_cloud ON prices(cloud);
CREATE INDEX IF NOT EXISTS idx_prices_composite ON prices(gpu_model, cloud, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_signups_email ON signups(email);
CREATE INDEX IF NOT EXISTS idx_signups_active ON signups(is_active);
CREATE INDEX IF NOT EXISTS idx_signups_stripe ON signups(stripe_customer_id);

CREATE INDEX IF NOT EXISTS idx_alert_rules_user ON alert_rules(user_id);
CREATE INDEX IF NOT EXISTS idx_alert_rules_active ON alert_rules(is_active);

CREATE INDEX IF NOT EXISTS idx_alerts_log_user ON alerts_log(user_id);
CREATE INDEX IF NOT EXISTS idx_alerts_log_sent_at ON alerts_log(sent_at DESC);

CREATE INDEX IF NOT EXISTS idx_analytics_events_name ON analytics_events(event_name);
CREATE INDEX IF NOT EXISTS idx_analytics_events_timestamp ON analytics_events(timestamp DESC);

-- Create update trigger for updated_at columns
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_signups_updated_at BEFORE UPDATE ON signups
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_alert_rules_updated_at BEFORE UPDATE ON alert_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
EOF

echo "✅ Created database initialization script"

# Create Dockerfiles for each service
echo "Creating Dockerfiles..."

# API Dockerfile
cat > api/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Frontend Dockerfile
cat > frontend/Dockerfile << 'EOF'
FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci --only=production

# Copy application code
COPY . .

# Expose port
EXPOSE 3000

# Default command
CMD ["npm", "run", "dev"]
EOF

# Worker Dockerfile
cat > worker/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Default command
CMD ["python", "alerts.py"]
EOF

# Scraper Dockerfile
cat > scrapper/Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p logs

# Default command
CMD ["python", "main.py"]
EOF

echo "✅ Created all Dockerfiles"

# Create logs directory
mkdir -p logs

echo ""
echo "🎉 Step 1 Complete!"
echo ""
echo "Next steps:"
echo "1. Run: docker-compose up -d postgres redis"
echo "2. Wait for databases to initialize"
echo "3. Run: docker-compose logs postgres redis"
echo "4. Then proceed to Step 2"
echo ""
echo "Quick commands:"
echo "• Start databases: docker-compose up -d postgres redis"
echo "• View logs: docker-compose logs -f"
echo "• Stop all: docker-compose down"
echo "• Remove volumes: docker-compose down -v"
EOF

chmod +x step1_env_setup.sh