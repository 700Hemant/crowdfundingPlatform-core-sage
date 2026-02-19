"""AI waste detection module.

This module provides a lightweight simulation of a YOLOv8-style detector so the
system can run in local environments without GPU-heavy dependencies. The API
shape mirrors a real detector and can be swapped with a true model later.
"""
from __future__ import annotations

import random
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from PIL import Image


class WasteDetector:
    """Mock detector that produces realistic campus geotagged detections."""

    # Map each class to suggestion and display color used by UI/overlay.
    WASTE_RULES = {
        "plastic": {
            "suggestion": "Send to plastic recycling stream.",
            "priority": "medium",
            "color": "#2E86DE",
        },
        "organic": {
            "suggestion": "Transfer to campus compost unit.",
            "priority": "low",
            "color": "#27AE60",
        },
        "metal": {
            "suggestion": "Collect for metal recovery and recycling.",
            "priority": "medium",
            "color": "#7F8C8D",
        },
        "e-waste": {
            "suggestion": "Handle with certified e-waste disposal vendor.",
            "priority": "high",
            "color": "#8E44AD",
        },
        "mixed": {
            "suggestion": "Segregate manually at waste sorting facility.",
            "priority": "high",
            "color": "#E67E22",
        },
    }

    def __init__(self) -> None:
        # SAGE University Bhopal-like coordinates used for map marker simulation.
        self.base_lat = 23.2114
        self.base_lon = 77.4341

    def detect(self, image_path: Path) -> list[dict]:
        """Run detection on image and return predicted objects.

        In production this method can be replaced with YOLOv8 inference:
        1) Load model weights.
        2) Run inference on satellite tiles.
        3) Convert pixel results to geographic coordinates.
        """

        image = Image.open(image_path)
        width, height = image.size
        # Simulate 3-8 detections depending on image dimensions.
        detection_count = max(3, min(8, (width * height) // 150000))
        return self.generate_mock_detections(detection_count, width, height)

    def generate_mock_detections(
        self, count: int, width: int = 1024, height: int = 768
    ) -> list[dict]:
        """Generate mock detections with bounding boxes and campus coordinates."""

        classes = list(self.WASTE_RULES.keys())
        detections: list[dict] = []

        for _ in range(count):
            waste_type = random.choice(classes)
            conf = round(random.uniform(0.62, 0.98), 3)
            box_w = random.randint(40, 140)
            box_h = random.randint(40, 140)
            x1 = random.randint(0, max(0, width - box_w - 1))
            y1 = random.randint(0, max(0, height - box_h - 1))
            x2 = x1 + box_w
            y2 = y1 + box_h

            lat_offset = random.uniform(-0.006, 0.006)
            lon_offset = random.uniform(-0.006, 0.006)
            rule = self.WASTE_RULES[waste_type]

            detections.append(
                {
                    "waste_type": waste_type,
                    "confidence": conf,
                    "bbox": [x1, y1, x2, y2],
                    "latitude": round(self.base_lat + lat_offset, 6),
                    "longitude": round(self.base_lon + lon_offset, 6),
                    "priority": rule["priority"],
                    "suggestion": rule["suggestion"],
                    "color": rule["color"],
                    "detected_at": "auto",
                }
            )
        return detections


def draw_detection_overlay(image_path: Path, output_path: Path, detections: list[dict]) -> None:
    """Draw YOLO-style boxes and heatmap overlay onto a satellite image."""

    image = Image.open(image_path).convert("RGB")
    image_array = np.array(image)
    height, width = image_array.shape[:2]

    # Create heatmap based on detection centroid density.
    heatmap = np.zeros((height, width), dtype=np.float32)
    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        cx = int((x1 + x2) / 2)
        cy = int((y1 + y2) / 2)
        radius = 30
        y_min = max(0, cy - radius)
        y_max = min(height, cy + radius)
        x_min = max(0, cx - radius)
        x_max = min(width, cx + radius)
        heatmap[y_min:y_max, x_min:x_max] += 1.0

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.imshow(image_array)

    if heatmap.max() > 0:
        ax.imshow(heatmap, cmap="jet", alpha=0.35)

    for d in detections:
        x1, y1, x2, y2 = d["bbox"]
        rect = plt.Rectangle(
            (x1, y1),
            x2 - x1,
            y2 - y1,
            fill=False,
            edgecolor=d["color"],
            linewidth=2,
        )
        ax.add_patch(rect)
        ax.text(
            x1,
            max(0, y1 - 8),
            f"{d['waste_type']} {d['confidence']:.2f}",
            color="white",
            fontsize=9,
            bbox={"facecolor": d["color"], "alpha": 0.8, "pad": 2},
        )

    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)
