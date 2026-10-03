"""EPIC 7 — basic production (manufacturing orders)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app.common.errors import BadRequest, Conflict
from app.extensions import db
from app.inventory.services import products as products_svc
from app.inventory.services import stock as stock_svc
from app.production.services import production as svc
from app.production.services.production import MaterialInput
from tests.helpers import create_user


def _product(sku: str, category: str = "clothing"):
    return products_svc.create_product(
        sku=sku, name_ar="صنف", category=category, created_by=1
    )


def _owner():
    u = create_user(kind="staff", email=f"owner{uuid.uuid4().hex[:6]}@example.com", roles=("staff",))
    db.session.commit()
    return u


def _seed_stock(owner_id: int, product_id: int, qty: str):
    stock_svc.manual_adjust(
        supplier_id=owner_id,
        product_id=product_id,
        location_type="supplier",
        location_id=None,
        delta=Decimal(qty),
    )


def _mo_with_materials(owner, *, material, output, mat_qty="10", out_qty="5", unit_cost="3"):
    return svc.create_mo(
        owner_id=owner.id,
        output_product_id=output.id,
        output_qty=Decimal(out_qty),
        materials=[MaterialInput(product_id=material.id, qty=Decimal(mat_qty), unit_cost=Decimal(unit_cost))],
        stages=["قص", "خياطة", "تعبئة"],
        actor_user_id=1,
    )


def test_complete_moves_stock_and_posts_journal(client) -> None:
    owner = _owner()
    material = _product("MAT-1")
    output = _product("FIN-1")
    _seed_stock(owner.id, material.id, "100")
    mo = _mo_with_materials(owner, material=material, output=output)
    assert mo.status == "draft"
    assert mo.total_material_cost == Decimal("30.0000")  # 10 * 3

    for _ in range(3):
        svc.advance_stage(mo_id=mo.id, actor_user_id=1)

    done = svc.complete(mo_id=mo.id, posted_by=1)
    assert done.status == "completed"
    assert done.journal_entry_id is not None

    mat_bal = stock_svc.get_balance(
        supplier_id=owner.id, product_id=material.id, location_type="supplier", location_id=None
    )
    out_bal = stock_svc.get_balance(
        supplier_id=owner.id, product_id=output.id, location_type="supplier", location_id=None
    )
    assert mat_bal is not None and mat_bal.on_hand == Decimal("90.0000")  # 100 - 10
    assert out_bal is not None and out_bal.on_hand == Decimal("5.0000")


def test_cannot_complete_before_stages_done(client) -> None:
    owner = _owner()
    material = _product("MAT-2")
    output = _product("FIN-2")
    _seed_stock(owner.id, material.id, "100")
    mo = _mo_with_materials(owner, material=material, output=output)
    svc.advance_stage(mo_id=mo.id, actor_user_id=1)  # only 1 of 3
    with pytest.raises(BadRequest):
        svc.complete(mo_id=mo.id, posted_by=1)


def test_insufficient_material_blocks_completion(client) -> None:
    owner = _owner()
    material = _product("MAT-3")
    output = _product("FIN-3")
    _seed_stock(owner.id, material.id, "4")  # need 10
    mo = _mo_with_materials(owner, material=material, output=output)
    for _ in range(3):
        svc.advance_stage(mo_id=mo.id, actor_user_id=1)
    with pytest.raises(BadRequest):
        svc.complete(mo_id=mo.id, posted_by=1)


def test_double_complete_rejected(client) -> None:
    owner = _owner()
    material = _product("MAT-4")
    output = _product("FIN-4")
    _seed_stock(owner.id, material.id, "100")
    mo = _mo_with_materials(owner, material=material, output=output)
    for _ in range(3):
        svc.advance_stage(mo_id=mo.id, actor_user_id=1)
    svc.complete(mo_id=mo.id, posted_by=1)
    with pytest.raises(Conflict):
        svc.complete(mo_id=mo.id, posted_by=1)


def test_cancel_blocks_completion(client) -> None:
    owner = _owner()
    material = _product("MAT-5")
    output = _product("FIN-5")
    _seed_stock(owner.id, material.id, "100")
    mo = _mo_with_materials(owner, material=material, output=output)
    svc.cancel(mo_id=mo.id, actor_user_id=1)
    with pytest.raises(Conflict):
        svc.advance_stage(mo_id=mo.id, actor_user_id=1)
