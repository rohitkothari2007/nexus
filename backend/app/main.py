# ============================================================
# NEXUS - Main API Server
# Complete fraud intelligence platform
# Phase 1: Identity Intelligence
# Phase 2: Device & Behavioral Intelligence
# Phase 3: Factory Fingerprinting + TrustScore
# ============================================================

from fastapi import FastAPI, File, UploadFile, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from agents.document_analyzer import DocumentAnalyzer
from agents.face_analyzer import FaceAnalyzer
from agents.device_analyzer import DeviceAnalyzer
from agents.factory_analyzer import FactoryAnalyzer
from orchestrator import TrustScoreOrchestrator
from db import get_db, create_tables
from sqlalchemy.orm import Session
from typing import Optional
import uvicorn
import uuid

# ============================================================
# Initialize the app
# ============================================================

app = FastAPI(
    title="NEXUS Fraud Intelligence API",
    description="Autonomous fraud detection for financial institutions",
    version="0.3.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize all modules once on startup
document_analyzer = DocumentAnalyzer()
face_analyzer = FaceAnalyzer()
device_analyzer = DeviceAnalyzer()
factory_analyzer = FactoryAnalyzer()
orchestrator = TrustScoreOrchestrator()

# Create database tables
create_tables()


# ============================================================
# Routes
# ============================================================

@app.get("/")
def root():
    return {
        "system": "NEXUS Fraud Intelligence Platform",
        "version": "0.3.0",
        "status": "online",
        "modules": {
            "document_analyzer": "active",
            "face_analyzer": "active",
            "device_analyzer": "active",
            "factory_analyzer": "active",
            "trust_score_orchestrator": "active"
        },
        "endpoints": {
            "full_analysis": "/analyze/full",
            "document_only": "/analyze/document",
            "face_only": "/analyze/face",
            "device_only": "/analyze/device",
            "factory_clusters": "/factory/clusters"
        }
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "accounts_indexed": factory_analyzer.index.ntotal,
        "factory_clusters": len(factory_analyzer.factory_clusters)
    }


# ============================================================
# MAIN ENDPOINT - Full Analysis
# Runs all 4 modules + TrustScore in one call
# This is the primary endpoint for account onboarding
# ============================================================

@app.post("/analyze/full")
async def analyze_full(
    document: UploadFile = File(...),
    face: UploadFile = File(...),
    account_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    THE MAIN NEXUS ENDPOINT.
    Accepts ID document + selfie.
    Runs all 4 analysis modules.
    Returns complete TrustScore with full explanation.
    This is what banks integrate into their onboarding flow.
    """

    # Generate account ID if not provided
    if not account_id:
        account_id = f"ACC-{str(uuid.uuid4())[:8].upper()}"

    allowed_types = ["image/jpeg", "image/jpg", "image/png"]

    if document.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid document file type.")
    if face.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid face file type.")

    document_bytes = await document.read()
    face_bytes = await face.read()

    # Run all modules
    try:
        # Layer 1 - Document analysis
        doc_result = document_analyzer.analyze(document_bytes)

        # Layer 2 - Face analysis
        face_result = face_analyzer.analyze(face_bytes)

        # Layer 3 - Factory fingerprinting
        # Uses document + face results as input
        factory_result = factory_analyzer.analyze(
            account_id=account_id,
            doc_result=doc_result,
            face_result=face_result,
            device_result=None
        )

        # Layer 4 - TrustScore
        trust_result = orchestrator.calculate(
            account_id=account_id,
            doc_result=doc_result,
            face_result=face_result,
            device_result=None,
            factory_result=factory_result
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

    return {
        "account_id": account_id,
        "trust_score": trust_result["trust_score"],
        "risk_level": trust_result["risk_level"],
        "action": trust_result["action"],
        "explanation": trust_result["explanation"],
        "signal_breakdown": trust_result["signal_breakdown"],
        "factory": {
            "factory_id": factory_result["factory_id"],
            "factory_alert": factory_result["factory_alert"],
            "cluster_size": factory_result["cluster_size"],
            "total_clusters": factory_result["total_factory_clusters"]
        },
        "detailed_results": {
            "document": doc_result,
            "face": face_result,
            "factory": factory_result
        },
        "files": {
            "document": document.filename,
            "face": face.filename
        }
    }


# ============================================================
# Individual module endpoints
# ============================================================

@app.post("/analyze/document")
async def analyze_document(file: UploadFile = File(...)):
    """Analyze ID document for forgery"""
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large.")

    try:
        result = document_analyzer.analyze(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    result["filename"] = file.filename
    return result


@app.post("/analyze/face")
async def analyze_face(file: UploadFile = File(...)):
    """Analyze face/selfie for deepfake"""
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(status_code=400, detail="Invalid file type.")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large.")

    try:
        result = face_analyzer.analyze(image_bytes)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

    result["filename"] = file.filename
    return result


@app.post("/analyze/device")
async def analyze_device(
    fingerprint: dict,
    account_id: str = "anonymous",
    db: Session = Depends(get_db)
):
    """Analyze device fingerprint from JS SDK"""
    try:
        result = device_analyzer.analyze(fingerprint, account_id, db)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Device analysis failed: {str(e)}")
    return result


# ============================================================
# Factory Intelligence endpoints
# ============================================================

@app.get("/factory/clusters")
def get_factory_clusters():
    """
    Returns all detected factory clusters.
    Shows the fraud ecosystem map.
    """
    return factory_analyzer.get_all_clusters()


@app.get("/factory/stats")
def get_factory_stats():
    """
    Returns factory detection statistics.
    """
    clusters = factory_analyzer.factory_clusters
    total_accounts_in_clusters = sum(
        c["size"] for c in clusters.values()
    )

    return {
        "total_clusters": len(clusters),
        "total_accounts_indexed": factory_analyzer.index.ntotal,
        "total_accounts_in_clusters": total_accounts_in_clusters,
        "largest_cluster": max(
            (c["size"] for c in clusters.values()), default=0
        ),
        "clusters": [
            {
                "factory_id": c["factory_id"],
                "size": c["size"],
                "created_at": c["created_at"]
            }
            for c in clusters.values()
        ]
    }


# ============================================================
# Run server
# ============================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)