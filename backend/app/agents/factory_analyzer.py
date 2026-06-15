# ============================================================
# NEXUS - Factory Fingerprint Analyzer
# Phase 3 - Core Innovation
# Groups accounts by manufacturing signature
# Assigns Factory IDs to fraud ecosystems
# ============================================================

import numpy as np
import faiss
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session


class FactoryAnalyzer:
    """
    The core innovation of NEXUS.
    
    Every fake account has a manufacturing signature —
    the combined fingerprint of the tools, devices, and 
    patterns used to create it.
    
    This analyzer:
    1. Extracts a 64-dimensional fingerprint vector from account signals
    2. Compares it against all known factory fingerprints using FAISS
    3. Groups similar accounts into factory clusters
    4. Assigns Factory IDs when clusters reach threshold size
    """

    def __init__(self):
        self.vector_dim = 64
        self.similarity_threshold = 0.82
        self.cluster_min_size = 3
        self.factory_clusters = {}
        self.index = faiss.IndexFlatIP(self.vector_dim)
        self.stored_vectors = []
        self.stored_account_ids = []
        self.factory_counter = 1
        print("FactoryAnalyzer ready.")

    def _extract_document_vector(self, doc_result: dict) -> np.ndarray:
        """
        Extract 16-dimensional vector from document analysis.
        Captures the forgery style signature.
        """
        vec = np.zeros(16, dtype=np.float32)

        if not doc_result:
            return vec

        signals = doc_result.get("signals", {})

        # ELA score — forgery tool leaves specific ELA patterns
        vec[0] = float(signals.get("ela_score", 0.0))

        # Noise inconsistency — editing tool signature
        vec[1] = float(signals.get("noise_inconsistency", 0.0))

        # Edge anomaly — pasting style
        vec[2] = float(signals.get("edge_anomaly", 0.0))

        # Metadata suspicious
        vec[3] = 1.0 if signals.get("metadata_suspicious", False) else 0.0

        # Overall forgery score
        vec[4] = float(doc_result.get("forgery_score", 0.0))

        # Risk level encoded as number
        risk_map = {"LOW": 0.0, "MEDIUM": 0.5, "HIGH": 1.0}
        vec[5] = risk_map.get(doc_result.get("risk_level", "LOW"), 0.0)

        # Number of flags
        flags = doc_result.get("flags", [])
        vec[6] = min(1.0, len(flags) / 5.0)

        return vec

    def _extract_face_vector(self, face_result: dict) -> np.ndarray:
        """
        Extract 16-dimensional vector from face analysis.
        Captures the GAN/deepfake generation signature.
        """
        vec = np.zeros(16, dtype=np.float32)

        if not face_result:
            return vec

        signals = face_result.get("signals", {})

        # Neural network fake probability
        vec[0] = float(signals.get("neural_fake_probability", 0.0))

        # Frequency anomaly — GAN model family signature
        vec[1] = float(signals.get("frequency_anomaly", 0.0))

        # Geometry anomaly
        vec[2] = float(signals.get("geometry_anomaly", 0.0))

        # Overall deepfake score
        vec[3] = float(face_result.get("deepfake_score", 0.0))

        # Risk level
        risk_map = {"LOW": 0.0, "MEDIUM": 0.5, "HIGH": 1.0}
        vec[4] = risk_map.get(face_result.get("risk_level", "LOW"), 0.0)

        # Face detected
        details = face_result.get("details", {})
        geometry = details.get("geometry", {})
        vec[5] = 1.0 if geometry.get("face_detected", False) else 0.0

        # Aspect ratio — GAN faces have characteristic ratios
        vec[6] = float(geometry.get("aspect_ratio", 0.0)) / 2.0

        return vec

    def _extract_device_vector(self, device_result: dict) -> np.ndarray:
        """
        Extract 16-dimensional vector from device analysis.
        Captures the device farm signature.
        """
        vec = np.zeros(16, dtype=np.float32)

        if not device_result:
            return vec

        # Device risk score
        vec[0] = float(device_result.get("device_risk_score", 0.0))

        # Is emulator
        vec[1] = 1.0 if device_result.get("signals", {}).get("is_emulator", False) else 0.0

        # Bot risk score
        vec[2] = float(device_result.get("signals", {}).get("bot_risk_score", 0.0))

        # Number of emulator flags
        emulator_flags = device_result.get("signals", {}).get("emulator_flags", [])
        vec[3] = min(1.0, len(emulator_flags) / 5.0)

        # Device reuse count
        reuse = device_result.get("device_reuse", {})
        account_count = reuse.get("account_count", 0)
        vec[4] = min(1.0, account_count / 20.0)

        # Is shared device
        vec[5] = 1.0 if reuse.get("is_shared_device", False) else 0.0

        # Behavior signals
        behavior = device_result.get("behavior_summary", {})
        total_time = behavior.get("total_time_ms", 60000)
        # Normalize time — very fast = suspicious
        vec[6] = max(0.0, 1.0 - (total_time / 120000.0))

        # Paste count
        paste_count = behavior.get("paste_count", 0)
        vec[7] = min(1.0, paste_count / 5.0)

        return vec

    def _extract_timing_vector(self, metadata: dict) -> np.ndarray:
        """
        Extract 16-dimensional vector from timing and metadata.
        Captures the operational timing signature of the fraud factory.
        """
        vec = np.zeros(16, dtype=np.float32)

        now = datetime.utcnow()

        # Hour of day — fraud factories often work in shifts
        # Encode as circular features to handle 23->0 wrap
        hour = now.hour
        vec[0] = float(np.sin(2 * np.pi * hour / 24))
        vec[1] = float(np.cos(2 * np.pi * hour / 24))

        # Day of week
        day = now.weekday()
        vec[2] = float(np.sin(2 * np.pi * day / 7))
        vec[3] = float(np.cos(2 * np.pi * day / 7))

        # Additional metadata signals
        if metadata:
            vec[4] = float(metadata.get("forgery_score", 0.0))
            vec[5] = float(metadata.get("deepfake_score", 0.0))
            vec[6] = float(metadata.get("device_risk", 0.0))

        return vec

    def build_factory_fingerprint(
        self,
        doc_result: dict,
        face_result: dict,
        device_result: dict,
        metadata: dict = None
    ) -> np.ndarray:
        """
        Combine all vectors into one 64-dimensional factory fingerprint.
        This is the manufacturing signature of the account.
        """
        doc_vec = self._extract_document_vector(doc_result)
        face_vec = self._extract_face_vector(face_result)
        device_vec = self._extract_device_vector(device_result)
        timing_vec = self._extract_timing_vector(metadata or {})

        # Concatenate all four 16-dim vectors into one 64-dim vector
        fingerprint = np.concatenate([doc_vec, face_vec, device_vec, timing_vec])

        # Normalize to unit vector for cosine similarity
        norm = np.linalg.norm(fingerprint)
        if norm > 0:
            fingerprint = fingerprint / norm

        return fingerprint.astype(np.float32)

    def find_similar_accounts(self, fingerprint: np.ndarray, top_k: int = 10) -> list:
        """
        Search FAISS index for the most similar existing fingerprints.
        Returns list of (account_id, similarity_score) tuples.
        """
        if self.index.ntotal == 0:
            return []

        # Reshape for FAISS
        query = fingerprint.reshape(1, -1)

        # Search
        k = min(top_k, self.index.ntotal)
        similarities, indices = self.index.search(query, k)

        results = []
        for i, (sim, idx) in enumerate(zip(similarities[0], indices[0])):
            if idx >= 0 and sim > 0:
                results.append({
                    "account_id": self.stored_account_ids[idx],
                    "similarity": round(float(sim), 4)
                })

        return results

    def assign_factory_id(
        self,
        account_id: str,
        fingerprint: np.ndarray,
        similar_accounts: list
    ) -> dict:
        """
        Determine factory ID for this account.
        If similar accounts exist above threshold -> same factory.
        If not -> potential new factory or standalone account.
        """
        # Check if any similar account already has a factory ID
        existing_factory = None
        max_similarity = 0.0

        for match in similar_accounts:
            if match["similarity"] >= self.similarity_threshold:
                matched_account = match["account_id"]
                # Check if matched account is in any factory
                for factory_id, cluster in self.factory_clusters.items():
                    if matched_account in cluster["accounts"]:
                        if match["similarity"] > max_similarity:
                            max_similarity = match["similarity"]
                            existing_factory = factory_id

        if existing_factory:
            # Add to existing factory cluster
            self.factory_clusters[existing_factory]["accounts"].append(account_id)
            self.factory_clusters[existing_factory]["size"] += 1
            self.factory_clusters[existing_factory]["last_seen"] = datetime.utcnow().isoformat()

            cluster_size = self.factory_clusters[existing_factory]["size"]
            return {
                "factory_id": existing_factory,
                "is_new_factory": False,
                "cluster_size": cluster_size,
                "similarity_to_cluster": round(max_similarity, 4),
                "factory_alert": cluster_size >= 5
            }

        else:
            # Check if this account's similar matches form a new cluster
            high_similarity_matches = [
                m for m in similar_accounts
                if m["similarity"] >= self.similarity_threshold
            ]

            if len(high_similarity_matches) >= self.cluster_min_size - 1:
                # Create new factory cluster
                new_factory_id = f"FF-{self.factory_counter:04d}"
                self.factory_counter += 1

                cluster_accounts = [account_id] + [m["account_id"] for m in high_similarity_matches]

                self.factory_clusters[new_factory_id] = {
                    "factory_id": new_factory_id,
                    "accounts": cluster_accounts,
                    "size": len(cluster_accounts),
                    "created_at": datetime.utcnow().isoformat(),
                    "last_seen": datetime.utcnow().isoformat()
                }

                return {
                    "factory_id": new_factory_id,
                    "is_new_factory": True,
                    "cluster_size": len(cluster_accounts),
                    "similarity_to_cluster": round(max_similarity, 4),
                    "factory_alert": True
                }

            else:
                return {
                    "factory_id": None,
                    "is_new_factory": False,
                    "cluster_size": 1,
                    "similarity_to_cluster": round(max_similarity, 4) if similar_accounts else 0.0,
                    "factory_alert": False
                }

    def analyze(
        self,
        account_id: str,
        doc_result: dict,
        face_result: dict,
        device_result: dict
    ) -> dict:
        """
        Main function.
        Builds factory fingerprint, searches for matches,
        assigns factory ID, updates FAISS index.
        """
        # Build the 64-dim factory fingerprint
        metadata = {
            "forgery_score": doc_result.get("forgery_score", 0.0) if doc_result else 0.0,
            "deepfake_score": face_result.get("deepfake_score", 0.0) if face_result else 0.0,
            "device_risk": device_result.get("device_risk_score", 0.0) if device_result else 0.0
        }

        fingerprint = self.build_factory_fingerprint(
            doc_result, face_result, device_result, metadata
        )

        # Find similar accounts in FAISS index
        similar_accounts = self.find_similar_accounts(fingerprint)

        # Assign factory ID
        factory_result = self.assign_factory_id(
            account_id, fingerprint, similar_accounts
        )

        # Add fingerprint to FAISS index
        self.index.add(fingerprint.reshape(1, -1))
        self.stored_account_ids.append(account_id)
        self.stored_vectors.append(fingerprint)

        # Factory risk score
        factory_risk = 0.0
        if factory_result["factory_id"]:
            cluster_size = factory_result["cluster_size"]
            factory_risk = min(1.0, cluster_size / 20.0)
            if factory_result["factory_alert"]:
                factory_risk = max(factory_risk, 0.7)

        return {
            "account_id": account_id,
            "factory_fingerprint_dim": len(fingerprint),
            "factory_id": factory_result["factory_id"],
            "factory_risk_score": round(factory_risk, 4),
            "cluster_size": factory_result["cluster_size"],
            "is_new_factory": factory_result["is_new_factory"],
            "factory_alert": factory_result["factory_alert"],
            "similarity_to_cluster": factory_result["similarity_to_cluster"],
            "similar_accounts": similar_accounts[:5],
            "total_accounts_indexed": self.index.ntotal,
            "total_factory_clusters": len(self.factory_clusters)
        }

    def get_all_clusters(self) -> dict:
        """
        Returns all detected factory clusters.
        Used by dashboard to show fraud ecosystem map.
        """
        return {
            "total_clusters": len(self.factory_clusters),
            "total_accounts_indexed": self.index.ntotal,
            "clusters": list(self.factory_clusters.values())
        }


