"""Request/response pydantic models for identity endpoints."""

from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, field_validator


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

    @field_validator("phone")
    @classmethod
    def _trim_phone(cls, v: str | None) -> str | None:
        return v.strip() if v else v


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
