import { useEffect, useMemo, useState } from "react";
import { getHistory } from "../services/api";

const COLOR = {
  green: "#22c55e",
  red: "#ef4444",
  blue: "#3b82f6",
  amber: "#f59e0b",
  slate: "#64748b",
  grid: "#e2e8f0",
  axis: "#94a3b8",
  line: "#0f172a",
};

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString();
}

function shortDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "-";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

function contractLabel(run) {
  return run?.contract_name || "UnknownContract";
}

function toTs(value) {
  if (!value) return 0;
  const t = new Date(value).getTime();
  return Number.isFinite(t) ? t : 0;
}

function clamp(value, min = 0, max = 100) {
  return Math.max(min, Math.min(max, value));
}

function runDurationMs(run) {
  const start = toTs(run.started_at);
  if (!start) return 0;
  const end = run.finished_at ? toTs(run.finished_at) : Date.now();
  return Math.max(0, end - start);
}

function msToHuman(value) {
  const seconds = Math.max(0, Math.round(value / 1000));
  const minutes = Math.floor(seconds / 60);
  const remaining = seconds % 60;
  if (minutes > 0) return `${minutes}m ${remaining}s`;
  return `${remaining}s`;
}

function qualityScore(run) {
  const total = Number(run.summary?.total || 0);
  const passed = Number(run.summary?.passed || 0);
  const statements = Number(run.summary?.coverage?.statements || 0);
  const passPart = total > 0 ? (passed / total) * 50 : 0;
  const score = passPart + statements * 0.5;
  return clamp(score, 0, 100);
}

function passRate(run) {
  const total = Number(run.summary?.total || 0);
  const passed = Number(run.summary?.passed || 0);
  if (total <= 0) return 0;
  return clamp((passed / total) * 100, 0, 100);
}

function polylinePoints(data, width, height, maxY = 100) {
  if (!data.length) return "";
  const padX = 20;
  const padY = 14;
  const drawW = width - padX * 2;
  const drawH = height - padY * 2;
  return data
    .map((point, index) => {
      const x = padX + (data.length === 1 ? drawW / 2 : (index / (data.length - 1)) * drawW);
      const y = padY + drawH - (clamp(point.value, 0, maxY) / maxY) * drawH;
      return `${x},${y}`;
    })
    .join(" ");
}

function radarPolygon(values, radius, cx, cy) {
  const count = values.length;
  return values
    .map((value, i) => {
      const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
      const r = (clamp(value) / 100) * radius;
      const x = cx + Math.cos(angle) * r;
      const y = cy + Math.sin(angle) * r;
      return `${x},${y}`;
    })
    .join(" ");
}

function radarAxisLabel(i, count, radius, cx, cy, text) {
  const angle = (Math.PI * 2 * i) / count - Math.PI / 2;
  const x = cx + Math.cos(angle) * (radius + 16);
  const y = cy + Math.sin(angle) * (radius + 16);
  return (
    <text key={text} x={x} y={y} textAnchor="middle" fontSize="10" fill={COLOR.slate}>
      {text}
    </text>
  );
}

