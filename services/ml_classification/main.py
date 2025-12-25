"""
ML Threat Classification Service - Explainable AI Threat Scoring
Uses ML models to classify threats and provide explainable threat scores.
"""

import os
import json
import pickle
import numpy as np
import redis
import requests
import psycopg2
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
from psycopg2.extras import RealDictCursor

app = FastAPI(title="APDS ML Classification Service", version="1.0.0")
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
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/threat_classifier.pkl")

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# ML Model
threat_classifier = None

# Classification statistics
classification_stats = {
    "total_classifications": 0,
    "high_threat_classifications": 0,
    "critical_threat_classifications": 0,
    "average_threat_score": 0.0,
    "last_classification_time": None
}


class ThreatClassificationRequest(BaseModel):
    detection_id: str
    camera_id: str
    detections: List[Dict]
    threat_level: str
    timestamp: datetime


class ThreatScore(BaseModel):
    detection_id: str
    threat_score: float
    threat_category: str  # benign, suspicious, high_threat, critical
    confidence: float
    features: Dict[str, float]
    explanation: str
    timestamp: datetime


class ClassificationStats(BaseModel):
    total_classifications: int
    high_threat_classifications: int
    critical_threat_classifications: int
    average_threat_score: float
    last_classification_time: Optional[datetime]
    model_loaded: bool


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
            CREATE TABLE IF NOT EXISTS threat_classifications (
                id SERIAL PRIMARY KEY,
                detection_id VARCHAR(255) UNIQUE NOT NULL,
                camera_id VARCHAR(255) NOT NULL,
                threat_score FLOAT NOT NULL,
                threat_category VARCHAR(50) NOT NULL,
                confidence FLOAT NOT NULL,
                features JSONB,
                explanation TEXT,
                timestamp TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_detection_id ON threat_classifications(detection_id);
            CREATE INDEX IF NOT EXISTS idx_timestamp ON threat_classifications(timestamp);
            CREATE INDEX IF NOT EXISTS idx_threat_score ON threat_classifications(threat_score);
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")


def load_model():
    """Load ML threat classification model."""
    global threat_classifier
    
    if os.path.exists(MODEL_PATH):
        try:
            with open(MODEL_PATH, 'rb') as f:
                threat_classifier = pickle.load(f)
            print(f"Loaded threat classifier from {MODEL_PATH}")
        except Exception as e:
            print(f"Failed to load model: {e}")
            threat_classifier = None
    else:
        print(f"Model file not found at {MODEL_PATH}, using rule-based classifier")
        threat_classifier = None


def extract_features(detections: List[Dict], threat_level: str) -> Dict[str, float]:
    """Extract features from detections for ML classification."""
    features = {
        "person_count": sum(1 for d in detections if d.get("class") == "person"),
        "vehicle_count": sum(1 for d in detections 
                           if d.get("class") in ["car", "truck", "motorcycle", "bus"]),
        "average_confidence": np.mean([d.get("confidence", 0.0) for d in detections]) if detections else 0.0,
        "max_confidence": max([d.get("confidence", 0.0) for d in detections]) if detections else 0.0,
        "detection_count": len(detections),
        "threat_level_numeric": {"low": 0.25, "medium": 0.5, "high": 0.75, "critical": 1.0}.get(threat_level, 0.0)
    }
    
    # Add bounding box features
    if detections:
        bboxes = [d.get("bbox", []) for d in detections]
        areas = [(bbox[2] - bbox[0]) * (bbox[3] - bbox[1]) for bbox in bboxes if len(bbox) == 4]
        features["average_bbox_area"] = np.mean(areas) if areas else 0.0
        features["max_bbox_area"] = max(areas) if areas else 0.0
    else:
        features["average_bbox_area"] = 0.0
        features["max_bbox_area"] = 0.0
    
    return features


def classify_threat(features: Dict[str, float]) -> Dict:
    """Classify threat using ML model or rule-based approach."""
    if threat_classifier is not None:
        try:
            # Use ML model
            feature_vector = np.array([
                features["person_count"],
                features["vehicle_count"],
                features["average_confidence"],
                features["max_confidence"],
                features["detection_count"],
                features["threat_level_numeric"],
                features["average_bbox_area"],
                features["max_bbox_area"]
            ]).reshape(1, -1)
            
            threat_score = float(threat_classifier.predict_proba(feature_vector)[0][1])
            prediction = threat_classifier.predict(feature_vector)[0]
            
            threat_category = "critical" if threat_score > 0.8 else \
                            "high_threat" if threat_score > 0.6 else \
                            "suspicious" if threat_score > 0.4 else "benign"
            
            explanation = f"ML model prediction: {threat_score:.2%} threat probability based on {features['person_count']} persons, {features['vehicle_count']} vehicles, avg confidence {features['average_confidence']:.2%}"
            
        except Exception as e:
            print(f"ML classification error: {e}, using rule-based")
            threat_score, threat_category, explanation = rule_based_classify(features)
    else:
        # Rule-based classification
        threat_score, threat_category, explanation = rule_based_classify(features)
    
    return {
        "threat_score": threat_score,
        "threat_category": threat_category,
        "confidence": min(threat_score + 0.1, 1.0),
        "explanation": explanation
    }


def rule_based_classify(features: Dict[str, float]) -> tuple:
    """Rule-based threat classification."""
    person_count = features["person_count"]
    vehicle_count = features["vehicle_count"]
    avg_confidence = features["average_confidence"]
    threat_level_numeric = features["threat_level_numeric"]
    
    # Calculate threat score
    threat_score = (
        (person_count * 0.2) +
        (vehicle_count * 0.3) +
        (avg_confidence * 0.3) +
        (threat_level_numeric * 0.2)
    )
    threat_score = min(threat_score, 1.0)
    
    # Determine category
    if threat_score > 0.8:
        category = "critical"
        explanation = f"Critical threat detected: {person_count} persons, {vehicle_count} vehicles, high confidence ({avg_confidence:.2%})"
    elif threat_score > 0.6:
        category = "high_threat"
        explanation = f"High threat: {person_count} persons, {vehicle_count} vehicles detected"
    elif threat_score > 0.4:
        category = "suspicious"
        explanation = f"Suspicious activity: {person_count} persons detected"
    else:
        category = "benign"
        explanation = "Low threat level, normal activity"
    
    return threat_score, category, explanation


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


def process_detection_queue():
    """Background task to process detection queue."""
    while True:
        try:
            # Get detection from queue
            detection_json = redis_client.brpop("detections:queue", timeout=5)
            if detection_json:
                detection_data = json.loads(detection_json[1])
                
                # Extract features
                features = extract_features(
                    detection_data["detections"],
                    detection_data["threat_level"]
                )
                
                # Classify threat
                classification = classify_threat(features)
                
                # Store result
                threat_score = ThreatScore(
                    detection_id=detection_data["detection_id"],
                    threat_score=classification["threat_score"],
                    threat_category=classification["threat_category"],
                    confidence=classification["confidence"],
                    features=features,
                    explanation=classification["explanation"],
                    timestamp=datetime.fromisoformat(detection_data["timestamp"])
                )
                
                # Save to database
                save_classification(threat_score)
                
                # Update statistics
                classification_stats["total_classifications"] += 1
                if classification["threat_category"] == "high_threat":
                    classification_stats["high_threat_classifications"] += 1
                elif classification["threat_category"] == "critical":
                    classification_stats["critical_threat_classifications"] += 1
                
                # Update average
                total = classification_stats["total_classifications"]
                current_avg = classification_stats["average_threat_score"]
                classification_stats["average_threat_score"] = (
                    (current_avg * (total - 1) + classification["threat_score"]) / total
                )
                classification_stats["last_classification_time"] = datetime.utcnow()
                
                # Push to alert queue if high threat
                if classification["threat_score"] > 0.6:
                    redis_client.lpush("alerts:queue", json.dumps({
                        "detection_id": detection_data["detection_id"],
                        "threat_score": classification["threat_score"],
                        "threat_category": classification["threat_category"],
                        "explanation": classification["explanation"],
                        "timestamp": datetime.utcnow().isoformat()
                    }))
        
        except Exception as e:
            print(f"Queue processing error: {e}")
            import time
            time.sleep(1)


def save_classification(threat_score: ThreatScore):
    """Save classification to database."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO threat_classifications 
            (detection_id, camera_id, threat_score, threat_category, confidence, features, explanation, timestamp)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (detection_id) DO UPDATE SET
                threat_score = EXCLUDED.threat_score,
                threat_category = EXCLUDED.threat_category,
                confidence = EXCLUDED.confidence,
                features = EXCLUDED.features,
                explanation = EXCLUDED.explanation,
                timestamp = EXCLUDED.timestamp
        """, (
            threat_score.detection_id,
            "camera_001",  # Would come from detection data
            threat_score.threat_score,
            threat_score.threat_category,
            threat_score.confidence,
            json.dumps(threat_score.features),
            threat_score.explanation,
            threat_score.timestamp
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
    load_model()
    # Start background task for queue processing
    import asyncio
    asyncio.create_task(asyncio.to_thread(process_detection_queue))


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        conn = get_db_connection()
        conn.close()
        return {
            "status": "healthy",
            "service": "ml-classification-service",
            "model_loaded": threat_classifier is not None,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "ml-classification-service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/classify", response_model=ThreatScore)
async def classify_threat_detection(
    request: ThreatClassificationRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Classify threat from detection data."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    # Extract features
    features = extract_features(request.detections, request.threat_level)
    
    # Classify
    classification = classify_threat(features)
    
    threat_score = ThreatScore(
        detection_id=request.detection_id,
        threat_score=classification["threat_score"],
        threat_category=classification["threat_category"],
        confidence=classification["confidence"],
        features=features,
        explanation=classification["explanation"],
        timestamp=request.timestamp
    )
    
    # Save to database
    save_classification(threat_score)
    
    return threat_score


@app.get("/stats", response_model=ClassificationStats)
async def get_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get classification statistics."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return ClassificationStats(
        total_classifications=classification_stats["total_classifications"],
        high_threat_classifications=classification_stats["high_threat_classifications"],
        critical_threat_classifications=classification_stats["critical_threat_classifications"],
        average_threat_score=classification_stats["average_threat_score"],
        last_classification_time=classification_stats["last_classification_time"],
        model_loaded=threat_classifier is not None
    )


@app.get("/classifications/{detection_id}", response_model=ThreatScore)
async def get_classification(
    detection_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Get classification by detection ID."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute(
            "SELECT * FROM threat_classifications WHERE detection_id = %s",
            (detection_id,)
        )
        
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if not row:
            raise HTTPException(status_code=404, detail="Classification not found")
        
        return ThreatScore(
            detection_id=row["detection_id"],
            threat_score=float(row["threat_score"]),
            threat_category=row["threat_category"],
            confidence=float(row["confidence"]),
            features=row["features"],
            explanation=row["explanation"],
            timestamp=row["timestamp"]
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

