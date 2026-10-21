"""Rule-based Kundli analysis and report built only from the computed chart."""
from datetime import datetime, timezone

from astro_calc import SIGNS, transits
from astro_extras import FRIENDS, LORD

GRAHAS = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn"]
EXALT = {"Sun": 0, "Moon": 1, "Mars": 9, "Mercury": 5, "Jupiter": 3, "Venus": 11, "Saturn": 6}
DEBIL = {k: (v + 6) % 12 for k, v in EXALT.items()}
OWN = {"Sun": [4], "Moon": [3], "Mars": [0, 7], "Mercury": [2, 5], "Jupiter": [8, 11], "Venus": [1, 6], "Saturn": [9, 10]}
MOOLA = {"Sun": (4, 0, 20), "Moon": (1, 3, 30), "Mars": (0, 0, 12), "Mercury": (5, 15, 20), "Jupiter": (8, 0, 10), "Venus": (6, 0, 15), "Saturn": (10, 0, 20)}
COMBUST = {"Moon": 12, "Mars": 17, "Mercury": 14, "Jupiter": 11, "Venus": 10, "Saturn": 15}
SPECIAL = {"Mars": [4, 8], "Jupiter": [5, 9], "Saturn": [3, 10], "Rahu": [5, 9], "Ketu": [5, 9]}
KENDRA, TRIKONA, DUSTHANA = {1, 4, 7, 10}, {1, 5, 9}, {6, 8, 12}

SIGN_TRAIT = ["direct, energetic and quick to start", "steady, practical and fond of comfort", "curious, talkative and adaptable",
              "caring, protective and emotionally deep", "confident, warm and expressive", "careful, analytical and service-minded",
              "balanced, sociable and fairness-seeking", "intense, private and determined", "optimistic, principled and freedom-loving",
              "disciplined, patient and ambitious", "independent, original and community-minded", "gentle, imaginative and compassionate"]
PLANET_THEME = {"Sun": "authority, self-confidence and public role", "Moon": "mind, emotions and nurturing", "Mars": "courage, drive and property",
                "Mercury": "communication, learning and trade", "Jupiter": "wisdom, guidance and growth", "Venus": "relationships, art and comforts",
                "Saturn": "discipline, effort and endurance", "Rahu": "ambition, unconventional paths and technology", "Ketu": "detachment, research and spirituality"}
HOUSE_THEME = ["self, body and outlook", "family, speech and savings", "courage, siblings and skills", "home, mother and inner peace",
               "intelligence, creativity and children", "work routines, service and obstacles", "partnership and marriage",
               "change, research and shared resources", "fortune, dharma and higher learning", "career, status and action",
               "gains, networks and goals", "expenses, rest and spiritual life"]
CAREER_ACT = {"Sun": "take visible responsibility; leadership, government or management roles suit this factor",
              "Moon": "work with people; care, hospitality, food or public-facing roles suit this factor",
              "Mars": "build technical or physical skills; engineering, defence, sports or property suit this factor",
              "Mercury": "sharpen writing, numbers and negotiation; trade, IT, media or accounts suit this factor",
              "Jupiter": "teach, advise or mentor; education, law, finance or counselling suit this factor",
              "Venus": "develop taste and client skills; design, arts, beauty, luxury or hospitality suit this factor",
              "Saturn": "commit to long, steady effort; operations, administration, manufacturing or service suit this factor",
              "Rahu": "learn new technology; foreign, digital or unconventional fields suit this factor",
              "Ketu": "go deep in one specialty; research, coding, healing or spiritual work suit this factor"}
