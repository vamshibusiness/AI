import { useEffect, useState, useRef, useCallback } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

// ── Helpers ──────────────────────────────────────────────────
const genId = () => Math.random().toString(36).slice(2, 10);
const now = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function loadSessions() {
  try { return JSON.parse(localStorage.getItem("jarvis_sessions") || "{}"); }
  catch { return {}; }
}
function saveSessions(sessions) {
  try { localStorage.setItem("jarvis_sessions", JSON.stringify(sessions)); } catch {}
}

// ── Simple Markdown renderer (no external deps) ───────────────
function renderMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    // code blocks
    .replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) =>
      `<pre class="code-block" data-lang="${lang || "code"}"><code>${code.trim()}</code></pre>`)
    // inline code
    .replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>')
    // bold
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    // italic
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    // headers
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm, "<h2>$2</h2>")
    .replace(/^# (.+)$/gm, "<h1>$1</h1>")
    // bullet lists
    .replace(/^[-•] (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>.*<\/li>\n?)+/g, s => `<ul>${s}</ul>`)
    // numbered lists
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    // line breaks
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");
}

// ── Message bubble ────────────────────────────────────────────
function MessageBubble({ msg }) {
  const [copied, setCopied] = useState(false);

  const copyCode = (code) => {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const isUser = msg.role === "user";

  return (
    <div className={`msg-row ${isUser ? "msg-user" : "msg-jarvis"}`}>
      {!isUser && (
        <div className="avatar avatar-jarvis" title="JARVIS">J</div>
      )}
      <div className={`bubble ${isUser ? "bubble-user" : "bubble-jarvis"}`}>
        {isUser ? (
          <span>{msg.content}</span>
        ) : (
          <div
            className="bubble-md"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
          />
        )}
        {msg.citations?.length > 0 && (
          <div className="citation-row">
            {msg.citations.map((c, i) => (
              <span key={i} className="citation-chip">
                📄 {c.source}{c.page ? ` p.${c.page}` : ""}
              </span>
            ))}
          </div>
        )}
        <div className="msg-meta">{msg.time || ""}</div>
      </div>
      {isUser && (
        <div className="avatar avatar-user" title="You">V</div>
      )}
    </div>
  );
}

// ── Typing indicator ─────────────────────────────────────────
function TypingIndicator() {
  return (
    <div className="msg-row msg-jarvis">
      <div className="avatar avatar-jarvis">J</div>
      <div className="bubble bubble-jarvis typing-bubble">
        <span className="dot" /><span className="dot" /><span className="dot" />
      </div>
    </div>
  );
}

// ── Status pill ───────────────────────────────────────────────
const STATUS_LABELS = {
  idle: "● Online",
  listening: "🎙 Listening",
  thinking: "⚡ Thinking",
  speaking: "🔊 Speaking",
  "checking-email": "✉ Checking Email",
  offline: "○ Offline",
};
const STATUS_COLORS = {
  idle: "#22d3ee",
  listening: "#a78bfa",
  thinking: "#fbbf24",
  speaking: "#34d399",
  "checking-email": "#60a5fa",
  offline: "#6b7280",
};

// ── RAG Panel ─────────────────────────────────────────────────
function RagPanel({ ragDocs, loadRagDocs }) {
  const [ragQueryText, setRagQueryText] = useState("");
  const [ragResult, setRagResult] = useState(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragUploading, setRagUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef(null);

  const uploadFile = (file) => {
    if (!file) return;
    const allowed = [".pdf", ".txt", ".md", ".markdown", ".csv"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
      alert("Unsupported file type. Please upload PDF, TXT, MD, or CSV.");
      return;
    }
    setRagUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    fetch(`${API_BASE}/rag/upload`, { method: "POST", body: formData })
      .then(r => r.json())
      .then(d => { setRagUploading(false); if (d.ok) loadRagDocs(); })
      .catch(() => setRagUploading(false));
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files?.[0];
    if (file) uploadFile(file);
  };

  const handleRagQuery = (e) => {
    e.preventDefault();
    if (!ragQueryText.trim()) return;
    setRagLoading(true);
    setRagResult(null);
    fetch(`${API_BASE}/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: ragQueryText.trim() }),
    })
      .then(r => r.json())
      .then(d => { setRagLoading(false); if (d.ok) setRagResult(d); })
      .catch(() => setRagLoading(false));
  };

  return (
    <div className="panel-content">
      <h2 className="panel-title">RAG Knowledge Base</h2>

      {/* Drop zone */}
      <div
        className={`drop-zone ${dragOver ? "drag-active" : ""} ${ragUploading ? "uploading" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: "none" }}
          accept=".pdf,.txt,.md,.markdown,.csv"
          onChange={e => uploadFile(e.target.files?.[0])}
        />
        <div className="drop-icon">{ragUploading ? "⏳" : "📁"}</div>
        <div className="drop-label">
          {ragUploading ? "Indexing document…" : "Drop PDF / TXT / MD / CSV here, or click to browse"}
        </div>
      </div>

      {/* Indexed docs */}
      <div className="section-label">Indexed Documents ({ragDocs.length})</div>
      <div className="doc-list">
        {ragDocs.length === 0 ? (
          <div className="empty-hint">No documents indexed yet.</div>
        ) : ragDocs.map((doc, i) => (
          <div key={i} className="doc-pill">
            <span className="doc-pill-icon">📄</span>
            <span className="doc-pill-name">{doc.filename}</span>
            <span className="doc-pill-meta">{doc.chunk_count} chunks • {doc.pages ?? "?"} pgs</span>
          </div>
        ))}
      </div>

      {/* Query */}
      <div className="section-label">Query Knowledge Base</div>
      <form className="rag-query-form" onSubmit={handleRagQuery}>
        <input
          type="text"
          className="panel-input"
          placeholder="Ask a question about your documents…"
          value={ragQueryText}
          onChange={e => setRagQueryText(e.target.value)}
        />
        <button type="submit" className="panel-btn primary" disabled={ragLoading}>
          {ragLoading ? "Searching…" : "Ask"}
        </button>
      </form>

      {ragResult && (
        <div className="rag-result">
          <div
            className="rag-answer"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(ragResult.answer) }}
          />
          {ragResult.citations?.length > 0 && (
            <div className="citation-row">
              {ragResult.citations.map((c, i) => (
                <span key={i} className="citation-chip">
                  📄 {c.source}{c.page ? ` p.${c.page}` : ""}
                  {c.score != null && ` (${(c.score * 100).toFixed(0)}%)`}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Memory Panel ──────────────────────────────────────────────
function MemoryPanel({ memories, loadMemories }) {
  const [newMemory, setNewMemory] = useState("");
  const [search, setSearch] = useState("");

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newMemory.trim()) return;
    fetch(`${API_BASE}/memory/remember`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: newMemory.trim(), category: "manual" }),
    })
      .then(r => r.json())
      .then(d => { if (d.ok) { setNewMemory(""); loadMemories(); } })
      .catch(() => {});
  };

  const handleForget = (content) => {
    fetch(`${API_BASE}/memory/forget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    })
      .then(r => r.json())
      .then(d => { if (d.ok) loadMemories(); })
      .catch(() => {});
  };

  const filtered = memories.filter(m =>
    (m.content || "").toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="panel-content">
      <h2 className="panel-title">Memory Vault</h2>
      <form className="memory-add-form" onSubmit={handleAdd}>
        <input
          type="text"
          className="panel-input"
          placeholder="Teach JARVIS a fact, preference, or key info…"
          value={newMemory}
          onChange={e => setNewMemory(e.target.value)}
        />
        <button type="submit" className="panel-btn primary">Remember</button>
      </form>

      <input
        type="text"
        className="panel-input search-input"
        placeholder="Filter memories…"
        value={search}
        onChange={e => setSearch(e.target.value)}
      />

      <div className="memory-list">
        {filtered.length === 0 ? (
          <div className="empty-hint">{memories.length === 0 ? "No memories stored yet." : "No matches."}</div>
        ) : filtered.map((m, i) => (
          <div key={i} className="memory-card">
            <div className="memory-text">{m.content}</div>
            <div className="memory-footer">
              <span className="memory-date">{m.created_at ? new Date(m.created_at).toLocaleDateString() : ""}</span>
              <button className="forget-btn" onClick={() => handleForget(m.content)} title="Forget">✕ Forget</button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Telemetry Bar ─────────────────────────────────────────────
function TelemetryBar({ stats }) {
  if (!stats) return null;
  const gpu = stats.gpu;
  const vramPct = gpu ? Math.round((gpu.vram_used_mb / gpu.vram_total_mb) * 100) : null;

  const bar = (pct, warn = 80, danger = 90) => {
    const cls = pct > danger ? "tel-bar-danger" : pct > warn ? "tel-bar-warn" : "tel-bar-ok";
    return (
      <div className="tel-bar-wrap">
        <div className={`tel-bar-fill ${cls}`} style={{ width: `${pct}%` }} />
      </div>
    );
  };

  return (
    <div className="telemetry-bar">
      <div className="tel-item">
        <span className="tel-label">CPU</span>
        {bar(stats.cpu_percent)}
        <span className="tel-val">{stats.cpu_percent}%</span>
      </div>
      <div className="tel-item">
        <span className="tel-label">RAM</span>
        {bar(stats.ram_percent)}
        <span className="tel-val">{stats.ram_percent}%</span>
      </div>
      {vramPct != null && (
        <div className="tel-item">
          <span className="tel-label">VRAM</span>
          {bar(vramPct, 70, 85)}
          <span className="tel-val">{vramPct}%</span>
        </div>
      )}
    </div>
  );
}

// ── Delete Confirmation Modal ──────────────────────────────────
function DeleteModal({ pendingDelete, onConfirm }) {
  if (!pendingDelete) return null;
  return (
    <div className="modal-backdrop">
      <div className="modal-box danger-modal">
        <div className="danger-badge">⚠ SECURITY CONFIRMATION</div>
        <h2 className="modal-title">Confirm Permanent Deletion</h2>
        <p className="modal-body-text">JARVIS is requesting to permanently delete:</p>
        <div className="delete-target">
          <div className="delete-name">{pendingDelete.name}</div>
          <div className="delete-meta">{pendingDelete.is_dir ? "Directory" : "File"}</div>
          <div className="delete-path">{pendingDelete.path}</div>
        </div>
        <div className="modal-actions">
          <button className="panel-btn danger" onClick={() => onConfirm(true)}>
            🗑 Permanently Delete
          </button>
          <button className="panel-btn" onClick={() => onConfirm(false)}>
            ✕ Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Research Modal ────────────────────────────────────────────
function ResearchModal({ items, onClose }) {
  const [selected, setSelected] = useState(null);
  const fmt = (d) => d ? new Date(d).toLocaleString() : "Unknown";

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-box research-modal-box" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="modal-title">Research Results</h2>
          <button className="modal-close" onClick={onClose}>×</button>
        </div>
        {selected ? (
          <div className="research-detail">
            <button className="back-btn" onClick={() => setSelected(null)}>← Back</button>
            <h3>{selected.topic}</h3>
            <div className="research-date">{fmt(selected.created_at)}</div>
            <div className="research-report"
              dangerouslySetInnerHTML={{ __html: renderMarkdown(selected.report || selected.summary) }} />
          </div>
        ) : (
          <div className="research-grid">
            {items.length === 0 ? (
              <div className="empty-hint">No completed research yet.</div>
            ) : items.map((item, i) => (
              <div key={i} className="research-card" onClick={() => setSelected(item)}>
                <h3>{item.topic}</h3>
                <div className="research-date">{fmt(item.created_at)}</div>
                <p className="research-preview">{item.summary?.slice(0, 160)}…</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ═══════════════════════════════════════════════════════════════
// MAIN APP
// ═══════════════════════════════════════════════════════════════
export default function App() {
  // ── Connection / Status ──────────────────────────────────────
  const [status, setStatus] = useState("idle");
  const [backendOnline, setBackendOnline] = useState(false);

  // ── Sidebar ──────────────────────────────────────────────────
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activePanel, setActivePanel] = useState(null); // null | 'rag' | 'memory' | 'telemetry'

  // ── Sessions / Chat ───────────────────────────────────────────
  const [sessions, setSessions] = useState(() => loadSessions());
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    const ids = Object.keys(loadSessions());
    if (ids.length > 0) return ids[ids.length - 1];
    const id = genId();
    const initial = { id, name: "New Chat", messages: [], createdAt: Date.now() };
    saveSessions({ [id]: initial });
    return id;
  });
  const [inputText, setInputText] = useState("");
  const [thinking, setThinking] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  // ── Google integrations ───────────────────────────────────────
  const [calendarSummary, setCalendarSummary] = useState({ event_count: 0, events: [] });
  const [gmailSummary, setGmailSummary] = useState({ unread_count: 0 });

  // ── Research ──────────────────────────────────────────────────
  const [researchSummary, setResearchSummary] = useState({ completed_count: 0, active_count: 0 });
  const [completedResearch, setCompletedResearch] = useState([]);
  const [showResearch, setShowResearch] = useState(false);

  // ── System stats ──────────────────────────────────────────────
  const [systemStats, setSystemStats] = useState(null);

  // ── RAG ───────────────────────────────────────────────────────
  const [ragDocs, setRagDocs] = useState([]);

  // ── Memory ────────────────────────────────────────────────────
  const [memories, setMemories] = useState([]);

  // ── Safety ────────────────────────────────────────────────────
  const [pendingDelete, setPendingDelete] = useState(null);
  const [actionToast, setActionToast] = useState(null);

  // ── Derived ───────────────────────────────────────────────────
  const normalizedStatus = status === "online" ? "idle" : status;
  const currentSession = sessions[currentSessionId] || { messages: [] };
  const messages = currentSession.messages || [];

  // ── Scroll to bottom ─────────────────────────────────────────
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, thinking]);

  // ── Session helpers ───────────────────────────────────────────
  const updateSession = useCallback((id, updater) => {
    setSessions(prev => {
      const updated = { ...prev, [id]: updater(prev[id] || { id, name: "New Chat", messages: [], createdAt: Date.now() }) };
      saveSessions(updated);
      return updated;
    });
  }, []);

  const newChat = () => {
    const id = genId();
    const session = { id, name: "New Chat", messages: [], createdAt: Date.now() };
    setSessions(prev => { const next = { ...prev, [id]: session }; saveSessions(next); return next; });
    setCurrentSessionId(id);
    setInputText("");
    inputRef.current?.focus();
  };

  const deleteSession = (id, e) => {
    e.stopPropagation();
    setSessions(prev => {
      const next = { ...prev };
      delete next[id];
      saveSessions(next);
      if (currentSessionId === id) {
        const remaining = Object.keys(next);
        if (remaining.length > 0) setCurrentSessionId(remaining[remaining.length - 1]);
        else { const nid = genId(); const s = { id: nid, name: "New Chat", messages: [], createdAt: Date.now() }; next[nid] = s; saveSessions(next); setCurrentSessionId(nid); }
      }
      return next;
    });
  };

  const addMessage = (sessionId, msg) => {
    updateSession(sessionId, sess => {
      const newMsgs = [...(sess.messages || []), msg];
      const name = newMsgs.find(m => m.role === "user")?.content?.slice(0, 40) || sess.name;
      return { ...sess, messages: newMsgs, name };
    });
  };

  // ── Loaders ───────────────────────────────────────────────────
  const loadGmailSummary = () =>
    fetch(`${API_BASE}/gmail/summary`).then(r => r.json()).then(d => setGmailSummary({ unread_count: d.unread_count || 0 })).catch(() => {});
  const loadCalendarSummary = () =>
    fetch(`${API_BASE}/calendar/summary`).then(r => r.json()).then(d => setCalendarSummary({ event_count: d.event_count || 0, events: d.events || [] })).catch(() => {});
  const loadResearchSummary = () =>
    fetch(`${API_BASE}/research/summary`).then(r => r.json()).then(d => setResearchSummary({ completed_count: d.completed_count || 0, active_count: d.active_count || 0 })).catch(() => {});
  const loadSystemStats = () =>
    fetch(`${API_BASE}/system/stats`).then(r => r.json()).then(d => { if (d.ok) setSystemStats(d); }).catch(() => {});
  const loadRagDocs = () =>
    fetch(`${API_BASE}/rag/documents`).then(r => r.json()).then(d => { if (d.ok) setRagDocs(d.documents || []); }).catch(() => {});
  const loadMemories = () =>
    fetch(`${API_BASE}/memory/all`).then(r => r.json()).then(d => { if (d.ok) setMemories(d.memories || []); }).catch(() => {});

  // ── WebSocket ──────────────────────────────────────────────────
  useEffect(() => {
    let ws;
    let reconnectTimer;

    const connect = () => {
      ws = new WebSocket(WS_URL);

      ws.onopen = () => { setBackendOnline(true); };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === "chat_message") {
            // Messages from /chat endpoint broadcast — add to current session
            setCurrentSessionId(sid => {
              addMessage(sid, { id: genId(), role: data.role, content: data.content, time: now() });
              return sid;
            });
            if (data.role === "assistant") setThinking(false);
            return;
          }
          if (data.type === "show_completed_research") {
            setCompletedResearch(data.items || []);
            setShowResearch(true);
            loadResearchSummary();
            return;
          }
          if (data.type === "home") { setShowResearch(false); loadResearchSummary(); return; }
          if (data.type === "gmail_summary") { setGmailSummary({ unread_count: data.unread_count || 0 }); return; }
          if (data.type === "calendar_summary") { setCalendarSummary({ event_count: data.event_count || 0, events: data.events || [] }); return; }
          if (data.type === "research_summary") { setResearchSummary({ completed_count: data.completed_count || 0, active_count: data.active_count || 0 }); return; }
          if (data.type === "confirm_delete") { setPendingDelete(data); return; }
          if (data.type === "rag_document_indexed") { loadRagDocs(); return; }
          if (data.type === "computer_action_status") {
            setActionToast(data);
            setTimeout(() => setActionToast(null), 4000);
            return;
          }
          if (data.status) setStatus(data.status.toLowerCase());
        } catch {}
      };

      ws.onclose = () => {
        setBackendOnline(false);
        setStatus("offline");
        reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => { ws.close(); };
    };

    connect();
    loadGmailSummary();
    loadCalendarSummary();
    loadResearchSummary();
    loadSystemStats();
    loadRagDocs();
    loadMemories();

    const statsInterval = setInterval(loadSystemStats, 5000);
    const summaryInterval = setInterval(loadResearchSummary, 8000);
    const gmailInterval = setInterval(loadGmailSummary, 30000);
    const calendarInterval = setInterval(loadCalendarSummary, 60000);

    return () => {
      clearTimeout(reconnectTimer);
      ws.close();
      clearInterval(statsInterval);
      clearInterval(summaryInterval);
      clearInterval(gmailInterval);
      clearInterval(calendarInterval);
    };
  }, []);

  // ── Send chat message ─────────────────────────────────────────
  const sendMessage = async (e) => {
    e?.preventDefault();
    const text = inputText.trim();
    if (!text || thinking) return;

    const userMsg = { id: genId(), role: "user", content: text, time: now() };
    addMessage(currentSessionId, userMsg);
    setInputText("");
    setThinking(true);

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, session_id: currentSessionId }),
      });
      const data = await res.json();
      if (data.ok && data.response) {
        const jarvisMsg = { id: genId(), role: "assistant", content: data.response, time: now() };
        addMessage(currentSessionId, jarvisMsg);
      }
    } catch {
      addMessage(currentSessionId, {
        id: genId(), role: "assistant",
        content: "⚠ Could not reach the JARVIS backend. Is the server running?", time: now(),
      });
    } finally {
      setThinking(false);
    }
  };

  // ── Stop speech ───────────────────────────────────────────────
  const stopSpeech = () => {
    fetch(`${API_BASE}/voice/stop`, { method: "POST" }).catch(() => {});
    setStatus("idle");
  };

  // ── Delete confirmation ───────────────────────────────────────
  const handleConfirmDelete = (confirm) => {
    if (!pendingDelete) return;
    fetch(`${API_BASE}/computer/confirm-delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pendingDelete.path, confirm }),
    }).catch(() => {});
    setPendingDelete(null);
  };

  // ── Keyboard shortcuts ────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      if (e.code === "Space" && normalizedStatus === "speaking" && document.activeElement?.tagName !== "INPUT" && document.activeElement?.tagName !== "TEXTAREA") {
        e.preventDefault();
        stopSpeech();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [normalizedStatus]);

  // ── Render ────────────────────────────────────────────────────
  const sortedSessions = Object.values(sessions).sort((a, b) => b.createdAt - a.createdAt);

  return (
    <div className={`app-shell status-${normalizedStatus}`}>

      {/* ── SIDEBAR ── */}
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : "sidebar-closed"}`}>
        <div className="sidebar-top">
          <div className="sidebar-logo">
            <div className="logo-orb">
              <div className="logo-ring" />
              <span className="logo-j">J</span>
            </div>
            {sidebarOpen && <span className="logo-text">JARVIS</span>}
          </div>
          <button className="sidebar-toggle" onClick={() => setSidebarOpen(v => !v)} title="Toggle sidebar">
            {sidebarOpen ? "◀" : "▶"}
          </button>
        </div>

        {sidebarOpen && (
          <>
            <button className="new-chat-btn" onClick={newChat}>
              + New Chat
            </button>

            {/* Session list */}
            <div className="session-list">
              {sortedSessions.map(sess => (
                <div
                  key={sess.id}
                  className={`session-item ${sess.id === currentSessionId ? "session-active" : ""}`}
                  onClick={() => setCurrentSessionId(sess.id)}
                >
                  <span className="session-name">{sess.name}</span>
                  <button
                    className="session-del"
                    onClick={e => deleteSession(sess.id, e)}
                    title="Delete"
                  >×</button>
                </div>
              ))}
            </div>

            {/* Panel nav */}
            <div className="sidebar-nav">
              <button
                className={`nav-btn ${activePanel === "rag" ? "nav-active" : ""}`}
                onClick={() => setActivePanel(v => v === "rag" ? null : "rag")}
              >
                📚 Knowledge Base
                {ragDocs.length > 0 && <span className="nav-badge">{ragDocs.length}</span>}
              </button>
              <button
                className={`nav-btn ${activePanel === "memory" ? "nav-active" : ""}`}
                onClick={() => setActivePanel(v => v === "memory" ? null : "memory")}
              >
                🧠 Memory Vault
                {memories.length > 0 && <span className="nav-badge">{memories.length}</span>}
              </button>
              <button
                className={`nav-btn ${activePanel === "telemetry" ? "nav-active" : ""}`}
                onClick={() => setActivePanel(v => v === "telemetry" ? null : "telemetry")}
              >
                📊 System Stats
              </button>
              {researchSummary.completed_count > 0 && (
                <button
                  className="nav-btn"
                  onClick={() => fetch(`${API_BASE}/research/show-completed`)}
                >
                  🔬 Research
                  <span className="nav-badge">{researchSummary.completed_count}</span>
                </button>
              )}
            </div>

            {/* Bottom status */}
            <div className="sidebar-footer">
              <div className="conn-status">
                <span
                  className="conn-dot"
                  style={{ background: backendOnline ? "#22d3ee" : "#ef4444" }}
                />
                {backendOnline ? "Backend Connected" : "Backend Offline"}
              </div>
              {gmailSummary.unread_count > 0 && (
                <div className="sidebar-badge email-badge">✉ {gmailSummary.unread_count} unread</div>
              )}
              {calendarSummary.event_count > 0 && (
                <div className="sidebar-badge cal-badge">📅 {calendarSummary.event_count} events</div>
              )}
            </div>
          </>
        )}
      </aside>

      {/* ── MAIN AREA ── */}
      <main className="main-area">

        {/* Top bar */}
        <header className="topbar">
          <div className="topbar-left">
            <div
              className="status-pill"
              style={{ "--status-color": STATUS_COLORS[normalizedStatus] || "#22d3ee" }}
            >
              <span className="status-dot" />
              {STATUS_LABELS[normalizedStatus] || normalizedStatus}
            </div>
            {researchSummary.active_count > 0 && (
              <div className="topbar-badge active-badge">⚡ Researching…</div>
            )}
          </div>
          <div className="topbar-right">
            {normalizedStatus === "speaking" && (
              <button className="stop-btn" onClick={stopSpeech}>
                ■ Silence JARVIS <kbd>Space</kbd>
              </button>
            )}
            {systemStats && (
              <div className="topbar-tel">
                <span>CPU {systemStats.cpu_percent}%</span>
                <span>RAM {systemStats.ram_percent}%</span>
                {systemStats.gpu && (
                  <span>VRAM {Math.round(systemStats.gpu.vram_used_mb / systemStats.gpu.vram_total_mb * 100)}%</span>
                )}
              </div>
            )}
          </div>
        </header>

        {/* Content split: chat + optional side panel */}
        <div className="content-row">

          {/* Chat column */}
          <div className="chat-column">

            {/* Messages */}
            <div className="messages-area">
              {messages.length === 0 && (
                <div className="welcome-screen">
                  <div className="welcome-orb">
                    <div className="orb-ring orb-ring-1" />
                    <div className="orb-ring orb-ring-2" />
                    <div className="orb-ring orb-ring-3" />
                    <div className="orb-core">J</div>
                  </div>
                  <h1 className="welcome-title">How can I assist you?</h1>
                  <p className="welcome-sub">JARVIS — Local AI Assistant</p>
                  <div className="suggestion-chips">
                    {["What's the weather today?", "Show my emails", "Take a screenshot", "What do you remember about me?"].map(s => (
                      <button key={s} className="chip" onClick={() => { setInputText(s); inputRef.current?.focus(); }}>
                        {s}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              {messages.map(msg => <MessageBubble key={msg.id} msg={msg} />)}
              {thinking && <TypingIndicator />}
              <div ref={messagesEndRef} />
            </div>

            {/* Action toast */}
            {actionToast && (
              <div className={`action-toast ${actionToast.success ? "toast-ok" : "toast-fail"}`}>
                {actionToast.success ? "✓" : "✗"} {actionToast.message}
              </div>
            )}

            {/* Input */}
            <form className="input-area" onSubmit={sendMessage}>
              <div className="input-wrap">
                <textarea
                  ref={inputRef}
                  className="chat-input"
                  placeholder="Message JARVIS… (Enter to send, Shift+Enter for new line)"
                  value={inputText}
                  rows={1}
                  onChange={e => {
                    setInputText(e.target.value);
                    e.target.style.height = "auto";
                    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
                  }}
                  onKeyDown={e => {
                    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
                  }}
                  disabled={thinking || normalizedStatus === "offline"}
                />
                <button
                  type="submit"
                  className="send-btn"
                  disabled={thinking || !inputText.trim() || normalizedStatus === "offline"}
                >
                  {thinking ? "⏳" : "↑"}
                </button>
              </div>
              <div className="input-hint">
                {normalizedStatus === "offline"
                  ? "⚠ Backend offline — start the server"
                  : "Enter to send • Shift+Enter for new line • Space to silence voice"}
              </div>
            </form>
          </div>

          {/* Side panel */}
          {activePanel && (
            <aside className="side-panel">
              <div className="side-panel-header">
                <button className="side-panel-close" onClick={() => setActivePanel(null)}>×</button>
              </div>
              {activePanel === "rag" && <RagPanel ragDocs={ragDocs} loadRagDocs={loadRagDocs} />}
              {activePanel === "memory" && <MemoryPanel memories={memories} loadMemories={loadMemories} />}
              {activePanel === "telemetry" && (
                <div className="panel-content">
                  <h2 className="panel-title">System Stats</h2>
                  {systemStats ? (
                    <>
                      <TelemetryBar stats={systemStats} />
                      <div className="stats-grid">
                        <StatCard label="CPU" val={`${systemStats.cpu_percent}%`} />
                        <StatCard label="RAM" val={`${systemStats.ram_used_gb} / ${systemStats.ram_total_gb} GB`} />
                        <StatCard label="RAM %" val={`${systemStats.ram_percent}%`} />
                        <StatCard label="Disk" val={`${systemStats.disk_used_gb} / ${systemStats.disk_total_gb} GB`} />
                        {systemStats.battery_percent != null && (
                          <StatCard label="Battery" val={`${systemStats.battery_percent}% ${systemStats.battery_plugged ? "⚡" : ""}`} />
                        )}
                        {systemStats.gpu && (
                          <>
                            <StatCard label="GPU" val={systemStats.gpu.name} />
                            <StatCard label="VRAM" val={`${systemStats.gpu.vram_used_mb} / ${systemStats.gpu.vram_total_mb} MB`} />
                            <StatCard label="GPU Load" val={`${systemStats.gpu.utilization_pct}%`} />
                          </>
                        )}
                      </div>
                    </>
                  ) : (
                    <div className="empty-hint">Loading system stats…</div>
                  )}
                </div>
              )}
            </aside>
          )}
        </div>
      </main>

      {/* ── MODALS ── */}
      <DeleteModal pendingDelete={pendingDelete} onConfirm={handleConfirmDelete} />
      {showResearch && (
        <ResearchModal items={completedResearch} onClose={() => setShowResearch(false)} />
      )}
    </div>
  );
}

function StatCard({ label, val }) {
  return (
    <div className="stat-card">
      <div className="stat-label">{label}</div>
      <div className="stat-val">{val}</div>
    </div>
  );
}