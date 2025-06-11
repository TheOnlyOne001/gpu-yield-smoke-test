from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio
import json
import logging
from typing import Set
import redis
import os
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter()

# Store active WebSocket connections
active_connections: Set[WebSocket] = set()

async def get_redis_connection():
    """Get async Redis connection"""
    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        raise Exception("Redis configuration missing")
    return redis.from_url(redis_url, decode_responses=True)

@router.websocket("/ws/aws-spot")
async def aws_spot_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time AWS Spot price updates"""
    await websocket.accept()
    active_connections.add(websocket)
    
    try:
        # Send initial data - fix the import issue
        try:
            # Get initial data using the same method as the REST endpoint
            redis_conn = await get_redis_connection()
            
            # Read recent AWS Spot data from Redis stream
            raw_offers = []
            stream_data = redis_conn.xrevrange("raw_prices", count=100)
            
            for stream_id, fields in stream_data:
                if fields.get('cloud') == 'aws_spot':
                    offer = {
                        'model': fields.get('gpu_model'),
                        'usd_hr': float(fields.get('price_usd_hr', 0)),
                        'region': fields.get('region'),
                        'availability': int(fields.get('availability', 1)),
                        'provider': 'aws_spot',
                        'timestamp': fields.get('iso_timestamp'),
                        'instance_type': fields.get('instance_type', ''),
                        'total_instance_price': float(fields.get('total_instance_price', 0)),
                        'gpu_memory_gb': int(fields.get('gpu_memory_gb', 16))
                    }
                    if offer['model'] and offer['usd_hr'] > 0:
                        raw_offers.append(offer)
            
            # Send initial data
            await websocket.send_text(json.dumps({
                "type": "aws_spot_update",
                "offers": raw_offers[:20],  # Limit to prevent large payloads
                "timestamp": datetime.now(timezone.utc).isoformat()
            }))
            
        except Exception as e:
            logger.error(f"Error sending initial WebSocket data: {e}")
        
        # Keep connection alive and send periodic updates
        while True:
            await asyncio.sleep(30)  # Send updates every 30 seconds
            
            try:
                # Get latest data using same method
                latest_offers = []
                stream_data = redis_conn.xrevrange("raw_prices", count=100)
                
                for stream_id, fields in stream_data:
                    if fields.get('cloud') == 'aws_spot':
                        offer = {
                            'model': fields.get('gpu_model'),
                            'usd_hr': float(fields.get('price_usd_hr', 0)),
                            'region': fields.get('region'),
                            'availability': int(fields.get('availability', 1)),
                            'provider': 'aws_spot',
                            'timestamp': fields.get('iso_timestamp'),
                            'instance_type': fields.get('instance_type', ''),
                            'total_instance_price': float(fields.get('total_instance_price', 0)),
                            'gpu_memory_gb': int(fields.get('gpu_memory_gb', 16))
                        }
                        if offer['model'] and offer['usd_hr'] > 0:
                            latest_offers.append(offer)
                
                await websocket.send_text(json.dumps({
                    "type": "aws_spot_update",
                    "offers": latest_offers[:20],
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "dataSource": "live"
                }))
                
            except Exception as e:
                logger.error(f"Error sending WebSocket update: {e}")
                break
            
    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.info("AWS Spot WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
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