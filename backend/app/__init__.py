from __future__ import annotations

from flask import Flask, jsonify

from .common.errors import ApiError
from .config import Config, get_config
from .extensions import db, jwt, migrate


def create_app(config: Config | None = None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config or get_config())

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)

    _register_jwt_callbacks()
    _register_blueprints(app)
    _register_error_handlers(app)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "white-moon-backend"}

    return app


def _register_blueprints(app: Flask) -> None:
    # Import inside the factory so test modules can import `create_app`
    # without triggering circular model loads at import time.
    from . import models  # noqa: F401 — attach models to metadata
    from .accounting.routes import bp as accounting_bp
    from .commerce.routes import bp as commerce_bp
    from .identity.admin_routes import bp as admin_bp
    from .identity.routes import bp as auth_bp
    from .inventory.routes import bp as inventory_bp
    from .partners.routes import bp as partners_bp
    from .pos.routes import bp as pos_bp
    from .production.routes import bp as production_bp
    from .sales.routes import bp as credit_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(accounting_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(commerce_bp)
    app.register_blueprint(credit_bp)
    app.register_blueprint(partners_bp)
    app.register_blueprint(production_bp)
    app.register_blueprint(pos_bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def _api_error(err: ApiError):
        return jsonify({"error": err.code, "message": err.message}), err.status


def _register_jwt_callbacks() -> None:
    from .identity.services.auth import is_token_revoked

    @jwt.token_in_blocklist_loader
    def _check_revoked(_jwt_header, jwt_payload):  # type: ignore[no-untyped-def]
        return is_token_revoked(jwt_payload["jti"])
