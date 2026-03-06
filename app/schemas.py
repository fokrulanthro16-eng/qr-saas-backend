from pydantic import BaseModel, EmailStr
from typing import Optional


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class QRCreate(BaseModel):
    text: str


class QRResponse(BaseModel):
    id: int
    qr_image_url: str
    used_today: int
    is_premium: bool