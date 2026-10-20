import json
import unicodedata
from datetime import datetime
from typing import Optional, Literal

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from starlette.concurrency import run_in_threadpool
from timezonefinder import TimezoneFinder
from zoneinfo import ZoneInfo, available_timezones

import astro_calc
import astro_extras
import horoscope
from core import db, now, new_id, current_user, rate_limit, client_ip

router = APIRouter(prefix="/api")
CITIES = json.loads((astro_calc.DATA / "cities.json").read_text(encoding="utf-8"))
TZS = available_timezones()
_tf = None
MAX_SAVED = 100


def _fold(s):
    return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()


for c in CITIES:
    c["_k"] = _fold(c["n"])


def _place(c, source):
    label = ", ".join(x for x in (c["n"], c["r"], c["c"]) if x)
    return {"label": label, "name": c["n"], "region": c["r"], "country": c["c"], "lat": c["lat"], "lon": c["lon"], "tz": c["tz"], "source": source}


@router.get("/places")
async def places(request: Request, q: str = Query(..., min_length=2, max_length=80), online: bool = False):
    k = _fold(q.strip())
    if not online:
        hits = [c for c in CITIES if c["_k"].startswith(k)]
        if len(hits) < 10:
            hits += [c for c in CITIES if k in c["_k"] and not c["_k"].startswith(k)]
        hits.sort(key=lambda c: (c["cc"] != "IN", -c["p"]))
        return {"items": [_place(c, "offline") for c in hits[:10]], "source": "offline"}
    await rate_limit(f"osm:{client_ip(request)}", 10, 60)
    await rate_limit("osm:global", 50, 60)
    try:
        async with httpx.AsyncClient(timeout=8) as hc:
            r = await hc.get("https://nominatim.openstreetmap.org/search", params={"q": q, "format": "jsonv2", "limit": 6, "addressdetails": 0},
                             headers={"User-Agent": "NakshatraVeda/1.0 (birthplace lookup)"})
            r.raise_for_status()
            rows = r.json()
    except Exception:
        raise HTTPException(502, "Worldwide place search is unavailable right now. Pick a nearby city from the list instead.")
    global _tf
    if _tf is None:
        _tf = TimezoneFinder(in_memory=True)
    items = []
    for row in rows:
        lat, lon = round(float(row["lat"]), 4), round(float(row["lon"]), 4)
        tz = _tf.timezone_at(lng=lon, lat=lat)
        if tz:
            items.append({"label": row.get("display_name", "")[:160], "name": row.get("name") or q, "region": "", "country": "",
                          "lat": lat, "lon": lon, "tz": tz, "source": "openstreetmap"})
    return {"items": items, "source": "openstreetmap", "attribution": "© OpenStreetMap contributors"}


class BirthIn(BaseModel):
    name: Optional[str] = Field(None, max_length=60)
    date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$")
    time: str = Field(..., pattern=r"^\d{2}:\d{2}$")
    place: str = Field(..., min_length=2, max_length=160)
    lat: float = Field(..., ge=-66.5, le=66.5)
    lon: float = Field(..., ge=-180, le=180)
    tz: str
    chart_style: Literal["north", "south"] = "north"

    @field_validator("tz")
    @classmethod
    def _tz(cls, v):
        if v not in TZS:
            raise ValueError("Unknown time zone")
        return v

    @field_validator("name")
    @classmethod
    def _name(cls, v):
        return v.strip() or None if v else None


def _full(b):
    c = astro_calc.kundli(b.date, b.time, b.lat, b.lon, b.tz)
    c["navamsa"] = astro_extras.navamsa(c)
    c["panchang"] = astro_extras.panchang(c, datetime.fromisoformat(c["birth"]["local"]), b.lat, b.lon)
    c["manglik"] = astro_extras.manglik(c)
    return c


async def _calc(b: BirthIn):
    try:
        return await run_in_threadpool(_full, b)
    except ValueError as e:
        raise HTTPException(422, str(e) if "year" in str(e) else "Invalid birth date or time")


@router.post("/kundli/calculate")
async def calculate(b: BirthIn, request: Request):
    await rate_limit(f"kundli:{client_ip(request)}", 30, 60)
    return {"input": b.model_dump(), "chart": await _calc(b)}


class MatchIn(BaseModel):
    boy: BirthIn
    girl: BirthIn


@router.post("/kundli/match")
async def match(m: MatchIn, request: Request):
    await rate_limit(f"kundli:{client_ip(request)}", 30, 60)
    boy, girl = await _calc(m.boy), await _calc(m.girl)
    return {"boy": m.boy.model_dump(), "girl": m.girl.model_dump(), "result": astro_extras.match(boy, girl)}


@router.get("/kundlis")
async def list_kundlis(user=Depends(current_user)):
    rows = await db.kundlis.find({"user_id": user["_id"]}).sort("created_at", -1).to_list(MAX_SAVED)
    return {"items": [{"id": r["_id"], **r["input"], "moon_sign": r["moon_sign"], "ascendant": r["ascendant"], "created_at": r["created_at"]} for r in rows]}


@router.post("/kundlis")
async def save_kundli(b: BirthIn, user=Depends(current_user)):
    await rate_limit(f"kundli-save:{user['_id']}", 20, 60)
    dup = await db.kundlis.find_one({"user_id": user["_id"], "input.date": b.date, "input.time": b.time, "input.lat": b.lat, "input.lon": b.lon, "input.name": b.name})
    if dup:
        return {"id": dup["_id"], "duplicate": True}
    if await db.kundlis.count_documents({"user_id": user["_id"]}) >= MAX_SAVED:
        raise HTTPException(409, f"You can save up to {MAX_SAVED} charts. Delete one to save another.")
    chart = await _calc(b)
    kid = new_id()
    await db.kundlis.insert_one({"_id": kid, "user_id": user["_id"], "input": b.model_dump(), "moon_sign": chart["moon_sign"],
                                 "ascendant": chart["ascendant"]["sign"], "created_at": now()})
    return {"id": kid, "duplicate": False}


async def _own(kid, user):
    r = await db.kundlis.find_one({"_id": kid, "user_id": user["_id"]})
    if not r:
        raise HTTPException(404, "Chart not found")
    return r


@router.get("/kundlis/{kid}")
async def get_kundli(kid: str, user=Depends(current_user)):
    r = await _own(kid, user)
    try:
        b = BirthIn(**r["input"])
    except ValueError:
        raise HTTPException(422, "This saved chart has invalid birth details. Delete it and create it again.")
    return {"id": r["_id"], "input": r["input"], "chart": await _calc(b)}


@router.delete("/kundlis/{kid}")
async def delete_kundli(kid: str, user=Depends(current_user)):
    await _own(kid, user)
    await db.kundlis.delete_one({"_id": kid, "user_id": user["_id"]})
    return {"ok": True}


@router.get("/horoscope/daily")
async def daily(date: Optional[str] = None):
    try:
        return await horoscope.daily(date)
    except ValueError as e:
        raise HTTPException(422, str(e))
