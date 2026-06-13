# ============================================================
# NEXUS - Main API Server
# Phase 1 - Identity Analysis Endpoints
# Phase 2 - Device & Behavioral Intelligence
# ============================================================

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from agents.document_analyzer import DocumentAnalyzer
from agents.face_analyzer import FaceAnalyzer
from agents.device_analyzer import DeviceAnalyzer
from db import get_db, create_tables
from sqlalchemy.orm import Session
import uvicorn

# ============================================================
# Initialize the app
# ============================================================

app = FastAPI(
    title="NEXUS Fraud Intelligence API",
    description="Autonomous fraud detection for financial institutions",
    version="0.2.0"
)

# Allow frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize analyzers once when server starts
document_analyzer = DocumentAnalyzer()
face_analyzer = FaceAnalyzer()
device_analyzer = DeviceAnalyzer()

# Create database tables on startup
create_tables()


# ============================================================
# Routes
# ============================================================

@app.get("/")
def root():
    return {
        "system": "NEXUS Fraud Intelligence Platform",
        "version": "0.2.0",
        "status": "online",
        "modules": {
            "document_analyzer": "active",
            "face_analyzer": "active",
            "device_analyzer": "active"
        }
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# ============================================================
# Module 1 - Document Forgery Detection
# ============================================================

@app.post("/analyze/document")
async def analyze_document(file: UploadFile = File(...)):
    """
    Accepts an ID document image.
    Returns forgery score, risk level, and detailed analysis.
    Signals: ELA + Noise Inconsistency + Edge Sharpness + Metadata
    """
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only JPEG and PNG allowed."
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    try:
        result = document_analyzer.analyze(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

    result["filename"] = file.filename
    return result


# ============================================================
# Module 2 - Deepfake Face Detection
# ============================================================

@app.post("/analyze/face")
async def analyze_face(file: UploadFile = File(...)):
    """
    Accepts a face or selfie image.
    Returns deepfake score, risk level, and signal breakdown.
    Signals: Deepfake-trained neural net + Frequency analysis + Facial geometry
    """
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Only JPEG and PNG allowed."
        )

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum 10MB."
        )

    try:
        result = face_analyzer.analyze(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

    result["filename"] = file.filename
    return result


# ============================================================
# Module 3 - Combined Identity Analysis (Document + Face)
# ============================================================

@app.post("/analyze/identity")
async def analyze_identity(
    document: UploadFile = File(...),
    face: UploadFile = File(...)
):
    """
    Accepts both an ID document AND a face image together.
    Returns a combined identity risk score.
    This is the main endpoint used during account onboarding.
    """
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]

    if document.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid document file type.")
    if face.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid face file type.")

    document_bytes = await document.read()
    face_bytes = await face.read()

    try:
        doc_result = document_analyzer.analyze(document_bytes)
        face_result = face_analyzer.analyze(face_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    doc_score = doc_result["forgery_score"]
    face_score = face_result["deepfake_score"]

    combined_identity_score = round(
        (doc_score * 0.50) + (face_score * 0.50), 4
    )

    if combined_identity_score < 0.25:
        risk_level = "LOW"
        verdict = "Identity appears genuine"
    elif combined_identity_score < 0.45:
        risk_level = "MEDIUM"
        verdict = "Identity shows anomalies - manual review recommended"
    else:
        risk_level = "HIGH"
        verdict = "Identity shows strong signs of fraud"

    return {
        "identity_risk_score": combined_identity_score,
        "risk_level": risk_level,
        "verdict": verdict,
        "document_analysis": doc_result,
        "face_analysis": face_result,
        "files": {
            "document": document.filename,
            "face": face.filename
        }
    }


# ============================================================
# Module 4 - Device & Behavioral Intelligence
# ============================================================

@app.post("/analyze/device")
async def analyze_device(
    fingerprint: dict,
    account_id: str = "anonymous",
    db: Session = Depends(get_db)
):
    """
    Accepts device fingerprint from the JS SDK.
    Stores in database and returns risk assessment.
    Detects emulators, bots, and shared devices.
    """
    try:
        result = device_analyzer.analyze(fingerprint, account_id, db)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Device analysis failed: {str(e)}"
        )
    return result


# ============================================================
# Run server
# ============================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)