#!/bin/bash
# GPU Yield Calculator Deployment Script

set -e

ENVIRONMENT=${1:-production}
BRANCH=${2:-main}

echo "🚀 Deploying GPU Yield Calculator"
echo "Environment: $ENVIRONMENT"
echo "Branch: $BRANCH"

# Pre-deployment checks
echo "Running pre-deployment checks..."

# Check if all required environment variables are set
required_vars=("REDIS_URL" "SENTRY_DSN" "SENDGRID_API_KEY")
for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        echo "❌ Required environment variable $var is not set"
        exit 1
    fi
done

echo "✅ Environment variables check passed"

# Run tests if in CI/CD
if [ "$CI" = "true" ]; then
    echo "Running tests..."
    
    # API tests
    cd api
    python -m pytest tests/ || exit 1
    cd ..
    
    # Frontend tests (if you have them)
    cd frontend
    npm test -- --passWithNoTests || exit 1
    cd ..
    
    echo "✅ Tests passed"
fi

# Build and deploy
echo "Building and deploying..."

# This would integrate with your deployment platform
# For Render, this might trigger a webhook or use the Render API
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Deploying to production..."
    # curl -X POST "https://api.render.com/deploy/srv-xxx" \
    #   -H "Authorization: Bearer $RENDER_API_KEY"
else
    echo "Deploying to staging..."
fi

echo "✅ Deployment completed successfully"
