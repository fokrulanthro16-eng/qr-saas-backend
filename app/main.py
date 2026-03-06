import os
import uuid
from datetime import datetime, date

import qrcode
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import text as sql_text

from .db import engine, Base, get_db
from . import models, schemas
from .auth import hash_password, verify_password, create_access_token, get_current_user

FREE_DAILY_LIMIT = 20

app = FastAPI(title="QR SaaS API", version="1.0.0")

# ✅ CORS (dev + deploy)
# Deploy করলে allow_origins এ তোমার frontend domain add করবে
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)


@app.get("/")
def root():
    return {"message": "QR SaaS API running", "free_daily_limit": FREE_DAILY_LIMIT}


@app.get("/debug/db")
def debug_db(db: Session = Depends(get_db)):
    one = db.execute(sql_text("SELECT 1")).scalar()
    return {"db_ok": True, "select_1": one}


@app.post("/auth/register")
def register(payload: schemas.RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(models.User).filter(models.User.email == payload.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    user = models.User(
        email=payload.email.strip().lower(),
        password_hash=hash_password(payload.password),
        is_premium=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"message": "registered", "is_premium": user.is_premium}


@app.post("/auth/login", response_model=schemas.TokenResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    # ✅ IMPORTANT FIX: create_access_token এখন user_id নেয় (dict না)
    token = create_access_token(user.id)
    return schemas.TokenResponse(access_token=token, token_type="bearer")


def _used_today(db: Session, user_id: int) -> int:
    today = date.today()
    rows = db.query(models.QRCode).filter(models.QRCode.user_id == user_id).all()
    return sum(1 for r in rows if r.created_at.date() == today)


@app.post("/qr/generate", response_model=schemas.QRResponse)
def generate_qr(
    payload: schemas.QRCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    used = _used_today(db, current_user.id)
    if (not current_user.is_premium) and used >= FREE_DAILY_LIMIT:
        raise HTTPException(status_code=403, detail="Daily limit reached")

    img = qrcode.make(payload.text)
    filename = f"{uuid.uuid4().hex}.png"
    path = os.path.join(UPLOAD_DIR, filename)
    img.save(path)

    row = models.QRCode(
        user_id=current_user.id,
        text=payload.text,
        image_path=path,
        created_at=datetime.utcnow(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)

    used2 = _used_today(db, current_user.id)
    return schemas.QRResponse(
        id=row.id,
        qr_image_url=f"/uploads/{filename}",
        used_today=used2,
        is_premium=current_user.is_premium,
    )


@app.get("/qr/history")
def qr_history(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    rows = (
        db.query(models.QRCode)
        .filter(models.QRCode.user_id == current_user.id)
        .order_by(models.QRCode.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "qr_image_url": f"/uploads/{os.path.basename(r.image_path)}",
            "created_at": r.created_at,
        }
        for r in rows
    ]