"""/auth blueprint — register, OTP, login, logout, refresh, 2FA enrollment."""

from __future__ import annotations

from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity, jwt_required
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..extensions import db
from .models import User
from .schemas import (
    LoginIn,
    OtpVerifyIn,
    RegisterCustomerIn,
    RegisterSupplierIn,
    TotpEnrollFinishIn,
)
from .services import auth as auth_svc
from .services import totp as totp_svc

bp = Blueprint("auth", __name__, url_prefix="/auth")


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e


@bp.post("/register/customer")
def register_customer():
    payload = _parse(RegisterCustomerIn)
    result = auth_svc.register_customer(
        phone=payload.phone,
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
    )
    return jsonify(
        {
            "user_id": result.user_id,
            "status": result.status,
            "otp": {
                "channel": result.channel,
                "expires_at": result.otp_expires_at.isoformat(),
                "debug_code": result.otp_debug_code,
            },
        }
    ), 201


@bp.post("/register/supplier")
def register_supplier():
    payload = _parse(RegisterSupplierIn)
    result = auth_svc.register_supplier(
        phone=payload.phone,
        email=payload.email,
        password=payload.password,
        legal_name=payload.legal_name,
        commercial_register_no=payload.commercial_register_no,
        tax_card_no=payload.tax_card_no,
        national_id=payload.national_id,
    )
    return jsonify(
        {
            "user_id": result.user_id,
            "status": result.status,
            "otp": {
                "channel": result.channel,
                "expires_at": result.otp_expires_at.isoformat(),
                "debug_code": result.otp_debug_code,
            },
        }
    ), 201


@bp.post("/otp/verify")
def otp_verify():
    payload = _parse(OtpVerifyIn)
    user = auth_svc.verify_registration_otp(user_id=payload.user_id, code=payload.code)
    return jsonify(
        {
            "user_id": user.id,
            "status": user.status,
            "kind": user.kind,
        }
    )


@bp.post("/login")
def login():
    payload = _parse(LoginIn)
    result = auth_svc.login(
        phone=payload.phone,
        email=payload.email,
        password=payload.password,
        totp_code=payload.totp_code,
    )
    body: dict[str, Any] = {
        "user_id": result.user_id,
        "requires_2fa": result.requires_2fa,
    }
    if not result.requires_2fa:
        body["access_token"] = result.access_token
        body["refresh_token"] = result.refresh_token
    return jsonify(body)


@bp.post("/logout")
@jwt_required()
def logout():
    auth_svc.logout_current()
    return jsonify({"status": "logged_out"})


@bp.post("/refresh")
@jwt_required(refresh=True)
def refresh():
    access = auth_svc.refresh_current()
    return jsonify({"access_token": access})


@bp.get("/me")
@jwt_required()
def me():
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    user = db.session.get(User, int(raw))
    if user is None:
        raise Unauthorized("User not found", code="user_not_found")
    return jsonify(auth_svc.user_summary(user))


# ---------------------------------------------------------------- 2FA


@bp.post("/2fa/enroll/start")
@jwt_required()
def totp_enroll_start():
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    user = db.session.get(User, int(raw))
    if user is None:
        raise Unauthorized("User not found", code="user_not_found")
    enrollment = totp_svc.start_enrollment(user)
    db.session.commit()
    return jsonify(
        {
            "secret": enrollment.secret,
            "otpauth_uri": enrollment.otpauth_uri,
            "backup_codes": enrollment.backup_codes,
        }
    )


@bp.post("/2fa/enroll/finish")
@jwt_required()
def totp_enroll_finish():
    payload = _parse(TotpEnrollFinishIn)
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    user = db.session.get(User, int(raw))
    if user is None:
        raise Unauthorized("User not found", code="user_not_found")
    totp_svc.finish_enrollment(user, payload.code)
    return jsonify({"status": "enrolled"})


# ---------------------------------------------------------------- errors


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status
