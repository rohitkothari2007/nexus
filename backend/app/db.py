# ============================================================
# NEXUS - Database Layer
# Stores device fingerprints, analysis results, accounts
# ============================================================

from sqlalchemy import create_engine, Column, String, Float, Boolean, DateTime, Integer, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# ============================================================
# Database connection
# ============================================================

DATABASE_URL = "postgresql://postgres:nexus123@localhost:5432/nexus_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


# ============================================================
# Tables
# ============================================================

class Account(Base):
    """
    Every account analyzed by NEXUS gets stored here.
    This is the central record linking all signals together.
    """
    __tablename__ = "accounts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Risk scores
    identity_risk_score = Column(Float, default=0.0)
    device_risk_score = Column(Float, default=0.0)
    behavior_risk_score = Column(Float, default=0.0)
    final_trust_score = Column(Float, default=100.0)

    # Risk level
    risk_level = Column(String, default="LOW")
    verdict = Column(Text, default="")

    # Factory cluster
    factory_id = Column(String, nullable=True)
    factory_confidence = Column(Float, default=0.0)

    # Status
    status = Column(String, default="pending")


class DeviceRecord(Base):
    """
    Every device fingerprint collected gets stored here.
    Used to detect shared devices across multiple accounts.
    """
    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, index=True)
    account_id = Column(String, index=True)
    collected_at = Column(DateTime, default=datetime.utcnow)

    # Device details
    user_agent = Column(Text)
    screen_resolution = Column(String)
    timezone = Column(String)
    webgl_renderer = Column(Text)
    hardware_concurrency = Column(Integer)
    device_memory = Column(Integer)

    # Risk signals
    is_emulator = Column(Boolean, default=False)
    emulator_flags = Column(JSON, default=list)
    bot_risk_score = Column(Float, default=0.0)

    # How many accounts use this device
    account_count = Column(Integer, default=1)


class AnalysisResult(Base):
    """
    Stores the full analysis result for every account.
    Complete record of what every agent found.
    """
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(String, index=True)
    analyzed_at = Column(DateTime, default=datetime.utcnow)

    # Document analysis
    document_forgery_score = Column(Float, default=0.0)
    document_risk_level = Column(String, default="LOW")
    document_signals = Column(JSON, default=dict)

    # Face analysis
    face_deepfake_score = Column(Float, default=0.0)
    face_risk_level = Column(String, default="LOW")
    face_signals = Column(JSON, default=dict)

    # Device analysis
    device_id = Column(String)
    device_risk_score = Column(Float, default=0.0)
    is_emulator = Column(Boolean, default=False)

    # Behavior analysis
    bot_risk_score = Column(Float, default=0.0)
    behavior_signals = Column(JSON, default=dict)

    # Final combined score
    final_trust_score = Column(Float, default=100.0)
    risk_level = Column(String, default="LOW")
    verdict = Column(Text, default="")


def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)
    print("NEXUS database tables created successfully.")


def get_db():
    """Get database session - used by FastAPI endpoints"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================
# Quick test
# ============================================================

if __name__ == "__main__":
    print("Creating NEXUS database tables...")
    create_tables()
    print("Done.")