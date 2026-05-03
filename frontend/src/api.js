const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  const response = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  let data = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const detail = data?.detail || "The API request failed.";
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data;
}

export function getHealth() {
  return request("/health");
}

export function getAgents() {
  return request("/agents");
}

export function getAgentsForSession(sessionId) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  return request(`/agents${query}`);
}

export function getStats(sessionId) {
  const query = sessionId ? `?session_id=${encodeURIComponent(sessionId)}` : "";
  return request(`/stats${query}`);
}

export function clearSession(sessionId) {
  return request("/clear", {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId || null }),
  });
}

export function sendChatMessage(message, sessionId) {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ message, session_id: sessionId || null }),
  });
}

export { API_URL };
