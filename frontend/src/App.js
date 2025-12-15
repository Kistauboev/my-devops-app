import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
import axios from "axios";
const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";
export default function App() {
    const [onboard, setOnboard] = useState({
        repoUrl: "",
        branch: "main",
    });
    const [approve, setApprove] = useState({ runId: "", token: "" });
    const [onboardResult, setOnboardResult] = useState("");
    const [approveResult, setApproveResult] = useState("");
    const submitOnboard = async () => {
        try {
            const res = await axios.post(`${API_BASE}/onboard`, {
                repo_url: onboard.repoUrl,
                branch: onboard.branch,
            });
            setOnboardResult(JSON.stringify(res.data, null, 2));
        }
        catch (err) {
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
        }
        catch (err) {
            setApproveResult(err?.response?.data?.detail || "Approve failed");
        }
    };
    return (_jsxs("main", { style: styles.page, children: [_jsxs("header", { children: [_jsx("h1", { children: "DevPlatform" }), _jsx("p", { children: "Onboard repos, deploy previews, and approve production." })] }), _jsxs("section", { style: styles.card, children: [_jsx("h2", { children: "1) Onboard repository" }), _jsxs("label", { style: styles.label, children: ["Repo URL", _jsx("input", { style: styles.input, value: onboard.repoUrl, onChange: (e) => setOnboard({ ...onboard, repoUrl: e.target.value }), placeholder: "https://github.com/org/repo" })] }), _jsxs("label", { style: styles.label, children: ["Branch", _jsx("input", { style: styles.input, value: onboard.branch, onChange: (e) => setOnboard({ ...onboard, branch: e.target.value }), placeholder: "main" })] }), _jsx("button", { style: styles.button, onClick: submitOnboard, children: "Submit" }), onboardResult && _jsx("pre", { style: styles.pre, children: onboardResult })] }), _jsxs("section", { style: styles.card, children: [_jsx("h2", { children: "2) Approve production deploy" }), _jsxs("label", { style: styles.label, children: ["Run ID", _jsx("input", { style: styles.input, value: approve.runId, onChange: (e) => setApprove({ ...approve, runId: e.target.value }), placeholder: "actions run id" })] }), _jsxs("label", { style: styles.label, children: ["Approval token", _jsx("input", { style: styles.input, value: approve.token, onChange: (e) => setApprove({ ...approve, token: e.target.value }), placeholder: "from backend env" })] }), _jsx("button", { style: styles.button, onClick: submitApprove, children: "Approve" }), approveResult && _jsx("pre", { style: styles.pre, children: approveResult })] }), _jsxs("section", { style: styles.card, children: [_jsx("h2", { children: "3) Logs (placeholder)" }), _jsx("p", { children: "Embed Loki/Grafana or stream from backend once wired." })] }), _jsxs("section", { style: styles.card, children: [_jsx("h2", { children: "4) Metrics (placeholder)" }), _jsx("p", { children: "Embed Grafana dashboards for CPU/memory and HTTP rate/errors." })] })] }));
}
const styles = {
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
};
