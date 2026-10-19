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
      <div data-testid="app-crash-screen" style={{ minHeight: "100vh", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 16, padding: 24, background: "#0B0F19", color: "#F8FAFC", fontFamily: "sans-serif", textAlign: "center" }}>
        <p style={{ color: "#E6B325", fontSize: 18 }}>Something went wrong while loading the app.</p>
        <p style={{ fontSize: 12, color: "#94A3B8", maxWidth: 360, wordBreak: "break-word" }}>{String(this.state.error?.message || this.state.error)}</p>
        <button data-testid="app-crash-reload" onClick={() => window.location.reload()} style={{ padding: "10px 20px", borderRadius: 999, background: "#E6B325", color: "#0B0F19", border: 0 }}>Reload</button>
      </div>
    );
  }
}
