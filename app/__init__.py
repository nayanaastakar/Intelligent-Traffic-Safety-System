import os
from flask import Flask, send_from_directory, abort
from app.config import Config
from app.models import db, SystemSetting, DetectionSession, Alert
from app.utils.storage import init_storage

def create_app(config_class=Config):
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static"
    )
    app.config.from_object(config_class)

    # Initialize storage directories
    init_storage()

    # Initialize extensions
    db.init_app(app)

    # Register Blueprints
    from app.routes.dashboard import bp as dashboard_bp
    from app.routes.vehicle import bp as vehicle_bp
    from app.routes.traffic import bp as traffic_bp
    from app.routes.accident import bp as accident_bp
    from app.routes.overspeed import bp as overspeed_bp
    from app.routes.drowsiness import bp as drowsiness_bp
    from app.routes.uploads import bp as uploads_bp
    from app.routes.alerts import bp as alerts_bp
    from app.routes.analytics import bp as analytics_bp
    from app.routes.history import bp as history_bp
    from app.routes.settings import bp as settings_bp
    from app.routes.about import bp as about_bp
    from app.routes.api import bp as api_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(vehicle_bp)
    app.register_blueprint(traffic_bp)
    app.register_blueprint(accident_bp)
    app.register_blueprint(overspeed_bp)
    app.register_blueprint(drowsiness_bp)
    app.register_blueprint(uploads_bp)
    app.register_blueprint(alerts_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(history_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(about_bp)
    app.register_blueprint(api_bp)

    # Controlled media serving route
    @app.route("/media/<path:filename>")
    def serve_media(filename):
        # Secure against directory traversal
        filename = filename.replace("\\", "/")
        base_dir = Config.BASE_DIR
        full_path = os.path.normpath(os.path.join(base_dir, filename))
        if not full_path.startswith(base_dir):
            abort(403)
        if not os.path.exists(full_path) or not os.path.isfile(full_path):
            abort(404)
        directory = os.path.dirname(full_path)
        fname = os.path.basename(full_path)
        return send_from_directory(directory, fname)

    # Initialize DB tables and seed if empty
    with app.app_context():
        db.create_all()
        seed_initial_data()

    return app

def seed_initial_data():
    """Seed baseline system records if newly installed."""
    if DetectionSession.query.first() is None:
        import uuid
        from datetime import datetime, timedelta
        
        # 1. Sample Vehicle detection session
        s1 = DetectionSession(
            id=uuid.uuid4().hex,
            module="vehicle",
            media_type="image",
            input_filename="sample_highway.png",
            input_path="data/sample_highway.png",
            output_path="data/sample_highway.png",
            evidence_path="data/sample_highway.png",
            status="COMPLETED",
            duration_sec=0.42,
            total_vehicles=8,
            created_at=datetime.utcnow() - timedelta(hours=3),
            completed_at=datetime.utcnow() - timedelta(hours=3) + timedelta(seconds=1)
        )
        s1.set_summary({
            "total_vehicles": 8,
            "vehicle_counts": {"car": 6, "truck": 1, "bus": 1}
        })
        db.session.add(s1)

        # 2. Sample Traffic density session
        s2 = DetectionSession(
            id=uuid.uuid4().hex,
            module="traffic",
            media_type="video",
            input_filename="sample_traffic.mp4",
            input_path="data/sample_traffic.mp4",
            output_path="data/sample_traffic.mp4",
            evidence_path="data/sample_traffic.mp4",
            status="COMPLETED",
            duration_sec=14.5,
            total_vehicles=32,
            density_level="Medium Density",
            created_at=datetime.utcnow() - timedelta(hours=2),
            completed_at=datetime.utcnow() - timedelta(hours=2) + timedelta(seconds=15)
        )
        s2.set_summary({
            "average_density": 4.25,
            "density_classification": "Medium Density",
            "vehicle_type_distribution": {"car": 24, "truck": 5, "bus": 3}
        })
        db.session.add(s2)

        # 3. Sample Overspeed alert
        s3 = DetectionSession(
            id=uuid.uuid4().hex,
            module="overspeed",
            media_type="image",
            input_filename="sample_car.png",
            input_path="data/sample_car.png",
            output_path="data/sample_car.png",
            evidence_path="data/sample_car.png",
            status="COMPLETED",
            duration_sec=0.18,
            overspeed_count=1,
            created_at=datetime.utcnow() - timedelta(minutes=45),
            completed_at=datetime.utcnow() - timedelta(minutes=45) + timedelta(seconds=1)
        )
        s3.set_summary({"speed_kmh": 85, "speed_limit_kmh": 70, "is_overspeed": True})
        db.session.add(s3)

        a1 = Alert(
            session_id=s3.id,
            alert_type="Overspeed Warning",
            severity="High",
            module="overspeed",
            description="Vehicle radar flagged 85 km/h in a 70 km/h restricted zone",
            evidence_image="data/sample_car.png",
            timestamp=datetime.utcnow() - timedelta(minutes=45),
            status="Active"
        )
        db.session.add(a1)

        db.session.commit()
