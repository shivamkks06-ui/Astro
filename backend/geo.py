"""GeoNames place search: reference data loaded once into MongoDB, indexed prefix search, India first."""
import asyncio
import gzip
import json
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path

from pymongo import ReplaceOne

from core import db, logger, now

DATA = Path(__file__).parent / "data" / "places.jsonl.gz"
VERSION = "geonames-2026-11-v1"
ATTRIBUTION = "Place data © GeoNames (geonames.org), CC BY 4.0"
PROJ = {"_id": 1, "n": 1, "r": 1, "d": 1, "c": 1, "cc": 1, "lat": 1, "lon": 1, "tz": 1, "p": 1, "k": 1}
state = {"ready": False}
_cache: OrderedDict = OrderedDict()


def fold(s):
    return re.sub(r"\s+", " ", unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode().lower()).strip()


async def ensure_places():
    try:
        meta = await db.meta.find_one({"_id": "places"})
        if meta and meta.get("version") == VERSION and meta.get("complete"):
            state["ready"] = True
            return
        await db.meta.update_one({"_id": "places"}, {"$set": {"version": VERSION, "complete": False, "started_at": now()}}, upsert=True)
        await db.places.create_index("k")
        await db.places.create_index([("m", 1), ("k", 1)])
        batch, n = [], 0
        with gzip.open(DATA, "rt", encoding="utf-8") as fh:
            for line in fh:
                d = json.loads(line)
                d["f"] = fold(" ".join([d.get("d", ""), d["r"], d["c"], d["cc"]]))
                batch.append(ReplaceOne({"_id": d["_id"]}, d, upsert=True))
                if len(batch) == 5000:
                    await db.places.bulk_write(batch, ordered=False); n += len(batch); batch = []
                    await asyncio.sleep(0)
        if batch:
            await db.places.bulk_write(batch, ordered=False); n += len(batch)
        await db.meta.update_one({"_id": "places"}, {"$set": {"complete": True, "count": n, "loaded_at": now()}})
        state["ready"] = True
        logger.info("places loaded: %s", n)
    except Exception:
        logger.exception("places load failed; offline city list stays in use")


def item(d):
    label = ", ".join(x for x in (d["n"], d.get("r"), d.get("c")) if x)
    return {"label": label, "name": d["n"], "region": d.get("r", ""), "district": d.get("d", ""), "country": d.get("c", ""),
            "lat": d["lat"], "lon": d["lon"], "tz": d["tz"], "source": "geonames", "geonames_id": d["_id"]}


async def _find(name, rest):
    flt = {"k": {"$regex": "^" + re.escape(name)}}
    if len(name) < 4:
        flt["m"] = True
    if rest:
        flt["$and"] = [{"f": {"$regex": re.escape(r)}} for r in rest]
    rows = await db.places.find(flt, PROJ).limit(3000).to_list(3000)
    def weight(d):
        return max(d["p"], 1) * (3 if d["cc"] == "IN" else 1) * (5 if name in d["k"] else 1) * (2 if d["k"] and d["k"][0].startswith(name) else 1)
    rows.sort(key=weight, reverse=True)
    return rows


async def search(q, page=0, size=10):
    key = (fold(q), page, size)
    if key in _cache:
        _cache.move_to_end(key)
        return _cache[key]
    parts = [fold(x) for x in q.split(",") if fold(x)]
    rows = await _find(parts[0], parts[1:]) if parts else []
    if not rows and parts and " " in parts[0]:
        head, tail = parts[0].rsplit(" ", 1)
        rows = await _find(head, [tail] + parts[1:])
    res = {"items": [item(d) for d in rows[page * size:(page + 1) * size]], "has_more": len(rows) > (page + 1) * size,
           "page": page, "source": "geonames", "attribution": ATTRIBUTION}
    _cache[key] = res
    if len(_cache) > 2000:
        _cache.popitem(last=False)
    return res
