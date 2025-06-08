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
