import json
import tempfile
import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pydantic import BaseModel

from services.ocr_service import OCRService
from services.bhunaksha_service import resolve_plot_coordinates
from services.damage_service import classify_crop_damage
from services.exif_verification_service import VideoEXIFVerificationService

app = FastAPI(
    title="ClaimKavach Vision API",
    version="1.0.0",
    description="PMFBY Agricultural Claim Verification & Spatial Assessment API"
)

# Initialize Services
ocr_service = OCRService()
video_verification_service = VideoEXIFVerificationService(max_allowed_distance_meters=150.0)

class URLVerificationRequest(BaseModel):
    media_url: str
    spatial_data: dict

# --- Root Endpoint ---
@app.get("/", tags=["Default"])
def read_root():
    return {"message": "ClaimKavach Vision API is running. Visit /docs for OpenAPI testing UI."}

# --- Deliverable #1: OCR & Cadastral Mapping ---
@app.post("/api/ocr/extract-712", tags=["OCR & Cadastral Mapping"])
async def extract_and_resolve_land_record(file: UploadFile = File(...)):
    """
    1. Runs OCR on Maharashtra 7/12 land record image using Gemini 3.6 Flash.
    2. Resolves plot spatial coordinates and boundary polygon from Bhunaksha.
    """
    try:
        contents = await file.read()
        mime_type = file.content_type or "image/jpeg"

        ocr_data = await ocr_service.extract_712_data(contents, mime_type=mime_type)
        spatial_data = resolve_plot_coordinates(ocr_data)

        return {
            "status": "success",
            "ocr_extracted": ocr_data,
            "cadastral_spatial": spatial_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Deliverable #2: Damage Classification ---
@app.post("/api/vision/classify-damage", tags=["Damage Classification"])
async def classify_damage(file: UploadFile = File(...)):
    """
    Analyzes uploaded crop damage photo evidence using Gemini 3.6 Flash.
    """
    try:
        contents = await file.read()
        mime_type = file.content_type or "image/jpeg"

        damage_report = classify_crop_damage(contents, mime_type=mime_type)

        return {
            "status": "success",
            "damage_report": damage_report
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- Deliverable #3 Option A: Direct Video/File Upload Verification ---
@app.post("/api/vision/verify-video-claim", tags=["Deliverable #3: Video & Metadata Verification"])
async def verify_video_claim(
    video_file: UploadFile = File(...),
    spatial_data_json: str = Form(...)
):
    """
    Checks uploaded video GPS metadata against Bhunaksha spatial data using Haversine distance.
    """
    try:
        plot_spatial_data = json.loads(spatial_data_json)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format for spatial_data_json.")

    suffix = os.path.splitext(video_file.filename)[1] or ".mp4"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        contents = await video_file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        verification_result = video_verification_service.verify_video_against_plot(
            video_path=tmp_path,
            plot_spatial_data=plot_spatial_data
        )
        return {
            "status": "success",
            "audit_result": verification_result
        }
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

# --- Deliverable #3 Option B: URL Metadata Verification ---
@app.post("/api/vision/verify-url-metadata", tags=["Deliverable #3: Video & Metadata Verification"])
async def verify_url_metadata(payload: URLVerificationRequest):
    """
    Extracts metadata directly from a public image/video URL and verifies plot proximity.
    """
    try:
        metadata = video_verification_service.extract_metadata_from_url(payload.media_url)
        return {
            "status": "success",
            "media_url": payload.media_url,
            "extracted_metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))