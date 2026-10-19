# Android build (Capacitor 7)

App id `in.nakshatraveda.app`. The native project is in `frontend/android/`.

## Build a debug APK (on a Mac, Windows or x86 Linux machine with Android Studio, JDK 21 and SDK 35)
The repo already contains a pre-built web bundle in `android/app/src/main/assets/public`, so you can open `frontend/android` in Android Studio and run it right away. That bundle points at the preview backend. To point it at your live backend, rebuild:
1. In `frontend/.env`, set `REACT_APP_BACKEND_URL` to the deployed backend URL (not the preview URL).
2. `cd frontend && yarn install && yarn build && npx cap sync android`
3. `npx cap open android` and click Run, or `cd android && ./gradlew assembleDebug`. The APK is written to `android/app/build/outputs/apk/debug/`.
4. Make sure the backend `CORS_ORIGINS` includes `https://localhost` (the Android WebView origin).

## What the app does natively
- Auth: the app sends `X-Client: native`. The backend then also returns `refresh_token` in the response body, and the app keeps both tokens in Capacitor Preferences and sends `Authorization: Bearer`. The web version keeps using httpOnly cookies only.
- Permissions: the manifest declares RECORD_AUDIO, CAMERA, MODIFY_AUDIO_SETTINGS and ACCESS_NETWORK_STATE. The in-app consent dialog explains the use first, then calls `getUserMedia`, which triggers the Android runtime prompt. If access is denied, the dialog explains how to allow it in Settings.
- Offline recovery: an offline banner (@capacitor/network), automatic GET retry with backoff, data reload on reconnect and on app resume, session re-check on resume, and chat retry for failed messages.
- The Android back button navigates back, or exits the app on the root screen.

## Before Play Store release
- Signing keystore and a release build (`./gradlew bundleRelease`)
- Move tokens to an encrypted store (e.g. a secure-storage plugin). Preferences are SharedPreferences, which are not encrypted.
- App icon and splash (`@capacitor/assets`), privacy policy URL, data-safety form