REMEDY = {
    "Sun": ("ॐ ह्रां ह्रीं ह्रौं सः सूर्याय नमः", "Om Hraam Hreem Hraum Sah Suryaya Namah", "Om Suryaya Namah", "Sunday", "Offer water to the rising Sun; donate wheat or jaggery", "Wake early and spend 10 minutes in morning sunlight", "Ruby"),
    "Moon": ("ॐ श्रां श्रीं श्रौं सः चन्द्रमसे नमः", "Om Shraam Shreem Shraum Sah Chandramase Namah", "Om Chandraya Namah", "Monday", "Donate rice or milk; offer water to someone in need", "Keep a regular sleep time and call your mother or an elder", "Pearl"),
    "Mars": ("ॐ क्रां क्रीं क्रौं सः भौमाय नमः", "Om Kraam Kreem Kraum Sah Bhaumaya Namah", "Om Mangalaya Namah", "Tuesday", "Donate red lentils (masoor); give blood if you are eligible", "Exercise regularly and pause before reacting in anger", "Red coral"),
    "Mercury": ("ॐ ब्रां ब्रीं ब्रौं सः बुधाय नमः", "Om Braam Breem Braum Sah Budhaya Namah", "Om Budhaya Namah", "Wednesday", "Donate green moong or books; help a student", "Read daily and keep written notes of plans and money", "Emerald"),
    "Jupiter": ("ॐ ग्रां ग्रीं ग्रौं सः गुरवे नमः", "Om Graam Greem Graum Sah Gurave Namah", "Om Gurave Namah", "Thursday", "Donate chana dal or turmeric; teach someone for free", "Learn from a mentor and keep promises", "Yellow sapphire"),
    "Venus": ("ॐ द्रां द्रीं द्रौं सः शुक्राय नमः", "Om Draam Dreem Draum Sah Shukraya Namah", "Om Shukraya Namah", "Friday", "Donate white rice, curd or clothes", "Practise gratitude in relationships and keep a creative hobby", "Diamond or white sapphire"),
    "Saturn": ("ॐ प्रां प्रीं प्रौं सः शनैश्चराय नमः", "Om Praam Preem Praum Sah Shanaishcharaya Namah", "Om Shanaye Namah", "Saturday", "Donate black sesame or mustard oil; serve elders or workers", "Keep a fixed routine and finish pending tasks", "Blue sapphire"),
    "Rahu": ("ॐ भ्रां भ्रीं भ्रौं सः राहवे नमः", "Om Bhraam Bhreem Bhraum Sah Rahave Namah", "Om Rahave Namah", "Saturday", "Donate a blanket to someone in need", "Limit screen time and avoid shortcuts or risky speculation", None),
    "Ketu": ("ॐ स्रां स्रीं स्रौं सः केतवे नमः", "Om Sraam Sreem Sraum Sah Ketave Namah", "Om Ketave Namah", "Tuesday", "Feed street animals; support a spiritual or animal shelter", "Meditate 10 minutes daily and simplify commitments", None),
}


def _dignity(p):
    n, s = p["name"], p["sign_index"]
    if n not in EXALT:
        return "node"
    if s == EXALT[n]:
        return "exalted"
    if s == DEBIL[n]:
        return "debilitated"
    m = MOOLA[n]
    if s == m[0] and m[1] <= p["degree"] < m[2]:
        return "moolatrikona"
    if s in OWN[n]:
        return "own sign"
    lord = LORD[s]
    fr, en = FRIENDS[n]
    return "friendly sign" if lord in fr else "enemy sign" if lord in en else "neutral sign"


def _hd(a, b):
    return (b - a) % 12 + 1


def analyse(chart, at=None):
    P = {p["name"]: p for p in chart["planets"]}
    asc = chart["ascendant"]["sign_index"]
    sun = P["Sun"]
    rows = {}
    for p in chart["planets"]:
        n = p["name"]
        comb = False
        if n in COMBUST:
            d = abs((p["lon"] - sun["lon"] + 180) % 360 - 180)
            orb = COMBUST[n] - (2 if n in ("Mercury", "Venus") and p["retrograde"] else 0)
            comb = d < orb
        asp = [((p["house"] - 1 + k - 1) % 12) + 1 for k in [7] + SPECIAL.get(n, [])]
        rows[n] = {"name": n, "sign": p["sign"], "house": p["house"], "degree": p["degree"], "retrograde": p["retrograde"],
                   "dignity": _dignity(p), "combust": comb, "aspects_houses": sorted(asp),
                   "lord_of": sorted(h["house"] for h in chart["houses"] if LORD[h["sign_index"]] == n)}
    houses = []
    for h in chart["houses"]:
        lord = LORD[h["sign_index"]]
        houses.append({"house": h["house"], "sign": SIGNS[h["sign_index"]], "lord": lord, "lord_in_house": P[lord]["house"],
                       "occupants": [p["name"] for p in chart["planets"] if p["house"] == h["house"]],
                       "aspected_by": [n for n, r in rows.items() if h["house"] in r["aspects_houses"]], "theme": HOUSE_THEME[h["house"] - 1]})
    conj = {}
    for p in chart["planets"]:
        conj.setdefault(p["sign"], []).append(p["name"])
    conj = [{"sign": s, "planets": v} for s, v in conj.items() if len(v) > 1]
    lord_house = {h["house"]: h["lord"] for h in houses}
    return {"planets": rows, "houses": houses, "conjunctions": conj, "lord_house": lord_house,
            "yogas": _yogas(chart, P, rows, lord_house), "doshas": _doshas(chart, P, at)}


