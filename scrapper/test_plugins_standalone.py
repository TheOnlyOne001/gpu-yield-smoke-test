#!/usr/bin/env python3
"""
Standalone test script for plugins without Redis dependency
"""
import sys
import os
import time
import logging

# Add the current directory to the path
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import plugins directly
from plugins import runpod, akash, aws_spot, vast_ai, io_net

def test_plugins_standalone():
    """Test plugins without Redis dependency"""
    logger.info("🧪 Testing plugins (standalone mode)...")
    
    plugins_to_test = [runpod, akash, aws_spot, vast_ai, io_net]
    results = {}
    
    for plugin in plugins_to_test:
        plugin_name = getattr(plugin, 'name', plugin.__name__)
        
        try:
            logger.info(f"Testing {plugin_name}...")
            start_time = time.time()
            
            offers = plugin.fetch()
            duration = time.time() - start_time
            
            if offers:
                # Validate offers format
                valid_count = 0
                for offer in offers:
                    if (isinstance(offer, dict) and 
                        'model' in offer and 
                        'usd_hr' in offer and 
                        'region' in offer):
                        valid_count += 1
                
                results[plugin_name] = {
                    'status': 'success',
                    'total_offers': len(offers),
                    'valid_offers': valid_count,
                    'duration': duration,
                    'sample': offers[:3] if offers else []
                }
                logger.info(f"✅ {plugin_name}: {valid_count} valid offers in {duration:.2f}s")
            else:
                results[plugin_name] = {
                    'status': 'no_data',
                    'total_offers': 0,
                    'duration': duration
                }
                logger.warning(f"⚠️  {plugin_name}: No offers returned")
                
        except Exception as e:
            results[plugin_name] = {
                'status': 'error',
                'error': str(e),
                'duration': time.time() - start_time if 'start_time' in locals() else 0
            }
            logger.error(f"❌ {plugin_name}: {e}")
    
    # Print summary
    print("\n" + "="*60)
    print("PLUGIN TEST RESULTS")
    print("="*60)
    
    for plugin_name, result in results.items():
        status = result['status']
        if status == 'success':
            print(f"✅ {plugin_name:12} | {result['valid_offers']:3d} offers | {result['duration']:.2f}s")
            # Show sample data
            if result['sample']:
                sample = result['sample'][0]
                print(f"   Sample: {sample.get('model', 'N/A')} - ${sample.get('usd_hr', 0):.4f}/hr")
        elif status == 'no_data':
            print(f"⚠️  {plugin_name:12} | No data returned | {result['duration']:.2f}s")
        else:
            print(f"❌ {plugin_name:12} | ERROR: {result.get('error', 'Unknown')}")
    
    total_offers = sum(r.get('valid_offers', 0) for r in results.values())
    successful = sum(1 for r in results.values() if r['status'] == 'success')
    
    print("-" * 60)
    print(f"Total valid offers: {total_offers}")
    print(f"Success rate: {successful}/{len(plugins_to_test)} ({(successful/len(plugins_to_test)*100):.1f}%)")
    print("="*60)
    
    return results

if __name__ == "__main__":
    test_plugins_standalone()