"""
Alert Service - Threat Alerting and Notification System
Processes high-threat classifications and generates alerts.
"""

import os
import json
import redis
import requests
import psycopg2
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
from psycopg2.extras import RealDictCursor

app = FastAPI(title="APDS Alert Service", version="1.0.0")
security = HTTPBearer()

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "apds")
POSTGRES_USER = os.getenv("POSTGRES_USER", "apds_user")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
ALERT_THRESHOLD = float(os.getenv("ALERT_THRESHOLD", "0.7"))

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Alert statistics
alert_stats = {
    "total_alerts": 0,
    "critical_alerts": 0,
    "high_threat_alerts": 0,
    "acknowledged_alerts": 0,
    "last_alert_time": None
}


class Alert(BaseModel):
    alert_id: str
    detection_id: str
    threat_score: float
    threat_category: str
    explanation: str
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    acknowledged_at: Optional[datetime] = None


class AlertStats(BaseModel):
    total_alerts: int
    critical_alerts: int
    high_threat_alerts: int
    acknowledged_alerts: int
    last_alert_time: Optional[datetime]
    active_alerts: int


def get_db_connection():
    """Get PostgreSQL database connection."""
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        database=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD
    )


def init_database():
    """Initialize database tables."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                alert_id VARCHAR(255) UNIQUE NOT NULL,
                detection_id VARCHAR(255) NOT NULL,
                threat_score FLOAT NOT NULL,
                threat_category VARCHAR(50) NOT NULL,
                explanation TEXT,
                timestamp TIMESTAMP NOT NULL,
                acknowledged BOOLEAN DEFAULT FALSE,
                acknowledged_by VARCHAR(255),
                acknowledged_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_alert_id ON alerts(alert_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON alerts(timestamp);
            CREATE INDEX IF NOT EXISTS idx_acknowledged ON alerts(acknowledged);
            CREATE INDEX IF NOT EXISTS idx_threat_category ON alerts(threat_category);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")


def verify_service_token(token: str) -> bool:
    """Verify service token with auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/validate",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )
        return response.status_code == 200 and response.json().get("valid", False)
    except Exception:
        return False


def process_alert_queue():
    """Background task to process alert queue."""
    while True:
        try:
            # Get alert from queue
            alert_json = redis_client.brpop("alerts:queue", timeout=5)
            if alert_json:
                alert_data = json.loads(alert_json[1])
                
                # Create alert
                alert_id = f"alert_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                
                alert = Alert(
                    alert_id=alert_id,
                    detection_id=alert_data["detection_id"],
                    threat_score=alert_data["threat_score"],
                    threat_category=alert_data["threat_category"],
                    explanation=alert_data["explanation"],
                    timestamp=datetime.fromisoformat(alert_data["timestamp"])
                )
                
                # Save alert
                save_alert(alert)
                
                # Update statistics
                alert_stats["total_alerts"] += 1
                if alert.threat_category == "critical":
                    alert_stats["critical_alerts"] += 1
                elif alert.threat_category == "high_threat":
                    alert_stats["high_threat_alerts"] += 1
                alert_stats["last_alert_time"] = datetime.utcnow()
                
                # Store in Redis for real-time dashboard
                redis_client.setex(
                    f"alert:{alert_id}",
                    86400,  # 24 hours
                    json.dumps(alert.dict(), default=str)
                )
                redis_client.lpush("alerts:recent", json.dumps(alert.dict(), default=str))
                redis_client.ltrim("alerts:recent", 0, 99)  # Keep last 100 alerts
        
        except Exception as e:
            print(f"Alert queue processing error: {e}")
            import time
            time.sleep(1)


def save_alert(alert: Alert):
    """Save alert to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO alerts 
            (alert_id, detection_id, threat_score, threat_category, explanation, timestamp, acknowledged)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (alert_id) DO NOTHING
        """, (
            alert.alert_id,
            alert.detection_id,
            alert.threat_score,
            alert.threat_category,
            alert.explanation,
            alert.timestamp,
            alert.acknowledged
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Database save error: {e}")


@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    init_database()
    # Start background task for queue processing
    import asyncio
    asyncio.create_task(asyncio.to_thread(process_alert_queue))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "service": "alert-service",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "alert-service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.get("/alerts", response_model=List[Alert])
async def get_alerts(
    limit: int = 100,
    acknowledged: Optional[bool] = None,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get alerts."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        query = "SELECT * FROM alerts"
        params = []
        
        if acknowledged is not None:
            query += " WHERE acknowledged = %s"
            params.append(acknowledged)
        
        query += " ORDER BY timestamp DESC LIMIT %s"
        params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        
        alerts = []
        for row in rows:
            alerts.append(Alert(
                alert_id=row["alert_id"],
                detection_id=row["detection_id"],
                threat_score=float(row["threat_score"]),
                threat_category=row["threat_category"],
                explanation=row["explanation"],
                timestamp=row["timestamp"],
                acknowledged=row["acknowledged"],
                acknowledged_by=row["acknowledged_by"],
                acknowledged_at=row["acknowledged_at"]
            ))
        
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/alerts/{alert_id}", response_model=Alert)
async def get_alert(
    alert_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get alert by ID."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("SELECT * FROM alerts WHERE alert_id = %s", (alert_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Alert not found")
        
        return Alert(
            alert_id=row["alert_id"],
            detection_id=row["detection_id"],
            threat_score=float(row["threat_score"]),
            threat_category=row["threat_category"],
            explanation=row["explanation"],
            timestamp=row["timestamp"],
            acknowledged=row["acknowledged"],
            acknowledged_by=row["acknowledged_by"],
            acknowledged_at=row["acknowledged_at"]
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(
    alert_id: str,
    username: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Acknowledge an alert."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE alerts 
            SET acknowledged = TRUE, acknowledged_by = %s, acknowledged_at = %s
            WHERE alert_id = %s AND acknowledged = FALSE
        """, (username, datetime.utcnow(), alert_id))
        
        if cursor.rowcount == 0:
            conn.rollback()
            cursor.close()
            conn.close()
            raise HTTPException(status_code=404, detail="Alert not found or already acknowledged")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        alert_stats["acknowledged_alerts"] += 1
        
        return {"message": "Alert acknowledged successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats", response_model=AlertStats)
async def get_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get alert statistics."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM alerts WHERE acknowledged = FALSE")
        active_alerts = cursor.fetchone()[0]
        cursor.close()
        conn.close()
    except Exception:
        active_alerts = 0
    
    return AlertStats(
        total_alerts=alert_stats["total_alerts"],
        critical_alerts=alert_stats["critical_alerts"],
        high_threat_alerts=alert_stats["high_threat_alerts"],
        acknowledged_alerts=alert_stats["acknowledged_alerts"],
        last_alert_time=alert_stats["last_alert_time"],
        active_alerts=active_alerts
    )


@app.get("/alerts/recent", response_model=List[Alert])
async def get_recent_alerts(
    limit: int = 20,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get recent alerts from Redis."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        alerts_json = redis_client.lrange("alerts:recent", 0, limit - 1)
        alerts = []
        for alert_json in alerts_json:
            alert_data = json.loads(alert_json)
            alert_data["timestamp"] = datetime.fromisoformat(alert_data["timestamp"])
            if alert_data.get("acknowledged_at"):
                alert_data["acknowledged_at"] = datetime.fromisoformat(alert_data["acknowledged_at"])
            alerts.append(Alert(**alert_data))
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