def _yogas(chart, P, rows, LH):
    out = []
    moon = P["Moon"]["sign_index"]
    same = lambda a, b: P[a]["sign_index"] == P[b]["sign_index"]
    def add(name, basis, meaning, needs_time=True):
        out.append({"name": name, "basis": basis, "meaning": meaning, "time_sensitive": needs_time})
    if _hd(moon, P["Jupiter"]["sign_index"]) in KENDRA:
        add("Gajakesari yoga", f"Jupiter is in house {_hd(moon, P['Jupiter']['sign_index'])} from the Moon (a kendra).",
            "Traditionally linked with good judgement, respect and support from others.", False)
    if same("Sun", "Mercury"):
        add("Budhaditya yoga", f"Sun and Mercury are together in {P['Sun']['sign']}.",
            "Traditionally linked with intelligence and communication skill; weaker if Mercury is combust.", False)
    if same("Moon", "Mars"):
        add("Chandra-Mangal yoga", f"Moon and Mars are together in {P['Moon']['sign']}.", "Traditionally linked with drive to earn and practical initiative.", False)
    for n, y in [("Mars", "Ruchaka"), ("Mercury", "Bhadra"), ("Jupiter", "Hamsa"), ("Venus", "Malavya"), ("Saturn", "Shasha")]:
        if rows[n]["dignity"] in ("exalted", "own sign", "moolatrikona") and P[n]["house"] in KENDRA:
            add(f"{y} yoga (Pancha Mahapurusha)", f"{n} is {rows[n]['dignity']} in house {P[n]['house']} (a kendra).",
                f"Traditionally strengthens {PLANET_THEME[n]}.")
    others = [p for p in chart["planets"] if p["name"] not in ("Sun", "Moon", "Rahu", "Ketu")]
    if not any(_hd(moon, p["sign_index"]) in (1, 2, 12) for p in others):
        cancelled = any(p["house"] in KENDRA for p in others)
        add("Kemadruma yoga" + (" (cancelled)" if cancelled else ""), "No planet other than the Sun and nodes is with, or next to, the Moon.",
            "Traditionally read as a need to build emotional support systems." + (" A planet in a kendra from the Lagna is a common cancellation." if cancelled else ""), cancelled)
    kl, tl = {LH[h] for h in (4, 7, 10)}, {LH[h] for h in (5, 9)}
    pairs = sorted({tuple(sorted((a, b))) for a in kl for b in tl if a != b and same(a, b)})
    for a, b in pairs:
        add("Raja yoga", f"{a} (kendra lord) and {b} (trikona lord) are together in {P[a]['sign']}.", "Traditionally linked with rise in status through effort.")
    for n in kl & tl:
        add("Yogakaraka planet", f"{n} rules both a kendra and a trikona for this Lagna.", f"Traditionally {n}'s periods support {PLANET_THEME[n]}.")
    wl, fl = {LH[2], LH[11]}, {LH[1], LH[5], LH[9]}
    dp = sorted({tuple(sorted((a, b))) for a in wl for b in fl if a != b and same(a, b)})
    for a, b in dp:
        add("Dhana yoga", f"{a} and {b} (lords of wealth and fortune houses) are together in {P[a]['sign']}.", "Traditionally linked with earning potential that grows with steady effort.")
    for h in DUSTHANA:
        if P[LH[h]]["house"] in DUSTHANA and P[LH[h]]["house"] != h:
            add("Vipareeta Raja yoga", f"Lord of house {h} ({LH[h]}) is in house {P[LH[h]]['house']}.", "Traditionally read as success that comes after difficulties.")
            break
    for n in GRAHAS:
        if rows[n]["dignity"] == "debilitated":
            disp = LORD[P[n]["sign_index"]]
            if P[disp]["house"] in KENDRA or _hd(moon, P[disp]["sign_index"]) in KENDRA:
                add("Neecha Bhanga (cancellation)", f"{n} is debilitated, but its sign lord {disp} is in a kendra from the Lagna or the Moon.",
                    f"Traditionally the weakness of {n} is softened over time.")
    return out


