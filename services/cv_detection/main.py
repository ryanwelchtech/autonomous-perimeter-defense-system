"""
Computer Vision Detection Service - Real-time Intrusion Detection
Uses YOLOv8 for object detection and tracking in perimeter defense scenarios.
"""

import os
import cv2
import numpy as np
import redis
import requests
import base64
from datetime import datetime
from typing import List, Dict, Optional
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
import uvicorn
import json

# Try to import ultralytics (YOLOv8)
try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not available. Using mock detection.")

app = FastAPI(title="APDS CV Detection Service", version="1.0.0")
security = HTTPBearer()

# Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
AUTH_SERVICE_URL = os.getenv("AUTH_SERVICE_URL", "http://localhost:8001")
MODEL_PATH = os.getenv("MODEL_PATH", "/app/models/yolov8n.pt")
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.5"))
DETECTION_INTERVAL = float(os.getenv("DETECTION_INTERVAL", "0.1"))

# Redis client
redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Initialize YOLO model
model = None
if YOLO_AVAILABLE and os.path.exists(MODEL_PATH):
    try:
        model = YOLO(MODEL_PATH)
        print(f"Loaded YOLO model from {MODEL_PATH}")
    except Exception as e:
        print(f"Failed to load YOLO model: {e}")
        model = None

# Detection statistics
detection_stats = {
    "total_detections": 0,
    "high_confidence_detections": 0,
    "person_detections": 0,
    "vehicle_detections": 0,
    "last_detection_time": None
}


class DetectionRequest(BaseModel):
    image_base64: str
    camera_id: str
    timestamp: Optional[datetime] = None


class DetectionResult(BaseModel):
    detection_id: str
    camera_id: str
    timestamp: datetime
    objects: List[Dict]
    confidence_scores: List[float]
    bounding_boxes: List[List[int]]
    threat_level: str  # low, medium, high, critical


class DetectionStats(BaseModel):
    total_detections: int
    high_confidence_detections: int
    person_detections: int
    vehicle_detections: int
    last_detection_time: Optional[datetime]
    model_loaded: bool


def get_service_token() -> str:
    """Get service account token from auth service."""
    try:
        response = requests.post(
            f"{AUTH_SERVICE_URL}/service-token",
            headers={"X-Service-Name": "cv-detection-service"},
            timeout=5
        )
        if response.status_code == 200:
            return response.json()["access_token"]
    except Exception as e:
        print(f"Failed to get service token: {e}")
    return None


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


def detect_objects(image: np.ndarray) -> List[Dict]:
    """Detect objects in image using YOLOv8."""
    detections = []
    
    if model is None:
        # Mock detection for testing
        return [
            {
                "class": "person",
                "confidence": 0.85,
                "bbox": [100, 100, 200, 300]
            }
        ]
    
    try:
        results = model(image, conf=CONFIDENCE_THRESHOLD, verbose=False)
        
        for result in results:
            boxes = result.boxes
            for box in boxes:
                cls_id = int(box.cls[0])
                confidence = float(box.conf[0])
                class_name = model.names[cls_id]
                
                # Get bounding box coordinates
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                
                detections.append({
                    "class": class_name,
                    "confidence": confidence,
                    "bbox": [int(x1), int(y1), int(x2), int(y2)],
                    "class_id": cls_id
                })
    except Exception as e:
        print(f"Detection error: {e}")
    
    return detections


def assess_threat_level(detections: List[Dict]) -> str:
    """Assess threat level based on detected objects."""
    if not detections:
        return "low"
    
    # Count high-confidence person detections
    person_count = sum(1 for d in detections 
                      if d["class"] == "person" and d["confidence"] > 0.7)
    
    # Count vehicle detections
    vehicle_count = sum(1 for d in detections 
                       if d["class"] in ["car", "truck", "motorcycle", "bus"] 
                       and d["confidence"] > 0.7)
    
    if person_count >= 3 or vehicle_count >= 2:
        return "critical"
    elif person_count >= 2 or vehicle_count >= 1:
        return "high"
    elif person_count >= 1:
        return "medium"
    else:
        return "low"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        redis_client.ping()
        return {
            "status": "healthy",
            "service": "cv-detection-service",
            "model_loaded": model is not None,
            "yolo_available": YOLO_AVAILABLE,
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "cv-detection-service",
            "error": str(e),
            "timestamp": datetime.utcnow().isoformat()
        }


@app.post("/detect", response_model=DetectionResult)
async def detect(
    request: DetectionRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Detect objects in image and return detection results."""
    # Verify token
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    try:
        # Decode base64 image
        image_data = base64.b64decode(request.image_base64)
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise HTTPException(status_code=400, detail="Invalid image data")
        
        # Perform detection
        detections = detect_objects(image)
        
        # Assess threat level
        threat_level = assess_threat_level(detections)
        
        # Update statistics
        detection_stats["total_detections"] += len(detections)
        if any(d["confidence"] > 0.7 for d in detections):
            detection_stats["high_confidence_detections"] += 1
        
        person_count = sum(1 for d in detections if d["class"] == "person")
        vehicle_count = sum(1 for d in detections 
                           if d["class"] in ["car", "truck", "motorcycle", "bus"])
        
        detection_stats["person_detections"] += person_count
        detection_stats["vehicle_detections"] += vehicle_count
        detection_stats["last_detection_time"] = datetime.utcnow()
        
        # Generate detection ID
        detection_id = f"det_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
        
        # Store in Redis for ML classification service
        detection_data = {
            "detection_id": detection_id,
            "camera_id": request.camera_id,
            "timestamp": datetime.utcnow().isoformat(),
            "detections": detections,
            "threat_level": threat_level
        }
        redis_client.lpush("detections:queue", json.dumps(detection_data))
        redis_client.setex(f"detection:{detection_id}", 3600, json.dumps(detection_data))
        
        return DetectionResult(
            detection_id=detection_id,
            camera_id=request.camera_id,
            timestamp=request.timestamp or datetime.utcnow(),
            objects=[d["class"] for d in detections],
            confidence_scores=[d["confidence"] for d in detections],
            bounding_boxes=[d["bbox"] for d in detections],
            threat_level=threat_level
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Detection failed: {str(e)}")


@app.get("/stats", response_model=DetectionStats)
async def get_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get detection statistics."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return DetectionStats(
        total_detections=detection_stats["total_detections"],
        high_confidence_detections=detection_stats["high_confidence_detections"],
        person_detections=detection_stats["person_detections"],
        vehicle_detections=detection_stats["vehicle_detections"],
        last_detection_time=detection_stats["last_detection_time"],
        model_loaded=model is not None
    )


@app.post("/reset-stats")
async def reset_stats(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Reset detection statistics."""
    token = credentials.credentials
    if not verify_service_token(token):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    detection_stats.update({
        "total_detections": 0,
        "high_confidence_detections": 0,
        "person_detections": 0,
        "vehicle_detections": 0,
        "last_detection_time": None
    })
    
    return {"message": "Statistics reset successfully"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

