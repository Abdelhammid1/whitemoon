from __future__ import annotations

from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from .common.base_model import Base

db = SQLAlchemy(model_class=Base)
migrate = Migrate()
jwt = JWTManager()
