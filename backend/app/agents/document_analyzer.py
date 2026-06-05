import numpy as np
from PIL import Image, ImageChops, ImageEnhance
import io
import os
import cv2


class DocumentAnalyzer:
    """
    NEXUS - Document Analyzer Agent
    Phase 1 - Multi-signal forgery detection
    Signals: ELA + Noise Inconsistency + Edge Sharpness + Metadata
    """

    def __init__(self):
        self.ela_quality = 90
        self.ela_amplifier = 20
        self.forgery_threshold = 0.35

    def _run_ela(self, image_bytes: bytes) -> tuple:
        """
        Signal 1 - Error Level Analysis
        Detects regions with different compression levels = edited areas
        """
        original = Image.open(io.BytesIO(image_bytes)).convert("RGB")

        buffer = io.BytesIO()
        original.save(buffer, format="JPEG", quality=self.ela_quality)
        buffer.seek(0)

        recompressed = Image.open(buffer).convert("RGB")
        diff = ImageChops.difference(original, recompressed)

        enhancer = ImageEnhance.Brightness(diff)
        ela_image = enhancer.enhance(self.ela_amplifier)

        ela_array = np.array(ela_image)
        mean_intensity = np.mean(ela_array) / 255.0
        std_intensity = np.std(ela_array) / 255.0

        forgery_score = (mean_intensity * 0.6) + (std_intensity * 0.4)

        return ela_image, round(float(forgery_score), 4)

    def _check_metadata(self, image_bytes: bytes) -> dict:
        """
        Signal 2 - Metadata Analysis
        Checks EXIF data, file size ratio, and image format
        Real ID scans have predictable metadata patterns
        """
        flags = []
        suspicious = False

        image = Image.open(io.BytesIO(image_bytes))

        # Check 1 - EXIF data presence
        exif_data = image._getexif() if hasattr(image, '_getexif') else None
        if exif_data is None:
            flags.append("No EXIF metadata found - may have been stripped by editing software")
            suspicious = True

        # Check 2 - File size vs dimensions ratio
        width, height = image.size
        file_size_kb = len(image_bytes) / 1024
        pixels = width * height
        size_ratio = file_size_kb / (pixels / 1000)

        if size_ratio < 0.3:
            flags.append(f"Unusually low file size ratio ({size_ratio:.2f}) - possible screenshot or heavy re-export")
            suspicious = True

        # Check 3 - Image format
        if image.format not in ["JPEG", "JPG", None]:
            flags.append(f"Unexpected format: {image.format} - genuine ID scans are typically JPEG")

        return {
            "suspicious": suspicious,
            "flags": flags,
            "image_size": f"{width}x{height}",
            "file_size_kb": round(file_size_kb, 2)
        }

    def _check_noise_inconsistency(self, image_bytes: bytes) -> dict:
        """
        Signal 3 - Noise Inconsistency Analysis
        Genuine scanned documents have consistent sensor noise throughout
        Edited regions have different noise patterns than surrounding areas
        High std deviation of block noise = suspicious
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return {"noise_score": 0.0, "suspicious": False}

        # Divide image into 32x32 blocks
        # Measure noise level in each block using Laplacian
        block_size = 32
        h, w = img.shape
        noise_values = []

        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = img[y:y+block_size, x:x+block_size]
                laplacian = cv2.Laplacian(block, cv2.CV_64F)
                noise_values.append(np.std(laplacian))

        if len(noise_values) < 4:
            return {"noise_score": 0.0, "suspicious": False}

        noise_array = np.array(noise_values)
        mean_noise = np.mean(noise_array)
        std_noise = np.std(noise_array)

        # High variation in noise across blocks = edited
        noise_inconsistency = min(1.0, std_noise / (mean_noise + 1e-6))
        suspicious = noise_inconsistency > 0.5

        return {
            "noise_score": round(float(noise_inconsistency), 4),
            "suspicious": suspicious
        }

    def _check_edge_sharpness(self, image_bytes: bytes) -> dict:
        """
        Signal 4 - Edge Sharpness Analysis
        Pasted or edited text creates unnaturally sharp edges
        Real scanned documents have slight blur from scanning process
        Blocks with too many sharp edges = suspicious
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)

        if img is None:
            return {"edge_score": 0.0, "suspicious": False}

        # Detect edges using Canny algorithm
        edges = cv2.Canny(img, 100, 200)

        # Measure edge density per block
        block_size = 32
        h, w = img.shape
        edge_densities = []

        for y in range(0, h - block_size, block_size):
            for x in range(0, w - block_size, block_size):
                block = edges[y:y+block_size, x:x+block_size]
                density = np.sum(block > 0) / (block_size * block_size)
                edge_densities.append(density)

        if len(edge_densities) < 4:
            return {"edge_score": 0.0, "suspicious": False}

        density_array = np.array(edge_densities)

        # Blocks with extremely high edge density = artificially inserted elements
        high_density_blocks = np.sum(density_array > 0.3)
        total_blocks = len(density_array)
        edge_anomaly_ratio = high_density_blocks / total_blocks
        suspicious = edge_anomaly_ratio > 0.15

        return {
            "edge_score": round(float(edge_anomaly_ratio), 4),
            "suspicious": suspicious
        }

    def analyze(self, image_bytes: bytes) -> dict:
        """
        Main function - runs all 4 signals and returns combined result
        Weighted ensemble: ELA 35% + Noise 35% + Edge 20% + Metadata 10%
        """
        # Run all four detectors
        ela_image, ela_score = self._run_ela(image_bytes)
        metadata_result = self._check_metadata(image_bytes)
        noise_result = self._check_noise_inconsistency(image_bytes)
        edge_result = self._check_edge_sharpness(image_bytes)

        # Weighted combination of all signals
        combined_score = (
            ela_score * 0.35 +
            noise_result["noise_score"] * 0.35 +
            edge_result["edge_score"] * 0.20
        )

        # Metadata suspicion adds 10%
        if metadata_result["suspicious"]:
            combined_score = min(1.0, combined_score + 0.10)

        final_score = round(combined_score, 4)

        # Risk classification
        if final_score < 0.25:
            risk_level = "LOW"
            verdict = "Document appears genuine"
        elif final_score < 0.45:
            risk_level = "MEDIUM"
            verdict = "Document shows some anomalies - manual review recommended"
        else:
            risk_level = "HIGH"
            verdict = "Document shows strong signs of tampering"

        return {
            "forgery_score": final_score,
            "risk_level": risk_level,
            "verdict": verdict,
            "signals": {
                "ela_score": ela_score,
                "noise_inconsistency": noise_result["noise_score"],
                "edge_anomaly": edge_result["edge_score"],
                "metadata_suspicious": metadata_result["suspicious"]
            },
            "metadata": metadata_result,
            "flags": metadata_result["flags"]
        }


# THIS IS OUTSIDE THE CLASS - zero indentation
if __name__ == "__main__":
    print("DocumentAnalyzer loaded successfully.")
    print("Ready to analyze ID documents.")
    analyzer = DocumentAnalyzer()
    print(f"ELA Quality setting: {analyzer.ela_quality}")
    print(f"Forgery threshold: {analyzer.forgery_threshold}")
    print("All systems go.")
    