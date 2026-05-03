import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  BarChart3,
  BookOpen,
  Bot,
  CheckCircle2,
  GraduationCap,
  Loader2,
  MessageSquareText,
  PanelLeft,
  RefreshCcw,
  Send,
  Trash2,
  UserRound,
  WifiOff,
} from "lucide-react";
import {
  API_URL,
  clearSession,
  getAgentsForSession,
  getHealth,
  getStats,
  sendChatMessage,
} from "./api";

const SESSION_STORAGE_KEY = "course_insight_session_id";

const examplePrompts = [
  "What is CMPUT 174 about?",
  "Tell me about prerequisites for MATH 100",
  "How difficult is ENGG 100?",
  "Tell me about Professor Richard Sutton at University of Alberta",
];

const initialMessages = [
  {
    id: "welcome",
    role: "assistant",
    content:
      "Ask about a course, prerequisite, difficulty, or professor. I will route your question to the right agent.",
  },
];

function formatMetric(value) {
  if (value === null || value === undefined) return "0";
  return String(value);
}

function App() {
  const [messages, setMessages] = useState(initialMessages);
  const [input, setInput] = useState("");
  const [agents, setAgents] = useState([]);
  const [stats, setStats] = useState(null);
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_STORAGE_KEY) || "");
  const [health, setHealth] = useState("checking");
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const messagesEndRef = useRef(null);

  const totalCalls = useMemo(() => {
    if (!stats?.agent_calls) return 0;
    return Object.values(stats.agent_calls).reduce((sum, count) => sum + count, 0);
  }, [stats]);

  useEffect(() => {
    refreshSystem();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isLoading]);

  async function refreshSystem() {
    setIsRefreshing(true);
    setError("");

    try {
      const healthResult = await getHealth();
      const statsResult = await getStats(sessionId);
      const activeSessionId = statsResult.session_id;
      persistSessionId(activeSessionId);
      const agentsResult = await getAgentsForSession(activeSessionId);

      setHealth(healthResult.status === "ok" ? "online" : "offline");
      setAgents(agentsResult.agents || []);
      setStats(statsResult.stats);
    } catch (err) {
      setHealth("offline");
      setError(err.message);
    } finally {
      setIsRefreshing(false);
    }
  }

  async function handleSubmit(event) {
    event?.preventDefault();
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content: trimmed,
    };

    setMessages((current) => [...current, userMessage]);
    setInput("");
    setIsLoading(true);
    setError("");

    try {
      const result = await sendChatMessage(trimmed, sessionId);
      persistSessionId(result.session_id);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: result.response,
          agent: result.agent,
          reasoning: result.reasoning,
        },
      ]);
      setStats(result.stats);
      await refreshAgentsOnly(result.session_id);
      setHealth("online");
    } catch (err) {
      setError(err.message);
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: "I could not reach the Course Insight API. Check the backend server and try again.",
          variant: "error",
        },
      ]);
      setHealth("offline");
    } finally {
      setIsLoading(false);
    }
  }

  async function refreshAgentsOnly(activeSessionId = sessionId) {
    try {
      const agentsResult = await getAgentsForSession(activeSessionId);
      setAgents(agentsResult.agents || []);
    } catch {
      // The chat response already handled user-facing API errors.
    }
  }

  async function handleClear() {
    setError("");

    try {
      const result = await clearSession(sessionId);
      persistSessionId(result.session_id);
      setStats(result.stats);
      setMessages(initialMessages);
      await refreshAgentsOnly(result.session_id);
    } catch (err) {
      setError(err.message);
    }
  }

  function persistSessionId(nextSessionId) {
    if (!nextSessionId) return;
    localStorage.setItem(SESSION_STORAGE_KEY, nextSessionId);
    setSessionId(nextSessionId);
  }

  function usePrompt(prompt) {
    setInput(prompt);
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "is-open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">
            <GraduationCap size={24} />
          </div>
          <div>
            <h1>Course Insight</h1>
            <p>Multi-agent course advisor</p>
          </div>
        </div>

        <section className="status-card" aria-label="API status">
          <div className="status-row">
            <span className={`status-dot ${health}`} />
            <span>{health === "online" ? "API online" : health === "checking" ? "Checking API" : "API offline"}</span>
          </div>
          <code>{API_URL}</code>
          {sessionId && <code>session {sessionId.slice(0, 12)}</code>}
        </section>

        <section className="panel">
          <div className="panel-heading">
            <h2>Agents</h2>
            <button className="icon-button" type="button" onClick={refreshSystem} disabled={isRefreshing} title="Refresh">
              {isRefreshing ? <Loader2 className="spin" size={18} /> : <RefreshCcw size={18} />}
            </button>
          </div>

          <div className="agent-list">
            {agents.map((agent) => (
              <div className="agent-item" key={agent.name}>
                <div className="agent-icon">
                  {agent.name === "CourseAgent" ? <BookOpen size={18} /> : <UserRound size={18} />}
                </div>
                <div>
                  <div className="agent-title">
                    <span>{agent.name}</span>
                    <strong>{agent.calls}</strong>
                  </div>
                  <p>{agent.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel metrics-panel">
          <div className="panel-heading">
            <h2>Stats</h2>
            <BarChart3 size={18} />
          </div>
          <div className="metrics-grid">
            <div>
              <span>Conversations</span>
              <strong>{formatMetric(stats?.total_conversations)}</strong>
            </div>
            <div>
              <span>Cached courses</span>
              <strong>{formatMetric(stats?.cached_courses)}</strong>
            </div>
            <div>
              <span>Agent calls</span>
              <strong>{formatMetric(totalCalls)}</strong>
            </div>
          </div>
        </section>

        <button className="secondary-action" type="button" onClick={handleClear}>
          <Trash2 size={17} />
          Clear session
        </button>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <button className="icon-button sidebar-toggle" type="button" onClick={() => setSidebarOpen((open) => !open)} title="Toggle sidebar">
            <PanelLeft size={20} />
          </button>
          <div>
            <h2>Ask Course Insight</h2>
            <p>Courses, prerequisites, difficulty, and instructor context.</p>
          </div>
          <div className={`connection-pill ${health}`}>
            {health === "online" ? <CheckCircle2 size={16} /> : <WifiOff size={16} />}
            <span>{health === "online" ? "Connected" : "Disconnected"}</span>
          </div>
        </header>

        {error && (
          <div className="error-banner" role="alert">
            <AlertCircle size={18} />
            <span>{error}</span>
          </div>
        )}

        <section className="prompt-strip" aria-label="Example prompts">
          {examplePrompts.map((prompt) => (
            <button type="button" key={prompt} onClick={() => usePrompt(prompt)}>
              {prompt}
            </button>
          ))}
        </section>

        <section className="chat-surface" aria-label="Conversation">
          <div className="messages">
            {messages.map((message) => (
              <article className={`message ${message.role} ${message.variant || ""}`} key={message.id}>
                <div className="message-avatar">
                  {message.role === "user" ? <UserRound size={18} /> : <Bot size={18} />}
                </div>
                <div className="message-body">
                  <div className="message-meta">
                    <span>{message.role === "user" ? "You" : "Course Insight"}</span>
                    {message.agent && <strong>{message.agent}</strong>}
                  </div>
                  <p>{message.content}</p>
                  {message.reasoning && <div className="message-reasoning">{message.reasoning}</div>}
                </div>
              </article>
            ))}

            {isLoading && (
              <article className="message assistant">
                <div className="message-avatar">
                  <Bot size={18} />
                </div>
                <div className="message-body loading-message">
                  <div className="message-meta">
                    <span>Course Insight</span>
                  </div>
                  <p>
                    <Loader2 className="spin" size={17} />
                    Routing your question...
                  </p>
                </div>
              </article>
            )}
            <div ref={messagesEndRef} />
          </div>

          <form className="composer" onSubmit={handleSubmit}>
            <div className="composer-input">
              <MessageSquareText size={20} />
              <textarea
                value={input}
                onChange={(event) => setInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    handleSubmit(event);
                  }
                }}
                rows={1}
                placeholder="Ask about CMPUT 174, MATH 100 prerequisites, or a professor..."
                disabled={isLoading}
              />
            </div>
            <button className="send-button" type="submit" disabled={!input.trim() || isLoading}>
              {isLoading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              Send
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}

export default App;
