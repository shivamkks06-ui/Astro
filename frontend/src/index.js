import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import "@/index.css";
import App from "@/App";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { BACKEND_MISSING } from "@/lib/api";

const ConfigError = () => (
  <div data-testid="app-config-error" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12, padding: 24, background: "#0B1225", color: "#F8F7F2", fontFamily: "sans-serif", textAlign: "center" }}>
    <p style={{ color: "#D4AF37", fontSize: 18 }}>This build is missing its server address.</p>
    <p style={{ fontSize: 13, color: "#B9C2D3", maxWidth: 380 }}>Set REACT_APP_BACKEND_URL in frontend/.env, then run: yarn build:android</p>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 60_000,
      refetchOnWindowFocus: false,
    },
  },
});

// keep the focused field visible above the Android soft keyboard
document.addEventListener("focusin", (e) => {
  const el = e.target;
  if (window.innerWidth < 768 && el.matches?.("input:not([type=checkbox]):not([type=radio]), textarea")) {
    setTimeout(() => el.scrollIntoView({ block: "center", behavior: "smooth" }), 300);
  }
});

const root = ReactDOM.createRoot(document.getElementById("root"));
root.render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        {BACKEND_MISSING ? <ConfigError /> : <App />}
      </ErrorBoundary>
    </QueryClientProvider>
  </React.StrictMode>,
);
