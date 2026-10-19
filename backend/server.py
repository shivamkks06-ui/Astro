from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent / ".env")

import os
import asyncio
from urllib.parse import urlparse
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

from core import client, logger
from migrations import run_migrations, seed_admin
from finance import sweep
from storage import init_storage
import routes_auth
import routes_user
import routes_astrologer
import routes_bookings
import routes_admin

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

app = FastAPI(title="NakshatraVeda API")
ALLOWED_ORIGINS = [o.strip() for o in os.environ["CORS_ORIGINS"].split(",") if o.strip()]


@app.middleware("http")
async def origin_guard(request: Request, call_next):
    origin = request.headers.get("origin")
    same_host = origin and urlparse(origin).netloc in (request.headers.get("x-forwarded-host"), request.headers.get("host"))
    if request.method in ("POST", "PUT", "PATCH", "DELETE") and origin and not same_host and origin not in ALLOWED_ORIGINS:
        return JSONResponse({"detail": "Origin not allowed"}, status_code=403)
    try:
        return await call_next(request)
    except Exception:
        logger.exception("unhandled error")
        return JSONResponse({"detail": "Something went wrong. Please retry."}, status_code=500)


for r in (routes_auth, routes_user, routes_astrologer, routes_bookings, routes_admin):
    app.include_router(r.router)


@app.get("/api/health")
async def health():
    return {"ok": True}


app.add_middleware(CORSMiddleware, allow_origins=ALLOWED_ORIGINS, allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


async def sweeper():
    while True:
        try:
            await sweep()
        except Exception:
            logger.exception("sweep failed")
        await asyncio.sleep(60)


@app.on_event("startup")
async def startup():
    await run_migrations()
    await seed_admin()
    try:
        init_storage()
    except Exception as e:
        logger.error(f"Storage init failed: {e}")
    app.state.sweeper = asyncio.create_task(sweeper())


@app.on_event("shutdown")
async def shutdown():
    client.close()