def _doshas(chart, P, at):
    out = []
    m = chart["manglik"]
    if m["manglik"]:
        out.append({"name": "Manglik (Kuja) dosha" + (" (traditionally cancelled)" if m["cancellations"] else ""),
                    "basis": f"Mars is in house {m['mars_house_from_lagna']} from the Lagna and house {m['mars_house_from_moon']} from the Moon.",
                    "meaning": "Traditionally checked before marriage. It is common, is often cancelled by other factors, and does not decide whether a marriage works."})
    rahu, ketu = P["Rahu"]["lon"], P["Ketu"]["lon"]
    arc = lambda x: (x - rahu) % 360 < (ketu - rahu) % 360
    sides = {arc(P[n]["lon"]) for n in GRAHAS}
    if len(sides) == 1:
        out.append({"name": "Kaal Sarp yoga", "basis": "All seven planets fall on one side of the Rahu-Ketu axis.",
                    "meaning": "A modern, debated combination. Many astrologers give it little weight; it is no reason for fear or costly rituals."})
    sat = next(p for p in transits(at or datetime.now(timezone.utc)) if p["name"] == "Saturn")
    h = _hd(P["Moon"]["sign_index"], sat["sign_index"])
    if h in (12, 1, 2):
        phase = {12: "rising (first)", 1: "peak (second)", 2: "setting (third)"}[h]
        out.append({"name": f"Sade Sati, {phase} phase", "basis": f"Saturn is now transiting {sat['sign']}, house {h} from your Moon sign.",
                    "meaning": "A roughly 7.5-year period traditionally associated with responsibility and hard work. Steady routines help; it is not a time to fear."})
    return out


def _p(t):
    return [x for x in t if x]


