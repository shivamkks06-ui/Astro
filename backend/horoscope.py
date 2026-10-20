"""Daily horoscope per Moon sign from real sidereal transits; rule text always, AI text cached per day."""
import asyncio
import json
import os
import re
from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo

from emergentintegrations.llm.chat import LlmChat, UserMessage, TextDelta, StreamDone

from astro_calc import SIGNS, RASHIS, transits
from core import db, now, logger

IST = ZoneInfo("Asia/Kolkata")
CATS = ["career", "relationships", "health", "finance"]
# classical Chandra-gochar favourable houses counted from the natal Moon sign
GOOD = {"Sun": {3, 6, 10, 11}, "Moon": {1, 3, 6, 7, 10, 11}, "Mars": {3, 6, 11}, "Mercury": {2, 4, 6, 8, 10, 11},
        "Jupiter": {2, 5, 7, 9, 11}, "Venus": {1, 2, 3, 4, 5, 8, 9, 11, 12}, "Saturn": {3, 6, 11}, "Rahu": {3, 6, 11}, "Ketu": {3, 6, 11}}
CAT_PLANETS = {"career": ["Sun", "Saturn", "Mercury"], "relationships": ["Venus", "Moon"], "health": ["Mars", "Saturn", "Moon"], "finance": ["Jupiter", "Mercury", "Venus"]}
TEXT = {
    "career": {"favourable": "Work matters move with less friction; a good day to present ideas or finish pending tasks.",
               "mixed": "Steady effort pays more than bold moves today; double-check details before committing.",
               "take care": "Keep a low profile at work and avoid hasty decisions; review rather than launch."},
    "relationships": {"favourable": "Warm, easy energy for conversations with partners, family and friends.",
                      "mixed": "Listen more than you speak; small misunderstandings clear up with patience.",
                      "take care": "Give people space and avoid reacting to passing moods, including your own."},
    "health": {"favourable": "Energy levels feel supportive; a good day for routine exercise and rest in balance.",
               "mixed": "Pace yourself and keep regular meals and sleep.",
               "take care": "Avoid overexertion and rest when you need to. See a doctor for any health concern."},
    "finance": {"favourable": "A sensible day to review budgets or plan savings.",
                "mixed": "Keep spending to plan and postpone non-essential purchases.",
                "take care": "Avoid impulsive spending or risky commitments today. This is not financial advice."},
}
OVERVIEW = {"favourable": "The Moon transits a supportive house from your sign, so the day's tone is generally encouraging.",
            "mixed": "A balanced day: some support, some friction. Keep plans flexible.",
            "take care": "The Moon transits a sensitive house from your sign; go gently and avoid rushing."}
SYSTEM = ("You write short daily Vedic horoscope interpretations for an Indian astrology app. Use ONLY the transit facts given. "
          "Tone: warm, calm, practical. Astrology is guidance, never a guarantee. Never predict death, illness, marriage, wealth or "
          "specific events; never give medical, legal or financial advice. Reply with JSON only.")
_locks: dict = {}
_tasks: set = set()


def ist_date(d: str | None):
    today = datetime.now(IST).date()
    if not d:
        return today
    v = datetime.strptime(d, "%Y-%m-%d").date()
    if abs((v - today).days) > 1:
        raise ValueError("Only yesterday, today and tomorrow are available")
    return v


def _tone(score):
    return "favourable" if score > 0 else "take care" if score < 0 else "mixed"


def rule_reading(sign_index, tr):
    house = {p["name"]: (p["sign_index"] - sign_index) % 12 + 1 for p in tr}
    pts = lambda n: 1 if house[n] in GOOD[n] else -1
    cats = {}
    for c in CATS:
        s = sum(pts(n) for n in CAT_PLANETS[c])
        t = _tone(s if abs(s) > 1 else 0)
        cats[c] = {"tone": t, "text": TEXT[c][t], "basis": [f"{n} in house {house[n]} from {SIGNS[sign_index]}" for n in CAT_PLANETS[c]]}
    t = _tone(pts("Moon"))
    return {"index": sign_index, "sign": SIGNS[sign_index], "rashi": RASHIS[sign_index], "tone": t, "overview": OVERVIEW[t],
            "moon_house": house["Moon"], "categories": cats}


