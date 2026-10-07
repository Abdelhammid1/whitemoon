"""Request/response pydantic models for identity endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


class ChangePasswordIn(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class RegisterCustomerIn(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)

    @field_validator("phone")
    @classmethod
    def _trim_phone(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class AdminCreateUserIn(BaseModel):
    """Admin-provisioned user (T-07) — any role, created active by default."""

    kind: str = Field(pattern="^(customer|supplier|agent|branch|staff|admin)$")
    roles: list[str] = Field(min_length=1)
    phone: str | None = None
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=200)
    status: str = Field(default="active", pattern="^(active|pending|suspended)$")
    # Customer territory (T-01) — so an admin can provision an in-scope customer.
    geo_area: str | None = Field(default=None, max_length=200)

    @field_validator("phone")
    @classmethod
    def _trim_phone(cls, v: str | None) -> str | None:
        return v.strip() if v else v


class AdminUpdateUserProfileIn(BaseModel):
    """Admin edit of profile-level fields: a customer's territory (T-01) and a
    supplier's minimum order value (T-03). Only the field matching the user's
    kind is applied."""

    geo_area: str | None = Field(default=None, max_length=200)
    min_order_value: float | None = Field(default=None, ge=0)


class RegisterSupplierIn(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    password: str = Field(min_length=8, max_length=128)
    legal_name: str = Field(min_length=1, max_length=200)
    commercial_register_no: str = Field(min_length=1, max_length=60)
    tax_card_no: str = Field(min_length=1, max_length=60)
    national_id: str = Field(min_length=1, max_length=60)


class OtpVerifyIn(BaseModel):
    user_id: int
    code: str = Field(min_length=4, max_length=10)


class LoginIn(BaseModel):
    phone: str | None = None
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)
    totp_code: str | None = None


class TotpEnrollFinishIn(BaseModel):
    code: str = Field(min_length=6, max_length=10)


class ImpersonateStartIn(BaseModel):
    target_user_id: int
    reason: str = Field(min_length=5, max_length=1000)


class RejectSupplierIn(BaseModel):
    reason: str = Field(min_length=5, max_length=1000)


class AssignRoleIn(BaseModel):
    user_id: int
    role_code: str = Field(min_length=1, max_length=60)
