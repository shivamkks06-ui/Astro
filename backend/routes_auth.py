from datetime import timedelta
import hashlib
import os
import re
import secrets
from html import escape
from urllib.parse import urlparse
from typing import Literal, Optional

import jwt
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, out, hash_password, verify_password, make_token, decode_token, current_user, client_ip, rate_limit, TERMS_VERSION, logger
from email_service import send_email

router = APIRouter(prefix="/api/auth")


class RegisterIn(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: Literal["customer", "astrologer"]
    accept_terms: bool


class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class RefreshIn(BaseModel):
    refresh_token: Optional[str] = Field(None, max_length=2000)


class ForgotIn(BaseModel):
    email: EmailStr


class ResetIn(BaseModel):
    token: str = Field(min_length=20, max_length=200)
    password: str = Field(min_length=8, max_length=128)


def _reset_base(request: Request) -> str:
    origin = (request.headers.get("origin") or "").rstrip("/")
    host = urlparse(origin).hostname or ""
    if origin.startswith("https://") and (host.endswith(".emergentagent.com") or host.endswith(".emergent.host")):
        return origin
    return os.environ["FRONTEND_URL"].rstrip("/")


@router.post("/forgot-password")
async def forgot_password(body: ForgotIn, request: Request):
    email = body.email.lower().strip()
    await rate_limit(f"forgot-ip:{client_ip(request)}", 5, 900)
    await rate_limit(f"forgot-email:{email}", 3, 3600)
    user = await db.users.find_one({"email": email})
    if user and user.get("status", "active") == "active":
        token = secrets.token_urlsafe(32)
        await db.password_resets.update_many({"user_id": user["_id"], "used": False}, {"$set": {"used": True}})
        await db.password_resets.insert_one({"_id": new_id(), "user_id": user["_id"], "token_hash": hashlib.sha256(token.encode()).hexdigest(),
                                             "expires_at": now() + timedelta(minutes=30), "used": False, "created_at": now()})
        link = f"{_reset_base(request)}/reset-password?token={token}"
        html = (f'<table role="presentation" width="100%"><tr><td style="padding:24px;font-family:Arial,sans-serif;color:#0B1225">'
                f'<p style="font-size:18px;color:#8A6F20"><strong>NakshatraVeda</strong></p>'
                f'<p>Hi {escape(user.get("name") or "there")},</p>'
                f'<p>We received a request to reset the password for your NakshatraVeda account. This link works once and expires in 30 minutes.</p>'
                f'<p><a href="{escape(link)}" style="display:inline-block;padding:12px 22px;background:#D4AF37;color:#0B1225;text-decoration:none;border-radius:24px;font-weight:bold">Reset password</a></p>'
                f'<p style="font-size:13px;color:#555">If you did not request this, ignore this email; your password stays the same.</p>'
                f'<p style="font-size:12px;color:#888">Sent by NakshatraVeda. We never ask for your password or payment details by email.</p></td></tr></table>')
        try:
            await send_email(to=user["email"], subject="Reset your NakshatraVeda password", html=html)
        except HTTPException:
            logger.warning("password reset email not sent")
    return {"ok": True, "message": "If an account exists for that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(body: ResetIn, request: Request):
    await rate_limit(f"reset-ip:{client_ip(request)}", 10, 900)
    doc = await db.password_resets.find_one_and_update(
        {"token_hash": hashlib.sha256(body.token.encode()).hexdigest(), "used": False, "expires_at": {"$gt": now()}},
        {"$set": {"used": True, "used_at": now()}})
    if not doc:
        raise HTTPException(400, "This reset link is invalid or has expired. Request a new one.")
    await db.users.update_one({"_id": doc["user_id"]}, {"$set": {"password_hash": hash_password(body.password), "password_changed_at": now()}})
    user = await db.users.find_one({"_id": doc["user_id"]}, {"email": 1})
    if user:
        await db.login_attempts.update_many({"identifier": {"$regex": f"^{re.escape(user['email'])}"}}, {"$set": {"count": 0, "locked_until": None}})
    return {"ok": True}


def set_session(resp: Response, uid: str):
    access = make_token(uid, "access", 15)
    refresh_tok = make_token(uid, "refresh", 60 * 24 * 7)
    resp.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    resp.set_cookie("refresh_token", refresh_tok, httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return access, refresh_tok


def session_body(request: Request, user, access, refresh_tok):
    body = {"user": out(user), "access_token": access}
    if request.headers.get("X-Client") == "native":
        body["refresh_token"] = refresh_tok  # Android app stores it; web relies on httpOnly cookie only
    return body


@router.post("/register")
async def register(body: RegisterIn, request: Request, response: Response):
    await rate_limit(f"register:{client_ip(request)}", 10, 3600)
    if not body.accept_terms:
        raise HTTPException(400, "You must accept the Terms, Privacy Policy and Community Guidelines")
    email = body.email.lower()
    user = {"_id": new_id(), "email": email, "name": body.name.strip(), "role": body.role, "status": "active",
            "password_hash": hash_password(body.password), "terms_version": TERMS_VERSION, "terms_accepted_at": now(),
            "privacy": {"share_birth_details": True, "marketing_opt_in": False}, "created_at": now()}
    try:
        await db.users.insert_one(user)
    except DuplicateKeyError:
        raise HTTPException(409, "An account with this email already exists")
    if body.role == "astrologer":
        await db.astrologer_profiles.insert_one({
            "_id": user["_id"], "display_name": user["name"], "bio": "", "languages": [], "expertise": [], "experience_years": 0,
            "rates": {"chat": 0, "audio": 0, "video": 0}, "modes_enabled": ["chat"], "payout_account": None,
            "identity_status": "not_submitted", "credential_status": "not_submitted", "listing_expires_at": None,
            "account_status": "active", "rating_avg": 0, "rating_count": 0, "created_at": now(), "updated_at": now()})
    access, refresh_tok = set_session(response, user["_id"])
    return session_body(request, user, access, refresh_tok)


@router.post("/login")
async def login(body: LoginIn, request: Request, response: Response):
    email = body.email.lower()
    ident = f"{client_ip(request)}:{email}"
    acct = f"acct:{email}"
    for key, limit in ((ident, 5), (acct, 20)):
        att = await db.login_attempts.find_one({"identifier": key})
        if att and att.get("count", 0) >= limit and att["locked_until"] > now():
            raise HTTPException(429, "Too many failed attempts. Try again in 15 minutes.")
    user = await db.users.find_one({"email": email})
    if not user or not verify_password(body.password, user["password_hash"]):
        for key in (ident, acct):
            await db.login_attempts.update_one({"identifier": key}, {"$inc": {"count": 1}, "$set": {"locked_until": now() + timedelta(minutes=15), "expires_at": now() + timedelta(minutes=15)}}, upsert=True)
        raise HTTPException(401, "Invalid email or password")
    if user["status"] != "active":
        raise HTTPException(403, f"Account is {user['status']}")
    await db.login_attempts.delete_many({"identifier": {"$in": [ident, acct]}})
    access, refresh_tok = set_session(response, user["_id"])
    return session_body(request, user, access, refresh_tok)


@router.post("/refresh")
async def refresh(request: Request, response: Response, body: Optional[RefreshIn] = None):
    token = request.cookies.get("refresh_token") or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(401, "No refresh session")
    try:
        payload = decode_token(token, "refresh")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh session")
    user = await db.users.find_one({"_id": payload["sub"]})
    if not user or user["status"] != "active":
        raise HTTPException(401, "Session no longer valid")
    if request.headers.get("X-Client") == "native":
        access, refresh_tok = set_session(response, user["_id"])
        return session_body(request, user, access, refresh_tok)
    access = make_token(user["_id"], "access", 15)
    response.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    return {"user": out(user), "access_token": access}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("access_token", path="/", secure=True, samesite="none")
    response.delete_cookie("refresh_token", path="/", secure=True, samesite="none")
    return {"ok": True}


@router.get("/me")
async def me(user=Depends(current_user)):
    return out(user)
