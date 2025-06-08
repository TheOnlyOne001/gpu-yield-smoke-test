#!/bin/bash
# GPU Yield Calculator - Environment Setup and Deployment Script

set -e  # Exit on any error

echo "🚀 Setting up GPU Yield Calculator Environment"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running in production
ENVIRONMENT=${ENVIRONMENT:-"development"}
print_status "Environment: $ENVIRONMENT"

# Create necessary directories
print_status "Creating project directories..."
mkdir -p logs
mkdir -p data/redis
mkdir -p monitoring

# Environment variables template
create_env_template() {
    print_status "Creating environment variables template..."
    
    cat > .env.template << EOF
# GPU Yield Calculator Environment Configuration

# Redis Configuration
REDIS_URL=redis://localhost:6379

# API Configuration
API_BASE_URL=http://localhost:8000
NEXT_PUBLIC_API_URL=http://localhost:8000

# Monitoring and Error Tracking
SENTRY_DSN=your_sentry_dsn_here
LOG_LEVEL=INFO

# Email Configuration (SendGrid)
SENDGRID_API_KEY=your_sendgrid_api_key_here
FROM_EMAIL=alerts@gpuyield.com

# Security
HCP_SECRET=your_hcaptcha_secret_here
JWT_SECRET=your_jwt_secret_here

# Application Settings
ENVIRONMENT=${ENVIRONMENT}
MAX_WORKERS=4
SCRAPE_INTERVAL_SECONDS=120
CACHE_TTL_SECONDS=30

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
RATE_LIMIT_BURST=10

# Data Retention
MAX_STREAM_LENGTH=10000
DATA_RETENTION_DAYS=7

# External APIs (if needed)
VAST_AI_API_KEY=optional
RUNPOD_API_KEY=optional
EOF

    print_status "Environment template created at .env.template"
    print_warning "Copy .env.template to .env and fill in your actual values"
}

# Setup development environment
setup_development() {
    print_status "Setting up development environment..."
    
    # Check for required tools
    command -v python3 >/dev/null 2>&1 || { print_error "Python 3 is required but not installed. Aborting."; exit 1; }
    command -v node >/dev/null 2>&1 || { print_error "Node.js is required but not installed. Aborting."; exit 1; }
   # command -v redis-server >/dev/null 2>&1 || { print_error "Redis is required but not installed. Aborting."; exit 1; }
    
    # Create virtual environment for Python
    if [ ! -d "venv" ]; then
        print_status "Creating Python virtual environment..."
        python3 -m venv venv
    fi

    print_status "Activating virtual environment..."
    # This block is now cross-platform compatible
    if [ -f "venv/Scripts/activate" ]; then
        source venv/Scripts/activate # For Windows/MINGW64
        print_status "Windows virtual environment activated."
    elif [ -f "venv/bin/activate" ]; then
        source venv/bin/activate # For Linux/macOS
        print_status "Linux/macOS virtual environment activated."
    else
        print_error "Could not find activation script for virtual environment."
        exit 1
    fi

    # Install Python dependencies
    print_status "Installing Python dependencies..."
    pip install -r api/requirements.txt
    pip install -r worker/requirements.txt
    pip install -r scrapper/requirements.txt
    
    # Install additional development tools
    pip install pytest black flake8 mypy
    
    # Install Node.js dependencies
    print_status "Installing Node.js dependencies..."
    cd frontend
    npm install
    cd ..
    
    # Start Redis in background (if not running)
    #if ! pgrep -x "redis-server" > /dev/null; then
    #    print_status "Starting Redis server..."
    #   redis-server --daemonize yes --logfile logs/redis.log
    #else
    #    print_status "Redis server already running"
    #fi
    
    print_status "Development environment setup complete!"
    print_warning "Don't forget to create and configure your .env file"
}

