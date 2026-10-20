"""Sidereal (Lahiri) chart calculations on the JPL DE421 ephemeris via Skyfield."""
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from skyfield.api import load, load_file
from skyfield.framelib import ecliptic_frame

DATA = Path(__file__).parent / "data"
EPH = load_file(str(DATA / "de421.bsp"))
TS = load.timescale(builtin=True)
EARTH = EPH["earth"]
BODIES = {"Sun": EPH["sun"], "Moon": EPH["moon"], "Mars": EPH["mars barycenter"], "Mercury": EPH["mercury"],
          "Jupiter": EPH["jupiter barycenter"], "Venus": EPH["venus"], "Saturn": EPH["saturn barycenter"]}
MIN_YEAR, MAX_YEAR = 1900, 2050

SIGNS = ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo", "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]
RASHIS = ["Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya", "Tula", "Vrishchika", "Dhanu", "Makara", "Kumbha", "Meena"]
NAKSHATRAS = ["Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra", "Punarvasu", "Pushya", "Ashlesha", "Magha",
              "Purva Phalguni", "Uttara Phalguni", "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha", "Mula",
              "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha", "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"]
DASHA = [("Ketu", 7), ("Venus", 20), ("Sun", 6), ("Moon", 10), ("Mars", 7), ("Rahu", 18), ("Jupiter", 16), ("Saturn", 19), ("Mercury", 17)]
NAK = 360 / 27
YEAR_DAYS = 365.2425


def ayanamsa(t):
    return float(23.85306 + (t.tt - 2451545.0) / 365.25 * 50.2788 / 3600)


def _tropical(body, t):
    _, lon, _ = EARTH.at(t).observe(body).apparent().frame_latlon(ecliptic_frame)
    return lon.degrees


def _mean_node(t):
    T = (t.tt - 2451545.0) / 36525
    return (125.0445479 - 1934.1362891 * T + 0.0020754 * T * T + T ** 3 / 467441) % 360


def _ascendant(t, lat, lon):
    T = (t.tt - 2451545.0) / 36525
    eps = math.radians(23.4392911 - 0.0130042 * T)
    theta = math.radians((t.gast * 15 + lon) % 360)
    phi = math.radians(lat)
    return float(math.degrees(math.atan2(math.cos(theta), -(math.sin(theta) * math.cos(eps) + math.tan(phi) * math.sin(eps)))) % 360)


def describe(lon):
    lon = float(lon)
    sign = int(lon // 30)
    nak = int(lon // NAK)
    return {"lon": round(lon, 4), "sign_index": sign, "sign": SIGNS[sign], "rashi": RASHIS[sign], "degree": round(lon % 30, 4),
            "nakshatra": NAKSHATRAS[nak], "pada": int((lon % NAK) // (NAK / 4)) + 1, "nakshatra_lord": DASHA[nak % 9][0]}


def sidereal_positions(t):
    ay = ayanamsa(t)
    t2 = TS.tt_jd(t.tt + 0.5)
    pos = {}
    for name, body in BODIES.items():
        a, b = float(_tropical(body, t)), float(_tropical(body, t2))
        pos[name] = ((a - ay) % 360, bool(name not in ("Sun", "Moon") and ((b - a + 540) % 360 - 180) < 0))
    rahu = (_mean_node(t) - ay) % 360
    pos["Rahu"] = (rahu, True)
    pos["Ketu"] = ((rahu + 180) % 360, True)
    return pos, ay


def _dashas(moon_lon, birth_utc, at_utc):
    nak = int(moon_lon // NAK)
    frac = (moon_lon % NAK) / NAK
    i0 = nak % 9
    start = birth_utc - timedelta(days=DASHA[i0][1] * frac * YEAR_DAYS)
    mahas, cur = [], None
    for k in range(9):
        lord, yrs = DASHA[(i0 + k) % 9]
        end = start + timedelta(days=yrs * YEAR_DAYS)
        m = {"lord": lord, "years": yrs, "start": start.date().isoformat(), "end": end.date().isoformat()}
        if start <= at_utc < end:
            subs, s = [], start
            for j in range(9):
                sl, sy = DASHA[(i0 + k + j) % 9]
                e = s + timedelta(days=yrs * sy / 120 * YEAR_DAYS)
                subs.append({"lord": sl, "start": s.date().isoformat(), "end": e.date().isoformat(), "current": s <= at_utc < e})
                s = e
            m["antardashas"] = subs
            cur = {"mahadasha": lord, "antardasha": next(x["lord"] for x in subs if x["current"]), "until": end.date().isoformat()}
        mahas.append(m)
        start = end
    return {"balance_years_at_birth": round(DASHA[i0][1] * (1 - frac), 2), "mahadashas": mahas, "current": cur}


def to_utc(date: str, time: str, tz: str):
    local = datetime.fromisoformat(f"{date}T{time}").replace(tzinfo=ZoneInfo(tz))
    if not MIN_YEAR <= local.year < MAX_YEAR:
        raise ValueError(f"Birth year must be between {MIN_YEAR} and {MAX_YEAR - 1}")
    return local, local.astimezone(timezone.utc)


def kundli(date: str, time: str, lat: float, lon: float, tz: str):
    local, utc = to_utc(date, time, tz)
    t = TS.from_datetime(utc)
    pos, ay = sidereal_positions(t)
    asc = describe((_ascendant(t, lat, lon) - ay) % 360)
    planets = []
    for name, (plon, retro) in pos.items():
        d = describe(plon)
        d.update(name=name, retrograde=retro, house=(d["sign_index"] - asc["sign_index"]) % 12 + 1)
        planets.append(d)
    houses = [{"house": h + 1, "sign_index": (asc["sign_index"] + h) % 12, "sign": SIGNS[(asc["sign_index"] + h) % 12],
               "planets": [p["name"] for p in planets if p["house"] == h + 1]} for h in range(12)]
    moon = next(p for p in planets if p["name"] == "Moon")
    return {
        "system": {"zodiac": "Sidereal", "ayanamsa": "Lahiri", "ayanamsa_degrees": round(ay, 4), "houses": "Whole sign",
                   "nodes": "Mean node", "ephemeris": "JPL DE421"},
        "birth": {"local": local.isoformat(), "utc": utc.isoformat(), "lat": lat, "lon": lon, "tz": tz,
                  "utc_offset_hours": round(local.utcoffset().total_seconds() / 3600, 2)},
        "ascendant": asc, "planets": planets, "houses": houses,
        "moon_sign": moon["sign"], "moon_rashi": moon["rashi"], "janma_nakshatra": moon["nakshatra"], "janma_pada": moon["pada"],
        "dasha": _dashas(moon["lon"], utc, datetime.now(timezone.utc)),
    }


def transits(at_utc: datetime):
    pos, ay = sidereal_positions(TS.from_datetime(at_utc))
    return [{**describe(lon), "name": n, "retrograde": r} for n, (lon, r) in pos.items()]