async def _generate_ai(date_s, tr, readings):
    facts = {"date": date_s, "transits": [{"planet": p["name"], "sign": p["sign"], "retrograde": p["retrograde"]} for p in tr],
             "signs": [{"sign": r["sign"], "moon_house": r["moon_house"], "tones": {c: r["categories"][c]["tone"] for c in CATS}} for r in readings]}
    prompt = ("Transit facts (sidereal, Lahiri):\n" + json.dumps(facts) +
              '\nFor each of the 12 signs return {"<Sign>": {"overview": "...", "career": "...", "relationships": "...", "health": "...", "finance": "..."}}. '
              "Each value 1-2 sentences, consistent with the given tones. JSON only.")
    chat = LlmChat(api_key=os.environ["EMERGENT_LLM_KEY"], session_id=f"horoscope-{date_s}", system_message=SYSTEM).with_model("anthropic", "claude-sonnet-4-5-20250929")
    text = ""
    async for ev in chat.stream_message(UserMessage(text=prompt)):
        if isinstance(ev, TextDelta):
            text += ev.content
        elif isinstance(ev, StreamDone):
            break
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0))
    return {s: {k: str(data[s][k])[:400] for k in ["overview"] + CATS} for s in SIGNS}


async def _ensure_ai(date_s, tr, readings):
    lock = _locks.setdefault(date_s, asyncio.Lock())
    if lock.locked():
        return
    async with lock:
        doc = await db.horoscopes.find_one({"_id": date_s})
        if doc and (doc.get("ai") or doc.get("ai_attempts", 0) >= 3):
            return
        await db.horoscopes.update_one({"_id": date_s}, {"$inc": {"ai_attempts": 1}, "$set": {"ai_status": "pending"}})
        try:
            ai = await _generate_ai(date_s, tr, readings)
            await db.horoscopes.update_one({"_id": date_s}, {"$set": {"ai": ai, "ai_status": "ready", "ai_model": "claude-sonnet-4-5", "ai_at": now()}})
        except Exception:
            logger.exception("horoscope AI generation failed for %s", date_s)
            await db.horoscopes.update_one({"_id": date_s}, {"$set": {"ai_status": "failed"}})


async def daily(d: str | None):
    day = ist_date(d)
    date_s = day.isoformat()
    doc = await db.horoscopes.find_one({"_id": date_s})
    if not doc:
        at = datetime.combine(day, time(6, 0), tzinfo=IST).astimezone(timezone.utc)
        tr = transits(at)
        doc = {"_id": date_s, "transits": tr, "computed_for": at.isoformat(), "ai": None, "ai_status": "pending", "ai_attempts": 0, "created_at": now()}
        await db.horoscopes.update_one({"_id": date_s}, {"$setOnInsert": doc}, upsert=True)
        doc = await db.horoscopes.find_one({"_id": date_s})
    tr = doc["transits"]
    readings = [rule_reading(i, tr) for i in range(12)]
    if not doc.get("ai") and doc.get("ai_attempts", 0) < 3:
        task = asyncio.create_task(_ensure_ai(date_s, tr, readings))
        _tasks.add(task)
        task.add_done_callback(_tasks.discard)
    ai = doc.get("ai") or {}
    for r in readings:
        r["ai"] = ai.get(r["sign"])
    status = "ready" if ai else "failed" if doc.get("ai_attempts", 0) >= 3 else "pending"
    return {"date": date_s, "computed_for": doc["computed_for"], "transits": tr, "signs": readings, "ai_status": status,
            "method": "Sidereal (Lahiri) transits at 06:00 IST, counted from your Moon sign (Chandra gochar)."}
