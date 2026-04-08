import { useEffect, useState } from "react";
import { getHealth } from "../services/api";

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");

  const refreshHealth = async () => {
    try {
      setIsLoading(true);
      const data = await getHealth();
      setHealth(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur lors du check santé.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  return (
    <div className="fade-in">
      <div className="page-title">System Settings</div>
      <div className="page-sub">Page opérationnelle: état backend et vérifications runtime.</div>

      <div style={{ display: "flex", gap: 8, marginBottom: "1rem" }}>
        <button className="btn" onClick={refreshHealth}>Refresh Health</button>
      </div>

      {error && (
        <div className="card" style={{ padding: "0.9rem 1rem", marginBottom: "1rem", borderColor: "#fecaca", color: "#b91c1c" }}>
          {error}
        </div>
      )}

      <div className="card" style={{ padding: "1rem", marginBottom: "1rem" }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>API Health</div>
        {isLoading ? (
          <div style={{ color: "#64748b" }}>Loading...</div>
        ) : !health ? (
          <div style={{ color: "#64748b" }}>Aucune donnée disponible.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: "0.6rem" }}>
            <div><strong>Status:</strong> {health.status}</div>
            <div><strong>Total Runs:</strong> {health.runs_total}</div>
            <div><strong>Active Runs:</strong> {health.runs_active}</div>
            <div><strong>Done Runs:</strong> {health.runs_done}</div>
            <div><strong>Error Runs:</strong> {health.runs_error}</div>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: "1rem" }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>Environment Checklist</div>
        <ul style={{ paddingLeft: "1.2rem", color: "#334155", lineHeight: 1.8 }}>
          <li>Backend API running on port 8000.</li>
          <li>Frontend running on port 3000.</li>
          <li>MISTRAL_API_KEY set in .env.</li>
          <li>Node modules installed in project root and solidtest/.</li>
        </ul>
      </div>
    </div>
  );
}
