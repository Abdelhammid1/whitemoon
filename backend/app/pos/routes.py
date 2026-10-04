"""/pos blueprint — fast sell + batch settlement (EPIC 8).

Selling requires `pos.sell` (branch/agent staff); settlement requires
`pos.settle` (finance/admin).
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity
from pydantic import ValidationError

from ..common.errors import ApiError, BadRequest, Unauthorized
from ..identity.services.rbac import has_permission, require_permission
from .schemas import CreateSaleIn, SettleIn
from .services import pos as svc
from .services.pos import SaleLineInput

bp = Blueprint("pos", __name__, url_prefix="/pos")


def _parse(model_cls: Any) -> Any:
    try:
        return model_cls.model_validate(request.get_json(silent=True) or {})
    except ValidationError as e:
        raise BadRequest(f"Invalid payload: {e.errors()[0]['msg']}", code="validation_error") from e


def _uid() -> int:
    raw = get_jwt_identity()
    if raw is None:
        raise Unauthorized("No identity", code="no_identity")
    return int(raw)


@bp.post("/sales")
@require_permission("pos.sell")
def create_sale():
    p = _parse(CreateSaleIn)
    uid = _uid()
    # The cashier sells only from their own channel-partner location — the
    # location is never taken from the request (IDOR on stock otherwise).
    sale = svc.create_sale(
        cashier_id=uid,
        location_type="channel_partner",
        location_id=uid,
        lines=[
            SaleLineInput(product_id=li.product_id, supplier_id=li.supplier_id, qty=Decimal(str(li.qty)))
            for li in p.lines
        ],
    )
    return jsonify(svc.serialize_sale(sale)), 201


def _read_scope() -> int | None:
    """Settlers (pos.settle) see every sale; a cashier only their own."""
    uid = _uid()
    return None if has_permission(uid, "pos.settle") else uid


@bp.get("/sales/<int:sale_id>")
@require_permission("pos.sell")
def get_sale(sale_id: int):
    return jsonify(svc.serialize_sale(svc.get_sale(sale_id, only_cashier_id=_read_scope())))


@bp.get("/sales")
@require_permission("pos.sell")
def list_sales():
    posted_arg = request.args.get("posted")
    posted = None if posted_arg is None else posted_arg.lower() == "true"
    sales = svc.list_sales(posted=posted, only_cashier_id=_read_scope())
    return jsonify({"items": [svc.serialize_sale(s) for s in sales]})


@bp.post("/settle")
@require_permission("pos.settle")
def settle():
    p = _parse(SettleIn)
    batch = svc.settle_batch(posted_by=_uid(), entry_date=p.entry_date)
    return jsonify(svc.serialize_batch(batch)), 201


@bp.app_errorhandler(ApiError)
def handle_api_error(err: ApiError):
    return jsonify({"error": err.code, "message": err.message}), err.status
