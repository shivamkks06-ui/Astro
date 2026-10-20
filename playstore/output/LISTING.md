# NakshatraVeda: Play Store kit

## Files
| Play Console field | File | Size |
|---|---|---|
| App icon | store/play-icon-512.png | 512×512 PNG |
| Feature graphic | store/feature-graphic-1024x500.png | 1024×500 |
| Phone screenshots (6) | store/phone/*.png | 1080×1920 |
| 7-inch tablet screenshots (6) | store/tablet7/*.png | 1200×1920 |
| 10-inch tablet screenshots (6) | store/tablet10/*.png | 1600×2560 |

The in-app icon, adaptive icon and splash (all densities, light and dark) are already generated in `frontend/android/app/src/main/res`. The source images are in `frontend/assets`.

Screenshots are real app screens with sample (demo) profiles; the "[DEMO]" prefix has been removed for the store images. Once real verified astrologers are live, re-capture them with `python3 screenshots.py <live-url>`.

## Store listing text (edit before publishing)
**App name (30):** NakshatraVeda: Vedic Astrology

**Short description (80):** Consult identity-verified Vedic astrologers by chat. Clear prices, private, safe.

**Full description:**
NakshatraVeda connects you with Vedic astrologers whose identity has been checked by our team.

• Verified profiles: identity verification and credential review are shown as separate badges, so you know exactly what was checked.
• Clear pricing: the per-minute rate, session length, total and refund terms are shown before you book. You pay only after the astrologer accepts.
• Chat consultations at a scheduled time slot. Audio and video calls are coming soon.
• Birth profiles: save birth details once and choose whether to share them with each astrologer.
• Fair refunds: full refund if the astrologer cancels or doesn't show up, a pro-rata refund if they end early, and a dispute window after every session.
• Safety: report or block anyone, community guidelines, and no pressure selling.
• Privacy: export your data or request account deletion at any time.

Astrology is offered as interpretive guidance only. It is not a substitute for medical, legal, financial or psychological advice, and no outcome about marriage, health, money or life events is guaranteed.

**Category:** Lifestyle · **Tags:** Astrology, Horoscope, Kundli
**Contact email / Privacy policy URL:** [your support email] / https://[your-live-domain]/legal/privacy

## Data safety form (based on the current app behaviour)
- Collected: name, email, birth date/time/place (user-provided), messages within bookings, payment transaction records (no card or UPI details), identity documents (astrologers only).
- Mic and camera are used only for consultations, and calls are not recorded.
- Data is encrypted in transit (HTTPS). Users can request deletion in the app (Account → Privacy).
- No data is sold, and no data is shared with advertisers.

## Before submitting
Release signing keystore, AAB (`./gradlew bundleRelease`), content rating questionnaire, target audience 18+, and the placeholders above filled in.