export default function Dashboard({ onNewTest, onOpenHistory }) {
  const [runs, setRuns] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [radarRunA, setRadarRunA] = useState("");
  const [radarRunB, setRadarRunB] = useState("");

  const load = async () => {
    try {
      const data = await getHistory();
      setRuns(Array.isArray(data) ? data : []);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error while loading dashboard data.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const hasRunning = runs.some((run) => run.status === "running");
    if (!hasRunning) return undefined;
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [runs]);

  const metrics = useMemo(() => {
    const doneRuns = runs.filter((run) => run.status === "done");
    const runningRuns = runs.filter((run) => run.status === "running");
    const erroredRuns = runs.filter((run) => run.status === "error");
    const totalTests = doneRuns.reduce((sum, run) => sum + (run.summary?.total || 0), 0);
    const totalPassed = doneRuns.reduce((sum, run) => sum + (run.summary?.passed || 0), 0);
    const avgCoverage = doneRuns.length
      ? (doneRuns.reduce((sum, run) => sum + (run.summary?.coverage?.statements || 0), 0) / doneRuns.length).toFixed(1)
      : "0.0";

    return {
      totalRuns: runs.length,
      totalTests,
      totalPassed,
      avgCoverage,
      running: runningRuns.length,
      errored: erroredRuns.length,
    };
  }, [runs]);

  const recent = useMemo(() => runs.slice(0, 8), [runs]);

  const chronologicalRuns = useMemo(
    () => [...runs].sort((a, b) => toTs(a.started_at) - toTs(b.started_at)),
    [runs],
  );

  const runsWithSummary = useMemo(
    () => chronologicalRuns.filter((run) => run.summary && Number(run.summary?.total || 0) >= 0),
    [chronologicalRuns],
  );

  const graphRuns = useMemo(() => chronologicalRuns.slice(-15), [chronologicalRuns]);

  useEffect(() => {
    if (!runsWithSummary.length) {
      setRadarRunA("");
      setRadarRunB("");
      return;
    }
    if (!radarRunA || !runsWithSummary.some((r) => r.run_id === radarRunA)) {
      setRadarRunA(runsWithSummary[runsWithSummary.length - 1].run_id);
    }
    if (radarRunB && !runsWithSummary.some((r) => r.run_id === radarRunB)) {
      setRadarRunB("");
    }
  }, [runsWithSummary, radarRunA, radarRunB]);

  const qualitySeries = useMemo(
    () => graphRuns
      .filter((run) => run.summary)
      .map((run, index) => ({
        idx: index + 1,
        run,
        value: qualityScore(run),
      })),
    [graphRuns],
  );

  const durationPool = useMemo(() => {
    const values = runsWithSummary.map((run) => runDurationMs(run)).filter((v) => v > 0);
    if (!values.length) return { min: 0, max: 1 };
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [runsWithSummary]);

  const averageCompletedDurationMs = useMemo(() => {
    const completed = chronologicalRuns
      .filter((run) => run.status !== "running")
      .map((run) => runDurationMs(run))
      .filter((v) => v > 0);

    if (!completed.length) return 0;
    return completed.reduce((sum, value) => sum + value, 0) / completed.length;
  }, [chronologicalRuns]);

  const timelineRows = useMemo(() => {
    const rows = chronologicalRuns.slice(-10);
    if (!rows.length) return [];

    const starts = rows.map((run) => toTs(run.started_at)).filter((v) => v > 0);
    if (!starts.length) return [];

    const minStart = Math.min(...starts);
    const maxEnd = Math.max(...rows.map((run) => run.finished_at ? toTs(run.finished_at) : Date.now()));
    const span = Math.max(1, maxEnd - minStart);

    return rows.map((run) => {
      const start = toTs(run.started_at);
      const end = run.finished_at ? toTs(run.finished_at) : Date.now();
      const elapsed = Math.max(0, end - start);
      const leftPct = ((start - minStart) / span) * 100;
      const widthPct = Math.max(1.5, ((end - start) / span) * 100);
      const remaining = run.status === "running" && averageCompletedDurationMs > 0
        ? Math.max(0, averageCompletedDurationMs - elapsed)
        : 0;

      const statusColor = run.status === "done" ? COLOR.green : run.status === "error" ? COLOR.red : COLOR.blue;
      const etaLabel = run.status === "running"
        ? (averageCompletedDurationMs > 0 ? `ETA ~ ${msToHuman(remaining)}` : "ETA ~ n/a")
        : `Done ${msToHuman(elapsed)}`;

      return {
        run,
        leftPct,
        widthPct,
        statusColor,
        etaLabel,
      };
    });
  }, [chronologicalRuns, averageCompletedDurationMs]);

  const runA = runsWithSummary.find((run) => run.run_id === radarRunA) || null;
  const runB = runsWithSummary.find((run) => run.run_id === radarRunB) || null;

  const radarValues = (run) => {
    if (!run) return [0, 0, 0, 0, 0];
    const stm = Number(run.summary?.coverage?.statements || 0);
    const br = Number(run.summary?.coverage?.branches || 0);
    const fn = Number(run.summary?.coverage?.functions || 0);
    const pr = passRate(run);
    const dur = runDurationMs(run);
    const speed = durationPool.max === durationPool.min
      ? 100
      : clamp((1 - (dur - durationPool.min) / (durationPool.max - durationPool.min)) * 100);
    return [stm, br, fn, pr, speed];
  };

  return (
    <div className="fade-in">
      <div className="page-title">Dashboard</div>
      <div className="page-sub">Real-time data from the backend API.</div>

      <div style={{ display: "flex", gap: 8, marginBottom: "1rem" }}>
        <button className="btn-primary" onClick={onNewTest}>Create New Test</button>
        <button className="btn" onClick={() => onOpenHistory()}>Open History</button>
        <button className="btn" onClick={load}>Refresh</button>
      </div>

      {error && (
        <div className="card" style={{ padding: "0.9rem 1rem", marginBottom: "1rem", borderColor: "#fecaca", color: "#b91c1c" }}>
          {error}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "1rem", marginBottom: "1rem" }}>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Total Runs</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{metrics.totalRuns}</div>
        </div>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Passed / Tests</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{metrics.totalPassed}/{metrics.totalTests}</div>
        </div>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Avg Statement Coverage</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{metrics.avgCoverage}%</div>
        </div>
        <div className="card" style={{ padding: "1rem 1.25rem" }}>
          <div style={{ fontSize: 12, color: "#94a3b8" }}>Running / Error</div>
          <div style={{ fontSize: 24, fontWeight: 600 }}>{metrics.running} / {metrics.errored}</div>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
        <div className="card" style={{ padding: "1rem" }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>1. Quality Score by Run</div>
          <div style={{ fontSize: 12, color: COLOR.slate, marginBottom: 8 }}>Score = (passed / total * 50) + (statements * 0.5)</div>
          {qualitySeries.length === 0 ? (
            <div style={{ color: COLOR.slate }}>Not enough data.</div>
          ) : (
            <svg width="100%" height="220" viewBox="0 0 560 220" preserveAspectRatio="none">
              <line x1="20" y1="186" x2="540" y2="186" stroke={COLOR.axis} />
              <line x1="20" y1="14" x2="20" y2="186" stroke={COLOR.axis} />
              <polyline fill="none" stroke={COLOR.line} strokeWidth="2.5" points={polylinePoints(qualitySeries, 560, 200)} />
              {qualitySeries.map((point, i) => {
                const x = 20 + (qualitySeries.length === 1 ? 260 : (i / (qualitySeries.length - 1)) * 520);
                const y = 14 + 172 - (point.value / 100) * 172;
                return <circle key={point.run.run_id} cx={x} cy={y} r="3.5" fill={COLOR.blue} />;
              })}
              <text x="24" y="24" fontSize="10" fill={COLOR.slate}>100</text>
              <text x="24" y="188" fontSize="10" fill={COLOR.slate}>0</text>
            </svg>
          )}
        </div>

        <div className="card" style={{ padding: "1rem" }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>3. Iterations Waterfall - Result</div>
          <div style={{ fontSize: 12, color: COLOR.slate, marginBottom: 8 }}>Bars colored by final status</div>
          {graphRuns.length === 0 ? (
            <div style={{ color: COLOR.slate }}>Not enough data.</div>
          ) : (
            <svg width="100%" height="220" viewBox="0 0 560 220" preserveAspectRatio="none">
              <line x1="30" y1="186" x2="540" y2="186" stroke={COLOR.axis} />
              {graphRuns.map((run, i) => {
                const iterations = Number(run.iterations || 0);
                const h = Math.min(150, iterations * 16 + 8);
                const x = 40 + i * 32;
                const y = 186 - h;
                const color = run.status === "done" ? COLOR.green : run.status === "error" ? COLOR.red : COLOR.blue;
                return (
                  <g key={run.run_id}>
                    <rect x={x} y={y} width="22" height={h} rx="4" fill={color} opacity="0.9" />
                    <text x={x + 11} y={y - 4} textAnchor="middle" fontSize="9" fill={COLOR.slate}>{iterations}</text>
                  </g>
                );
              })}
            </svg>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: "1rem", marginBottom: "1rem" }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>4. Runs Timeline</div>
        <div style={{ fontSize: 12, color: COLOR.slate, marginBottom: 8 }}>Bar length = execution duration, with remaining-time estimate</div>
        {timelineRows.length === 0 ? (
          <div style={{ color: COLOR.slate }}>Not enough data.</div>
        ) : (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "120px 1fr 110px", gap: 12, fontSize: 10, color: COLOR.slate, marginBottom: 6 }}>
              <span>Contract</span>
              <span style={{ textAlign: "center" }}>Timeline</span>
              <span style={{ textAlign: "right" }}>ETA / Duration</span>
            </div>

            <div style={{ display: "grid", gap: 8 }}>
              {timelineRows.map(({ run, leftPct, widthPct, statusColor, etaLabel }) => (
                <div key={run.run_id} style={{ display: "grid", gridTemplateColumns: "120px 1fr 110px", gap: 12, alignItems: "center" }}>
                  <div style={{ fontSize: 11, color: COLOR.slate }}>{contractLabel(run)}</div>
                  <div style={{ position: "relative", height: 16, borderRadius: 8, background: "#f1f5f9", overflow: "hidden" }}>
                    <div
                      style={{
                        position: "absolute",
                        left: `${leftPct}%`,
                        width: `${widthPct}%`,
                        height: "100%",
                        borderRadius: 8,
                        background: statusColor,
                      }}
                      title={`${contractLabel(run)} - ${shortDate(run.started_at)}`}
                    />
                  </div>
                  <div style={{ fontSize: 11, color: COLOR.slate, textAlign: "right" }}>{etaLabel}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
        <div className="card" style={{ padding: "1rem" }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>5. Radar by Run</div>
          <div style={{ display: "flex", gap: 8, marginBottom: 8, flexWrap: "wrap" }}>
            <select value={radarRunA} onChange={(e) => setRadarRunA(e.target.value)}>
              {runsWithSummary.map((run) => (
                <option key={run.run_id} value={run.run_id}>{contractLabel(run)}</option>
              ))}
            </select>
            <select value={radarRunB} onChange={(e) => setRadarRunB(e.target.value)}>
              <option value="">No compare</option>
              {runsWithSummary.map((run) => (
                <option key={run.run_id} value={run.run_id}>{contractLabel(run)}</option>
              ))}
            </select>
          </div>
          {!runA ? (
            <div style={{ color: COLOR.slate }}>Not enough data.</div>
          ) : (
            <svg width="100%" height="300" viewBox="0 0 560 300" preserveAspectRatio="none">
              {(() => {
                const labels = ["stmts", "branches", "functions", "pass%", "speed"];
                const cxA = 180;
                const cxB = 400;
                const cy = 150;
                const radius = 70;
                const valsA = radarValues(runA);
                const valsB = runB ? radarValues(runB) : null;
                const guide = [20, 40, 60, 80, 100];
                return (
                  <>
                    {guide.map((g) => (
                      <g key={`ga-${g}`}>
                        <polygon points={radarPolygon([g, g, g, g, g], radius, cxA, cy)} fill="none" stroke={COLOR.grid} />
                        {runB && <polygon points={radarPolygon([g, g, g, g, g], radius, cxB, cy)} fill="none" stroke={COLOR.grid} />}
                      </g>
                    ))}
                    {labels.map((label, i) => radarAxisLabel(i, labels.length, radius, cxA, cy, label))}
                    {runB && labels.map((label, i) => radarAxisLabel(i, labels.length, radius, cxB, cy, label))}
                    <polygon points={radarPolygon(valsA, radius, cxA, cy)} fill="rgba(59,130,246,0.25)" stroke={COLOR.blue} strokeWidth="2" />
                    {valsB && <polygon points={radarPolygon(valsB, radius, cxB, cy)} fill="rgba(34,197,94,0.24)" stroke={COLOR.green} strokeWidth="2" />}
                    <text x={cxA} y="272" textAnchor="middle" fontSize="10" fill={COLOR.slate}>{contractLabel(runA)}</text>
                    {runB && <text x={cxB} y="272" textAnchor="middle" fontSize="10" fill={COLOR.slate}>{contractLabel(runB)}</text>}
                  </>
                );
              })()}
            </svg>
          )}
        </div>

        <div className="card" style={{ padding: "1rem" }}>
          <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>6. Passed vs Failed Tests (Stacked)</div>
          <div style={{ fontSize: 12, color: COLOR.slate, marginBottom: 8 }}>100% stacked bars per run</div>
          {graphRuns.length === 0 ? (
            <div style={{ color: COLOR.slate }}>Not enough data.</div>
          ) : (
            <svg width="100%" height="300" viewBox="0 0 560 300" preserveAspectRatio="none">
              {graphRuns.map((run, i) => {
                const total = Number(run.summary?.total || 0);
                const passed = Number(run.summary?.passed || 0);
                const failed = Number(run.summary?.failed || 0);
                const passPct = total > 0 ? (passed / total) * 100 : 0;
                const failPct = total > 0 ? (failed / total) * 100 : 0;
                const x = 30 + i * 34;
                const baseY = 250;
                const fullH = 180;
                const passH = (passPct / 100) * fullH;
                const failH = (failPct / 100) * fullH;
                return (
                  <g key={run.run_id}>
                    <rect x={x} y={baseY - passH - failH} width="22" height={failH || 2} fill={COLOR.red} />
                    <rect x={x} y={baseY - passH} width="22" height={passH || 2} fill={COLOR.green} />
                    <text x={x + 11} y={265} textAnchor="middle" fontSize="8" fill={COLOR.slate}>{i + 1}</text>
                  </g>
                );
              })}
              <line x1="20" y1="250" x2="540" y2="250" stroke={COLOR.axis} />
            </svg>
          )}
        </div>
      </div>

      <div className="card" style={{ padding: "1rem" }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Recent Runs</div>
        {isLoading ? (
          <div style={{ color: "#64748b" }}>Loading runs...</div>
        ) : recent.length === 0 ? (
          <div style={{ color: "#64748b" }}>No runs yet.</div>
        ) : (
          <div style={{ display: "grid", gap: "0.6rem" }}>
            {recent.map((run) => (
              <div key={run.run_id} style={{
                display: "grid",
                gridTemplateColumns: "2fr 100px 120px 170px 100px",
                gap: "0.75rem",
                alignItems: "center",
                padding: "0.65rem 0",
                borderBottom: "1px solid rgba(0,0,0,0.06)",
              }}>
                <div style={{ fontWeight: 500 }}>{run.contract_name || "UnknownContract"}</div>
                <div style={{ color: run.status === "done" ? "#22c55e" : run.status === "running" ? "#3b82f6" : "#ef4444", fontWeight: 600 }}>
                  {run.status}
                </div>
                <div>{run.summary?.passed ?? 0}/{run.summary?.total ?? 0}</div>
                <div style={{ color: "#64748b", fontSize: 12 }}>{formatDate(run.started_at)}</div>
                <button className="btn" onClick={() => onOpenHistory(run.run_id)}>Open</button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
