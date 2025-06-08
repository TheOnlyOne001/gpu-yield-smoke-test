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
