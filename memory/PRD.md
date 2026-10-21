# NakshatraVeda: Vedic Astrology & Verified Astrologer Marketplace

## Original problem statement
Build a responsive Indian astrology marketplace with Android compatibility (React + Capacitor), a secure backend and a relational database. Roles: customers, astrologers, administrators. Business model: paid astrologer listings (Monthly ₹299 / Quarterly ₹799, admin-editable), commission on completed paid consultations (default 25%), and premium reports later. Modes: chat, audio, video. Requirements include: server-side authorization; astrologer onboarding with private documents and identity verification kept separate from credential verification; paid listings verified server-side; a booking state machine (requested, accepted, payment_pending, confirmed, in_progress, completed, cancelled, expired, disputed) with double-booking prevention and immutable price snapshots; chat/audio/video behind a provider abstraction (not operational without credentials); a payment and commission engine with integer paise, idempotency, verified webhooks and a double-entry ledger; admin-reviewed payouts; an admin dashboard; safety, privacy and consent; and the 14 acceptance tests. Execution phases 1 to 7. (The full original text is in the first user message.)

## User choices
- DB: MongoDB with enforced constraints (unique and partial indexes, JSON-schema validators, versioned migrations)
- Payments: build the provider boundary now, plug a real provider in later. MOCK sandbox provider active
- Auth: email/password JWT (httpOnly cookies plus a Bearer token for Capacitor)
- Calls: no credentials. Boundary only, clearly NOT operational
- Scope: phases 1 to 5 now, plus basic chat and the call boundary

## Architecture
- backend: core.py (db, auth deps, audit, rate limits, settings), migrations.py (001 indexes, 002 validators, 003 seed config, admin seed), ledger.py (append-only balanced journals with idempotent keys and deterministic entry ids; astrologer balances), finance.py (PaymentProvider boundary + MockSandboxProvider with HMAC webhooks, booking state machine, settlements, refunds, disputes, payouts, 60s sweep), storage.py (Emergent object storage, private), routes_auth/user/astrologer/bookings/admin.py
- frontend: React + shadcn, dark celestial theme; pages: Landing, Discover, AstrologerPage, Auth, Legal, PayPage (MOCK banner), BookingPage (chat polling, actions, extensions), CustomerDashboard, AstrologerDashboard (Studio), AdminDashboard (18 tabs, generic DataTable with CSV)

## User personas
Customer seeking guidance; independent astrologer; platform admin/finance/safety reviewer.

## Implemented (2026-10-19)
- Auth, roles, lockout (per IP plus per account), origin guard, audit logs, account suspension
- Astrologer profile, private KYC/credential uploads, separate verification cases, admin approve/reject/resubmit, 5-min audited document links
- Listing plans (admin-editable), subscriptions activated only by a verified webhook, extension from current expiry, cancel-at-period-end, admin refund
- Slots, bookings with server price snapshot, slot-claim atomicity plus unique partial index, full state machine, cancellation windows, no-show, partial-session pro-rata, extension consent and payment, unconnected calls never charged
- Double-entry ledger, 25% configurable commission, tax-on-commission setting, gateway fees, refunds via reversal journals, dispute hold, reconciliation, eligible-balance payouts (one open per astrologer), MOCK settlement webhooks, finance summary and commission report
- Polling chat (participants only, live sessions only, rate limited, idempotent client ids); call-token endpoint returns 503 "not operational"
- Reviews (completed and attended bookings only), reports, blocks, privacy toggles, data export, deletion request with admin anonymisation, legal pages, disclaimers
- Tests: 38/38 backend tests (tests/test_marketplace_e2e.py, test_chat_extras.py, test_iteration2_changes.py) plus frontend flows

## Implemented (2026-10-19), Android shell
- Capacitor 7 Android project (frontend/android, appId in.nakshatraveda.app); manifest declares mic, camera and network permissions
- Native auth: X-Client: native gets refresh_token in the body, which rotates on refresh; tokens are kept in Capacitor Preferences and sent as Bearer. The web version stays cookie-only
- Mic/camera consent dialog before the Android runtime prompt, with recovery steps if denied
- Offline banner, reload on reconnect/resume, GET retry on network errors, back-button handling, session re-check on resume
- APK NOT built: the container is ARM64 and Android's aapt2 tool doesn't run on ARM Linux. Build steps are in frontend/ANDROID.md

