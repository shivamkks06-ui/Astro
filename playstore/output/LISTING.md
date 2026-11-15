# NakshatraVeda — Google Play Console kit (A to Z)

Fill each Play Console section in the order below. Text in [brackets] must be filled by you.

---

## 1. Graphics (Main store listing → Graphics)
| Play Console field | File | Size |
|---|---|---|
| App icon | store/play-icon-512.png | 512×512 PNG |
| Feature graphic | store/feature-graphic-1024x500.png | 1024×500 |
| Phone screenshots (8) | store/phone/*.png | 1080×1920 |
| 7-inch tablet screenshots (8) | store/tablet7/*.png | 1200×1920 |
| 10-inch tablet screenshots (8) | store/tablet10/*.png | 1600×2560 |

Screenshot order: 01 Home (Shubh Din) · 02 Kundli report · 03 Astro AI · 04 Discover · 05 Astrologer profile · 06 Booking · 07 Account · 08 Astrologer studio.
Screens are real app screens with demo/sample data ("[DEMO]" prefix removed).

---

## 2. Store listing text (Main store listing)
**App name (max 30):** NakshatraVeda: Kundli & Astro

**Short description (max 80):**
Detailed Kundli, daily Panchang, Astro AI and verified Vedic astrologers.

**Full description (max 4000):**
NakshatraVeda brings authentic Vedic astrology to your phone: a detailed Kundli calculated from real planetary positions, a daily Shubh Din Panchang, Astro AI that answers questions about your own chart, and consultations with astrologers whose identity has been checked.

KUNDLI & REPORTS
• Free Kundli from your birth date, time and place (India and worldwide cities).
• North and South Indian charts, Lagna, planets with degrees, nakshatra and pada.
• Navamsa (D9) and Dashamsha (D10), current Vimshottari dasha.
• Detailed report: 12 houses, 9 planets, yogas, Manglik and other doshas, and remedies with a daily routine.
• Kundli matching (Ashtakoota 36 Guna Milan) and Manglik check.
• Download your full report as a PDF to keep or share.
• Full report in Hindi with one tap.

DAILY GUIDANCE
• Shubh Din card: today's tithi, nakshatra, Abhijit and Brahma Muhurat and Rahu Kaal for your own city.
• Daily horoscope for every rashi.

ASTRO AI
• Ask questions about your saved Kundli: career, marriage, dasha and more.
• Answers in Hindi or English, based on your real chart, and read aloud on tap.

VERIFIED ASTROLOGERS
• Identity verification and credential review shown as separate badges.
• See who is online now, their experience, completed consultations and customer ratings.
• Clear price, session length and refund terms before you book. Pay securely by UPI, card or netbanking.
• Fair refunds: full refund if the astrologer cancels or does not join.

SAFETY & PRIVACY
• Report or block anyone; community guidelines for everyone.
• Choose whether to share your birth details with each astrologer.
• Export your data or request account deletion at any time.
• Sign in with email or Google.

Astrology is offered as interpretive guidance only. It is not a substitute for medical, legal, financial or psychological advice, and no outcome about marriage, health, money or life events is guaranteed. AI answers are clearly labelled as AI interpretation.

**App category:** Lifestyle
**Tags:** Astrology, Horoscope, Lifestyle
**Contact email:** [your support email, e.g. shivamkks9088@outlook.com]
**Website:** https://guru-astro-hub.emergent.host
**Privacy policy URL:** https://guru-astro-hub.emergent.host/legal/privacy

---

## 3. App content (Policy → App content) — answers

### Privacy policy
URL: https://guru-astro-hub.emergent.host/legal/privacy

### App access
Select: **All or some functionality is restricted** → Add instructions:
- Name: Demo customer — Username: demo.customer@nakshatraveda.test — Password: DemoPass@123
- Name: Demo astrologer — Username: demo.astro1@nakshatraveda.test — Password: DemoPass@123
- Notes: "Log in with email and password. Kundli, Astro AI and bookings are under the bottom menu."
Check that these demo accounts exist on the live app before submitting (run seed_demo.py on live or create them by signing up). Do not use your admin account here.

### Ads
**Does your app contain ads?** No.

### Content rating (IARC questionnaire)
- Email: [your email]
- Category: **All other app types** (not a game, not social/communication-only)
- Violence: No · Fear/horror: No · Sexuality/nudity: No · Profanity/crude humour: No
- Controlled substances (drugs, alcohol, tobacco): No
- Gambling (real or simulated): No
- Hate speech / discrimination: No
- **Users can interact or exchange content with other users?** Yes (chat with astrologers during booked consultations; report and block are available)
- **Shares user's current physical location with other users?** No (birthplace is typed, not GPS)
- **Allows users to purchase digital goods?** Yes (paid consultations and astrologer listing plans)
- Unrestricted web access / browser: No
- Expected result: Everyone / PEGI 3 to Teen / 12+ with notices "Users Interact, In-App Purchases". Accept whatever IARC gives.

### Target audience and content
- Target age groups: **18 and over** only.
- Appeals to children? No.

### News app
No.

### COVID-19 contact tracing / status app
No.

### Data safety
**Does your app collect or share user data?** Yes.
**Is all data encrypted in transit?** Yes (HTTPS).
**Can users request deletion?** Yes — in app: Account → Privacy → Request deletion. Deletion URL: https://guru-astro-hub.emergent.host/account

| Data type (Play category) | Collected | Shared | Required/Optional | Purpose |
|---|---|---|---|---|
| Name | Yes | No | Required | Account management, App functionality |
| Email address | Yes | No | Required | Account management, App functionality |
| User IDs | Yes | No | Required | Account management |
| Other info (birth date, time and place) | Yes | No | Optional | App functionality (Kundli, matching) |
| Purchase history | Yes | No | Required for bookings | App functionality, Fraud prevention |
| In-app messages | Yes | No | Optional | App functionality (consultation chat, Astro AI questions) |
| Photos | Yes (astrologers only) | No | Optional | App functionality (profile photo) |
| Files and docs | Yes (astrologers only) | No | Required for astrologers | Fraud prevention, security (identity verification) |
| Approximate/precise location | **No** | — | — | — |
| Contacts, SMS, call logs, calendar | **No** | — | — | — |
| Device or other IDs, analytics | **No** | — | — | — |
| Financial info (card/UPI numbers) | **No** — handled by Razorpay, never stored by the app | — | — | — |

Notes for the form:
- "Shared" = No: payment processing (Razorpay), AI answers (chart facts and questions sent to the AI service) and Google sign-in are service providers acting for you, which Google does not count as sharing.
- Data is not sold and not used for advertising.
- Data is processed ephemerally? No (it is stored).

### Government apps
No.

### Financial features
Select **My app doesn't provide any financial features** (it only takes payments for its own services).

### Health
Select **My app does not have any health features**.

### Permissions (if Play asks)
- RECORD_AUDIO, CAMERA, MODIFY_AUDIO_SETTINGS: used for consultation calls. Audio/video calls are still "coming soon" in the app; if the reviewer flags unused permissions, remove these three lines from AndroidManifest.xml until calls go live.
- INTERNET, ACCESS_NETWORK_STATE: normal.

---

## 4. Release (Test and release)
1. In Android Studio: Build → Generate Signed App Bundle → AAB, signed with your release keystore (keep the keystore and passwords safe; losing them blocks future updates).
2. Enrol in **Play App Signing** (default).
3. Copy the **App signing key SHA-1** (Play Console → Test and release → App integrity) into your Google Cloud **Android OAuth client** for package `in.nakshatraveda.app`, otherwise Google sign-in fails in the Play build.
4. New personal developer accounts must run a **Closed test with at least 12 testers for 14 days** before Production access.
5. Create release → upload the AAB → release notes:
   "First release: detailed Kundli with D9/D10 and remedies, Hindi report, Shubh Din Panchang with Rahu Kaal, Astro AI chat, verified astrologer consultations with secure payments."
6. Countries: India (add others as you like). Pricing: Free.

---

## 5. Before you press "Send for review"
- [ ] Razorpay live keys and webhook secret set, then the live app re-published.
- [ ] Demo accounts work on the live app.
- [ ] Support email and privacy policy URL open correctly.
- [ ] Target SDK 36 build installs and opens on a real phone.
- [ ] Google sign-in tested on the Play-signed build.
