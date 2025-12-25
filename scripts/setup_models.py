"""
Setup script to download and prepare ML models for APDS.
"""

import os
import urllib.request
from pathlib import Path

MODELS_DIR = Path("models")
MODELS_DIR.mkdir(exist_ok=True)

# YOLOv8 model URL (nano version for faster inference)
YOLO_MODEL_URL = "https://github.com/ultralytics/assets/releases/download/v0.0.0/yolov8n.pt"
YOLO_MODEL_PATH = MODELS_DIR / "yolov8n.pt"

# Create a simple threat classifier model placeholder
# In production, this would be trained on real threat data
THREAT_CLASSIFIER_PATH = MODELS_DIR / "threat_classifier.pkl"


def download_yolo_model():
    """Download YOLOv8 nano model."""
    if YOLO_MODEL_PATH.exists():
        print(f"YOLO model already exists at {YOLO_MODEL_PATH}")
        return
    
    print(f"Downloading YOLOv8 model from {YOLO_MODEL_URL}...")
    try:
        urllib.request.urlretrieve(YOLO_MODEL_URL, YOLO_MODEL_PATH)
        print(f"✓ YOLO model downloaded to {YOLO_MODEL_PATH}")
    except Exception as e:
        print(f"✗ Failed to download YOLO model: {e}")
        print("The CV detection service will use mock detection mode.")


def create_threat_classifier_placeholder():
    """Create a placeholder threat classifier model."""
    if THREAT_CLASSIFIER_PATH.exists():
        print(f"Threat classifier already exists at {THREAT_CLASSIFIER_PATH}")
        return
    
    print("Creating placeholder threat classifier...")
    print("Note: In production, train this model on real threat detection data.")
    
    # Create a simple placeholder file
    # In production, this would be a trained scikit-learn model
    with open(THREAT_CLASSIFIER_PATH, "w") as f:
        f.write("# Placeholder threat classifier model\n")
        f.write("# Replace with trained scikit-learn model in production\n")
    
    print(f"✓ Placeholder created at {THREAT_CLASSIFIER_PATH}")


if __name__ == "__main__":
    print("Setting up APDS models...")
    print(f"Models directory: {MODELS_DIR.absolute()}\n")
    
    download_yolo_model()
    create_threat_classifier_placeholder()
    
    print("\n✓ Model setup complete!")
    print("\nNote: The ML classification service will use rule-based classification")
    print("until a trained model is provided.")

