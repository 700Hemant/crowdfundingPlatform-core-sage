"""Main Flask application for AI-based Smart Waste Management System."""
from __future__ import annotations

import csv
import random
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

from flask import (
    Flask,
    Response,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

from waste_detector import WasteDetector, draw_detection_overlay

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
REPORT_DIR = BASE_DIR / "reports"
UPLOAD_DIR.mkdir(exist_ok=True)
REPORT_DIR.mkdir(exist_ok=True)

app = Flask(__name__, template_folder="templates", static_folder="static")
app.config["SECRET_KEY"] = "dev-smart-waste-secret"
app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{BASE_DIR / 'smart_waste.db'}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = "login"
detector = WasteDetector()


class User(db.Model, UserMixin):
    """Stores authenticated staff/admin users."""

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="staff")


class Detection(db.Model):
    """Stores each detected waste item and geolocation details."""

    id = db.Column(db.Integer, primary_key=True)
    image_name = db.Column(db.String(255), nullable=False)
    waste_type = db.Column(db.String(50), nullable=False)
    confidence = db.Column(db.Float, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    bbox_x1 = db.Column(db.Integer, nullable=False)
    bbox_y1 = db.Column(db.Integer, nullable=False)
    bbox_x2 = db.Column(db.Integer, nullable=False)
    bbox_y2 = db.Column(db.Integer, nullable=False)
    priority = db.Column(db.String(20), nullable=False)
    suggestion = db.Column(db.String(255), nullable=False)
    resolved = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    """Flask-Login callback to reload a user from session."""

    return db.session.get(User, int(user_id))


def initialize_defaults() -> None:
    """Initialize DB tables and default users/data at startup."""

    with app.app_context():
        db.create_all()
        if not User.query.filter_by(username="admin").first():
            db.session.add(
                User(
                    username="admin",
                    password_hash=generate_password_hash("admin123"),
                    role="admin",
                )
            )
        if not User.query.filter_by(username="staff").first():
            db.session.add(
                User(
                    username="staff",
                    password_hash=generate_password_hash("staff123"),
                    role="staff",
                )
            )
        db.session.commit()


def record_detections(image_name: str, detections: list[dict]) -> None:
    """Save detection records in database."""

    for item in detections:
        db.session.add(
            Detection(
                image_name=image_name,
                waste_type=item["waste_type"],
                confidence=item["confidence"],
                latitude=item["latitude"],
                longitude=item["longitude"],
                bbox_x1=item["bbox"][0],
                bbox_y1=item["bbox"][1],
                bbox_x2=item["bbox"][2],
                bbox_y2=item["bbox"][3],
                priority=item["priority"],
                suggestion=item["suggestion"],
            )
        )
    db.session.commit()


def detection_to_dict(item: Detection) -> dict:
    """Serialize database detection to API-friendly dict."""

    return {
        "id": item.id,
        "image_name": item.image_name,
        "waste_type": item.waste_type,
        "confidence": round(item.confidence, 3),
        "latitude": item.latitude,
        "longitude": item.longitude,
        "bbox": [item.bbox_x1, item.bbox_y1, item.bbox_x2, item.bbox_y2],
        "priority": item.priority,
        "suggestion": item.suggestion,
        "resolved": item.resolved,
        "created_at": item.created_at.isoformat(),
    }


def stats_payload() -> dict:
    """Compute dashboard statistics and alerts."""

    rows = Detection.query.order_by(Detection.created_at.desc()).all()
    type_counts = Counter(row.waste_type for row in rows)
    unresolved = [row for row in rows if not row.resolved]
    alerts = [
        {
            "id": row.id,
            "message": f"{row.waste_type.title()} detected near ({row.latitude:.5f}, {row.longitude:.5f})",
            "time": row.created_at.strftime("%Y-%m-%d %H:%M"),
            "priority": row.priority,
        }
        for row in unresolved
        if row.priority == "high"
    ]
    return {
        "total": len(rows),
        "resolved": len(rows) - len(unresolved),
        "unresolved": len(unresolved),
        "by_type": type_counts,
        "alerts": alerts,
    }


@app.route("/")
def index() -> str:
    """Public landing page redirects users appropriately."""

    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login() -> str | Response:
    """Simple login page for staff/admin accounts."""

    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            login_user(user)
            return redirect(url_for("dashboard"))
        flash("Invalid username or password", "error")
    return render_template("login.html")


@app.route("/logout")
@login_required
def logout() -> Response:
    """Logs out currently authenticated user."""

    logout_user()
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard() -> str:
    """Main staff dashboard view with map and analytics."""

    return render_template("dashboard.html", username=current_user.username, role=current_user.role)


@app.post("/api/upload")
@login_required
def upload_image() -> Response:
    """Accept satellite image upload and run AI detector."""

    if "image" not in request.files:
        return jsonify({"error": "Missing image file"}), 400

    image = request.files["image"]
    if not image.filename:
        return jsonify({"error": "No selected file"}), 400

    filename = f"{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{secure_filename(image.filename)}"
    image_path = UPLOAD_DIR / filename
    image.save(image_path)

    detections = detector.detect(image_path)
    record_detections(filename, detections)

    overlay_path = UPLOAD_DIR / f"overlay_{filename}"
    draw_detection_overlay(image_path, overlay_path, detections)

    return jsonify(
        {
            "message": "Image processed successfully",
            "detections": detections,
            "overlay_image": f"/uploads/{overlay_path.name}",
        }
    )


@app.get("/uploads/<path:file_name>")
def serve_upload(file_name: str):
    """Serve generated images for dashboard display."""

    return send_file(UPLOAD_DIR / file_name)


@app.get("/api/detections")
@login_required
def api_detections() -> Response:
    """Return all detections for map markers and table."""

    rows = Detection.query.order_by(Detection.created_at.desc()).all()
    return jsonify([detection_to_dict(row) for row in rows])


@app.get("/api/stats")
@login_required
def api_stats() -> Response:
    """Return summary statistics and high-priority alert list."""

    payload = stats_payload()
    payload["by_type"] = dict(payload["by_type"])
    return jsonify(payload)


@app.post("/api/resolve/<int:detection_id>")
@login_required
def resolve_detection(detection_id: int) -> Response:
    """Admin-only endpoint to mark a detection as resolved."""

    if current_user.role != "admin":
        return jsonify({"error": "Admin privileges required"}), 403
    detection = db.session.get(Detection, detection_id)
    if not detection:
        return jsonify({"error": "Detection not found"}), 404
    detection.resolved = True
    db.session.commit()
    return jsonify({"message": "Detection resolved"})


@app.get("/api/reports/<period>")
@login_required
def generate_report(period: str):
    """Generate CSV report for weekly or monthly summaries."""

    now = datetime.utcnow()
    if period == "weekly":
        start_date = now - timedelta(days=7)
    elif period == "monthly":
        start_date = now - timedelta(days=30)
    else:
        return jsonify({"error": "Unsupported period. Use weekly or monthly."}), 400

    rows = (
        Detection.query.filter(Detection.created_at >= start_date)
        .order_by(Detection.created_at.desc())
        .all()
    )

    report_path = REPORT_DIR / f"waste_report_{period}_{now.strftime('%Y%m%d%H%M%S')}.csv"
    with report_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(
            [
                "ID",
                "Waste Type",
                "Confidence",
                "Latitude",
                "Longitude",
                "Priority",
                "Suggestion",
                "Resolved",
                "Created At",
            ]
        )
        for row in rows:
            writer.writerow(
                [
                    row.id,
                    row.waste_type,
                    f"{row.confidence:.3f}",
                    row.latitude,
                    row.longitude,
                    row.priority,
                    row.suggestion,
                    row.resolved,
                    row.created_at.isoformat(),
                ]
            )

    return send_file(report_path, as_attachment=True)


@app.post("/api/seed-demo")
def seed_demo_data() -> Response:
    """Seed mock satellite detections to help demo quickly."""

    sample_names = ["campus_zone_a.png", "campus_zone_b.png", "campus_zone_c.png"]
    for name in sample_names:
        fake_detections = detector.generate_mock_detections(random.randint(3, 7))
        record_detections(name, fake_detections)
    return jsonify({"message": "Demo detections seeded"})


if __name__ == "__main__":
    initialize_defaults()
    app.run(host="0.0.0.0", port=5000, debug=True)
