#!/usr/bin/env python3
# filepath: test_fixed_pipeline.py

import asyncio
import requests
import redis
import json
import websockets
from datetime import datetime, timezone

async def test_fixed_pipeline():
    """Test the fixed AWS pipeline end-to-end"""
    print("🧪 Testing Fixed AWS Data Pipeline")
    print("=" * 50)
    
    # 1. Test Redis connection
    try:
        r = redis.Redis(host='localhost', port=6379, decode_responses=True)
        r.ping()
        print("✅ Redis: Connected")
    except Exception as e:
        print(f"❌ Redis: {e}")
        return False
    
    # 2. Test backend health
    try:
        response = requests.get('http://localhost:8000/health', timeout=10)
        if response.status_code == 200:
            print("✅ Backend: Healthy")
        else:
            print(f"❌ Backend: Status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Backend: {e}")
        print("   Make sure to start: uvicorn main:app --reload --port 8000")
        return False
    
    # 3. Test AWS Spot endpoint with synthetic data
    try:
        response = requests.get('http://localhost:8000/api/aws-spot/prices?limit=10&include_synthetic=true', timeout=15)
        if response.status_code == 200:
            data = response.json()
            offers = data.get('offers', [])
            print(f"✅ AWS Spot API: {len(offers)} offers returned")
            
            if offers:
                sample = offers[0]
                print(f"   Sample: {sample.get('model')} @ ${sample.get('usd_hr')}/hr in {sample.get('region')}")
                print(f"   Data source: {data.get('metadata', {}).get('data_source', 'unknown')}")
                
                # Check for enrichment (may not be present with fallbacks)
                enriched_fields = ['interruption_risk', 'data_freshness', 'vcpu_count']
                found = [f for f in enriched_fields if f in sample]
                if found:
                    print(f"   Enriched fields: {found}")
                else:
                    print("   Using fallback mode (enrichment not available)")
        else:
            print(f"❌ AWS Spot API: Status {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
    except Exception as e:
        print(f"❌ AWS Spot API: {e}")
        return False
    
    # 4. Test regions endpoint
    try:
        response = requests.get('http://localhost:8000/api/aws-spot/regions', timeout=10)
        if response.status_code == 200:
            data = response.json()
            regions = data.get('regions', [])
            print(f"✅ Regions API: {len(regions)} regions available")
        else:
            print(f"⚠️ Regions API: Status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Regions API: {e}")
    
    # 5. Test models endpoint
    try:
        response = requests.get('http://localhost:8000/api/aws-spot/models', timeout=10)
        if response.status_code == 200:
            data = response.json()
            models = data.get('models', [])
            print(f"✅ Models API: {len(models)} GPU models available")
        else:
            print(f"⚠️ Models API: Status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Models API: {e}")
    
    # 6. Test summary endpoint
    try:
        response = requests.get('http://localhost:8000/api/aws-spot/summary', timeout=10)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Summary API: {data.get('total_offers', 0)} total offers")
            print(f"   Price range: ${data.get('price_range', {}).get('min', 0):.2f} - ${data.get('price_range', {}).get('max', 0):.2f}")
        else:
            print(f"⚠️ Summary API: Status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Summary API: {e}")
    
    # 7. Test WebSocket connection
    try:
        print("🔌 Testing WebSocket connection...")
        async with websockets.connect('ws://localhost:8000/ws/aws-spot') as websocket:
            print("✅ WebSocket: Connected")
            
            # Wait for initial message
            try:
                message = await asyncio.wait_for(websocket.recv(), timeout=10)
                data = json.loads(message)
                print(f"✅ WebSocket: Received {data.get('type', 'unknown')} message")
                
                offers = data.get('offers', [])
                if offers:
                    print(f"   {len(offers)} offers in WebSocket message")
                    sample = offers[0]
                    print(f"   Sample: {sample.get('model')} @ ${sample.get('usd_hr')}/hr")
                
            except asyncio.TimeoutError:
                print("⚠️ WebSocket: No message received within 10 seconds")
                print("   This is normal if no data updates are available")
                
    except Exception as e:
        print(f"❌ WebSocket: {e}")
    
    # 8. Test filtering
    try:
        response = requests.get('http://localhost:8000/api/aws-spot/prices?model=A100&region=us-east-1&limit=5', timeout=10)
        if response.status_code == 200:
            data = response.json()
            offers = data.get('offers', [])
            print(f"✅ Filtering: {len(offers)} A100 offers in us-east-1")
        else:
            print(f"⚠️ Filtering: Status {response.status_code}")
    except Exception as e:
        print(f"⚠️ Filtering: {e}")
    
    print("\n🎉 Pipeline Test Complete!")
    print("\n📋 Manual Tests:")
    print("1. Start frontend: cd frontend && npm run dev")
    print("2. Visit: http://localhost:3000/dashboard")
    print("3. Toggle AWS data display to see offers")
    print("4. Check browser console for any errors")
    
    print("\n🔧 If you see issues:")
    print("1. Check Redis is running: redis-cli ping")
    print("2. Check backend logs for errors")
    print("3. Verify environment variables are set")
    
    return True

if __name__ == "__main__":
    asyncio.run(test_fixed_pipeline())