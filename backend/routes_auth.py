from datetime import timedelta
from typing import Literal

import jwt
from fastapi import APIRouter, Request, Response, HTTPException, Depends
from pydantic import BaseModel, Field, EmailStr
from pymongo.errors import DuplicateKeyError

from core import db, now, new_id, out, hash_password, verify_password, make_token, decode_token, current_user, client_ip, rate_limit, TERMS_VERSION

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


def set_session(resp: Response, uid: str) -> str:
    access = make_token(uid, "access", 15)
    resp.set_cookie("access_token", access, httponly=True, secure=True, samesite="none", max_age=900, path="/")
    resp.set_cookie("refresh_token", make_token(uid, "refresh", 60 * 24 * 7), httponly=True, secure=True, samesite="none", max_age=604800, path="/")
    return access


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
    token = set_session(response, user["_id"])
    return {"user": out(user), "access_token": token}


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
    token = set_session(response, user["_id"])
    return {"user": out(user), "access_token": token}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get("refresh_token")
    if not token:
        raise HTTPException(401, "No refresh session")
    try:
        payload = decode_token(token, "refresh")
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid refresh session")
    user = await db.users.find_one({"_id": payload["sub"]})
    if not user or user["status"] != "active":
        raise HTTPException(401, "Session no longer valid")
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
