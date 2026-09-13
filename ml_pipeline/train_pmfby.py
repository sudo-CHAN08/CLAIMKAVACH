import os
from pathlib import Path
from ultralytics import YOLO

# Resolve absolute path to dataset
SCRIPT_DIR = Path(__file__).resolve().parent
DATASET_PATH = SCRIPT_DIR / "dataset"

print(f"Loading dataset from: {DATASET_PATH}")

# Load base classification model
model = YOLO("yolov8n-cls.pt")

# Train fine-tuned classifier on Apple Silicon MPS
results = model.train(
    data=str(DATASET_PATH),
    epochs=25,
    imgsz=224,
    batch=32,
    device="mps"
)

print("\nTraining complete! Weights saved to runs/classify/train/weights/best.pt")
