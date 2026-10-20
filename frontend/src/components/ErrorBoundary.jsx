import React from "react";

export class ErrorBoundary extends React.Component {
  state = { error: null };

  static getDerivedStateFromError(error) {
    return { error };
  }

  componentDidCatch(error) {
    console.error("App crashed:", error);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div data-testid="app-crash-screen" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, padding: 24, background: "#0B1225", color: "#F8F7F2", fontFamily: "sans-serif", textAlign: "center" }}>
        <p style={{ color: "#D4AF37", fontSize: 18 }}>Something went wrong while loading the app.</p>
        <p style={{ fontSize: 13, color: "#B9C2D3", maxWidth: 360 }}>Please check your connection and tap Reload. If it keeps happening, reinstall the latest version.</p>
        <p style={{ fontSize: 11, color: "#7C879C", maxWidth: 360, wordBreak: "break-word" }}>{String(this.state.error?.message || this.state.error)}</p>
        <button data-testid="app-crash-reload" onClick={() => window.location.reload()} style={{ padding: "10px 20px", borderRadius: 999, background: "#D4AF37", color: "#0B1225", border: 0, minHeight: 44, fontWeight: 600 }}>Reload</button>
      </div>
    );
  }
}
