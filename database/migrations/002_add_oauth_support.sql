-- Migration: Add OAuth support to signups table
-- File: migrations/002_add_oauth_support.sql

-- Add OAuth-related columns to signups table
ALTER TABLE signups 
ADD COLUMN IF NOT EXISTS auth_provider VARCHAR(20) DEFAULT 'email',
ADD COLUMN IF NOT EXISTS provider_id VARCHAR(255),
ADD COLUMN IF NOT EXISTS avatar_url TEXT,
ADD COLUMN IF NOT EXISTS full_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS is_verified BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS last_login TIMESTAMP WITH TIME ZONE;

-- Make hashed_password optional (for OAuth users)
ALTER TABLE signups ALTER COLUMN hashed_password DROP NOT NULL;

-- Add constraints
ALTER TABLE signups ADD CONSTRAINT check_auth_provider 
CHECK (auth_provider IN ('email', 'google', 'twitter', 'discord'));

-- Create unique index for OAuth users
CREATE UNIQUE INDEX IF NOT EXISTS idx_signups_oauth_provider 
ON signups (auth_provider, provider_id) 
WHERE auth_provider != 'email' AND provider_id IS NOT NULL;

-- Create index for email lookups
CREATE INDEX IF NOT EXISTS idx_signups_email ON signups (email);

-- Create index for auth provider
CREATE INDEX IF NOT EXISTS idx_signups_auth_provider ON signups (auth_provider);

-- Create index for provider_id
CREATE INDEX IF NOT EXISTS idx_signups_provider_id ON signups (provider_id);

-- Create index for last_login
CREATE INDEX IF NOT EXISTS idx_signups_last_login ON signups (last_login);

-- Create index for created_at if not exists
CREATE INDEX IF NOT EXISTS idx_signups_created_at ON signups (created_at);

-- Create index for is_active if not exists
CREATE INDEX IF NOT EXISTS idx_signups_is_active ON signups (is_active);

-- Create table for OAuth tokens (optional, for refresh tokens)
CREATE TABLE IF NOT EXISTS oauth_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES signups(id) ON DELETE CASCADE,
    provider VARCHAR(20) NOT NULL,
    access_token TEXT,
    refresh_token TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for OAuth tokens
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_user_provider 
ON oauth_tokens (user_id, provider);

-- Create index for OAuth tokens expiry
CREATE INDEX IF NOT EXISTS idx_oauth_tokens_expires 
ON oauth_tokens (expires_at);

