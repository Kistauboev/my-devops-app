import React, { Component, ErrorInfo, ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("React Error Boundary caught an error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div style={{
          padding: "2rem",
          maxWidth: "800px",
          margin: "0 auto",
          fontFamily: "system-ui, sans-serif",
        }}>
          <h1 style={{ color: "#dc2626" }}>Something went wrong</h1>
          <p>The application encountered an error. Please refresh the page.</p>
          <details style={{ marginTop: "1rem", padding: "1rem", background: "#f3f4f6", borderRadius: "4px" }}>
            <summary style={{ cursor: "pointer", fontWeight: 600 }}>Error details</summary>
            <pre style={{ marginTop: "0.5rem", fontSize: "0.85rem", overflow: "auto" }}>
              {this.state.error?.toString()}
            </pre>
          </details>
          <button
            onClick={() => window.location.reload()}
            style={{
              marginTop: "1rem",
              padding: "0.6rem 1.2rem",
              background: "#111827",
              color: "#fff",
              border: "none",
              borderRadius: "6px",
              cursor: "pointer",
            }}
          >
            Refresh Page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;

