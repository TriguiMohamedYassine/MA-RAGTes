import { useEffect, useMemo, useRef, useState } from "react";
import { clearHistory, getHistory, getResults } from "../services/api";

const FILTERS = ["All", "Done", "Running", "Error"];

function statusColor(status) {
  if (status === "done") return "#22c55e";
  if (status === "running") return "#3b82f6";
  return "#ef4444";
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function downloadJson(fileName, payload) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

function downloadText(fileName, content) {
  const blob = new Blob([content || ""], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  link.click();
  URL.revokeObjectURL(url);
}

export default function History({ selectedRunId = "", navigationToken = 0, onNewTest }) {
  const [runs, setRuns] = useState([]);
  const [filter, setFilter] = useState("All");
  const [isLoading, setIsLoading] = useState(true);
  const [isClearing, setIsClearing] = useState(false);
  const [error, setError] = useState("");
  const [details, setDetails] = useState(null);
  const [detailsRunId, setDetailsRunId] = useState("");
  const [detailsLoading, setDetailsLoading] = useState(false);
  const detailsSectionRef = useRef(null);

  const scrollToDetails = () => {
    if (detailsSectionRef.current) {
      detailsSectionRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  };

  const loadRuns = async () => {
    try {
      const history = await getHistory();
      setRuns(Array.isArray(history) ? history : []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error while loading history.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadRuns();
  }, []);

  useEffect(() => {
    const hasRunning = runs.some((run) => run.status === "running");
    if (!hasRunning) return undefined;

    const id = setInterval(loadRuns, 3000);
    return () => clearInterval(id);
  }, [runs]);

  useEffect(() => {
    if (!selectedRunId) return;
    setDetailsRunId(selectedRunId);
    void handleViewResults(selectedRunId, { scroll: true });
  }, [selectedRunId, navigationToken]);

  const filteredRuns = useMemo(() => {
    if (filter === "All") return runs;
    return runs.filter((run) => run.status === filter.toLowerCase());
  }, [runs, filter]);

  const stats = useMemo(() => {
    const doneRuns = runs.filter((run) => run.status === "done");
    const successRate = runs.length > 0 ? Math.round((doneRuns.length / runs.length) * 100) : 0;
    const avgCoverage = doneRuns.length > 0
      ? (doneRuns.reduce((sum, run) => sum + (run.summary?.coverage?.statements || 0), 0) / doneRuns.length).toFixed(1)
      : "0.0";
    return {
      totalRuns: runs.length,
      successRate,
      avgCoverage,
    };
  }, [runs]);

  const handleViewResults = async (runId, options = {}) => {
    const shouldScroll = Boolean(options.scroll);
    try {
      setDetailsLoading(true);
      setDetailsRunId(runId);
      const response = await getResults(runId);
      setDetails(response);
      if (shouldScroll) {
        setTimeout(scrollToDetails, 50);
      }
    } catch (err) {
      setDetails(null);
      setError(err instanceof Error ? err.message : "Unable to load results.");
      if (shouldScroll) {
        setTimeout(scrollToDetails, 50);
      }
    } finally {
      setDetailsLoading(false);
    }
  };

  const handleClearHistory = async () => {
    if (!window.confirm("Delete all run history?")) return;
    try {
      setIsClearing(true);
      await clearHistory();
      setDetails(null);
      setDetailsRunId("");
      await loadRuns();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to clear history.");
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-title">Test History</div>
      <div className="page-sub">Live run history from the FastAPI backend.</div>

      <div style={{ display: "flex", gap: 8, marginBottom: "1rem" }}>
        <button className="btn" onClick={loadRuns}>Refresh</button>
        <button className="btn" onClick={onNewTest}>New Test</button>
        <button className="btn" onClick={handleClearHistory} disabled={isClearing}>
          {isClearing ? "Clearing..." : "Clear History"}
        </button>
      </div>

      {error && (
        <div className="card" style={{ padding: "0.9rem 1rem", marginBottom: "1rem", borderColor: "#fecaca", color: "#b91c1c" }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "1rem", marginBottom: "1rem" }}>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Total Runs</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{stats.totalRuns}</div>
        </div>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Done Rate</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{stats.successRate}%</div>
        </div>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Avg Statement Coverage</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{stats.avgCoverage}%</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 6, flexWrap: "wrap", marginBottom: "1rem" }}>
        {FILTERS.map((value) => (
          <button
            key={value}
            className="btn"
            onClick={() => setFilter(value)}
            style={{
              background: filter === value ? "#7c3aed" : "white",
              color: filter === value ? "white" : "#334155",
            }}
          >
            {value}
          </button>
        ))}
      </div>

      <div className="card" style={{ overflow: "hidden", marginBottom: "1rem" }}>
        <div style={{
          display: "grid",
          gridTemplateColumns: "2fr 110px 120px 110px 160px 110px 120px",
          gap: "0.75rem",
          padding: "0.75rem 1rem",
          background: "#f8fafc",
          fontSize: 12,
          color: "#64748b",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}>
          <span>Contract</span>
          <span>Status</span>
          <span>Tests</span>
          <span>Coverage</span>
          <span>Started At</span>
          <span>Iterations</span>
          <span>Action</span>
        </div>

        {isLoading ? (
          <div style={{ padding: "1rem", color: "#64748b" }}>Loading history...</div>
        ) : filteredRuns.length === 0 ? (
          <div style={{ padding: "1rem", color: "#64748b" }}>No runs found.</div>
        ) : filteredRuns.map((run) => {
          const tests = run.summary?.total ?? 0;
          const passed = run.summary?.passed ?? 0;
          const coverage = run.summary?.coverage?.statements ?? 0;
          const canViewResults = run.status === "done";
          return (
            <div
              key={run.run_id}
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 110px 120px 110px 160px 110px 120px",
                gap: "0.75rem",
                padding: "0.85rem 1rem",
                borderBottom: "1px solid rgba(0,0,0,0.05)",
                alignItems: "center",
                fontSize: 13,
              }}
            >
              <span style={{ fontWeight: 500 }}>{run.contract_name || "UnknownContract"}</span>
              <span style={{ color: statusColor(run.status), fontWeight: 600 }}>{run.status}</span>
              <span>{passed}/{tests}</span>
              <span>{Number(coverage).toFixed(1)}%</span>
              <span>{formatDate(run.started_at)}</span>
              <span>{run.iterations ?? 0}</span>
              <span>
                <button
                  className="btn"
                  onClick={() => canViewResults ? handleViewResults(run.run_id, { scroll: true }) : undefined}
                  disabled={!canViewResults || detailsLoading}
                >
                  {canViewResults ? "Details" : "Running"}
                </button>
              </span>
            </div>
          );
        })}
      </div>

      <div ref={detailsSectionRef} className="card" style={{ padding: "1rem" }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Run Details {detailsRunId ? `(${detailsRunId})` : ""}</div>
        {detailsLoading ? (
          <div style={{ color: "#64748b" }}>Loading results...</div>
        ) : details ? (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, minmax(0,1fr))", gap: "0.75rem", marginBottom: "0.9rem" }}>
              <div className="card" style={{ padding: "0.7rem" }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Contract</div>
                <div style={{ fontWeight: 600 }}>{details.contract_name || "UnknownContract"}</div>
              </div>
              <div className="card" style={{ padding: "0.7rem" }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Tests</div>
                <div style={{ fontWeight: 600 }}>{details.summary?.passed ?? 0}/{details.summary?.total ?? 0}</div>
              </div>
              <div className="card" style={{ padding: "0.7rem" }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Statements</div>
                <div style={{ fontWeight: 600 }}>{Number(details.summary?.coverage?.statements ?? 0).toFixed(1)}%</div>
              </div>
              <div className="card" style={{ padding: "0.7rem" }}>
                <div style={{ fontSize: 12, color: "#94a3b8" }}>Iterations</div>
                <div style={{ fontWeight: 600 }}>{details.summary?.iterations ?? 0}</div>
              </div>
            </div>

            <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: "0.9rem" }}>
              <button className="btn" onClick={() => downloadJson(`summary-${details.run_id}.json`, details.summary || {})}>Download Summary JSON</button>
              <button className="btn" onClick={() => downloadJson(`test-report-${details.run_id}.json`, details.test_report || {})}>Download Test Report JSON</button>
              <button className="btn" onClick={() => downloadJson(`coverage-${details.run_id}.json`, details.coverage_report || {})}>Download Coverage JSON</button>
              <button className="btn" onClick={() => downloadJson(`analyzer-${details.run_id}.json`, details.analyzer_report || {})}>Download Analyzer JSON</button>
              <button className="btn" onClick={() => downloadText(`generated-tests-${details.run_id}.js`, details.test_code || "")}>Download Generated Tests</button>
            </div>

            <div className="card" style={{ padding: "0.75rem", marginBottom: "0.75rem" }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Evaluation</div>
              <div style={{ fontSize: 13, color: "#334155" }}>
                Decision: <strong>{details.summary?.evaluation_decision || "N/A"}</strong>
              </div>
              <div style={{ fontSize: 13, color: "#64748b" }}>
                Reason: {details.summary?.evaluation_reason || "N/A"}
              </div>
            </div>

            <div className="card" style={{ padding: "0.75rem" }}>
              <div style={{ fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Generated Test Code</div>
              <pre style={{ margin: 0, whiteSpace: "pre-wrap", wordBreak: "break-word", fontSize: 12, maxHeight: 260, overflow: "auto" }}>
                {details.test_code || "No test code generated."}
              </pre>
            </div>
          </div>
        ) : (
          <div style={{ color: "#64748b" }}>Select a completed run to view detailed results.</div>
        )}
      </div>
    </div>
  );
}