# Setup production monitoring
setup_monitoring() {
    print_status "Setting up monitoring configuration..."
    
    # Create monitoring configuration
    cat > monitoring/healthcheck.py << 'EOF'
#!/usr/bin/env python3
"""
Health check script for monitoring GPU Yield Calculator services
"""
import requests
import json
import sys
import time
from datetime import datetime

def check_api_health(base_url):
    """Check API health endpoint"""
    try:
        response = requests.get(f"{base_url}/health", timeout=10)
        if response.status_code == 200:
            data = response.json()
            return True, data.get('status', 'unknown')
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def check_redis_data(base_url):
    """Check if fresh data is available"""
    try:
        response = requests.get(f"{base_url}/delta", timeout=10)
        if response.status_code == 200:
            data = response.json()
            deltas = data.get('deltas', [])
            return len(deltas) > 0, f"{len(deltas)} pricing records"
        else:
            return False, f"HTTP {response.status_code}"
    except Exception as e:
        return False, str(e)

def main():
    base_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    
    print(f"🔍 Health Check Report - {datetime.now()}")
    print(f"Target: {base_url}")
    print("-" * 50)
    
    # Check API health
    api_healthy, api_status = check_api_health(base_url)
    status_icon = "✅" if api_healthy else "❌"
    print(f"{status_icon} API Health: {api_status}")
    
    # Check data freshness
    data_available, data_status = check_redis_data(base_url)
    data_icon = "✅" if data_available else "❌"
    print(f"{data_icon} Data Availability: {data_status}")
    
    # Overall status
    overall_healthy = api_healthy and data_available
    overall_icon = "✅" if overall_healthy else "❌"
    print(f"{overall_icon} Overall Status: {'Healthy' if overall_healthy else 'Issues Detected'}")
    
    # Exit with error code if unhealthy
    sys.exit(0 if overall_healthy else 1)

if __name__ == "__main__":
    main()
EOF
    
    chmod +x monitoring/healthcheck.py
    
    # Create Docker monitoring setup
    cat > monitoring/docker-compose.monitoring.yml << 'EOF'
version: '3.8'

services:
  # Prometheus for metrics collection
  prometheus:
    image: prom/prometheus:latest
    container_name: gpu-yield-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--storage.tsdb.retention.time=200h'
      - '--web.enable-lifecycle'
    restart: unless-stopped

  # Grafana for visualization
  grafana:
    image: grafana/grafana:latest
    container_name: gpu-yield-grafana
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin123
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    restart: unless-stopped

  # Redis Exporter for Redis metrics
  redis-exporter:
    image: oliver006/redis_exporter
    container_name: gpu-yield-redis-exporter
    ports:
      - "9121:9121"
    environment:
      - REDIS_ADDR=redis://host.docker.internal:6379
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
EOF

    # Create Prometheus configuration
    cat > monitoring/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files: []

scrape_configs:
  - job_name: 'gpu-yield-api'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: /metrics
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']
    scrape_interval: 30s

  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']
EOF

    print_status "Monitoring configuration created"
}

# Setup production deployment helpers
setup_deployment() {
    print_status "Creating deployment helpers..."
    
    # Create deployment script
    cat > deploy.sh << 'EOF'
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
EOF

    chmod +x deploy.sh
    
    # Create backup script
    cat > backup.sh << 'EOF'
#!/bin/bash
# GPU Yield Calculator Backup Script

set -e

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "🗄️ Creating backup in $BACKUP_DIR"

# Backup Redis data (if local)
if command -v redis-cli >/dev/null 2>&1; then
    echo "Backing up Redis data..."
    redis-cli --rdb "$BACKUP_DIR/redis_backup.rdb"
fi

# Backup configuration files
echo "Backing up configuration..."
cp .env "$BACKUP_DIR/" 2>/dev/null || echo "No .env file found"
cp render.yaml "$BACKUP_DIR/" 2>/dev/null || echo "No render.yaml found"

# Create backup info
cat > "$BACKUP_DIR/backup_info.txt" << EOL
Backup created: $(date)
Environment: ${ENVIRONMENT:-unknown}
Git commit: $(git rev-parse HEAD 2>/dev/null || echo "unknown")
Git branch: $(git branch --show-current 2>/dev/null || echo "unknown")
EOL

echo "✅ Backup completed: $BACKUP_DIR"
EOF

    chmod +x backup.sh
    
    print_status "Deployment helpers created"
}

# Main setup function
main() {
    case "${1:-all}" in
        "dev"|"development")
            create_env_template
            setup_development
            ;;
        "monitoring")
            setup_monitoring
            ;;
        "deploy")
            setup_deployment
            ;;
        "all")
            create_env_template
            setup_development
            setup_monitoring
            setup_deployment
            ;;
        *)
            echo "Usage: $0 [dev|monitoring|deploy|all]"
            echo "  dev        - Setup development environment"
            echo "  monitoring - Setup monitoring tools"
            echo "  deploy     - Setup deployment helpers"
            echo "  all        - Setup everything (default)"
            exit 1
            ;;
    esac
    
    print_status "Setup completed! 🎉"
    
    if [ "${1:-all}" = "all" ] || [ "${1:-all}" = "dev" ]; then
        echo
        print_status "Next steps:"
        echo "1. Copy .env.template to .env and configure your values"
        echo "2. Start the development servers:"
        echo "   - API: cd api && uvicorn main:app --reload"
        echo "   - Frontend: cd frontend && npm run dev"
        echo "   - Worker: cd worker && python alerts.py"
        echo "   - Scraper: cd scrapper && python main.py"
        echo "3. Visit http://localhost:3000 to see your app"
        echo "4. API docs available at http://localhost:8000/docs"
        echo
        print_warning "For production deployment, configure your secrets in Render dashboard"
    fi
}

# Run main function with all arguments
main "$@"