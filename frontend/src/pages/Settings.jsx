import { useEffect, useState } from "react";
import { getHealth, saveLlmApiKey } from "../services/api";

export default function Settings() {
  const [health, setHealth] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [llmApiKey, setLlmApiKey] = useState("");
  const [isSavingKey, setIsSavingKey] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");

  const refreshHealth = async () => {
    try {
      setIsLoading(true);
      const data = await getHealth();
      setHealth(data);
      setError("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error while checking API health.");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    refreshHealth();
  }, []);

  const handleSaveLlmApiKey = async () => {
    const key = llmApiKey.trim();
    if (!key) {
      setSaveMessage("Please enter a valid LLM API key.");
      return;
    }

    try {
      setIsSavingKey(true);
      setSaveMessage("");
      await saveLlmApiKey(key);
      setSaveMessage("LLM API key saved successfully.");
      setLlmApiKey("");
      await refreshHealth();
    } catch (err) {
      setSaveMessage(err instanceof Error ? err.message : "Error while saving API key.");
    } finally {
      setIsSavingKey(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-title">System Settings</div>
      <div className="page-sub">Operational page: backend status and runtime checks.</div>

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
          <div style={{ color: "#64748b" }}>No data available.</div>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(2,1fr)", gap: "0.6rem" }}>
            <div><strong>Status:</strong> {health.status}</div>
            <div><strong>Total Runs:</strong> {health.runs_total}</div>
            <div><strong>Active Runs:</strong> {health.runs_active}</div>
            <div><strong>Done Runs:</strong> {health.runs_done}</div>
            <div><strong>Error Runs:</strong> {health.runs_error}</div>
            <div><strong>LLM API Key:</strong> {health.llm_api_key_configured ? "Configured" : "Not configured"}</div>
          </div>
        )}
      </div>

      <div className="card" style={{ padding: "1rem" }}>
        <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 8 }}>LLM API Configuration</div>
        <div style={{ color: "#64748b", marginBottom: 10 }}>
          Add or update your Mistral API key for LLM agents.
        </div>

        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", marginBottom: 10 }}>
          <input
            type="password"
            value={llmApiKey}
            onChange={(event) => setLlmApiKey(event.target.value)}
            placeholder="mistral_api_key..."
            style={{ minWidth: 320, flex: 1 }}
          />
          <button className="btn-primary" onClick={handleSaveLlmApiKey} disabled={isSavingKey}>
            {isSavingKey ? "Saving..." : "Save API Key"}
          </button>
        </div>

        {saveMessage && (
          <div style={{ fontSize: 13, color: saveMessage.toLowerCase().includes("succ") ? "#166534" : "#b91c1c" }}>
            {saveMessage}
          </div>
        )}
      </div>
    </div>
  );
}
