#!/usr/bin/env python3
"""
Quick test to verify OAuth router is working
"""
import sys
import os
import asyncio

# Add API directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

async def test_router_import():
    """Test if we can import the OAuth router."""
    try:
        from routers.oauth import router as oauth_router
        print("✅ OAuth router imported successfully")
        
        # Check if router has routes
        routes = []
        for route in oauth_router.routes:
            if hasattr(route, 'path') and hasattr(route, 'methods'):
                routes.append(f"{list(route.methods)[0]} {route.path}")
        
        print(f"✅ OAuth router has {len(routes)} routes:")
        for route in routes:
            print(f"   - {route}")
            
        return True
        
    except ImportError as e:
        print(f"❌ Failed to import OAuth router: {e}")
        return False
    except Exception as e:
        print(f"❌ Error testing OAuth router: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_router_import())