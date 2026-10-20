"""Navamsa, Panchang, Manglik and Ashtakoota matching on top of astro_calc."""
from datetime import datetime, time, timedelta

from skyfield import almanac
from skyfield.api import wgs84

from astro_calc import EPH, EARTH, TS, SIGNS, NAKSHATRAS, NAK

TITHIS = ["Pratipada", "Dwitiya", "Tritiya", "Chaturthi", "Panchami", "Shashthi", "Saptami", "Ashtami", "Navami", "Dashami",
          "Ekadashi", "Dwadashi", "Trayodashi", "Chaturdashi"]
YOGAS = ["Vishkambha", "Priti", "Ayushman", "Saubhagya", "Shobhana", "Atiganda", "Sukarma", "Dhriti", "Shula", "Ganda", "Vriddhi",
         "Dhruva", "Vyaghata", "Harshana", "Vajra", "Siddhi", "Vyatipata", "Variyana", "Parigha", "Shiva", "Siddha", "Sadhya",
         "Shubha", "Shukla", "Brahma", "Indra", "Vaidhriti"]
KARANAS = ["Bava", "Balava", "Kaulava", "Taitila", "Garaja", "Vanija", "Vishti"]
VARAS = ["Somavara (Monday)", "Mangalavara (Tuesday)", "Budhavara (Wednesday)", "Guruvara (Thursday)", "Shukravara (Friday)",
         "Shanivara (Saturday)", "Ravivara (Sunday)"]


def navamsa(chart):
    d9 = lambda lon: int(lon * 9 / 30) % 12
    asc = d9(chart["ascendant"]["lon"])
    planets = [{"name": p["name"], "sign_index": d9(p["lon"]), "sign": SIGNS[d9(p["lon"])], "retrograde": p["retrograde"],
                "house": (d9(p["lon"]) - asc) % 12 + 1} for p in chart["planets"]]
    houses = [{"house": h + 1, "sign_index": (asc + h) % 12, "sign": SIGNS[(asc + h) % 12]} for h in range(12)]
    return {"ascendant": {"sign_index": asc, "sign": SIGNS[asc]}, "planets": planets, "houses": houses}


def _sunrise(local, lat, lon):
    start = datetime.combine(local.date(), time(0), tzinfo=local.tzinfo)
    t, up = almanac.find_risings(EARTH + wgs84.latlon(lat, lon), EPH["sun"], TS.from_datetime(start), TS.from_datetime(start + timedelta(days=1)))
    return t[0].utc_datetime().astimezone(local.tzinfo) if len(t) and up[0] else None


