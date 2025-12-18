import { useState, useEffect, useRef } from "react";
import axios from "axios";
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

type OnboardForm = {
  repoUrl: string;
  branch: string;
};

type ApproveForm = {
  runId: string;
  token: string;
};

type MetricsData = {
  namespace: string;
  pods: Array<{
    name: string;
    cpu: string;
    cpu_value: number;
    memory: string;
    memory_value: number;
  }>;
  http_metrics: {
    requests_per_minute: number;
    total_requests: number;
    error_requests: number;
    error_rate: number;
  };
  timestamp: string;
};

// Auto-detect API base URL based on current hostname
// If accessed via network IP, use that IP for API; otherwise use localhost
const getApiBase = () => {
  if (import.meta.env.VITE_API_BASE) {
    return import.meta.env.VITE_API_BASE;
  }
  // If accessed via network IP, use the same hostname for API
  const hostname = window.location.hostname;
  if (hostname !== "localhost" && hostname !== "127.0.0.1") {
    return `http://${hostname}:8000`;
  }
  return "http://localhost:8000";
};

const API_BASE = getApiBase();

export default function App() {
  const [onboard, setOnboard] = useState<OnboardForm>({
    repoUrl: "",
    branch: "main",
  });
  const [approve, setApprove] = useState<ApproveForm>({ runId: "", token: "" });
  const [onboardResult, setOnboardResult] = useState<string>("");
  const [onboardLoading, setOnboardLoading] = useState<boolean>(false);
  const [approveResult, setApproveResult] = useState<string>("");
  const [health, setHealth] = useState<string>("");
  const [logs, setLogs] = useState<string>("");
  const [streamingLogs, setStreamingLogs] = useState<boolean>(false);
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [metricsHistory, setMetricsHistory] = useState<Array<MetricsData>>([]);
  const [logsNamespace, setLogsNamespace] = useState<string>("default");
  const [metricsNamespace, setMetricsNamespace] = useState<string>("default");
  const [loadingLogs, setLoadingLogs] = useState<boolean>(false);
  const [loadingMetrics, setLoadingMetrics] = useState<boolean>(false);
  const eventSourceRef = useRef<EventSource | null>(null);

  const checkHealth = async () => {
    try {
      const res = await axios.get(`${API_BASE}/health`);
      setHealth(JSON.stringify(res.data, null, 2));
    } catch (err: any) {
      const errorMsg = err?.response 
        ? `Error ${err.response.status}: ${JSON.stringify(err.response.data)}`
        : err?.request
        ? `Cannot connect to ${API_BASE}. Is backend running?`
        : `Error: ${err?.message || "Unknown error"}`;
      setHealth(`unreachable - ${errorMsg}`);
      console.error("Health check failed:", err);
    }
  };

  const submitOnboard = async () => {
    setOnboardLoading(true);
    setOnboardResult(""); // Clear previous result
    try {
      const res = await axios.post(`${API_BASE}/onboard`, {
        repo_url: onboard.repoUrl,
        branch: onboard.branch,
      });
      setOnboardResult(JSON.stringify(res.data, null, 2));
    } catch (err: any) {
      console.error("Onboard error:", err);
      const errorDetail = err?.response?.data?.detail || err?.response?.data?.message || err?.message || "Onboard failed";
      setOnboardResult(`❌ Error: ${errorDetail}\n\nFull response: ${JSON.stringify(err?.response?.data || {}, null, 2)}`);
    } finally {
      setOnboardLoading(false);
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

  const fetchLogs = async () => {
    setLoadingLogs(true);
    try {
      const res = await axios.get(`${API_BASE}/logs`, {
        params: { namespace: logsNamespace, lines: 100 },
      });
      setLogs(res.data.logs || JSON.stringify(res.data, null, 2));
    } catch (err: any) {
      setLogs(err?.response?.data?.detail || "Failed to fetch logs");
    } finally {
      setLoadingLogs(false);
    }
  };

  const startLogStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    setStreamingLogs(true);
    setLogs(""); // Clear existing logs

    const eventSource = new EventSource(
      `${API_BASE}/logs/stream?namespace=${logsNamespace}`
    );

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.logs) {
          setLogs((prev) => prev + data.logs + "\n");
        } else if (data.error) {
          setLogs((prev) => prev + `[ERROR] ${data.error}\n`);
        }
      } catch (err) {
        console.error("Failed to parse log event:", err);
      }
    };

    eventSource.onerror = (err) => {
      console.error("EventSource error:", err);
      eventSource.close();
      setStreamingLogs(false);
    };

    eventSourceRef.current = eventSource;
  };

  const stopLogStreaming = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStreamingLogs(false);
  };

  const fetchMetrics = async () => {
    setLoadingMetrics(true);
    try {
      const res = await axios.get(`${API_BASE}/metrics`, {
        params: { namespace: metricsNamespace },
      });
      const metricsData = res.data as MetricsData;
      setMetrics(metricsData);
      // Keep last 20 data points for history
      setMetricsHistory((prev) => {
        const updated = [...prev, metricsData];
        return updated.slice(-20);
      });
    } catch (err: any) {
      console.error("Failed to fetch metrics:", err);
      // Show error to user
      if (err?.response) {
        console.error("Backend responded with:", err.response.status, err.response.data);
      } else if (err?.request) {
        console.error("No response from backend. Is it running?");
      } else {
        console.error("Error setting up request:", err.message);
      }
    } finally {
      setLoadingMetrics(false);
    }
  };

  // Auto-refresh metrics every minute
  useEffect(() => {
    fetchMetrics(); // Initial fetch
    const interval = setInterval(fetchMetrics, 60000); // Every 60 seconds
    return () => clearInterval(interval);
  }, [metricsNamespace]);

  // Cleanup event source on unmount
  useEffect(() => {
    return () => {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
      }
    };
  }, []);

  // Prepare chart data
  const cpuChartData = metricsHistory
    .filter((m) => m.pods && m.pods.length > 0)
    .map((m, idx) => ({
      time: idx,
      ...Object.fromEntries(
        m.pods.map((pod) => [pod.name, pod.cpu_value || 0])
      ),
    }));

  const memoryChartData = metricsHistory
    .filter((m) => m.pods && m.pods.length > 0)
    .map((m, idx) => ({
      time: idx,
      ...Object.fromEntries(
        m.pods.map((pod) => [pod.name, pod.memory_value || 0])
      ),
    }));

  const httpRateData = metricsHistory.map((m, idx) => ({
    time: idx,
    requestsPerMinute: m.http_metrics?.requests_per_minute || 0,
    errorRate: (m.http_metrics?.error_rate || 0) * 100,
  }));

  return (
    <main style={styles.page}>
      <header>
        <h1>DevPlatform</h1>
        <p>Onboard repos, deploy previews, and approve production.</p>
        <button style={styles.secondaryButton} onClick={checkHealth}>
          Check backend health
        </button>
        {health && <pre style={styles.healthBadge}>{health}</pre>}
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
        <button 
          style={styles.button} 
          onClick={submitOnboard}
          disabled={onboardLoading}
        >
          {onboardLoading ? "Submitting..." : "Submit"}
        </button>
        {onboardLoading && <p style={{color: "#666", marginTop: "0.5rem"}}>Processing...</p>}
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
        <h2>3) Logs (Real-time Streaming)</h2>
        <label style={styles.label}>
          Namespace
          <input
            style={styles.input}
            value={logsNamespace}
            onChange={(e) => setLogsNamespace(e.target.value)}
            placeholder="default"
            disabled={streamingLogs}
          />
        </label>
        <div style={styles.buttonGroup}>
          <button
            style={styles.button}
            onClick={fetchLogs}
            disabled={loadingLogs || streamingLogs}
          >
            {loadingLogs ? "Loading..." : "Fetch Logs"}
          </button>
          {!streamingLogs ? (
            <button
              style={{ ...styles.button, ...styles.streamButton }}
              onClick={startLogStreaming}
            >
              Start Streaming
            </button>
          ) : (
            <button
              style={{ ...styles.button, ...styles.stopButton }}
              onClick={stopLogStreaming}
            >
              Stop Streaming
            </button>
          )}
        </div>
        {streamingLogs && (
          <div style={styles.streamingIndicator}>
            <span style={styles.streamingDot}></span> Streaming logs in
            real-time...
          </div>
        )}
        {logs && (
          <pre style={styles.pre} id="logs-container">
            {logs}
          </pre>
        )}
      </section>

      <section style={styles.card}>
        <h2>4) Metrics Dashboard (Auto-refresh every minute)</h2>
        <label style={styles.label}>
          Namespace
          <input
            style={styles.input}
            value={metricsNamespace}
            onChange={(e) => setMetricsNamespace(e.target.value)}
            placeholder="default"
          />
        </label>
        <button
          style={styles.button}
          onClick={fetchMetrics}
          disabled={loadingMetrics}
        >
          {loadingMetrics ? "Loading..." : "Refresh Now"}
        </button>

        {metrics && (
          <div>
            <h3 style={styles.metricTitle}>HTTP Request Metrics</h3>
            <div style={styles.metricGrid}>
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Requests/Min</div>
                <div style={styles.metricValue}>
                  {metrics.http_metrics?.requests_per_minute || 0}
                </div>
              </div>
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Total Requests</div>
                <div style={styles.metricValue}>
                  {metrics.http_metrics?.total_requests || 0}
                </div>
              </div>
              <div style={styles.metricCard}>
                <div style={styles.metricLabel}>Error Rate</div>
                <div style={styles.metricValue}>
                  {((metrics.http_metrics?.error_rate || 0) * 100).toFixed(2)}%
                </div>
              </div>
            </div>

            {httpRateData.length > 0 && (
              <div style={styles.chartContainer}>
                <h3 style={styles.metricTitle}>HTTP Request Rate Over Time</h3>
                <ResponsiveContainer width="100%" height={200}>
                  <LineChart data={httpRateData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="time" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="requestsPerMinute"
                      stroke="#8884d8"
                      name="Requests/Min"
                    />
                    <Line
                      type="monotone"
                      dataKey="errorRate"
                      stroke="#82ca9d"
                      name="Error Rate %"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {cpuChartData.length > 0 &&
              metrics &&
              metrics.pods &&
              metrics.pods.length > 0 && (
                <div style={styles.chartContainer}>
                  <h3 style={styles.metricTitle}>CPU Usage Over Time</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={cpuChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {metrics.pods.map((pod, idx) => {
                        // Use consistent colors for each pod
                        const colors = [
                          "#8884d8",
                          "#82ca9d",
                          "#ffc658",
                          "#ff7300",
                          "#00ff00",
                        ];
                        return (
                          <Line
                            key={pod.name}
                            type="monotone"
                            dataKey={pod.name}
                            stroke={colors[idx % colors.length]}
                            name={pod.name}
                            dot={{ r: 3 }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

            {memoryChartData.length > 0 &&
              metrics &&
              metrics.pods &&
              metrics.pods.length > 0 && (
                <div style={styles.chartContainer}>
                  <h3 style={styles.metricTitle}>Memory Usage Over Time</h3>
                  <ResponsiveContainer width="100%" height={200}>
                    <LineChart data={memoryChartData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="time" />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      {metrics.pods.map((pod, idx) => {
                        // Use consistent colors for each pod (same as CPU chart)
                        const colors = [
                          "#8884d8",
                          "#82ca9d",
                          "#ffc658",
                          "#ff7300",
                          "#00ff00",
                        ];
                        return (
                          <Line
                            key={pod.name}
                            type="monotone"
                            dataKey={pod.name}
                            stroke={colors[idx % colors.length]}
                            name={pod.name}
                            dot={{ r: 3 }}
                          />
                        );
                      })}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}

            <h3 style={styles.metricTitle}>Current Pod Metrics</h3>
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th>Pod Name</th>
                    <th>CPU</th>
                    <th>Memory</th>
                  </tr>
                </thead>
                <tbody>
                  {metrics.pods.map((pod) => (
                    <tr key={pod.name}>
                      <td>{pod.name}</td>
                      <td>{pod.cpu}</td>
                      <td>{pod.memory}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

const styles: Record<string, React.CSSProperties> = {
  page: {
    maxWidth: 1200,
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
    boxSizing: "border-box",
  },
  button: {
    padding: ".6rem 1.2rem",
    background: "#111827",
    color: "#fff",
    border: "none",
    borderRadius: 6,
    cursor: "pointer",
    marginTop: ".25rem",
    marginRight: ".5rem",
  },
  buttonGroup: {
    display: "flex",
    gap: ".5rem",
  },
  streamButton: {
    background: "#059669",
  },
  stopButton: {
    background: "#dc2626",
  },
  pre: {
    background: "#111827",
    color: "#f9fafb",
    padding: ".75rem",
    borderRadius: 6,
    marginTop: ".75rem",
    fontSize: ".9rem",
    overflowX: "auto",
    maxHeight: "400px",
    overflowY: "auto",
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
  healthBadge: {
    display: "inline-block",
    marginLeft: ".75rem",
    padding: ".5rem",
    background: "#e5e7eb",
    borderRadius: 6,
    fontSize: ".85rem",
    maxWidth: "400px",
    overflow: "auto",
  },
  streamingIndicator: {
    marginTop: ".5rem",
    padding: ".5rem",
    background: "#dbeafe",
    borderRadius: 4,
    color: "#1e40af",
    display: "flex",
    alignItems: "center",
    gap: ".5rem",
  },
  streamingDot: {
    width: "8px",
    height: "8px",
    background: "#3b82f6",
    borderRadius: "50%",
    animation: "pulse 2s infinite",
  },
  metricTitle: {
    marginTop: "1.5rem",
    marginBottom: ".75rem",
    fontSize: "1.1rem",
    fontWeight: 600,
  },
  metricGrid: {
    display: "grid",
    gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))",
    gap: "1rem",
    marginBottom: "1.5rem",
  },
  metricCard: {
    background: "#fff",
    padding: "1rem",
    borderRadius: 6,
    border: "1px solid #e5e7eb",
    textAlign: "center",
  },
  metricLabel: {
    fontSize: ".85rem",
    color: "#6b7280",
    marginBottom: ".5rem",
  },
  metricValue: {
    fontSize: "1.5rem",
    fontWeight: 700,
    color: "#111827",
  },
  chartContainer: {
    marginTop: "1.5rem",
    marginBottom: "1.5rem",
  },
  tableContainer: {
    marginTop: "1rem",
    overflowX: "auto",
  },
  table: {
    width: "100%",
    borderCollapse: "collapse",
    background: "#fff",
    borderRadius: 6,
    overflow: "hidden",
  },
};
