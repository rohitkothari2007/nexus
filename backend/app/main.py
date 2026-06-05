# ============================================================
# NEXUS - Main API Server
# Phase 1 - Identity Analysis Endpoint
# ============================================================

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agents.document_analyzer import DocumentAnalyzer
import uvicorn

# ============================================================
# Initialize the app
# ============================================================

app = FastAPI(
    title="NEXUS Fraud Intelligence API",
    description="Autonomous fraud detection for financial institutions",
    version="0.1.0"
)

# Allow frontend to talk to this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize our analyzer once when server starts
document_analyzer = DocumentAnalyzer()


# ============================================================
# Routes
# ============================================================

@app.get("/")
def root():
    return {
        "system": "NEXUS Fraud Intelligence Platform",
        "version": "0.1.0",
        "status": "online",
        "phase": "1 - Identity Intelligence"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/analyze/document")
async def analyze_document(file: UploadFile = File(...)):
    """
    Accepts an ID document image.
    Returns forgery score, risk level, and detailed analysis.
    """

    # Check file is an image
    allowed_types = ["image/jpeg", "image/jpg", "image/png"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Only JPEG and PNG allowed."
        )

    # Check file size - max 10MB
    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail="File too large. Maximum size is 10MB."
        )

    # Run analysis
    try:
        result = document_analyzer.analyze(image_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

    # Add filename to result
    result["filename"] = file.filename

    return result


# ============================================================
# Run server
# ============================================================

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)