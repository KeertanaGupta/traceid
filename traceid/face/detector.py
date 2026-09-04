import os
from pathlib import Path
import cv2
import insightface
from insightface.app import FaceAnalysis

_face_app: FaceAnalysis | None = None


def get_face_app() -> FaceAnalysis:
    """Lazy initialization of InsightFace FaceAnalysis instance."""
    global _face_app
    if _face_app is None:
        _face_app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        _face_app.prepare(ctx_id=0, det_size=(640, 640))
    return _face_app


def load_and_detect(image_path: str) -> dict:
    """Load an image and detect faces using InsightFace with quality checks.

    Args:
        image_path: Path to the image file.

    Returns:
        dict: {
            "face_found": bool,
            "bbox": [x1, y1, x2, y2] | None,
            "det_confidence": float,
            "quality_ok": bool,
            "quality_reasons": list[str]
        }
    """
    path_obj = Path(image_path)
    if not path_obj.exists() or not path_obj.is_file():
        return {
            "face_found": False,
            "bbox": None,
            "det_confidence": 0.0,
            "quality_ok": False,
            "quality_reasons": [f"Image file not found: {image_path}"],
        }

    img = cv2.imread(str(path_obj))
    if img is None:
        return {
            "face_found": False,
            "bbox": None,
            "det_confidence": 0.0,
            "quality_ok": False,
            "quality_reasons": [f"Failed to decode image file: {image_path}"],
        }

    app = get_face_app()
    faces = app.get(img)

    if not faces:
        return {
            "face_found": False,
            "bbox": None,
            "det_confidence": 0.0,
            "quality_ok": False,
            "quality_reasons": ["No face detected in image"],
        }

    # Select the largest face by bounding box area
    largest_face = max(
        faces,
        key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1])
    )

    x1, y1, x2, y2 = [int(round(coord)) for coord in largest_face.bbox]
    det_confidence = float(largest_face.det_score)
    width = x2 - x1
    height = y2 - y1

    quality_reasons: list[str] = []

    if det_confidence < 0.5:
        quality_reasons.append(
            f"Low detection confidence ({det_confidence:.2f} < 0.50)"
        )

    if width < 80 or height < 80:
        quality_reasons.append(
            f"Face too small in frame ({width}x{height} < 80x80 pixels)"
        )

    quality_ok = len(quality_reasons) == 0

    return {
        "face_found": True,
        "bbox": [x1, y1, x2, y2],
        "det_confidence": det_confidence,
        "quality_ok": quality_ok,
        "quality_reasons": quality_reasons,
    }
