from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin


db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_picture = db.Column(db.String(255), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    last_login = db.Column(db.DateTime, nullable=True)
    theme = db.Column(db.String(20), default="dark")
    language = db.Column(db.String(20), default="en")
    notifications_enabled = db.Column(db.Boolean, default=True)
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    session_token = db.Column(db.String(255), nullable=True)
    session_token_expiry = db.Column(db.DateTime, nullable=True)

    scans = db.relationship(
        "ScanHistory",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    feedbacks = db.relationship(
        "Feedback",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )

    preferences = db.relationship(
        "UserPreference",
        backref="user",
        lazy=True,
        cascade="all, delete-orphan"
    )


class UserPreference(db.Model):
    __tablename__ = "user_preferences"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    health_profile_placeholder = db.Column(db.Boolean, default=True)
    scan_history_placeholder = db.Column(db.Boolean, default=True)
    ai_preferences_placeholder = db.Column(db.Boolean, default=True)


class HealthProfilePlaceholder(db.Model):
    __tablename__ = "health_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())


class ScanHistory(db.Model):
    __tablename__ = "scan_history"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    product = db.Column(
        db.String(200),
        nullable=False
    )

    prediction = db.Column(
        db.String(50),
        nullable=False
    )

    confidence = db.Column(
        db.Float,
        nullable=False
    )

    calories = db.Column(
        db.String(50),
        nullable=True
    )

    scan_date = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )


class Feedback(db.Model):
    __tablename__ = "feedback"

    id = db.Column(db.Integer, primary_key=True)

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("user.id"),
        nullable=False
    )

    rating = db.Column(
        db.Integer,
        nullable=False
    )

    comment = db.Column(
        db.Text,
        nullable=True
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )