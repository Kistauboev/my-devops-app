import { useState } from "react";
import axios from "axios";

type OnboardForm = {
  repoUrl: string;
  branch: string;
};

type ApproveForm = {
  runId: string;
  token: string;
};

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export default function App() {
  const [onboard, setOnboard] = useState<OnboardForm>({
    repoUrl: "",
    branch: "main",
  });
  const [approve, setApprove] = useState<ApproveForm>({ runId: "", token: "" });
  const [onboardResult, setOnboardResult] = useState<string>("");
  const [approveResult, setApproveResult] = useState<string>("");
  const [health, setHealth] = useState<string>("");

  const checkHealth = async () => {
    try {
      const res = await axios.get(`${API_BASE}/health`);
      setHealth(JSON.stringify(res.data));
    } catch {
      setHealth("unreachable");
    }
  };

  const submitOnboard = async () => {
    try {
      const res = await axios.post(`${API_BASE}/onboard`, {
        repo_url: onboard.repoUrl,
        branch: onboard.branch,
      });
      setOnboardResult(JSON.stringify(res.data, null, 2));
    } catch (err: any) {
      setOnboardResult(err?.response?.data?.detail || "Onboard failed");
    }
  };

  const submitApprove = async () => {
    try {
      const res = await axios.post(`${API_BASE}/approve`, {
        run_id: approve.runId,
        approval_token: approve.token,
      });
      setApproveResult(JSON.stringify(res.data, null, 2));
    } catch (err: any) {
      setApproveResult(err?.response?.data?.detail || "Approve failed");
    }
  };

  return (
    <main style={styles.page}>
      <header>
        <h1>DevPlatform</h1>
        <p>Onboard repos, deploy previews, and approve production.</p>
        <button style={styles.secondaryButton} onClick={checkHealth}>
          Check backend health
        </button>
        {health && <span style={styles.badge}>Health: {health}</span>}
      </header>

      <section style={styles.card}>
        <h2>1) Onboard repository</h2>
        <label style={styles.label}>
          Repo URL
          <input
            style={styles.input}
            value={onboard.repoUrl}
            onChange={(e) =>
              setOnboard({ ...onboard, repoUrl: e.target.value })
            }
            placeholder="https://github.com/org/repo"
          />
        </label>
        <label style={styles.label}>
          Branch
          <input
            style={styles.input}
            value={onboard.branch}
            onChange={(e) => setOnboard({ ...onboard, branch: e.target.value })}
            placeholder="main"
          />
        </label>
        <button style={styles.button} onClick={submitOnboard}>
          Submit
        </button>
        {onboardResult && <pre style={styles.pre}>{onboardResult}</pre>}
      </section>

      <section style={styles.card}>
        <h2>2) Approve production deploy</h2>
        <label style={styles.label}>
          Run ID
          <input
            style={styles.input}
            value={approve.runId}
            onChange={(e) => setApprove({ ...approve, runId: e.target.value })}
            placeholder="actions run id"
          />
        </label>
        <label style={styles.label}>
          Approval token
          <input
            style={styles.input}
            value={approve.token}
            onChange={(e) => setApprove({ ...approve, token: e.target.value })}
            placeholder="from backend env"
          />
        </label>
        <button style={styles.button} onClick={submitApprove}>
          Approve
        </button>
        {approveResult && <pre style={styles.pre}>{approveResult}</pre>}
      </section>

      <section style={styles.card}>
        <h2>3) Logs (placeholder)</h2>
        <p>Embed Loki/Grafana or stream from backend once wired.</p>
      </section>

      <section style={styles.card}>
        <h2>4) Metrics (placeholder)</h2>
        <p>Embed Grafana dashboards for CPU/memory and HTTP rate/errors.</p>
      </section>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    maxWidth: 920,
    margin: "0 auto",
    padding: "2rem",
    fontFamily: "Inter, system-ui, sans-serif",
  },
  card: {
    border: "1px solid #ddd",
    borderRadius: 8,
    padding: "1.5rem",
    marginBottom: "1rem",
    background: "#fafafa",
  },
  label: {
    display: "block",
    marginBottom: ".75rem",
    fontWeight: 600,
  },
  input: {
    width: "100%",
    padding: ".5rem",
    borderRadius: 4,
    border: "1px solid #ccc",
    marginTop: ".25rem",
  },
  button: {
    padding: ".6rem 1.2rem",
    background: "#111827",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    marginTop: ".25rem",
  },
  pre: {
    background: "#111827",
    color: "#f9fafb",
    padding: ".75rem",
    borderRadius: 6,
    marginTop: ".75rem",
    fontSize: ".9rem",
    overflowX: "auto",
  },
  secondaryButton: {
    padding: ".4rem .9rem",
    marginLeft: ".5rem",
    background: "#4b5563",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
  },
  badge: {
    marginLeft: ".75rem",
    padding: ".25rem .6rem",
    background: "#e5e7eb",
    borderRadius: 6,
    fontSize: ".85rem",
  },
};
