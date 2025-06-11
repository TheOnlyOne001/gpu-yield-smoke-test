from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import logging
from typing import Set
import redis.asyncio as redis
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

async def get_redis_connection():
    """Get async Redis connection"""
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        pool = redis.ConnectionPool.from_url(redis_url, decode_responses=True)
        return redis.Redis(connection_pool=pool)
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        raise Exception("Redis configuration missing")

def build_offer_from_redis_fields(fields: dict) -> dict:
    """Build AWS Spot offer from Redis stream fields"""
    offer = {
        'model': fields.get('gpu_model'),
        'region': fields.get('region'),
        'availability': 1,
        'provider': 'aws_spot',
        'timestamp': fields.get('iso_timestamp'),
        'instance_type': fields.get('instance_type', ''),
    }
    
    # Handle price with validation
    try:
        offer['usd_hr'] = float(fields.get('price_usd_hr', 0))
    except (ValueError, TypeError):
        offer['usd_hr'] = 0
    
    # Handle optional fields
    if fields.get('availability'):
        try:
            offer['availability'] = int(fields.get('availability'))
        except (ValueError, TypeError):
            offer['availability'] = 1
    
    if fields.get('total_instance_price'):
        try:
            offer['total_instance_price'] = float(fields.get('total_instance_price'))
        except (ValueError, TypeError):
            pass
    
    if fields.get('gpu_memory_gb'):
        try:
            offer['gpu_memory_gb'] = int(fields.get('gpu_memory_gb'))
        except (ValueError, TypeError):
            pass
    
    if fields.get('synthetic'):
        offer['synthetic'] = fields.get('synthetic').lower() == 'true'
    
    return offer

@router.websocket("/ws/aws-spot")
async def aws_spot_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time AWS Spot price updates"""
    await websocket.accept()
    active_connections.add(websocket)
    
    redis_conn = None
    try:
        redis_conn = await get_redis_connection()
        
        # Send initial data
        try:
            stream_data = await redis_conn.xrevrange("raw_prices", count=100)
            
            raw_offers = []
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot':
                    offer = build_offer_from_redis_fields(fields)
                    if offer.get('model') and offer.get('usd_hr', 0) > 0:
                        raw_offers.append(offer)
            
            # Send synthetic data if no real data
            if not raw_offers:
                raw_offers = [
                    {
                        'model': 'A100',
                        'usd_hr': 1.229,
                        'region': 'us-east-1',
                        'availability': 8,
                        'instance_type': 'p4d.24xlarge',
                        'provider': 'aws_spot',
                        'synthetic': True,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                ]
            
            await websocket.send_text(json.dumps({
                "type": "aws_spot_update",
                "offers": raw_offers[:20],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "dataSource": "synthetic" if any(o.get('synthetic') for o in raw_offers) else "live"
            }))
            
        except Exception as e:
            logger.error(f"Error sending initial WebSocket data: {e}")
        
        # Keep connection alive with periodic updates
        while True:
            await asyncio.sleep(30)
            
            try:
                # Get latest data
                stream_data = await redis_conn.xrevrange("raw_prices", count=100)
                latest_offers = []
                
                for stream_id, fields in stream_data:
                    if fields.get('cloud') == 'aws_spot':
                        offer = build_offer_from_redis_fields(fields)
                        if offer.get('model') and offer.get('usd_hr', 0) > 0:
                            latest_offers.append(offer)
                
                # Send synthetic data if no real data
                if not latest_offers:
                    latest_offers = [
                        {
                            'model': 'A100',
                            'usd_hr': 1.229 + (len(active_connections) * 0.01),  # Slight variation
                            'region': 'us-east-1',
                            'availability': 8,
                            'instance_type': 'p4d.24xlarge',
                            'provider': 'aws_spot',
                            'synthetic': True,
                            'timestamp': datetime.now(timezone.utc).isoformat()
                        }
                    ]
                
                await websocket.send_text(json.dumps({
                    "type": "aws_spot_update",
                    "offers": latest_offers[:20],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dataSource": "synthetic" if any(o.get('synthetic') for o in latest_offers) else "live"
                }))
                
            except Exception as e:
                logger.error(f"Error sending WebSocket update: {e}")
                break
                
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info("WebSocket disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)
    finally:
        if redis_conn:
            await redis_conn.close()
        active_connections.discard(websocket)

async def broadcast_aws_spot_update(data: dict):
    """Broadcast AWS Spot updates to all connected clients"""
    if not active_connections:
        return
        
    message = json.dumps({
        "type": "aws_spot_update",
        "offers": data.get("offers", []),
        "timestamp": data.get("timestamp"),
        "dataSource": data.get("dataSource", "live")
    })
    
    # Send to all connected clients
    disconnected = set()
    for websocket in active_connections:
        try:
            await websocket.send_text(message)
        except Exception:
            disconnected.add(websocket)
    
    # Remove disconnected clients
    active_connections.difference_update(disconnected)