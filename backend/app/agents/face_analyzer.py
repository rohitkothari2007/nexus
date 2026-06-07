# ============================================================
# NEXUS - Face Analyzer Agent
# Phase 1 Module 2 - Deepfake Detection
# Using Hugging Face model trained specifically on deepfake data
# + Frequency domain analysis + Facial geometry
# ============================================================

import numpy as np
from PIL import Image
import io
import cv2
from transformers import pipeline


class FaceAnalyzer:
    """
    Detects AI-generated and deepfake faces.
    Three signals:
    1. Deepfake-trained classifier (Hugging Face)
    2. Frequency domain GAN artifact detection  
    3. Facial geometry consistency check
    """

    def __init__(self):
        self.classifier = self._load_model()
        print("FaceAnalyzer ready.")

    def _load_model(self):
        """
        Load deepfake detection model from Hugging Face.
        This model was specifically trained on real vs AI-generated faces.
        Not a general image classifier -- purpose-built for deepfake detection.
        """
        print("Loading deepfake detection model...")
        classifier = pipeline(
            "image-classification",
            model="dima806/deepfake_vs_real_image_detection",
            device=-1  # -1 means CPU
        )
        print("Deepfake model loaded successfully.")
        return classifier

    def _run_neural_detection(self, image: Image.Image) -> dict:
        """
        Signal 1 - Deepfake-trained Neural Network
        Model was trained specifically on real vs fake face images.
        Returns probability for REAL and FAKE classes.
        """
        # Run the classifier
        results = self.classifier(image)

        real_prob = 0.0
        fake_prob = 0.0

        for result in results:
            label = result["label"].upper()
            score = float(result["score"])
            if "REAL" in label:
                real_prob = score
            elif "FAKE" in label or "AI" in label or "DEEPFAKE" in label:
                fake_prob = score

        # If only one label returned, infer the other
        if real_prob == 0.0 and fake_prob > 0.0:
            real_prob = 1.0 - fake_prob
        elif fake_prob == 0.0 and real_prob > 0.0:
            fake_prob = 1.0 - real_prob

        return {
            "real_probability": round(real_prob, 4),
            "fake_probability": round(fake_prob, 4),
            "raw_labels": results
        }

    def _run_frequency_analysis(self, image_bytes: bytes) -> dict:
        """
        Signal 2 - Frequency Domain Analysis
        GAN-generated faces leave artifacts in high frequency bands.
        Real photos have natural frequency distributions.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return {"frequency_score": 0.0, "suspicious": False}

        # Apply Fast Fourier Transform
        fft = np.fft.fft2(img)
        fft_shift = np.fft.fftshift(fft)
        magnitude = np.log(np.abs(fft_shift) + 1)
        magnitude_norm = magnitude / magnitude.max()

        h, w = magnitude_norm.shape
        center_h, center_w = h // 2, w // 2
        radius = min(h, w) // 4

        y, x = np.ogrid[:h, :w]
        low_freq_mask = (x - center_w)**2 + (y - center_h)**2 <= radius**2
        high_freq_mask = ~low_freq_mask

        low_freq_energy = float(np.mean(magnitude_norm[low_freq_mask]))
        high_freq_energy = float(np.mean(magnitude_norm[high_freq_mask]))

        freq_ratio = high_freq_energy / (low_freq_energy + 1e-6)

        # GAN images typically have freq_ratio > 0.6
        # Real images typically between 0.3 - 0.5
        frequency_score = min(1.0, max(0.0, (freq_ratio - 0.4) / 0.4))
        suspicious = bool(frequency_score > 0.5)

        return {
            "frequency_score": round(float(frequency_score), 4),
            "freq_ratio": round(float(freq_ratio), 4),
            "suspicious": suspicious
        }

    def _check_facial_geometry(self, image_bytes: bytes) -> dict:
        """
        Signal 3 - Facial Geometry Check
        GAN faces have subtle geometric inconsistencies.
        Uses OpenCV face detector for basic geometry validation.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img is None:
            return {"face_detected": False, "geometry_score": 0.0}

        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        faces = face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
        )

        if len(faces) == 0:
            return {
                "face_detected": False,
                "geometry_score": 0.0,
                "note": "No face detected in image"
            }

        largest_face = max(faces, key=lambda f: f[2] * f[3])
        x, y, w, h = largest_face

        aspect_ratio = float(w / h)
        ratio_suspicious = bool(aspect_ratio < 0.5 or aspect_ratio > 1.1)

        img_h, img_w = img.shape[:2]
        face_coverage = float((w * h) / (img_w * img_h))
        coverage_suspicious = bool(face_coverage < 0.05 or face_coverage > 0.90)

        geometry_score = 0.0
        if ratio_suspicious:
            geometry_score += 0.4
        if coverage_suspicious:
            geometry_score += 0.3

        return {
            "face_detected": True,
            "face_count": int(len(faces)),
            "aspect_ratio": round(aspect_ratio, 3),
            "face_coverage": round(face_coverage, 3),
            "geometry_score": round(float(geometry_score), 4)
        }

    def analyze(self, image_bytes: bytes) -> dict:
        """
        Main function - combines all 3 signals.
        Neural network (deepfake-trained): 70% weight
        Frequency analysis: 20% weight
        Geometry check: 10% weight
        """
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        # Run all three detectors
        neural_result = self._run_neural_detection(image)
        frequency_result = self._run_frequency_analysis(image_bytes)
        geometry_result = self._check_facial_geometry(image_bytes)

        neural_score = float(neural_result["fake_probability"])
        freq_score = float(frequency_result["frequency_score"])
        geo_score = float(geometry_result.get("geometry_score", 0.0))

        # Neural network dominates because it's purpose-trained
        combined_score = (
            neural_score * 0.70 +
            freq_score * 0.20 +
            geo_score * 0.10
        )

        final_score = round(combined_score, 4)

        # Risk classification
        if final_score < 0.30:
            risk_level = "LOW"
            verdict = "Face appears genuine"
        elif final_score < 0.55:
            risk_level = "MEDIUM"
            verdict = "Face shows some anomalies - manual review recommended"
        else:
            risk_level = "HIGH"
            verdict = "Face shows strong signs of being AI-generated or manipulated"

        return {
            "deepfake_score": final_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "signals": {
                "neural_fake_probability": neural_score,
                "frequency_anomaly": freq_score,
                "geometry_anomaly": geo_score
            },
            "details": {
                "neural": neural_result,
                "frequency": frequency_result,
                "geometry": geometry_result
            }
        }


if __name__ == "__main__":
    print("Initializing FaceAnalyzer...")
    analyzer = FaceAnalyzer()
    print("FaceAnalyzer loaded successfully.")
    print("Ready to detect deepfakes.")