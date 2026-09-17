import { useEffect, useState, useRef } from "react";
import "./App.css";

const API_BASE = "http://localhost:8000";

function App() {
  const [status, setStatus] = useState("idle");
  const [view, setView] = useState("home"); // 'home' | 'completedResearch' | 'rag' | 'memory'
  
  // Research state
  const [completedResearch, setCompletedResearch] = useState([]);
  const [selectedResearch, setSelectedResearch] = useState(null);
  const [researchSummary, setResearchSummary] = useState({ completed_count: 0, active_count: 0, active_research: null });
  
  // Google integrations state
  const [calendarSummary, setCalendarSummary] = useState({ event_count: 0, events: [] });
  const [gmailSummary, setGmailSummary] = useState({ unread_count: 0 });

  // System Stats Telemetry
  const [systemStats, setSystemStats] = useState(null);

  // RAG State
  const [ragDocs, setRagDocs] = useState([]);
  const [ragQueryText, setRagQueryText] = useState("");
  const [ragResult, setRagResult] = useState(null);
  const [ragLoading, setRagLoading] = useState(false);
  const [ragUploading, setRagUploading] = useState(false);
  const fileInputRef = useRef(null);

  // Memory State
  const [memories, setMemories] = useState([]);
  const [newMemoryText, setNewMemoryText] = useState("");
  const [memorySearchText, setMemorySearchText] = useState("");
  const [memoryLoading, setMemoryLoading] = useState(false);

  // Computer Control State
  const [pendingDelete, setPendingDelete] = useState(null); // { name, size, path, is_dir }
  const [actionStatus, setActionStatus] = useState(null); // { status, message, success }

  const normalizedStatus = status === "online" ? "idle" : status;

  const formatDate = (dateValue) => {
    if (!dateValue) return "Unknown date";
    const date = new Date(dateValue);
    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      year: "numeric",
      hour: "numeric",
      minute: "2-digit",
    });
  };

  // -------------------------------------------------------------
  // Loaders
  // -------------------------------------------------------------
  const loadGmailSummary = () => {
    fetch(`${API_BASE}/gmail/summary`)
      .then((r) => r.json())
      .then((d) => setGmailSummary({ unread_count: d.unread_count || 0 }))
      .catch(() => {});
  };

  const loadCalendarSummary = () => {
    fetch(`${API_BASE}/calendar/summary`)
      .then((r) => r.json())
      .then((d) => setCalendarSummary({ event_count: d.event_count || 0, events: d.events || [] }))
      .catch(() => {});
  };

  const loadResearchSummary = () => {
    fetch(`${API_BASE}/research/summary`)
      .then((r) => r.json())
      .then((d) => setResearchSummary({
        completed_count: d.completed_count || 0,
        active_count: d.active_count || 0,
        active_research: d.active_research || null,
      }))
      .catch(() => {});
  };

  const loadSystemStats = () => {
    fetch(`${API_BASE}/system/stats`)
      .then((r) => r.json())
      .then((d) => { if (d.ok) setSystemStats(d); })
      .catch(() => {});
  };

  const loadRagDocs = () => {
    fetch(`${API_BASE}/rag/documents`)
      .then((r) => r.json())
      .then((d) => { if (d.ok) setRagDocs(d.documents || []); })
      .catch(() => {});
  };

  const loadMemories = () => {
    fetch(`${API_BASE}/memory/all`)
      .then((r) => r.json())
      .then((d) => { if (d.ok) setMemories(d.memories || []); })
      .catch(() => {});
  };

  // -------------------------------------------------------------
  // Actions
  // -------------------------------------------------------------
  const stopSpeech = () => {
    fetch(`${API_BASE}/voice/stop`, { method: "POST" })
      .then(() => setStatus("listening"))
      .catch(() => {});
  };

  const handleRagUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setRagUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    fetch(`${API_BASE}/rag/upload`, { method: "POST", body: formData })
      .then((r) => r.json())
      .then((d) => {
        setRagUploading(false);
        if (d.ok) {
          loadRagDocs();
          if (fileInputRef.current) fileInputRef.current.value = "";
        }
      })
      .catch(() => setRagUploading(false));
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
      .then((r) => r.json())
      .then((d) => {
        setRagLoading(false);
        if (d.ok) setRagResult(d);
      })
      .catch(() => setRagLoading(false));
  };

  const handleAddMemory = (e) => {
    e.preventDefault();
    if (!newMemoryText.trim()) return;
    fetch(`${API_BASE}/memory/remember`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: newMemoryText.trim(), category: "manual" }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) {
          setNewMemoryText("");
          loadMemories();
        }
      })
      .catch(() => {});
  };

  const handleForgetMemory = (content) => {
    fetch(`${API_BASE}/memory/forget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    })
      .then((r) => r.json())
      .then((d) => {
        if (d.ok) loadMemories();
      })
      .catch(() => {});
  };

  const handleConfirmDelete = (confirm) => {
    if (!pendingDelete) return;
    fetch(`${API_BASE}/computer/confirm-delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pendingDelete.path, confirm }),
    })
      .then((r) => r.json())
      .then(() => setPendingDelete(null))
      .catch(() => setPendingDelete(null));
  };

  // -------------------------------------------------------------
  // WebSockets & Polling
  // -------------------------------------------------------------
  useEffect(() => {
    const socket = new WebSocket("ws://localhost:8000/ws");

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "show_completed_research") {
          setCompletedResearch(data.items || []);
          setSelectedResearch(null);
          setView("completedResearch");
          loadResearchSummary();
          return;
        }

        if (data.type === "home") {
          setSelectedResearch(null);
          setView("home");
          loadResearchSummary();
          return;
        }

        if (data.type === "gmail_summary") {
          setGmailSummary({ unread_count: data.unread_count || 0 });
          return;
        }

        if (data.type === "calendar_summary") {
          setCalendarSummary({ event_count: data.event_count || 0, events: data.events || [] });
          return;
        }

        if (data.type === "research_summary") {
          setResearchSummary({
            completed_count: data.completed_count || 0,
            active_count: data.active_count || 0,
            active_research: data.active_research || null,
          });
          return;
        }

        if (data.type === "confirm_delete") {
          setPendingDelete(data);
          return;
        }

        if (data.type === "computer_action_status") {
          setActionStatus(data);
          setTimeout(() => setActionStatus(null), 4000);
          return;
        }

        if (data.type === "rag_document_indexed") {
          loadRagDocs();
          return;
        }

        if (data.status) {
          setStatus(data.status.toLowerCase());
        }
      } catch (err) {
        console.error("Error parsing WebSocket message:", err);
      }
    };

    socket.onclose = () => setStatus("offline");
    socket.onerror = () => setStatus("offline");

    loadResearchSummary();
    loadGmailSummary();
    loadCalendarSummary();
    loadSystemStats();
    loadRagDocs();
    loadMemories();

    const statsInterval = setInterval(loadSystemStats, 4000);
    const summaryInterval = setInterval(loadResearchSummary, 4000);
    const gmailInterval = setInterval(loadGmailSummary, 15000);
    const calendarInterval = setInterval(loadCalendarSummary, 60000);

    return () => {
      socket.close();
      clearInterval(statsInterval);
      clearInterval(summaryInterval);
      clearInterval(gmailInterval);
      clearInterval(calendarInterval);
    };
  }, []);

  // Filter memories
  const filteredMemories = memories.filter((m) =>
    (m.content || "").toLowerCase().includes(memorySearchText.toLowerCase())
  );

  // -------------------------------------------------------------
  // Views
  // -------------------------------------------------------------
  if (view === "completedResearch") {
    return (
      <div className="screen hud-screen research-screen">
        <div className="hud-grid"></div>
        <div className="scan-line"></div>
        <button
          type="button"
          className="research-page-close"
          onClick={() => { setSelectedResearch(null); setView("home"); }}
        >
          Close [Esc]
        </button>
        <h1 className="research-title">Completed Research</h1>
        <div className="research-panel">
          {completedResearch.length === 0 ? (
            <p className="empty-notice">No completed research yet.</p>
          ) : (
            completedResearch.map((item, index) => (
              <div className="research-card" key={index} onClick={() => setSelectedResearch(item)}>
                <h2>{item.topic}</h2>
                <p className="research-date">{formatDate(item.created_at)}</p>
                <p className="research-preview">{item.summary || item.report}</p>
              </div>
            ))
          )}
        </div>

        {selectedResearch && (
          <div className="research-modal-backdrop" onClick={() => setSelectedResearch(null)}>
            <div className="research-modal" onClick={(e) => e.stopPropagation()}>
              <button className="research-close" onClick={() => setSelectedResearch(null)}>×</button>
              <h2>{selectedResearch.topic}</h2>
              <p className="research-date">{formatDate(selectedResearch.created_at)}</p>
              <div className="research-full-report">{selectedResearch.report || selectedResearch.summary}</div>
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className={`screen hud-screen ${normalizedStatus}`}>
      <div className="hud-grid"></div>
      <div className="scan-line"></div>

      <div className="corner corner-top-left"></div>
      <div className="corner corner-top-right"></div>
      <div className="corner corner-bottom-left"></div>
      <div className="corner corner-bottom-right"></div>

      {/* ARC REACTOR CORE */}
      <div className="core reactor-core">
        <div className="hud-ring hud-ring-outer"></div>
        <div className="hud-ring hud-ring-mid"></div>
        <div className="hud-ring hud-ring-inner"></div>
        <div className="reactor-orb">
          <div className="reactor-triangle"></div>
          <div className="reactor-center"></div>
        </div>
      </div>

      {/* TOP HUD ROW - INTEGRATIONS & BADGES */}
      <div className="hud-top-badge-row">
        <div className="hud-badge-left">
          <button
            type="button"
            className="research-hud-badge research-clickable"
            onClick={() => {
              fetch(`${API_BASE}/research/show-completed`);
            }}
          >
            Research: {researchSummary.completed_count}
          </button>

          <button
            type="button"
            className={`research-hud-badge research-clickable ${view === 'rag' ? 'active' : ''}`}
            onClick={() => setView(view === 'rag' ? 'home' : 'rag')}
          >
            RAG Knowledge: {ragDocs.length}
          </button>

          <button
            type="button"
            className={`research-hud-badge research-clickable ${view === 'memory' ? 'active' : ''}`}
            onClick={() => setView(view === 'memory' ? 'home' : 'memory')}
          >
            Memory: {memories.length}
          </button>

          {researchSummary.active_count > 0 && (
            <div className="research-hud-badge active">
              Active Research: {researchSummary.active_count}
              {researchSummary.active_research?.topic && (
                <span>{researchSummary.active_research.topic}</span>
              )}
            </div>
          )}
        </div>

        <div className="hud-badge-right">
          {gmailSummary.unread_count > 0 && (
            <div className="research-hud-badge email has-email">
              Inbox: {gmailSummary.unread_count}
            </div>
          )}

          {calendarSummary.event_count > 0 && (
            <div className="research-hud-badge calendar has-calendar">
              Events: {calendarSummary.event_count}
            </div>
          )}

          {/* TELEMETRY */}
          {systemStats && (
            <div className="telemetry-badge">
              <span>CPU: {systemStats.cpu_percent}%</span>
              <span>RAM: {systemStats.ram_percent}%</span>
              {systemStats.gpu && (
                <span>VRAM: {Math.round((systemStats.gpu.vram_used_mb / systemStats.gpu.vram_total_mb) * 100)}%</span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* ACTION STATUS TOAST */}
      {actionStatus && (
        <div className={`hud-toast ${actionStatus.success ? 'toast-ok' : 'toast-fail'}`}>
          {actionStatus.message}
        </div>
      )}

      {/* VOICE BARGE-IN BUTTON */}
      {normalizedStatus === "speaking" && (
        <div className="barge-in-container">
          <div className="voice-bars">
            <span></span><span></span><span></span><span></span><span></span><span></span><span></span>
          </div>
          <button type="button" className="barge-in-btn" onClick={stopSpeech}>
            ■ SILENCE JARVIS (SPACE)
          </button>
        </div>
      )}

      {normalizedStatus === "thinking" && (
        <div className="thinking-text">NEURAL PROCESSING</div>
      )}

      {/* RAG MODAL DRAWER */}
      {view === "rag" && (
        <div className="hud-modal-backdrop" onClick={() => setView("home")}>
          <div className="hud-modal rag-modal" onClick={(e) => e.stopPropagation()}>
            <div className="hud-modal-header">
              <h2>RAG KNOWLEDGE VAULT (LOCAL FAISS)</h2>
              <button className="hud-modal-close" onClick={() => setView("home")}>×</button>
            </div>

            <div className="hud-modal-body">
              {/* Upload section */}
              <div className="rag-upload-box">
                <input
                  type="file"
                  ref={fileInputRef}
                  style={{ display: "none" }}
                  accept=".pdf,.txt,.md,.markdown,.csv"
                  onChange={handleRagUpload}
                />
                <button
                  type="button"
                  className="hud-btn"
                  disabled={ragUploading}
                  onClick={() => fileInputRef.current?.click()}
                >
                  {ragUploading ? "INDEXING DOCUMENT..." : "+ UPLOAD DOCUMENT (PDF, TXT, MD, CSV)"}
                </button>
                <span className="rag-hint">Auto-chunked, embedded with MiniLM, and indexed into FAISS.</span>
              </div>

              {/* Document List */}
              <div className="rag-docs-list">
                <h3>INDEXED DOCUMENTS ({ragDocs.length})</h3>
                <div className="rag-docs-grid">
                  {ragDocs.map((doc, idx) => (
                    <div key={idx} className="rag-doc-pill">
                      <span className="rag-doc-name">{doc.filename}</span>
                      <span className="rag-doc-meta">{doc.chunk_count} chunks • {doc.pages} pgs</span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Interactive RAG Query */}
              <div className="rag-query-section">
                <h3>QUERY KNOWLEDGE BASE</h3>
                <form onSubmit={handleRagQuery} className="rag-query-form">
                  <input
                    type="text"
                    className="hud-input"
                    placeholder="Ask a question about your indexed documents..."
                    value={ragQueryText}
                    onChange={(e) => setRagQueryText(e.target.value)}
                  />
                  <button type="submit" className="hud-btn primary" disabled={ragLoading}>
                    {ragLoading ? "SEARCHING..." : "QUERY"}
                  </button>
                </form>

                {ragResult && (
                  <div className="rag-result-box">
                    <div className="rag-answer">{ragResult.answer}</div>
                    {ragResult.citations?.length > 0 && (
                      <div className="rag-citations">
                        <h4>SOURCES & CITATIONS:</h4>
                        {ragResult.citations.map((c, i) => (
                          <span key={i} className="citation-badge">
                            [{c.source}{c.page ? ` p.${c.page}` : ""}]
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* MEMORY MODAL DRAWER */}
      {view === "memory" && (
        <div className="hud-modal-backdrop" onClick={() => setView("home")}>
          <div className="hud-modal memory-modal" onClick={(e) => e.stopPropagation()}>
            <div className="hud-modal-header">
              <h2>LONG-TERM MEMORY STORE (SQLITE + FAISS)</h2>
              <button className="hud-modal-close" onClick={() => setView("home")}>×</button>
            </div>

            <div className="hud-modal-body">
              {/* Add Memory Form */}
              <form onSubmit={handleAddMemory} className="memory-add-form">
                <input
                  type="text"
                  className="hud-input"
                  placeholder="Teach JARVIS a new personal fact, preference, or key info..."
                  value={newMemoryText}
                  onChange={(e) => setNewMemoryText(e.target.value)}
                />
                <button type="submit" className="hud-btn primary">+ REMEMBER</button>
              </form>

              {/* Memory Search */}
              <div className="memory-search-box">
                <input
                  type="text"
                  className="hud-input search"
                  placeholder="Filter memories..."
                  value={memorySearchText}
                  onChange={(e) => setMemorySearchText(e.target.value)}
                />
              </div>

              {/* Memory List */}
              <div className="memory-list">
                {filteredMemories.length === 0 ? (
                  <p className="empty-notice">No memories matching your search.</p>
                ) : (
                  filteredMemories.map((m, idx) => (
                    <div key={idx} className="memory-item">
                      <div className="memory-text">{m.content}</div>
                      <div className="memory-actions">
                        <span className="memory-date">{m.created_at ? new Date(m.created_at).toLocaleDateString() : ""}</span>
                        <button
                          type="button"
                          className="memory-del-btn"
                          onClick={() => handleForgetMemory(m.content)}
                          title="Forget this memory"
                        >
                          ✕ Forget
                        </button>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* COMPUTER CONTROL CONFIRMATION MODAL */}
      {pendingDelete && (
        <div className="hud-modal-backdrop alert-backdrop">
          <div className="hud-modal alert-modal" onClick={(e) => e.stopPropagation()}>
            <div className="alert-badge">SECURITY CONFIRMATION REQUIRED</div>
            <h2>CONFIRM PERMANENT DELETION</h2>
            <p className="alert-text">
              JARVIS requested to permanently delete:
            </p>
            <div className="alert-target-box">
              <div className="alert-name">{pendingDelete.name}</div>
              <div className="alert-meta">{pendingDelete.size} • {pendingDelete.is_dir ? "Directory" : "File"}</div>
              <div className="alert-path">{pendingDelete.path}</div>
            </div>
            <div className="alert-actions">
              <button
                type="button"
                className="hud-btn danger"
                onClick={() => handleConfirmDelete(true)}
              >
                PERMANENTLY DELETE
              </button>
              <button
                type="button"
                className="hud-btn"
                onClick={() => handleConfirmDelete(false)}
              >
                CANCEL (ABORT)
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;