def report(chart, analysis, time_unknown=False):
    A, P, LH = analysis, analysis["planets"], analysis["lord_house"]
    asc, lagna_lord = chart["ascendant"], LH[1]
    moon = next(p for p in chart["planets"] if p["name"] == "Moon")
    sun = next(p for p in chart["planets"] if p["name"] == "Sun")
    cur = chart["dasha"]["current"]
    H = {h["house"]: h for h in A["houses"]}
    moon_edge = moon["degree"] < 6.6 or moon["degree"] > 23.4

    def house_line(n):
        h = H[n]
        occ = ", ".join(h["occupants"]) or "no planets"
        return f"House {n} ({h['theme']}): {h['sign']}, lord {h['lord']} in house {h['lord_in_house']}; holds {occ}."

    def pl(n):
        r = P[n]
        extra = ", combust" if r["combust"] else ""
        return f"{n} in {r['sign']} (house {r['house']}, {r['dignity']}{extra}{', retrograde' if r['retrograde'] and n not in ('Rahu', 'Ketu') else ''})"

    S = []
    def sec(id, title, facts, text, time_sensitive=False, items=None, premium=False, unavailable=None):
        S.append({"id": id, "title": title, "facts": _p(facts), "text": _p(text), "items": items or [], "premium": premium,
                  "time_sensitive": time_sensitive and time_unknown, "unavailable": unavailable or []})

    yogas, doshas = A["yogas"], A["doshas"]
    summary = _p([
        None if time_unknown else f"{asc['sign']} Lagna with its lord {pl(lagna_lord)}.",
        f"Moon in {moon['sign']} in {moon['nakshatra']} nakshatra, pada {moon['pada']}; Sun in {sun['sign']}.",
        f"Current period: {cur['mahadasha']} mahadasha, {cur['antardasha']} antardasha (mahadasha until {cur['until']})." if cur else None,
        f"{len(yogas)} traditional yoga{'s' if len(yogas) != 1 else ''} and {len(doshas)} dosha{'s' if len(doshas) != 1 else ''} identified from the calculated chart.",
    ])
    sec("overview", "Personalized overview", summary, [
        f"Your rising sign suggests a {SIGN_TRAIT[asc['sign_index']]} approach to life." if not time_unknown else None,
        f"Your Moon sign points to an inner nature that is {SIGN_TRAIT[moon['sign_index']]}.",
        "Use this report as reflective guidance, not as a prediction of fixed outcomes."])
    b = chart["birth"]
    sec("birth", "Birth details and calculation settings", [
        f"Local time {b['local'][:16].replace('T', ' ')} ({b['tz']}), UTC {b['utc'][:16].replace('T', ' ')}.",
        f"Coordinates {b['lat']:.4f}, {b['lon']:.4f}.",
        f"{chart['system']['zodiac']} zodiac, Lahiri ayanamsa {chart['system']['ayanamsa_degrees']:.4f}°, whole sign houses, mean nodes, JPL DE421 ephemeris.",
        "Birth time not known: calculated for 12:00 noon local time." if time_unknown else None], [
        "Daylight-saving time is applied automatically from the time-zone database for the birth date.",
        "Lagna, houses, house lords, yogas based on houses and the Navamsa depend on the exact birth time and are unreliable when the time is unknown." if time_unknown else None])
    sec("core", "Lagna, Rashi and Nakshatra", [
        None if time_unknown else f"Lagna: {asc['sign']} {asc['degree']:.2f}°, lord {lagna_lord}, nakshatra {asc['nakshatra']}.",
        f"Rashi (Moon sign): {moon['sign']} ({moon['rashi']}), nakshatra {moon['nakshatra']} pada {moon['pada']}, nakshatra lord {moon['nakshatra_lord']}.",
        f"Sun sign (sidereal): {sun['sign']}."], [
        None if time_unknown else f"The Lagna lord {lagna_lord} placed in house {P[lagna_lord]['house']} directs attention to {HOUSE_THEME[P[lagna_lord]['house'] - 1]}.",
        f"The nakshatra lord {moon['nakshatra_lord']} colours your temperament with themes of {PLANET_THEME[moon['nakshatra_lord']]}.",
        "Your Moon is near a sign edge, so with an unknown birth time the Moon sign and nakshatra may differ." if time_unknown and moon_edge else None], True)
    sec("charts", "Birth charts", [f"D1 Rashi chart Lagna: {asc['sign']}.", f"D9 Navamsa chart Lagna: {chart['navamsa']['ascendant']['sign']}."],
        ["Both charts are shown above; use the Rashi / Navamsa switch to change between them."], True,
        unavailable=["Other divisional charts (D10 and above)", "Shadbala and Ashtakavarga strength scores", "Bhava Chalit / unequal house systems"])
    sec("planets", "Planetary placements", [pl(n) for n in P], [
        "Conjunctions: " + "; ".join(f"{', '.join(c['planets'])} in {c['sign']}" for c in A["conjunctions"]) + "." if A["conjunctions"] else "No two planets share a sign.",
        "Dignity uses exaltation, debilitation, moolatrikona, own sign and natural friendships. Combustion uses standard orbs from the Sun."],
        True, items=[{"title": n, "rows": [["Sign", r["sign"]], ["House", r["house"]], ["Dignity", r["dignity"]], ["Combust", "yes" if r["combust"] else "no"],
                                         ["Aspects houses", ", ".join(map(str, r["aspects_houses"]))], ["Rules houses", ", ".join(map(str, r["lord_of"])) or "—"]]} for n, r in P.items()])
    sec("houses", "Twelve houses (Bhavas)", [house_line(n) for n in range(1, 13)],
        ["Aspects follow classical graha drishti: every planet aspects the 7th house from itself; Mars also the 4th and 8th, Jupiter the 5th and 9th, Saturn the 3rd and 10th, Rahu and Ketu the 5th and 9th (a common view)."],
        True, items=[{"title": f"House {h['house']}", "rows": [["Sign", h["sign"]], ["Lord", f"{h['lord']} (in house {h['lord_in_house']})"],
                      ["Planets", ", ".join(h["occupants"]) or "—"], ["Aspected by", ", ".join(h["aspected_by"]) or "—"], ["Theme", h["theme"]]]} for h in A["houses"]], premium=True)
    yd = [{"title": y["name"], "rows": [["Basis", y["basis"]], ["Meaning", y["meaning"]]] + ([["Note", "Depends on birth time"]] if y.get("time_sensitive") and time_unknown else [])} for y in yogas + doshas]
    sec("yogas", "Important yogas and doshas", [f"{len(yogas)} yoga(s) and {len(doshas)} dosha(s) found."] if yd else ["No listed yoga or dosha conditions are met in this chart."], [
        "Checked: Gajakesari, Budhaditya, Chandra-Mangal, Pancha Mahapurusha, Kemadruma, Raja, Yogakaraka, Dhana, Vipareeta Raja, Neecha Bhanga, Manglik, Kaal Sarp and current Sade Sati.",
        "A yoga shows a tendency, not a guarantee; many charts have several, and their effect depends on the whole chart and your own choices."], True, items=yd, premium=True)

    def theme(id, title, houses, karakas, extra_text):
        facts = [house_line(n) for n in houses] + [pl(k) for k in karakas]
        sec(id, title, facts, extra_text, True, premium=True)

    L10 = LH[10]
    theme("career", "Career and profession", [10, 6, 7], ["Sun", "Saturn", "Mercury"], [
        f"The 10th lord {L10} in house {P[L10]['house']} links your work with {HOUSE_THEME[P[L10]['house'] - 1]}.",
        f"Practical step: {CAREER_ACT[L10]}.",
        f"Planets in the 10th house ({', '.join(H[10]['occupants'])}) add themes of " + "; ".join(PLANET_THEME[o] for o in H[10]["occupants"]) + "." if H[10]["occupants"] else None,
        "Business (7th house) or service (6th house) both remain open; skills and effort matter more than any single placement."])
    theme("finance", "Finance and wealth", [2, 11], ["Jupiter", "Venus"], [
        f"The 2nd lord {LH[2]} and 11th lord {LH[11]} describe how savings and gains are traditionally read in this chart.",
        "Dhana yoga is present, which is traditionally encouraging for earnings built over time." if any(y["name"] == "Dhana yoga" for y in yogas) else None,
        "Practical steps: keep a monthly budget, build an emergency fund of 3-6 months of expenses, and avoid decisions based only on astrology.",
        "Nothing here promises wealth; for investments consult a qualified financial adviser."])
    theme("relationships", "Marriage and relationships", [7], ["Venus", "Jupiter"], [
        f"The 7th lord {LH[7]} in house {P[LH[7]]['house']} links partnership with {HOUSE_THEME[P[LH[7]]['house'] - 1]}.",
        f"Venus is in {P['Venus']['dignity']}, which traditionally colours how you give and receive affection.",
        "Practical steps: speak about expectations early, listen fully before replying, and make time together a routine.",
        "This chart cannot tell marriage dates, divorce or a partner's behaviour; compatibility depends on both people."])
    theme("education", "Education and personal growth", [4, 5, 9], ["Mercury", "Jupiter"], [
        f"The 5th lord {LH[5]} in house {P[LH[5]]['house']} points to learning through {HOUSE_THEME[P[LH[5]]['house'] - 1]}.",
        "Practical steps: study in focused 25-40 minute blocks, teach what you learn to someone else, and pick one skill to build each quarter."])
    theme("family", "Family, home and general well-being", [2, 4, 1], ["Moon"], [
        f"The 4th lord {LH[4]} in house {P[LH[4]]['house']} relates home life to {HOUSE_THEME[P[LH[4]]['house'] - 1]}.",
        "Supportive habits: regular sleep, daily movement, time outdoors and honest conversations at home.",
        "This report does not assess health. For any health concern, consult a qualified doctor and never stop prescribed treatment."])

    dfacts, dtext = [], []
    m = next((x for x in chart["dasha"]["mahadashas"] if "antardashas" in x), None) if cur else None
    if m:
        a = next(x for x in m["antardashas"] if x["current"])
        dfacts = [f"Mahadasha: {m['lord']} {m['start']} to {m['end']}.", f"Antardasha: {a['lord']} {a['start']} to {a['end']}."]
        nxt = [x for x in m["antardashas"] if x["start"] > a["start"]][:2]
        dfacts += [f"Next antardasha: {x['lord']} {x['start']} to {x['end']}." for x in nxt]
        i = chart["dasha"]["mahadashas"].index(m)
        if i + 1 < len(chart["dasha"]["mahadashas"]):
            n2 = chart["dasha"]["mahadashas"][i + 1]
            dfacts.append(f"Next mahadasha: {n2['lord']} from {n2['start']}.")
        dtext = [f"Dasha reading: {m['lord']} ({P[m['lord']]['dignity']}, house {P[m['lord']]['house']}) brings focus to {PLANET_THEME[m['lord']]}"
                 + (f" and the houses it rules ({', '.join(map(str, P[m['lord']]['lord_of']))})." if P[m['lord']]['lord_of'] and not time_unknown else ".")]
    tr = transits(datetime.now(timezone.utc))
    msign = moon["sign_index"]
    tfacts = [f"Today {p['name']} is in {p['sign']}, house {_hd(msign, p['sign_index'])} from your Moon." for p in tr if p["name"] in ("Jupiter", "Saturn", "Rahu")]
    sec("dasha", "Current and upcoming dasha periods", dfacts + tfacts, dtext + [
        "Transit reading: slow planets moving through houses from the Moon describe the current background; only today's real positions are used, no future positions are forecast.",
        "Dasha dates are calculated from the Moon's exact position; an unknown birth time can shift them by months." if time_unknown else None], premium=True)

    focus = []
    for n in ([cur["mahadasha"], cur["antardasha"]] if cur else []) + [n for n, r in P.items() if r["dignity"] in ("debilitated", "enemy sign") or r["combust"]]:
        if n not in focus:
            focus.append(n)
    items = []
    for n in focus[:4]:
        dev, iast, simple, day, charity, habit, _ = REMEDY[n]
        why = []
        if cur and n == cur["mahadasha"]: why.append("current mahadasha lord")
        if cur and n == cur["antardasha"]: why.append("current antardasha lord")
        r = P[n]
        if r["dignity"] in ("debilitated", "enemy sign"): why.append(f"in {r['dignity']}")
        if r["combust"]: why.append("combust")
        items.append({"title": n, "rows": [["Astrological rationale", f"{n} is " + ", ".join(why) + "."], ["Mantra", f"{dev} ({iast})"],
                      ["Simple form", simple], ["Suggested practice", f"Chant 108 times (one mala) on {day}s, or daily if you wish"],
                      ["Charity", charity], ["Free alternative", f"{habit}; chant the simple form for 5 minutes"],
                      ["Limitations", "A traditional spiritual practice; optional, with no guaranteed outcome"]]})
    if not time_unknown and P[lagna_lord]["dignity"] != "node" and REMEDY[lagna_lord][6]:
        items.append({"title": "Optional gemstone", "rows": [["Rationale", f"{lagna_lord} is your Lagna lord, the stone most often considered traditionally."],
                      ["Stone", REMEDY[lagna_lord][6]], ["Note", "Entirely optional. Mantra, charity and habits are free alternatives. Get any stone checked by a qualified expert; never buy under pressure."]]})
    sec("remedies", "Personalized traditional remedies", [f"Remedies focus on: {', '.join(focus[:4])}."] if focus else [], [
        "These are traditional spiritual practices. They are optional and are not scientifically guaranteed; no costly ritual is needed."], items=items, premium=True)
    sec("plan", "Practical action plan", [], [
        f"Career: {CAREER_ACT[L10]}.", "Money: track spending weekly and save a fixed share of income first.",
        "Relationships: one honest, unhurried conversation each week with the people closest to you.",
        "Learning: choose one skill for the next 90 days and practise it daily.",
        f"Inner balance: {REMEDY[focus[0]][5] if focus else 'meditate 10 minutes daily'}."], premium=True)
    sec("disclaimer", "Disclaimer and calculation limitations", [], [
        "Planet positions, houses, dashas and yogas are calculated from your birth details; the explanations are traditional interpretations, not facts or predictions.",
        "Not available: Shadbala, Ashtakavarga, divisional charts beyond D9 and future transit forecasts.",
        "Do not make medical, legal, financial or relationship decisions based only on astrology. Consult qualified professionals."])
    return {"summary": summary, "time_unknown": time_unknown, "sections": S}
