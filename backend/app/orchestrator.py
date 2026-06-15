# ============================================================
# NEXUS - TrustScore Orchestrator
# Combines all 4 analysis layers into one unified score
# This is the final decision engine of NEXUS
# ============================================================

from datetime import datetime


class TrustScoreOrchestrator:
    """
    Combines signals from all 4 NEXUS layers:
    1. Document forgery analysis
    2. Deepfake face detection
    3. Device fingerprint analysis
    4. Factory fingerprint clustering

    Returns a single TrustScore (0-100) with full explanation.
    0 = Maximum fraud risk
    100 = Fully trusted
    """

    def __init__(self):
        # Weight of each layer in final score
        self.weights = {
            "document": 0.25,
            "face": 0.25,
            "device": 0.20,
            "factory": 0.30
        }
        print("TrustScore Orchestrator ready.")

    def _calculate_trust_score(
        self,
        doc_risk: float,
        face_risk: float,
        device_risk: float,
        factory_risk: float
    ) -> float:
        """
        Calculate weighted risk score then convert to TrustScore.
        Risk score 0-1 → TrustScore 0-100 (inverted)
        """
        weighted_risk = (
            doc_risk * self.weights["document"] +
            face_risk * self.weights["face"] +
            device_risk * self.weights["device"] +
            factory_risk * self.weights["factory"]
        )

        # Convert risk to trust — higher risk = lower trust
        trust_score = round((1.0 - weighted_risk) * 100, 1)
        return max(0.0, min(100.0, trust_score))

    def _generate_explanation(
        self,
        doc_result: dict,
        face_result: dict,
        device_result: dict,
        factory_result: dict,
        trust_score: float
    ) -> list:
        """
        Generate human-readable explanation of why the score is what it is.
        This is the explainability layer — critical for compliance.
        """
        reasons = []

        # Document signals
        if doc_result:
            doc_score = doc_result.get("forgery_score", 0.0)
            if doc_score > 0.6:
                reasons.append(
                    f"HIGH document forgery risk (score: {doc_score:.2f}) — "
                    f"{doc_result.get('verdict', '')}"
                )
            elif doc_score > 0.3:
                reasons.append(
                    f"MEDIUM document anomaly detected (score: {doc_score:.2f})"
                )

            flags = doc_result.get("flags", [])
            for flag in flags:
                reasons.append(f"Document flag: {flag}")

        # Face signals
        if face_result:
            face_score = face_result.get("deepfake_score", 0.0)
            if face_score > 0.6:
                reasons.append(
                    f"HIGH deepfake probability (score: {face_score:.2f}) — "
                    f"{face_result.get('verdict', '')}"
                )
            elif face_score > 0.3:
                reasons.append(
                    f"MEDIUM face anomaly detected (score: {face_score:.2f})"
                )

        # Device signals
        if device_result:
            if device_result.get("signals", {}).get("is_emulator"):
                reasons.append("CRITICAL: Emulator detected — not a real device")

            bot_score = device_result.get("signals", {}).get("bot_risk_score", 0.0)
            if bot_score > 0.5:
                reasons.append(f"Bot behavior detected (score: {bot_score:.2f})")

            reuse = device_result.get("device_reuse", {})
            account_count = reuse.get("account_count", 0)
            if account_count >= 3:
                reasons.append(
                    f"Device shared across {account_count} accounts — "
                    f"possible device farm"
                )

        # Factory signals
        if factory_result:
            factory_id = factory_result.get("factory_id")
            if factory_id:
                cluster_size = factory_result.get("cluster_size", 0)
                similarity = factory_result.get("similarity_to_cluster", 0.0)
                reasons.append(
                    f"FACTORY MATCH: Account belongs to cluster {factory_id} "
                    f"({cluster_size} accounts, {similarity:.0%} similarity) — "
                    f"coordinated fraud ecosystem detected"
                )

            if factory_result.get("factory_alert"):
                reasons.append(
                    f"FACTORY ALERT: Cluster size {factory_result.get('cluster_size')} "
                    f"has reached alert threshold"
                )

        if not reasons:
            reasons.append("No significant fraud signals detected")

        return reasons

    def _get_action(self, trust_score: float, factory_alert: bool) -> dict:
        """
        Determine recommended action based on TrustScore.
        """
        # Factory alert overrides normal scoring
        if factory_alert:
            return {
                "action": "FREEZE",
                "reason": "Factory cluster alert — coordinated fraud ecosystem",
                "priority": "CRITICAL"
            }

        if trust_score >= 80:
            return {
                "action": "APPROVE",
                "reason": "Low risk — account appears genuine",
                "priority": "LOW"
            }
        elif trust_score >= 60:
            return {
                "action": "REVIEW",
                "reason": "Medium risk — manual review recommended",
                "priority": "MEDIUM"
            }
        elif trust_score >= 40:
            return {
                "action": "HOLD",
                "reason": "High risk — hold account pending investigation",
                "priority": "HIGH"
            }
        else:
            return {
                "action": "FREEZE",
                "reason": "Critical risk — freeze account immediately",
                "priority": "CRITICAL"
            }

    def calculate(
        self,
        account_id: str,
        doc_result: dict = None,
        face_result: dict = None,
        device_result: dict = None,
        factory_result: dict = None
    ) -> dict:
        """
        Main function — calculate TrustScore from all signals.
        """
        # Extract risk scores from each layer
        doc_risk = float(doc_result.get("forgery_score", 0.0)) if doc_result else 0.0
        face_risk = float(face_result.get("deepfake_score", 0.0)) if face_result else 0.0
        device_risk = float(device_result.get("device_risk_score", 0.0)) if device_result else 0.0
        factory_risk = float(factory_result.get("factory_risk_score", 0.0)) if factory_result else 0.0

        # Calculate TrustScore
        trust_score = self._calculate_trust_score(
            doc_risk, face_risk, device_risk, factory_risk
        )

        # Determine risk level
        if trust_score >= 80:
            risk_level = "LOW"
        elif trust_score >= 60:
            risk_level = "MEDIUM"
        elif trust_score >= 40:
            risk_level = "HIGH"
        else:
            risk_level = "CRITICAL"

        # Generate explanation
        factory_alert = factory_result.get("factory_alert", False) if factory_result else False
        explanation = self._generate_explanation(
            doc_result, face_result, device_result, factory_result, trust_score
        )

        # Get recommended action
        action = self._get_action(trust_score, factory_alert)

        return {
            "account_id": account_id,
            "trust_score": trust_score,
            "risk_level": risk_level,
            "action": action,
            "explanation": explanation,
            "signal_breakdown": {
                "document_risk": round(doc_risk, 4),
                "face_risk": round(face_risk, 4),
                "device_risk": round(device_risk, 4),
                "factory_risk": round(factory_risk, 4)
            },
            "weights_used": self.weights,
            "factory_id": factory_result.get("factory_id") if factory_result else None,
            "factory_alert": factory_alert,
            "analyzed_at": datetime.utcnow().isoformat()
        }