def panchang(chart, local, lat, lon):
    sun = next(p["lon"] for p in chart["planets"] if p["name"] == "Sun")
    moon = next(p["lon"] for p in chart["planets"] if p["name"] == "Moon")
    diff = (moon - sun) % 360
    n = int(diff // 12)
    tithi = "Purnima" if n == 14 else "Amavasya" if n == 29 else TITHIS[n % 15]
    k = int(diff // 6)
    karana = "Kimstughna" if k == 0 else KARANAS[(k - 1) % 7] if k < 57 else ["Shakuni", "Chatushpada", "Naga"][k - 57]
    rise = _sunrise(local, lat, lon)
    day = local.date() - timedelta(days=1) if rise and local < rise else local.date()
    return {"tithi": tithi, "tithi_number": n + 1, "paksha": "Shukla" if n < 15 else "Krishna",
            "vara": VARAS[day.weekday()], "yoga": YOGAS[int(((sun + moon) % 360) // NAK)], "karana": karana,
            "nakshatra": NAKSHATRAS[int(moon // NAK)], "sunrise": rise.strftime("%H:%M") if rise else None,
            "note": "Vedic day starts at sunrise; births before sunrise take the previous weekday."}


def manglik(chart):
    mars = next(p for p in chart["planets"] if p["name"] == "Mars")
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    bad = {1, 2, 4, 7, 8, 12}
    from_moon = (mars["sign_index"] - moon["sign_index"]) % 12 + 1
    lagna, chandra = mars["house"] in bad, from_moon in bad
    cancel = []
    if (lagna or chandra) and mars["sign"] in ("Aries", "Scorpio"):
        cancel.append("Mars is in its own sign")
    if (lagna or chandra) and mars["sign"] == "Capricorn":
        cancel.append("Mars is exalted")
    return {"mars_house_from_lagna": mars["house"], "mars_house_from_moon": from_moon, "from_lagna": lagna, "from_moon": chandra,
            "manglik": lagna or chandra, "cancellations": cancel,
            "rule": "Traditional rule: Mars in house 1, 2, 4, 7, 8 or 12 counted from the Lagna or the Moon."}


# ---- Ashtakoota (36 guna) ----
VARNA = [3, 2, 1, 4, 3, 2, 1, 4, 3, 2, 1, 4]  # by Moon sign; Brahmin 4 .. Shudra 1
VASHYA_ORDER = ["Chatushpada", "Manava", "Jalachara", "Vanachara", "Keeta"]
VASHYA_TABLE = [[2, 1, 1, 0, 1], [1, 2, 0.5, 0, 1], [1, 0.5, 2, 1, 1], [0, 0, 1, 2, 0], [1, 1, 1, 0, 2]]
YONI_ORDER = ["Horse", "Elephant", "Sheep", "Serpent", "Dog", "Cat", "Rat", "Cow", "Buffalo", "Tiger", "Deer", "Monkey", "Mongoose", "Lion"]
YONI_NAK = [0, 1, 2, 3, 3, 4, 5, 2, 5, 6, 6, 7, 8, 9, 8, 9, 10, 10, 4, 11, 12, 11, 13, 0, 13, 7, 1]
YONI_TABLE = [[4, 2, 2, 3, 2, 2, 2, 1, 0, 1, 3, 3, 2, 1], [2, 4, 3, 3, 2, 2, 2, 2, 3, 1, 2, 3, 2, 0], [2, 3, 4, 2, 1, 2, 1, 3, 3, 1, 2, 0, 3, 1],
              [3, 3, 2, 4, 2, 1, 1, 1, 1, 2, 2, 2, 0, 2], [2, 2, 1, 2, 4, 2, 1, 2, 2, 1, 0, 2, 1, 1], [2, 2, 2, 1, 2, 4, 0, 2, 2, 1, 3, 3, 2, 1],
              [2, 2, 1, 1, 1, 0, 4, 2, 2, 2, 2, 2, 1, 2], [1, 2, 3, 1, 2, 2, 2, 4, 3, 0, 3, 2, 2, 1], [0, 3, 3, 1, 2, 2, 2, 3, 4, 1, 2, 2, 2, 1],
              [1, 1, 1, 2, 1, 1, 2, 0, 1, 4, 1, 1, 2, 1], [3, 2, 2, 2, 0, 3, 2, 3, 2, 1, 4, 2, 2, 1], [3, 3, 0, 2, 2, 3, 2, 2, 2, 1, 2, 4, 3, 2],
              [2, 2, 3, 0, 1, 2, 1, 2, 2, 2, 2, 3, 4, 2], [1, 0, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 2, 4]]
LORD = ["Mars", "Venus", "Mercury", "Moon", "Sun", "Mercury", "Venus", "Mars", "Jupiter", "Saturn", "Saturn", "Jupiter"]
FRIENDS = {"Sun": ({"Moon", "Mars", "Jupiter"}, {"Venus", "Saturn"}), "Moon": ({"Sun", "Mercury"}, set()),
           "Mars": ({"Sun", "Moon", "Jupiter"}, {"Mercury"}), "Mercury": ({"Sun", "Venus"}, {"Moon"}),
           "Jupiter": ({"Sun", "Moon", "Mars"}, {"Mercury", "Venus"}), "Venus": ({"Mercury", "Saturn"}, {"Sun", "Moon"}),
           "Saturn": ({"Mercury", "Venus"}, {"Sun", "Moon", "Mars"})}
GANA = "DMRMDMDDRRMMDRDRDRRMMDRRMMD"  # Deva / Manushya / Rakshasa per nakshatra
GANA_TABLE = {"D": {"D": 6, "M": 6, "R": 1}, "M": {"D": 5, "M": 6, "R": 0}, "R": {"D": 1, "M": 0, "R": 6}}  # [girl][boy]
NADI = "AMNNMAAMNNMAAMNNMAAMNNMAAMN"  # Adi / Madhya / Antya per nakshatra
NADI_NAMES = {"A": "Adi", "M": "Madhya", "N": "Antya"}
GANA_NAMES = {"D": "Deva", "M": "Manushya", "R": "Rakshasa"}


def _vashya(sign, deg):
    if sign == 8:
        return 1 if deg < 15 else 0
    if sign == 9:
        return 0 if deg < 15 else 2
    return [0, 0, 1, 2, 3, 1, 1, 4, None, None, 1, 2][sign]


def _rel(a, b):
    f, e = FRIENDS[a]
    return "F" if b in f else "E" if b in e else "N"


def _maitri(a, b):
    if a == b:
        return 5
    pair = "".join(sorted(_rel(a, b) + _rel(b, a)))
    return {"FF": 5, "FN": 4, "NN": 3, "EF": 1, "EN": 0.5, "EE": 0}[pair]


def _tara_ok(frm, to):
    return ((to - frm) % 27 + 1) % 9 not in (3, 5, 7)


def match(boy, girl):
    bm = next(p for p in boy["planets"] if p["name"] == "Moon")
    gm = next(p for p in girl["planets"] if p["name"] == "Moon")
    bs, gs = bm["sign_index"], gm["sign_index"]
    bn, gn = int(bm["lon"] // NAK), int(gm["lon"] // NAK)
    bv, gv = _vashya(bs, bm["degree"]), _vashya(gs, gm["degree"])
    tara = _tara_ok(gn, bn) + _tara_ok(bn, gn)
    dist = ((bs - gs) % 12 + 1, (gs - bs) % 12 + 1)
    kootas = [
        ("Varna", 1, 1 if VARNA[bs] >= VARNA[gs] else 0, "Temperament and work ethic"),
        ("Vashya", 2, VASHYA_TABLE[bv][gv], f"{VASHYA_ORDER[bv]} / {VASHYA_ORDER[gv]}"),
        ("Tara", 3, [0, 1.5, 3][tara], "Birth-star compatibility"),
        ("Yoni", 4, YONI_TABLE[YONI_NAK[bn]][YONI_NAK[gn]], f"{YONI_ORDER[YONI_NAK[bn]]} / {YONI_ORDER[YONI_NAK[gn]]}"),
        ("Graha Maitri", 5, _maitri(LORD[bs], LORD[gs]), f"{LORD[bs]} / {LORD[gs]}"),
        ("Gana", 6, GANA_TABLE[GANA[gn]][GANA[bn]], f"{GANA_NAMES[GANA[bn]]} / {GANA_NAMES[GANA[gn]]}"),
        ("Bhakoot", 7, 0 if set(dist) in ({2, 12}, {5, 9}, {6, 8}) else 7, f"{SIGNS[bs]} / {SIGNS[gs]}"),
        ("Nadi", 8, 0 if NADI[bn] == NADI[gn] else 8, f"{NADI_NAMES[NADI[bn]]} / {NADI_NAMES[NADI[gn]]}"),
    ]
    total = sum(k[2] for k in kootas)
    band = "Excellent" if total > 32 else "Good" if total >= 25 else "Average" if total >= 18 else "Low"
    return {"kootas": [{"name": n, "max": m, "score": s, "detail": d} for n, m, s, d in kootas], "total": total, "max": 36, "band": band,
            "nadi_dosha": NADI[bn] == NADI[gn], "bhakoot_dosha": set(dist) in ({2, 12}, {5, 9}, {6, 8}),
            "boy": {"moon_sign": SIGNS[bs], "nakshatra": NAKSHATRAS[bn], "manglik": manglik(boy)},
            "girl": {"moon_sign": SIGNS[gs], "nakshatra": NAKSHATRAS[gn], "manglik": manglik(girl)}}