## Implemented (2026-10-20), Android/mobile optimisation
- Single Back handler (NativeShell in lib/native.js): closes the top Radix overlay first, then goes back one history step (RR idx), goes to home if there is no history, and minimises at home (never exits)
- History fixes: login, register and logout use replace; login from a profile steps back instead of duplicating it; PayPage returns with history -1
- Responsive: 30px hero on mobile, full-width 48px CTAs, tighter spacing, grid-cols-1 fix for the 320px overflow, xs text is 13px, 44px touch targets (buttons, inputs, selects, tabs, chips, sheet close), no blur on mobile
- Cards show next_slot_at availability (new API field) and a book CTA
- Native: values-v35 edge-to-edge opt-out with dark bars, adjustMarginsForEdgeToEdge auto, adjustResize; silent data refresh on resume/reconnect

## Implemented (2026-10-20), Astrologer profile photos
- POST/DELETE /api/astrologer/photo: JPG/PNG/WEBP up to 5 MB, at least 200px; re-encoded to a 512px WEBP with EXIF stripped; versioned public URL /api/astrologers/{id}/photo?v= (old versions 404)
- Cards, profile page and studio show the photo (Avatar), falling back to initials; admin can remove a photo with a reason (audited), and the astrologer sees the reason

## Implemented (2026-10-20), Native-feel Android UI
- Mobile bottom tab bar (role-aware), dialogs become Android bottom sheets on phones (44px close, 92dvh scroll), centred with 90dvh scroll on larger screens
- LoginSheet: login in place on the astrologer profile with inline validation; chat/audio/video and book actions open login or booking; register keeps ?next without duplicate history
- Profile redesign: photo, badges, real stat cards (experience, rating, next slot, from-price), section chips, sticky mobile book bar
- Skeleton loaders, press feedback (active:scale), opacity-only screen transition, @capacitor/haptics on key actions
- Note: the testing agent's cleanup wiped the preview DB on 2026-10-20; it was reseeded with demo data (production DB unaffected)

## Implemented (2026-10-20), Drawer + old-WebView fix
- Root cause: Chrome <87 WebViews ignore the CSS `inset` shorthand, so the hero image, drawer and overlays weren't anchored. Fixed with scripts/postcss-inset-fallback.js, appended to CRA's postcss-loader in craco.config.js webpack.configure
- Drawer: min(84vw,320px), brand row, 48px aligned links, stacked full-width Log in/Join, trust card at the bottom, safe-area insets, black/50 backdrop, no focus ring on open

## Implemented (2026-10-20), Android Back exit + Discover state
- Root-screen double-press exit: the first Back shows "Press back again to exit" (bottom, above the nav); a second press within 2 s calls App.exitApp(); after 2 s it re-arms. Nested screens with no history go home and never exit
- Discover filters, sort and page live in the URL (replace), so Back from a profile restores them; clear-filters; singular/plural count
- useApi ignores out-of-order responses; Avatar falls back to initials on error; image width/height set
- Audit: no immersive/fullscreen flags, Recent Apps untouched; dev-only window.__nvBack for QA (not in the production bundle)