-- Create table for OAuth state management (for security)
CREATE TABLE IF NOT EXISTS oauth_states (
    id SERIAL PRIMARY KEY,
    state_token VARCHAR(255) UNIQUE NOT NULL,
    provider VARCHAR(20) NOT NULL,
    redirect_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

-- Create index for OAuth states
CREATE INDEX IF NOT EXISTS idx_oauth_states_token ON oauth_states (state_token);
CREATE INDEX IF NOT EXISTS idx_oauth_states_expires ON oauth_states (expires_at);

-- Create function to clean up expired OAuth states
CREATE OR REPLACE FUNCTION cleanup_expired_oauth_states()
RETURNS void AS $$
BEGIN
    DELETE FROM oauth_states WHERE expires_at < NOW();
END;
$$ LANGUAGE plpgsql;

-- Add trigger to update updated_at column for oauth_tokens
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger for oauth_tokens table
DROP TRIGGER IF EXISTS update_oauth_tokens_updated_at ON oauth_tokens;
CREATE TRIGGER update_oauth_tokens_updated_at
    BEFORE UPDATE ON oauth_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Update existing users to have default values
UPDATE signups 
SET 
    auth_provider = 'email',
    is_verified = CASE 
        WHEN is_verified IS NULL THEN FALSE 
        ELSE is_verified 
    END
WHERE auth_provider IS NULL;

-- Add sample OAuth provider configurations (optional)
CREATE TABLE IF NOT EXISTS oauth_provider_configs (
    id SERIAL PRIMARY KEY,
    provider VARCHAR(20) UNIQUE NOT NULL,
    display_name VARCHAR(50) NOT NULL,
    is_enabled BOOLEAN DEFAULT TRUE,
    client_id VARCHAR(255),
    redirect_uri TEXT,
    scope TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create trigger for oauth_provider_configs table
DROP TRIGGER IF EXISTS update_oauth_configs_updated_at ON oauth_provider_configs;
CREATE TRIGGER update_oauth_configs_updated_at
    BEFORE UPDATE ON oauth_provider_configs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default OAuth provider configurations
INSERT INTO oauth_provider_configs (provider, display_name, is_enabled, scope) VALUES
('google', 'Google', TRUE, 'openid email profile'),
('twitter', 'Twitter', TRUE, 'users.read tweet.read'),
('discord', 'Discord', TRUE, 'identify email')
ON CONFLICT (provider) DO NOTHING;

-- Create view for user authentication summary
CREATE OR REPLACE VIEW user_auth_summary AS
SELECT 
    s.id,
    s.email,
    s.username,
    s.full_name,
    s.auth_provider,
    s.provider_id,
    s.avatar_url,
    s.is_verified,
    s.is_active,
    s.last_login,
    s.created_at,
    s.gpu_models_interested,
    s.min_profit_threshold,
    CASE 
        WHEN s.hashed_password IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_password,
    CASE 
        WHEN s.auth_provider != 'email' THEN TRUE 
        ELSE FALSE 
    END AS is_oauth_user,
    CASE 
        WHEN s.last_login IS NOT NULL THEN TRUE 
        ELSE FALSE 
    END AS has_logged_in
FROM signups s;

-- Create function to get OAuth statistics
CREATE OR REPLACE FUNCTION get_oauth_stats()
RETURNS TABLE (
    provider VARCHAR(20),
    user_count BIGINT,
    active_users BIGINT,
    verified_users BIGINT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.auth_provider as provider,
        COUNT(*) as user_count,
        COUNT(*) FILTER (WHERE s.is_active = TRUE) as active_users,
        COUNT(*) FILTER (WHERE s.is_verified = TRUE) as verified_users
    FROM signups s
    GROUP BY s.auth_provider
    ORDER BY user_count DESC;
END;
$$ LANGUAGE plpgsql;

-- Create function to cleanup old OAuth tokens
CREATE OR REPLACE FUNCTION cleanup_expired_oauth_tokens()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM oauth_tokens 
    WHERE expires_at < NOW();
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;

-- Create function to get user's OAuth providers
CREATE OR REPLACE FUNCTION get_user_oauth_providers(user_email TEXT)
RETURNS TABLE (
    provider VARCHAR(20),
    provider_id VARCHAR(255),
    avatar_url TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.auth_provider as provider,
        s.provider_id,
        s.avatar_url,
        s.created_at
    FROM signups s
    WHERE s.email = user_email
    AND s.auth_provider != 'email';
END;
$$ LANGUAGE plpgsql;

-- Add comments for documentation
COMMENT ON TABLE oauth_tokens IS 'Stores OAuth access and refresh tokens for users';
COMMENT ON TABLE oauth_states IS 'Temporary storage for OAuth state tokens during authentication flow';
COMMENT ON TABLE oauth_provider_configs IS 'Configuration for OAuth providers';
COMMENT ON VIEW user_auth_summary IS 'Summary view of user authentication methods and status';

COMMENT ON COLUMN signups.auth_provider IS 'Authentication provider: email, google, twitter, discord';
COMMENT ON COLUMN signups.provider_id IS 'Unique ID from OAuth provider';
COMMENT ON COLUMN signups.avatar_url IS 'User avatar URL from OAuth provider';
COMMENT ON COLUMN signups.full_name IS 'Full name from OAuth provider';
COMMENT ON COLUMN signups.is_verified IS 'Whether user email is verified';
COMMENT ON COLUMN signups.last_login IS 'Last login timestamp';

-- Grant basic permissions (uncomment and adjust as needed)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON signups TO gpu_yield_api;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_tokens TO gpu_yield_api;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_states TO gpu_yield_api;
-- GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_provider_configs TO gpu_yield_api;
-- GRANT SELECT ON user_auth_summary TO gpu_yield_api;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gpu_yield_api;

-- Add this migration to your database
ALTER TABLE signups ADD COLUMN is_admin BOOLEAN DEFAULT FALSE;

-- Make your admin user an admin (replace with your email)
UPDATE signups SET is_admin = TRUE WHERE email = 'shayanahmad78600@gmail.com';