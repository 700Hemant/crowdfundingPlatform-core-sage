# AI-based Smart Waste Management System (SAGE University Campus)

A complete Flask + Leaflet + SQLite application for monitoring waste on SAGE University campus using satellite-image-style detection and geospatial visualization.

## Features

- **Satellite Waste Detection Module**
  - Uploads satellite/mock images.
  - Uses an AI detector service (`WasteDetector`) that simulates YOLOv8-like outputs and can be swapped with real YOLO inference.
  - Detects and classifies: `plastic`, `organic`, `metal`, `e-waste`, `mixed`.
  - Generates annotated image with **bounding boxes** and **heatmap overlay**.

- **Map Integration (Leaflet.js)**
  - Interactive map centered around SAGE University coordinates.
  - Pins display type, confidence, priority, and detection timestamp.

- **Backend REST API (Flask)**
  - `POST /api/upload` for satellite image processing.
  - `GET /api/detections` for map/list data.
  - `GET /api/stats` for dashboard analytics.
  - `POST /api/resolve/<id>` for admin resolution.
  - `GET /api/reports/weekly` and `/api/reports/monthly` for downloadable CSV reports.

- **Staff Dashboard**
  - Login authentication (Flask-Login).
  - Live map markers.
  - Detection statistics by waste type.
  - High-priority alert panel.
  - Alert popups/messages in dashboard.

- **Smart Waste Suggestions**
  - Auto-generated disposal/recycling guidance based on waste class.
  - Color-coded suggestion/priority panel.

- **Admin Features**
  - Admin marks detections as resolved.
  - Weekly/monthly report downloads.

- **Clean Modular Structure + Detailed Comments**
  - `app/app.py` backend + routes
  - `app/waste_detector.py` AI module
  - `app/templates/*` frontend views
  - `app/static/*` responsive CSS/JS

---

## Tech Stack

- **Frontend:** HTML/CSS/JavaScript
- **Backend:** Flask (Python)
- **Database:** SQLite (via SQLAlchemy)
- **Map:** Leaflet.js + OpenStreetMap tiles
- **AI/ML:** YOLOv8-compatible architecture (mock implementation for local demo)

---

## Setup Instructions

1. **Clone and enter project**
   ```bash
   cd /workspace/crowdfundingPlatform-core-sage
   ```

2. **Create virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run server**
   ```bash
   python run.py
   ```

5. **Open browser**
   - Visit: `http://localhost:5000`

6. **Demo credentials**
   - Admin: `admin / admin123`
   - Staff: `staff / staff123`

---

## API Quick Reference

### `POST /api/upload`
Upload `multipart/form-data` with key `image`.

### `GET /api/detections`
Returns list of all detections with geolocation and metadata.

### `GET /api/stats`
Returns counts, unresolved totals, and high-priority alerts.

### `POST /api/resolve/<id>`
Admin-only endpoint for resolution workflow.

### `GET /api/reports/weekly|monthly`
Downloads CSV summaries.

---

## AI Model Design & Map Integration

### How the model works

The `WasteDetector` module currently simulates a YOLOv8-style detector pipeline:
1. Image is loaded from upload endpoint.
2. Detector returns object-level predictions with:
   - class label (`plastic`, `organic`, `metal`, `e-waste`, `mixed`)
   - confidence score
   - pixel bounding box (`x1, y1, x2, y2`)
3. Class-specific actions are mapped automatically:
   - Plastic → recycling stream
   - Organic → compost flow
   - E-waste → special disposal
4. Overlay utility draws:
   - Bounding boxes with class labels
   - Heatmap to emphasize density hotspots

### Real YOLOv8 integration path

To use a real YOLOv8 model:
- Replace `WasteDetector.detect()` with `ultralytics.YOLO` inference.
- Convert detections from pixel coordinates into geo-coordinates.
- Keep response schema unchanged, so dashboard and map continue to work.

### Map linkage

Each detection record stores latitude/longitude in SQLite.
Frontend fetches `/api/detections` and renders Leaflet markers. Clicking a marker displays:
- Waste type
- Confidence score
- Priority
- Detection timestamp

This allows operations staff to route cleanup teams efficiently.

---

## Project Structure

```
.
├── app/
│   ├── app.py
│   ├── waste_detector.py
│   ├── templates/
│   │   ├── index.html
│   │   ├── login.html
│   │   └── dashboard.html
│   ├── static/
│   │   ├── css/style.css
│   │   └── js/dashboard.js
│   ├── uploads/
│   └── reports/
├── run.py
├── requirements.txt
└── README.md
```

---

## Error Handling

- Validates missing files and invalid report periods.
- Handles unauthorized admin actions.
- Frontend displays API failures in visible alert blocks.
- Uses defensive checks before rendering map and upload actions.