## Implemented (2026-10-20), Brand system & Android icon/splash
- Exact palette tokens (#0B1225/#111B32/#16223B, gold #D4AF37/#F4D675, text #F8F7F2/#B9C2D3); Tailwind amber scale remapped to brand gold; Noto Sans Devanagari fallback; gold focus ring
- Title/description/OG/Twitter meta, favicon, apple-touch-icon, manifest.json, og-image
- Header/drawer: mandala mark + NAKSHATRAVEDA wordmark + tagline; drawer closes on route change
- Assets built from the user's logo artwork (playstore/build_assets.py): simplified yantra mark for favicon/launcher/adaptive foreground; splash = full mandala + wordmark + tagline; Android resources regenerated via @capacitor/assets; Play Store kit zip + screenshots regenerated
- Hero image compressed (829KB -> 389KB)
- Deferred by user: Daily Horoscope, Kundli, compatibility, AI reports, premium plans (future phase)

## Implemented (2026-10-20), Daily Horoscope & Kundli
- Backend: astro_calc.py (Skyfield + JPL DE421, Lahiri ayanamsa, mean nodes, whole-sign houses, Ascendant, nakshatra/pada, Vimshottari maha/antar dasha); data/cities.json (6,171 GeoNames cities, 3,783 Indian, offline) + OpenStreetMap Nominatim fallback with timezonefinder; routes_astro.py: /api/places, /api/kundli/calculate, /api/kundlis CRUD (per user, max 100), /api/horoscope/daily (IST yesterday/today/tomorrow)
- horoscope.py: Chandra-gochar rule readings (career/relationships/health/finance + basis) always; Claude Sonnet 4.5 (Emergent key) writes the "AI interpretation" once per date, cached in db.horoscopes, max 3 attempts, rule fallback
- Frontend: /horoscope (sign picker persisted, day tabs, AI vs calculated labels, tone badges, transit list), /kundli (birth form, place search, North SVG + South grid charts, planet table, dasha, save/history, /kundli/:id), 5-tab bottom nav, header links, landing quick tiles
- Tests: iteration_14 (backend 17/17, frontend all flows, 101/101 regression); low-priority follow-ups fixed afterwards

## Implemented (2026-10-20), Kundli extras
- astro_extras.py: Navamsa (D9) chart, Panchang at birth (tithi/paksha, vara by sunrise, yoga, karana, sunrise via Skyfield almanac), Manglik check (Lagna and Moon, own sign/exalted cancellations), Ashtakoota 36 Guna Milan (8 kootas, Nadi/Bhakoot dosha)
- API: chart now includes navamsa/panchang/manglik; POST /api/kundli/match
- Frontend: D1/D9 toggle, Panchang + Manglik cards, Share (native share or clipboard), Print/PDF (web only, print CSS), /kundli/match two-step page
- Tests: iteration_15 (backend 29/29, all flows); then fixed the Gana Ardra data, prefill when editing the boy's details, and the mobile match table

## Implemented (2026-10-20), Hindi mode for astrology results
- frontend/src/lib/i18n.js: built-in Hindi dictionary (planets, signs, nakshatras, tithis, yogas, karanas, kootas, yoni/gana/nadi, labels, rule-based horoscope sentences); useLang() hook with t()/tp(), saved in localStorage nv:lang, sets html[lang]
- LangToggle (English | हिन्दी) on /kundli, /kundli/match, /horoscope; charts, tables, panchang, manglik, dasha, match and horoscope fully switch; AI horoscope text stays English (labelled)
- No backend change and no AI cost; Devanagari letter-spacing fix. Tested in iteration_16; leftovers fixed afterwards
- Not translated by design: header, menus, booking and account pages

## Implemented (2026-10-20), Mobile UI fixes and functional audit
- Login/Register: in-app validation (noValidate, role=alert), password show/hide toggle, spinner, double-submit guard
- Inputs: 48px mobile height, darker field background, stronger border, gold focus border, dark date/time pickers
- Global focusin handler keeps the focused field above the Android keyboard (<768px)
- Kundli: birth-year range validation; Horoscope: spinner while AI is pending and brighter calculated text; AstroCard: gold primary "View profile & book"
- Tests: iteration_17 33/33 (mobile); the user's screenshots were not attached, so the audit was done at 390px

## Implemented (2026-10-21), Detailed Kundli report & remedies
- astro_report.py: dignity (exalted/debilitated/moolatrikona/own/friend/neutral/enemy), combustion, graha drishti, house lords, conjunctions; yogas (Gajakesari, Budhaditya, Chandra-Mangal, Pancha Mahapurusha, Kemadruma, Raja, Yogakaraka, Dhana, Vipareeta Raja, Neecha Bhanga); doshas (Manglik, Kaal Sarp, Sade Sati from today's Saturn); 16-section rule-based report with remedies (Navagraha beej mantras, charity, free alternatives, optional gemstone only for the Lagna lord) and an action plan
- "I don't know my exact birth time" (time_unknown; uses 12:00, flags time-sensitive sections, no gemstone)
- Optional AI interpretation for saved charts only: POST /api/kundlis/{id}/ai-report (owner only, Claude Sonnet 4.5, cached on the doc, lock, 5/hour)
- FullReport.jsx: summary, Read full report, expandable sections with Calculated / Traditional / AI labels; PREMIUM_LOCK flag present but OFF
- Not supported (shown as unavailable): Shadbala, Ashtakavarga, D10+, future transit forecasts
- Tests: iteration_18 (backend 41/41, frontend all flows); minor follow-ups fixed afterwards

## Known limitations
- Payments are MOCKED (mock_sandbox). A real provider (e.g. Razorpay with Route for marketplace splits) must be confirmed and plugged into finance.PaymentProvider
- Audio/video NOT operational (no SDK credentials)
- Standalone MongoDB has no multi-document transactions; idempotent keys and deterministic entries are used instead. Move to a replica set or Atlas for transactions
- No password reset or email yet; receipts are not GST invoices; Android/Capacitor build not started
- Per-account lock (20 failures) could be abused to lock out a user; consider CAPTCHA or progressive delay

## Backlog
- P0: Real payment provider integration (Razorpay), Android Capacitor build, password reset email
- P1: Audio/video SDK (Agora/100ms) with server tokens and connection webhooks; WebSocket chat; GST invoices
- P2: Premium astrology reports, notifications, analytics

## Next tasks
Connect a real payment gateway, then the Capacitor Android shell.