if __name__ == "__main__":
    print("Testing TrustScore Orchestrator...")
    orchestrator = TrustScoreOrchestrator()

    # Test 1 - Clean account
    print("\nTest 1 - Clean account:")
    result = orchestrator.calculate(
        account_id="ACC-CLEAN-001",
        doc_result={"forgery_score": 0.1, "risk_level": "LOW",
                   "verdict": "Document appears genuine", "flags": []},
        face_result={"deepfake_score": 0.05, "risk_level": "LOW",
                    "verdict": "Face appears genuine"},
        device_result={"device_risk_score": 0.0,
                      "signals": {"is_emulator": False, "bot_risk_score": 0.0},
                      "device_reuse": {"account_count": 0, "is_shared_device": False}},
        factory_result={"factory_id": None, "factory_risk_score": 0.0,
                       "factory_alert": False, "cluster_size": 1}
    )
    print(f"TrustScore: {result['trust_score']}/100")
    print(f"Action: {result['action']['action']}")
    print(f"Explanation: {result['explanation']}")

    # Test 2 - Fraud factory account
    print("\nTest 2 - Fraud factory account:")
    result2 = orchestrator.calculate(
        account_id="ACC-FRAUD-001",
        doc_result={"forgery_score": 0.85, "risk_level": "HIGH",
                   "verdict": "Document tampered", "flags": ["No EXIF", "ELA anomaly"]},
        face_result={"deepfake_score": 0.9, "risk_level": "HIGH",
                    "verdict": "AI generated face detected"},
        device_result={"device_risk_score": 0.8,
                      "signals": {"is_emulator": True, "bot_risk_score": 0.9},
                      "device_reuse": {"account_count": 15, "is_shared_device": True}},
        factory_result={"factory_id": "FF-0001", "factory_risk_score": 0.9,
                       "factory_alert": True, "cluster_size": 15,
                       "similarity_to_cluster": 0.94}
    )
    print(f"TrustScore: {result2['trust_score']}/100")
    print(f"Action: {result2['action']['action']}")
    print(f"Explanation: {result2['explanation']}")