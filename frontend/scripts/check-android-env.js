// Fails the Android build early if the backend URL isn't configured (.env is not part of the code download).
const fs = require("fs");
const path = require("path");

const fromFile = (f) => {
  const p = path.join(__dirname, "..", f);
  if (!fs.existsSync(p)) return null;
  const m = fs.readFileSync(p, "utf8").match(/^REACT_APP_BACKEND_URL\s*=\s*"?([^"\r\n]+)"?/m);
  return m ? m[1].trim() : null;
};

const envSet = Object.prototype.hasOwnProperty.call(process.env, "REACT_APP_BACKEND_URL");
// CRA won't override an existing (even empty) env var with .env, so an empty one means an empty build
const url = envSet ? process.env.REACT_APP_BACKEND_URL : fromFile(".env.production.local") || fromFile(".env.production") || fromFile(".env");
if (!url || !/^https:\/\/[^\s]+$/.test(url) || /localhost|127\.0\.0\.1/.test(url)) {
  console.error("\n[build:android] REACT_APP_BACKEND_URL is missing or invalid.");
  console.error("Create frontend/.env with:  REACT_APP_BACKEND_URL=https://<your-live-domain>\n");
  process.exit(1);
}
console.log(`[build:android] Backend: ${url}`);
