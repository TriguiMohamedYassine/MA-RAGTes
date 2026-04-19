const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    const detail = payload?.detail || `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return payload;
}

export function startRun(body) {
  return request("/api/run", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getRunStatus(runId) {
  return request(`/api/run/${runId}`);
}

export function getHistory() {
  return request("/api/history");
}

export function getResults(runId) {
  return request(`/api/results/${runId}`);
}

export function clearHistory() {
  return request("/api/history", { method: "DELETE" });
}

export function getHealth() {
  return request("/api/health");
}

export function saveLlmApiKey(apiKey) {
  return request("/api/settings/llm-key", {
    method: "POST",
    body: JSON.stringify({ api_key: apiKey }),
  });
}