if __name__ == "__main__":
    print("Initializing FactoryAnalyzer...")
    analyzer = FactoryAnalyzer()

    # Simulate 5 accounts from same factory
    print("\nSimulating 5 accounts from same fraud factory...")

    fake_doc = {"forgery_score": 0.8, "risk_level": "HIGH",
                "signals": {"ela_score": 0.7, "noise_inconsistency": 0.8,
                           "edge_anomaly": 0.6, "metadata_suspicious": True},
                "flags": ["flag1", "flag2"]}

    fake_face = {"deepfake_score": 0.85, "risk_level": "HIGH",
                "signals": {"neural_fake_probability": 0.9,
                           "frequency_anomaly": 0.8, "geometry_anomaly": 0.3},
                "details": {"geometry": {"face_detected": True, "aspect_ratio": 1.0}}}

    fake_device = {"device_risk_score": 0.7,
                  "signals": {"is_emulator": True, "bot_risk_score": 0.8,
                             "emulator_flags": ["webdriver_detected"]},
                  "device_reuse": {"account_count": 5, "is_shared_device": True},
                  "behavior_summary": {"total_time_ms": 5000, "paste_count": 3}}

    for i in range(5):
        result = analyzer.analyze(f"ACC-{i+1:03d}", fake_doc, fake_face, fake_device)
        print(f"Account ACC-{i+1:03d}: Factory={result['factory_id']} "
              f"Cluster={result['cluster_size']} "
              f"Alert={result['factory_alert']}")

    print("\nAll clusters detected:")
    clusters = analyzer.get_all_clusters()
    print(f"Total clusters: {clusters['total_clusters']}")
    print(f"Total accounts indexed: {clusters['total_accounts_indexed']}")
    print("FactoryAnalyzer test complete.")