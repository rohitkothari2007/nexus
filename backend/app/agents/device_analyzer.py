# ============================================================
# NEXUS - Device Analyzer Agent
# Phase 2 - Device fingerprint analysis and storage
# Detects shared devices, emulators, and bot behavior
# ============================================================

from sqlalchemy.orm import Session
from db import DeviceRecord
import hashlib
import json


class DeviceAnalyzer:
    """
    Analyzes device fingerprints.
    Stores device records in database.
    Detects when multiple accounts share the same device.
    """

    def __init__(self):
        print("DeviceAnalyzer ready.")

    def _calculate_risk_score(self, fingerprint_data: dict) -> float:
        """
        Calculate device risk score from fingerprint signals.
        """
        risk_score = 0.0
        flags = []

        # Check emulator detection
        emulator = fingerprint_data.get("emulator_detection", {})
        if emulator.get("is_emulator", False):
            risk_score += 0.5
            flags.append("emulator_detected")

        # Check bot behavior
        behavior = fingerprint_data.get("behavior", {})
        bot_risk = behavior.get("bot_risk_score", 0.0)
        risk_score += bot_risk * 0.3

        # Check for missing signals (bots often block fingerprinting)
        fp = fingerprint_data.get("fingerprint", {})
        if fp.get("canvas") == "canvas_blocked":
            risk_score += 0.1
            flags.append("canvas_blocked")
        if fp.get("webgl") == "webgl_not_supported":
            risk_score += 0.1
            flags.append("webgl_missing")
        if fp.get("audio") == "audio_blocked":
            risk_score += 0.1
            flags.append("audio_blocked")

        return min(1.0, round(risk_score, 4)), flags

    def _check_device_reuse(self, device_id: str, db: Session) -> dict:
        """
        Check how many accounts have used this device before.
        High reuse = fraud signal.
        """
        existing_records = db.query(DeviceRecord).filter(
            DeviceRecord.device_id == device_id
        ).all()

        account_count = len(existing_records)
        accounts_using_device = [r.account_id for r in existing_records]

        reuse_risk = 0.0
        if account_count >= 2:
            reuse_risk = min(1.0, account_count / 10)

        return {
            "account_count": account_count,
            "accounts_using_device": accounts_using_device,
            "reuse_risk_score": round(reuse_risk, 4),
            "is_shared_device": account_count >= 2
        }

    def analyze(self, fingerprint_data: dict, account_id: str, db: Session) -> dict:
        """
        Main function - analyze device fingerprint.
        Store in database.
        Return risk assessment.
        """
        device_id = fingerprint_data.get("device_id", "unknown")
        basic = fingerprint_data.get("fingerprint", {}).get("basic", {})
        emulator = fingerprint_data.get("emulator_detection", {})
        behavior = fingerprint_data.get("behavior", {})

        # Calculate risk score
        device_risk_score, flags = self._calculate_risk_score(fingerprint_data)

        # Check device reuse
        reuse_info = self._check_device_reuse(device_id, db)

        # Add reuse risk to total score
        final_risk_score = min(1.0, device_risk_score + reuse_info["reuse_risk_score"] * 0.5)

        # Store in database
        device_record = DeviceRecord(
            device_id=device_id,
            account_id=account_id,
            user_agent=basic.get("userAgent", ""),
            screen_resolution=basic.get("screenResolution", ""),
            timezone=basic.get("timezone", ""),
            webgl_renderer=fingerprint_data.get("fingerprint", {}).get("webgl", ""),
            hardware_concurrency=basic.get("hardwareConcurrency", 0),
            device_memory=basic.get("deviceMemory", 0),
            is_emulator=bool(emulator.get("is_emulator", False)),
            emulator_flags=emulator.get("emulator_flags", []),
            bot_risk_score=float(behavior.get("bot_risk_score", 0.0)),
            account_count=reuse_info["account_count"] + 1
        )
        db.add(device_record)
        db.commit()

        # Risk classification
        if final_risk_score < 0.25:
            risk_level = "LOW"
            verdict = "Device appears legitimate"
        elif final_risk_score < 0.50:
            risk_level = "MEDIUM"
            verdict = "Device shows some suspicious signals"
        else:
            risk_level = "HIGH"
            verdict = "Device shows strong fraud signals"

        return {
            "device_id": device_id,
            "device_risk_score": final_risk_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "signals": {
                "is_emulator": bool(emulator.get("is_emulator", False)),
                "emulator_flags": emulator.get("emulator_flags", []),
                "bot_risk_score": float(behavior.get("bot_risk_score", 0.0)),
                "blocked_signals": flags
            },
            "device_reuse": reuse_info,
            "behavior_summary": {
                "total_time_ms": behavior.get("total_time_ms", 0),
                "keystroke_count": behavior.get("keystroke_count", 0),
                "mouse_movement_count": behavior.get("mouse_movement_count", 0),
                "paste_count": behavior.get("paste_count", 0)
            }
        }


if __name__ == "__main__":
    print("DeviceAnalyzer loaded successfully.")
    analyzer = DeviceAnalyzer()
    print("All systems go.")