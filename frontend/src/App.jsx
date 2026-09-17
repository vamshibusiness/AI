import { useEffect, useState, useRef, useCallback } from "react";
import "./App.css";
import {
  PlusIcon,
  SearchIcon,
  MessageSquareIcon,
  TrashIcon,
  BookOpenIcon,
  BrainIcon,
  BarChartIcon,
  CompassIcon,
  PaperclipIcon,
  MicIcon,
  SendIcon,
  SquareIcon,
  CloseIcon,
  MenuIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  FileTextIcon,
  UploadCloudIcon,
  SparklesIcon,
  AlertTriangleIcon,
  VolumeIcon,
} from "./icons.jsx";

const API_BASE = "http://localhost:8000";
const WS_URL = "ws://localhost:8000/ws";

const STORAGE_KEY = "jarvis_conversations_v4";
const genId = () => "msg_" + Math.random().toString(36).slice(2, 10) + "_" + Date.now().toString(36);
const fmtTime = () => new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

function loadSessionsFromStorage() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed === "object" && Object.keys(parsed).length > 0) {
        return parsed;
      }
    }
  } catch {}
  const initialId = "chat_" + Date.now();
  const initial = {
    [initialId]: {
      id: initialId,
      name: "New Chat",
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
  };
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(initial)); } catch {}
  return initial;
}

function saveSessionsToStorage(sessions) {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions)); } catch {}
}

// ── Markdown Parser (Zero Emojis, Clean Code Cards) ───────────
function renderMarkdown(text) {
  if (!text) return "";
  let html = text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");

  // Code blocks: ```lang ... ```
  html = html.replace(/```(\w*)\n?([\s\S]*?)```/g, (_, lang, code) => {
    const cleanCode = code.trim();
    const l = lang ? lang.toLowerCase() : "code";
    return `<div class="code-block-card">
      <div class="code-block-header">
        <span class="code-block-lang">${l}</span>
        <button class="copy-code-button" onclick="navigator.clipboard.writeText(decodeURIComponent('${encodeURIComponent(cleanCode)}')).then(()=>{this.innerText='Copied!';setTimeout(()=>this.innerText='Copy',1500)})">Copy</button>
      </div>
      <pre><code>${cleanCode}</code></pre>
    </div>`;
  });

  // Inline code: `code`
  html = html.replace(/`([^`]+)`/g, '<code class="code-inline">$1</code>');

  // Bold & Italic
  html = html.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/\*(.+?)\*/g, "<em>$1</em>");

  // Headers
  html = html.replace(/^### (.+)$/gm, "<h3>$1</h3>");
  html = html.replace(/^## (.+)$/gm, "<h2>$1</h2>");
  html = html.replace(/^# (.+)$/gm, "<h1>$1</h1>");

  // Lists
  html = html.replace(/^[-*•] (.+)$/gm, "<li>$1</li>");
  html = html.replace(/(<li>.*<\/li>\n?)+/g, "<ul>$&</ul>");

  // Paragraphs
  html = html.replace(/\n\n/g, "</p><p>");
  html = html.replace(/\n/g, "<br/>");

  return `<p>${html}</p>`;
}

export default function App() {
  // ── Connection & Assistant State ──
  const [status, setStatus] = useState("idle");
  const [backendOnline, setBackendOnline] = useState(false);
  const [agentActionStatus, setAgentActionStatus] = useState(null); // { type, status, message, success }

  // ── Layout & Modals ──
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [activeModal, setActiveModal] = useState(null); // null | 'rag' | 'memory' | 'stats' | 'research'

  // ── Voice Assistant Overlay ──
  const [voiceOverlayActive, setVoiceOverlayActive] = useState(false);

  // ── Chat Sessions ──
  const [sessions, setSessions] = useState(() => loadSessionsFromStorage());
  const [currentSessionId, setCurrentSessionId] = useState(() => {
    const s = loadSessionsFromStorage();
    const ids = Object.keys(s);
    return ids[ids.length - 1] || "chat_default";
  });
  const [chatSearch, setChatSearch] = useState("");

  // ── Message Input ──
  const [inputText, setInputText] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [toastMessage, setToastMessage] = useState(null);

  // ── Modules Data ──
  const [ragDocs, setRagDocs] = useState([]);
  const [ragUploading, setRagUploading] = useState(false);
  const [memories, setMemories] = useState([]);
  const [systemStats, setSystemStats] = useState(null);
  const [researchSummary, setResearchSummary] = useState({ completed_count: 0, active_count: 0 });
  const [completedResearch, setCompletedResearch] = useState([]);
  const [pendingDelete, setPendingDelete] = useState(null);

  // ── Refs ──
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const wsRef = useRef(null);

  const normalizedStatus = status === "online" ? "idle" : status;
  const currentSession = sessions[currentSessionId] || { id: currentSessionId, messages: [] };
  const messages = currentSession.messages || [];

  // Scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, isStreaming]);

  const showToast = (msg, duration = 3200) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), duration);
  };

  // ── Session Management (Strict Deduplication) ─────────────────
  const addMessageToSession = useCallback((sessionId, message) => {
    setSessions(prev => {
      const sess = prev[sessionId] || {
        id: sessionId,
        name: "New Chat",
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      // Strict Deduplication Rule 1: ID uniqueness
      if (message.id && sess.messages.some(m => m.id === message.id)) {
        return prev;
      }

      // Strict Deduplication Rule 2: same content within 3s
      const last = sess.messages[sess.messages.length - 1];
      if (
        last &&
        last.role === message.role &&
        last.content === message.content &&
        Math.abs(Date.now() - (last.timestamp || 0)) < 3000
      ) {
        return prev;
      }

      const stamped = {
        ...message,
        id: message.id || genId(),
        timestamp: message.timestamp || Date.now(),
        time: message.time || fmtTime(),
      };

      let newName = sess.name;
      if (sess.name === "New Chat" && stamped.role === "user") {
        newName = stamped.content.slice(0, 30).trim() || "New Chat";
      }

      const updated = {
        ...prev,
        [sessionId]: {
          ...sess,
          messages: [...sess.messages, stamped],
          name: newName,
          updatedAt: Date.now(),
        },
      };

      saveSessionsToStorage(updated);
      return updated;
    });
  }, []);

  const updateAssistantMessageChunk = useCallback((sessionId, messageId, chunk, isDone = false) => {
    setSessions(prev => {
      const sess = prev[sessionId];
      if (!sess) return prev;

      const updatedMessages = sess.messages.map(m => {
        if (m.id === messageId) {
          return {
            ...m,
            content: m.content + chunk,
            isStreaming: !isDone,
          };
        }
        return m;
      });

      const updated = {
        ...prev,
        [sessionId]: {
          ...sess,
          messages: updatedMessages,
          updatedAt: Date.now(),
        },
      };

      if (isDone) {
        saveSessionsToStorage(updated);
      }
      return updated;
    });
  }, []);

  const createNewChat = () => {
    const newId = "chat_" + Date.now();
    const newSession = {
      id: newId,
      name: "New Chat",
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setSessions(prev => {
      const updated = { ...prev, [newId]: newSession };
      saveSessionsToStorage(updated);
      return updated;
    });
    setCurrentSessionId(newId);
    setInputText("");
    setTimeout(() => textareaRef.current?.focus(), 50);
  };

  const deleteChat = (id, e) => {
    e.stopPropagation();
    setSessions(prev => {
      const updated = { ...prev };
      delete updated[id];
      const remainingIds = Object.keys(updated);
      if (remainingIds.length === 0) {
        const freshId = "chat_" + Date.now();
        updated[freshId] = {
          id: freshId,
          name: "New Chat",
          messages: [],
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        setCurrentSessionId(freshId);
      } else if (currentSessionId === id) {
        setCurrentSessionId(remainingIds[remainingIds.length - 1]);
      }
      saveSessionsToStorage(updated);
      return updated;
    });
  };

  // ── Loaders ───────────────────────────────────────────────────
  const fetchRagDocs = () => {
    fetch(`${API_BASE}/rag/documents`)
      .then(r => r.json())
      .then(d => { if (d.ok) setRagDocs(d.documents || []); })
      .catch(() => {});
  };

  const fetchMemories = () => {
    fetch(`${API_BASE}/memory/all`)
      .then(r => r.json())
      .then(d => { if (d.ok) setMemories(d.memories || []); })
      .catch(() => {});
  };

  const fetchSystemStats = () => {
    fetch(`${API_BASE}/system/stats`)
      .then(r => r.json())
      .then(d => { if (d.ok) setSystemStats(d); })
      .catch(() => {});
  };

  const fetchResearchSummary = () => {
    fetch(`${API_BASE}/research/summary`)
      .then(r => r.json())
      .then(d => setResearchSummary({ completed_count: d.completed_count || 0, active_count: d.active_count || 0 }))
      .catch(() => {});
  };

  // ── WebSocket Lifecycle ───────────────────────────────────────
  useEffect(() => {
    let reconnectTimer = null;
    let isMounted = true;

    const connectWS = () => {
      if (!isMounted) return;
      if (wsRef.current && (wsRef.current.readyState === WebSocket.OPEN || wsRef.current.readyState === WebSocket.CONNECTING)) {
        return;
      }

      try {
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          if (!isMounted) return;
          setBackendOnline(true);
        };

        ws.onmessage = (e) => {
          if (!isMounted) return;
          try {
            const data = JSON.parse(e.data);

            if (data.status) {
              const s = data.status.toLowerCase();
              setStatus(s);
              // Auto-open voice overlay if voice wake-word triggers listening or speaking
              if (s === "listening" || s === "speaking") {
                setVoiceOverlayActive(true);
              } else if (s === "idle") {
                // Auto-close overlay after brief settle
                setTimeout(() => {
                  setVoiceOverlayActive(false);
                  setAgentActionStatus(null);
                }, 3000);
              }
            }

            if (data.type === "computer_action_status") {
              setAgentActionStatus(data);
              setVoiceOverlayActive(true);
              if (data.status === "done" || data.status === "failed") {
                setTimeout(() => setAgentActionStatus(null), 4000);
              }
            }

            if (data.type === "confirm_delete") {
              setPendingDelete(data);
            }

            if (data.type === "rag_document_indexed") {
              fetchRagDocs();
              showToast("Document indexed in Knowledge Base.");
            }

            if (data.type === "show_completed_research") {
              setCompletedResearch(data.items || []);
              setActiveModal("research");
              fetchResearchSummary();
            }

            if (data.type === "research_summary") {
              setResearchSummary({ completed_count: data.completed_count || 0, active_count: data.active_count || 0 });
            }
          } catch {}
        };

        ws.onclose = () => {
          if (!isMounted) return;
          setBackendOnline(false);
          setStatus("offline");
          wsRef.current = null;
          reconnectTimer = setTimeout(connectWS, 4000);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        reconnectTimer = setTimeout(connectWS, 4000);
      }
    };

    connectWS();
    fetchRagDocs();
    fetchMemories();
    fetchSystemStats();
    fetchResearchSummary();

    const statsTimer = setInterval(fetchSystemStats, 6000);
    const researchTimer = setInterval(fetchResearchSummary, 10000);

    return () => {
      isMounted = false;
      clearTimeout(reconnectTimer);
      clearInterval(statsTimer);
      clearInterval(researchTimer);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, []);

  // ── MODE A: CHAT MODE (PROGRESSIVE SSE STREAMING — NO TTS) ─────
  const handleSendMessage = async (e) => {
    if (e) e.preventDefault();
    const text = inputText.trim();
    if (!text || isStreaming || normalizedStatus === "offline") return;

    const userMsgId = genId();
    const assistantMsgId = genId();

    // 1. Append user message ONCE
    addMessageToSession(currentSessionId, {
      id: userMsgId,
      role: "user",
      content: text,
      time: fmtTime(),
      timestamp: Date.now(),
    });

    setInputText("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setIsStreaming(true);

    // 2. Append empty assistant message ready to receive streaming chunks
    addMessageToSession(currentSessionId, {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      time: fmtTime(),
      timestamp: Date.now(),
      isStreaming: true,
    });

    try {
      const response = await fetch(`${API_BASE}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          session_id: currentSessionId,
          msg_id: assistantMsgId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server returned HTTP ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            try {
              const payload = JSON.parse(line.slice(6));
              if (payload.chunk) {
                updateAssistantMessageChunk(currentSessionId, assistantMsgId, payload.chunk, false);
              }
              if (payload.done) {
                updateAssistantMessageChunk(currentSessionId, assistantMsgId, "", true);
              }
              if (payload.error) {
                updateAssistantMessageChunk(currentSessionId, assistantMsgId, `\n\n*Error: ${payload.error}*`, true);
              }
            } catch {}
          }
        }
      }

      // Finalize message stream
      updateAssistantMessageChunk(currentSessionId, assistantMsgId, "", true);
    } catch (err) {
      updateAssistantMessageChunk(
        currentSessionId,
        assistantMsgId,
        `Could not reach the JARVIS backend mainframe (${err.message}).`,
        true
      );
    } finally {
      setIsStreaming(false);
      setTimeout(() => textareaRef.current?.focus(), 50);
    }
  };

  // ── MODE B: VOICE MODE (MICROPHONE & OVERLAY) ─────────────────
  const handleMicToggle = () => {
    if (normalizedStatus === "speaking") {
      // Silence active speech
      fetch(`${API_BASE}/voice/stop`, { method: "POST" }).catch(() => {});
      setStatus("idle");
      setVoiceOverlayActive(false);
      showToast("JARVIS voice output silenced.");
    } else {
      // Activate voice listening
      setVoiceOverlayActive(true);
      fetch(`${API_BASE}/voice/trigger`, { method: "POST" })
        .then(r => r.json())
        .then(d => {
          if (d.ok) showToast("Voice Mode activated. Speak naturally.");
        })
        .catch(() => showToast("Could not activate voice listening."));
    }
  };

  const handleSilenceVoice = () => {
    fetch(`${API_BASE}/voice/stop`, { method: "POST" }).catch(() => {});
    setStatus("idle");
    setVoiceOverlayActive(false);
    showToast("JARVIS voice silenced.");
  };

  // Keyboard shortcut: Space to silence active voice
  useEffect(() => {
    const onKey = (e) => {
      if (
        e.code === "Space" &&
        normalizedStatus === "speaking" &&
        document.activeElement?.tagName !== "INPUT" &&
        document.activeElement?.tagName !== "TEXTAREA"
      ) {
        e.preventDefault();
        handleSilenceVoice();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [normalizedStatus]);

  // ── Document Attachment Upload (RAG) ──────────────────────────
  const handleFileUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const allowed = [".pdf", ".txt", ".md", ".markdown", ".csv"];
    const ext = "." + file.name.split(".").pop().toLowerCase();
    if (!allowed.includes(ext)) {
      alert("Unsupported file. Please select a PDF, TXT, MD, or CSV document.");
      return;
    }

    setRagUploading(true);
    showToast(`Indexing "${file.name}" into Knowledge Base...`, 5000);

    const formData = new FormData();
    formData.append("file", file);

    fetch(`${API_BASE}/rag/upload`, { method: "POST", body: formData })
      .then(r => r.json())
      .then(d => {
        setRagUploading(false);
        if (d.ok) {
          fetchRagDocs();
          showToast(`"${file.name}" successfully indexed into Knowledge Base.`);
        } else {
          showToast(`Upload failed: ${d.error || "Unknown error"}`);
        }
      })
      .catch(() => {
        setRagUploading(false);
        showToast("Upload failed: server connection error.");
      });

    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── Permanent Deletion Confirmation ───────────────────────────
  const handleConfirmDelete = (confirmed) => {
    if (!pendingDelete) return;
    fetch(`${API_BASE}/computer/confirm-delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ path: pendingDelete.path, confirm: confirmed }),
    }).catch(() => {});
    setPendingDelete(null);
    showToast(confirmed ? "Item deleted." : "Deletion cancelled.");
  };

  const filteredSessions = Object.values(sessions)
    .filter(s => s.name?.toLowerCase().includes(chatSearch.toLowerCase()))
    .sort((a, b) => (b.updatedAt || 0) - (a.updatedAt || 0));

  return (
    <div className="agent-shell">
      {/* Hidden file input for attachment upload */}
      <input
        type="file"
        ref={fileInputRef}
        style={{ display: "none" }}
        accept=".pdf,.txt,.md,.markdown,.csv"
        onChange={handleFileUpload}
      />

      {/* ── LEFT COLLAPSIBLE SIDEBAR ── */}
      <aside className={`agent-sidebar ${sidebarOpen ? "open" : "collapsed"}`}>
        <div className="sidebar-top-bar">
          <div className="sidebar-brand">
            <div className="brand-badge">
              <div className="brand-badge-ring" />
              <span>J</span>
            </div>
            {sidebarOpen && <span className="brand-text">JARVIS</span>}
          </div>
          <button
            className="sidebar-collapse-btn"
            onClick={() => setSidebarOpen(v => !v)}
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {sidebarOpen ? <ChevronLeftIcon /> : <ChevronRightIcon />}
          </button>
        </div>

        {sidebarOpen && (
          <>
            {/* New Chat Button */}
            <div className="sidebar-action-container">
              <button className="new-chat-button" onClick={createNewChat}>
                <PlusIcon />
                <span>New chat</span>
              </button>
            </div>

            {/* Chat Search */}
            <div className="sidebar-search-container">
              <div className="search-input-box">
                <SearchIcon />
                <input
                  type="text"
                  placeholder="Search conversations..."
                  value={chatSearch}
                  onChange={e => setChatSearch(e.target.value)}
                />
              </div>
            </div>

            {/* Conversation History */}
            <div className="sidebar-chats-scroll">
              <div className="section-heading">Conversations</div>
              {filteredSessions.map(sess => (
                <div
                  key={sess.id}
                  className={`chat-session-row ${sess.id === currentSessionId ? "active" : ""}`}
                  onClick={() => setCurrentSessionId(sess.id)}
                >
                  <MessageSquareIcon className="chat-row-icon" />
                  <span className="chat-row-label">{sess.name}</span>
                  <button
                    className="chat-delete-button"
                    onClick={e => deleteChat(sess.id, e)}
                    title="Delete conversation"
                  >
                    <TrashIcon />
                  </button>
                </div>
              ))}
            </div>

            {/* Assistant Tools Navigation */}
            <div className="sidebar-tools-container">
              <div className="section-heading">Assistant Tools</div>
              <button
                className={`tool-nav-btn ${activeModal === "rag" ? "active" : ""}`}
                onClick={() => setActiveModal("rag")}
              >
                <div className="tool-nav-left">
                  <BookOpenIcon />
                  <span>Knowledge Base</span>
                </div>
                {ragDocs.length > 0 && <span className="tool-count-pill">{ragDocs.length}</span>}
              </button>
              <button
                className={`tool-nav-btn ${activeModal === "memory" ? "active" : ""}`}
                onClick={() => setActiveModal("memory")}
              >
                <div className="tool-nav-left">
                  <BrainIcon />
                  <span>Memory Vault</span>
                </div>
                {memories.length > 0 && <span className="tool-count-pill">{memories.length}</span>}
              </button>
              <button
                className={`tool-nav-btn ${activeModal === "stats" ? "active" : ""}`}
                onClick={() => setActiveModal("stats")}
              >
                <div className="tool-nav-left">
                  <BarChartIcon />
                  <span>System Stats</span>
                </div>
              </button>
              {researchSummary.completed_count > 0 && (
                <button
                  className="tool-nav-btn"
                  onClick={() => fetch(`${API_BASE}/research/show-completed`)}
                >
                  <div className="tool-nav-left">
                    <CompassIcon />
                    <span>Research Reports</span>
                  </div>
                  <span className="tool-count-pill">{researchSummary.completed_count}</span>
                </button>
              )}
            </div>

            {/* Sidebar Footer */}
            <div className="sidebar-bottom-bar">
              <div className="connection-status-indicator">
                <span
                  className="status-dot"
                  style={{ background: backendOnline ? "#22d3ee" : "#ef4444" }}
                />
                <span className="status-label-text">
                  {backendOnline ? "JARVIS Online" : "Backend Offline"}
                </span>
              </div>
              <div className="developer-tag">Owner: Vamshi Krishna</div>
            </div>
          </>
        )}
      </aside>

      {/* ── MAIN WORKSPACE (FULL WIDTH CHAT) ── */}
      <main className="agent-main-view">
        {/* Top Header Navbar */}
        <header className="main-top-navbar">
          <div className="top-nav-left">
            {!sidebarOpen && (
              <button
                className="expand-sidebar-trigger"
                onClick={() => setSidebarOpen(true)}
                title="Expand sidebar"
              >
                <MenuIcon />
              </button>
            )}
            <div className="model-chip">
              <SparklesIcon />
              <span>JARVIS • llama3.2:3b</span>
            </div>
          </div>

          <div className="top-nav-right">
            {/* Live Status Pill */}
            <div className={`status-pill ${normalizedStatus}`}>
              <span className="pill-dot" />
              <span className="pill-text">{normalizedStatus.toUpperCase()}</span>
            </div>

            {/* Silence Button (visible when JARVIS is speaking in Voice Mode) */}
            {normalizedStatus === "speaking" && (
              <button className="silence-voice-trigger" onClick={handleSilenceVoice}>
                <SquareIcon />
                <span>Silence JARVIS</span>
                <kbd>Space</kbd>
              </button>
            )}
          </div>
        </header>

        {/* Conversation Message Stream */}
        <div className="conversation-viewport">
          {messages.length === 0 ? (
            /* Clean Assistant Welcome Hero */
            <div className="agent-welcome-hero">
              <div className="welcome-orb-container">
                <div className="welcome-ring ring-outer" />
                <div className="welcome-ring ring-inner" />
                <div className="welcome-core">J</div>
              </div>
              <h1 className="welcome-hero-title">How can I assist you today, sir?</h1>
              <p className="welcome-hero-subtitle">
                Local-First Autonomous AI Agent • Multi-step Computer Control, Voice, RAG & Memory
              </p>

              <div className="starter-prompts-grid">
                {[
                  { title: "Open Notepad and type Hello Vamshi", sub: "Multi-step computer control agent" },
                  { title: "Search for today's AI news", sub: "Deep web research & synthesis" },
                  { title: "What key facts do you remember about me?", sub: "Query long-term Memory Vault" },
                  { title: "What is the weather forecast today?", sub: "Retrieve local meteorological report" },
                ].map((p, idx) => (
                  <div
                    key={idx}
                    className="starter-prompt-card"
                    onClick={() => {
                      setInputText(p.title);
                      textareaRef.current?.focus();
                    }}
                  >
                    <div className="starter-card-title">{p.title}</div>
                    <div className="starter-card-sub">{p.sub}</div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            /* Messages Stream with Strict Left/Right Alignment */
            <div className="messages-stream-list">
              {messages.map(msg => {
                const isUser = msg.role === "user";
                return (
                  <div
                    key={msg.id}
                    className={`message-turn-row ${isUser ? "user-side-row" : "jarvis-side-row"}`}
                  >
                    <div className="turn-card-wrapper">
                      {/* Avatar */}
                      <div className={`avatar-pill ${isUser ? "avatar-user" : "avatar-jarvis"}`}>
                        {isUser ? "V" : "J"}
                      </div>

                      {/* Message Content Bubble */}
                      <div className={`message-bubble ${isUser ? "user-bubble" : "jarvis-bubble"}`}>
                        <div className="message-header-meta">
                          <span className="sender-name">{isUser ? "Vamshi Krishna" : "JARVIS"}</span>
                          <span className="sent-time">{msg.time}</span>
                        </div>

                        {isUser ? (
                          <div className="user-raw-text">{msg.content}</div>
                        ) : (
                          <div
                            className="jarvis-formatted-markdown"
                            dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                          />
                        )}

                        {/* RAG Citations */}
                        {msg.citations?.length > 0 && (
                          <div className="citations-tray">
                            {msg.citations.map((c, i) => (
                              <span key={i} className="citation-tag">
                                <FileTextIcon size={12} />
                                <span>{c.source}{c.page ? ` p.${c.page}` : ""}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Floating Toast Notification */}
        {toastMessage && (
          <div className="floating-agent-toast">
            <span>{toastMessage}</span>
          </div>
        )}

        {/* ── CHATGPT-STYLE BOTTOM INPUT BAR ── */}
        <div className="bottom-input-container">
          <form className="input-bar-card" onSubmit={handleSendMessage}>
            {/* Attachment Button (Uploads to RAG Knowledge Base) */}
            <button
              type="button"
              className="action-icon-btn attachment-btn"
              onClick={() => fileInputRef.current?.click()}
              title="Upload document to Knowledge Base"
              disabled={ragUploading}
            >
              <PaperclipIcon />
            </button>

            {/* Auto-expanding Message Textarea */}
            <textarea
              ref={textareaRef}
              className="chat-textarea-field"
              placeholder="Message JARVIS... (Enter to send, Shift+Enter for newline)"
              rows={1}
              value={inputText}
              onChange={e => {
                setInputText(e.target.value);
                e.target.style.height = "auto";
                e.target.style.height = Math.min(e.target.scrollHeight, 180) + "px";
              }}
              onKeyDown={e => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              disabled={isStreaming || normalizedStatus === "offline"}
            />

            {/* Real Microphone Button (Activates Voice Mode) */}
            <button
              type="button"
              className={`action-icon-btn mic-btn ${normalizedStatus}`}
              onClick={handleMicToggle}
              title={normalizedStatus === "speaking" ? "Silence JARVIS" : "Activate Voice Mode"}
            >
              {normalizedStatus === "speaking" ? <VolumeIcon /> : <MicIcon />}
            </button>

            {/* Send Button */}
            <button
              type="submit"
              className="action-icon-btn send-btn"
              disabled={isStreaming || !inputText.trim() || normalizedStatus === "offline"}
              title="Send message"
            >
              <SendIcon />
            </button>
          </form>

          <div className="bottom-sub-disclaimer">
            JARVIS Local AI Agent • llama3.2:3b • Press Space to silence speech output
          </div>
        </div>
      </main>

      {/* ── MAX-STYLE FLOATING VOICE ASSISTANT OVERLAY ── */}
      {voiceOverlayActive && (
        <div className="voice-assistant-overlay-hud">
          <div className="voice-hud-header">
            <div className="voice-hud-brand">
              <span className="hud-orb-dot" />
              <span>JARVIS Assistant</span>
            </div>
            <button
              className="voice-hud-close"
              onClick={() => {
                setVoiceOverlayActive(false);
                if (normalizedStatus === "speaking") handleSilenceVoice();
              }}
              title="Close voice HUD"
            >
              <CloseIcon size={14} />
            </button>
          </div>

          <div className="voice-hud-body">
            {/* Animated Waveform Bars */}
            <div className={`waveform-visualizer ${normalizedStatus}`}>
              <span className="wave-bar bar-1" />
              <span className="wave-bar bar-2" />
              <span className="wave-bar bar-3" />
              <span className="wave-bar bar-4" />
              <span className="wave-bar bar-5" />
            </div>

            <div className="voice-hud-status-line">
              {agentActionStatus ? (
                <span className="action-status-msg">{agentActionStatus.message}</span>
              ) : normalizedStatus === "listening" ? (
                <span>Listening for speech...</span>
              ) : normalizedStatus === "thinking" ? (
                <span>Thinking & planning...</span>
              ) : normalizedStatus === "speaking" ? (
                <span>Speaking response...</span>
              ) : (
                <span>Standing by</span>
              )}
            </div>
          </div>

          {normalizedStatus === "speaking" && (
            <div className="voice-hud-actions">
              <button className="hud-silence-btn" onClick={handleSilenceVoice}>
                <SquareIcon size={12} />
                <span>Silence</span>
              </button>
            </div>
          )}
        </div>
      )}

      {/* ── OPTIONAL OVERLAY MODALS (CLOSED BY DEFAULT) ── */}

      {/* 1. Knowledge Base (RAG) Modal */}
      {activeModal === "rag" && (
        <ModalContainer title="Knowledge Base (RAG)" onClose={() => setActiveModal(null)}>
          <RagModalView
            ragDocs={ragDocs}
            fetchRagDocs={fetchRagDocs}
            onSelectFile={() => fileInputRef.current?.click()}
            ragUploading={ragUploading}
          />
        </ModalContainer>
      )}

      {/* 2. Memory Vault Modal */}
      {activeModal === "memory" && (
        <ModalContainer title="Memory Vault" onClose={() => setActiveModal(null)}>
          <MemoryModalView memories={memories} fetchMemories={fetchMemories} />
        </ModalContainer>
      )}

      {/* 3. System Stats Modal */}
      {activeModal === "stats" && (
        <ModalContainer title="Hardware & System Telemetry" onClose={() => setActiveModal(null)}>
          <StatsModalView stats={systemStats} />
        </ModalContainer>
      )}

      {/* 4. Research Reports Modal */}
      {activeModal === "research" && (
        <ModalContainer title="Completed Research Reports" onClose={() => setActiveModal(null)}>
          <ResearchModalView items={completedResearch} />
        </ModalContainer>
      )}

      {/* 5. Security Confirmation Modal for File Deletion */}
      {pendingDelete && (
        <div className="modal-backdrop-scrim">
          <div className="modal-window-card danger-window">
            <div className="danger-header-tag">
              <AlertTriangleIcon />
              <span>SECURITY CONFIRMATION REQUIRED</span>
            </div>
            <h2 className="modal-window-title">Confirm Permanent Deletion</h2>
            <p className="modal-window-desc">
              JARVIS is requesting permission to delete the following target on your Windows filesystem:
            </p>
            <div className="delete-target-preview">
              <div className="target-name">{pendingDelete.name}</div>
              <div className="target-path">{pendingDelete.path}</div>
            </div>
            <div className="modal-window-actions">
              <button className="modal-action-btn danger-confirm" onClick={() => handleConfirmDelete(true)}>
                Permanently Delete
              </button>
              <button className="modal-action-btn neutral-cancel" onClick={() => handleConfirmDelete(false)}>
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Generic Modal Container ───────────────────────────────────
function ModalContainer({ title, children, onClose }) {
  return (
    <div className="modal-backdrop-scrim" onClick={onClose}>
      <div className="modal-window-card" onClick={e => e.stopPropagation()}>
        <div className="modal-window-header">
          <h2 className="modal-window-title">{title}</h2>
          <button className="modal-close-trigger" onClick={onClose} title="Close">
            <CloseIcon />
          </button>
        </div>
        <div className="modal-window-body">{children}</div>
      </div>
    </div>
  );
}

// ── RAG Modal Content View ────────────────────────────────────
function RagModalView({ ragDocs, fetchRagDocs, onSelectFile, ragUploading }) {
  const [queryText, setQueryText] = useState("");
  const [queryResult, setQueryResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleQuery = (e) => {
    e.preventDefault();
    if (!queryText.trim()) return;
    setLoading(true);
    setQueryResult(null);

    fetch(`${API_BASE}/rag/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: queryText.trim() }),
    })
      .then(r => r.json())
      .then(d => {
        setLoading(false);
        if (d.ok) setQueryResult(d);
      })
      .catch(() => setLoading(false));
  };

  return (
    <div className="modal-content-stack">
      {/* Upload zone */}
      <div className="upload-drop-card" onClick={onSelectFile}>
        <UploadCloudIcon />
        <div className="upload-drop-title">
          {ragUploading ? "Indexing document..." : "Click to select PDF, TXT, MD, or CSV"}
        </div>
        <div className="upload-drop-sub">
          Automatic chunking and indexing into FAISS vector knowledge store
        </div>
      </div>

      {/* Catalog of indexed docs */}
      <div className="stack-section-title">Indexed Documents ({ragDocs.length})</div>
      <div className="documents-scroll-list">
        {ragDocs.length === 0 ? (
          <div className="empty-state-text">No documents indexed yet.</div>
        ) : (
          ragDocs.map((d, i) => (
            <div key={i} className="document-list-entry">
              <FileTextIcon />
              <span className="entry-filename">{d.filename}</span>
              <span className="entry-meta">{d.chunk_count} chunks • {d.pages ?? 1} pgs</span>
            </div>
          ))
        )}
      </div>

      {/* Query document store */}
      <div className="stack-section-title">Query Knowledge Base</div>
      <form className="modal-input-row" onSubmit={handleQuery}>
        <input
          type="text"
          className="modal-text-input"
          placeholder="Ask a question against your indexed documents..."
          value={queryText}
          onChange={e => setQueryText(e.target.value)}
        />
        <button type="submit" className="modal-action-btn primary-btn" disabled={loading}>
          {loading ? "Searching..." : "Query"}
        </button>
      </form>

      {queryResult && (
        <div className="query-response-card">
          <div
            className="query-response-text"
            dangerouslySetInnerHTML={{ __html: renderMarkdown(queryResult.answer) }}
          />
          {queryResult.citations?.length > 0 && (
            <div className="citations-tray">
              {queryResult.citations.map((c, i) => (
                <span key={i} className="citation-tag">
                  <FileTextIcon size={12} />
                  <span>{c.source}{c.page ? ` p.${c.page}` : ""}</span>
                  {c.score != null && ` (${Math.round(c.score * 100)}%)`}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── Memory Modal Content View ─────────────────────────────────
function MemoryModalView({ memories, fetchMemories }) {
  const [newMemory, setNewMemory] = useState("");
  const [filter, setFilter] = useState("");

  const handleAdd = (e) => {
    e.preventDefault();
    if (!newMemory.trim()) return;

    fetch(`${API_BASE}/memory/remember`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content: newMemory.trim(), category: "manual" }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.ok) {
          setNewMemory("");
          fetchMemories();
        }
      })
      .catch(() => {});
  };

  const handleForget = (content) => {
    fetch(`${API_BASE}/memory/forget`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ content }),
    })
      .then(r => r.json())
      .then(d => {
        if (d.ok) fetchMemories();
      })
      .catch(() => {});
  };

  const filtered = memories.filter(m =>
    (m.content || "").toLowerCase().includes(filter.toLowerCase())
  );

  return (
    <div className="modal-content-stack">
      {/* Remember new fact */}
      <form className="modal-input-row" onSubmit={handleAdd}>
        <input
          type="text"
          className="modal-text-input"
          placeholder="Teach JARVIS a new fact, habit, or preference..."
          value={newMemory}
          onChange={e => setNewMemory(e.target.value)}
        />
        <button type="submit" className="modal-action-btn primary-btn">
          Remember
        </button>
      </form>

      {/* Filter */}
      <input
        type="text"
        className="modal-text-input filter-field"
        placeholder="Filter remembered memories..."
        value={filter}
        onChange={e => setFilter(e.target.value)}
      />

      {/* Memory cards */}
      <div className="memory-entries-list">
        {filtered.length === 0 ? (
          <div className="empty-state-text">
            {memories.length === 0 ? "No memories stored in database." : "No matches found."}
          </div>
        ) : (
          filtered.map((m, i) => (
            <div key={i} className="memory-entry-card">
              <div className="memory-entry-text">{m.content}</div>
              <div className="memory-entry-footer">
                <span className="entry-timestamp">
                  {m.created_at ? new Date(m.created_at).toLocaleDateString() : ""}
                </span>
                <button className="entry-forget-trigger" onClick={() => handleForget(m.content)}>
                  Forget
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

// ── Stats Modal Content View ──────────────────────────────────
function StatsModalView({ stats }) {
  if (!stats) return <div className="empty-state-text">Loading hardware metrics...</div>;

  return (
    <div className="stats-cards-grid">
      <div className="stats-card-entry">
        <div className="metric-title">CPU Utilization</div>
        <div className="metric-value">{stats.cpu_percent}%</div>
        <div className="metric-meter-track">
          <div
            className="metric-meter-fill"
            style={{ width: `${stats.cpu_percent}%`, background: stats.cpu_percent > 80 ? "#f43f5e" : "#38bdf8" }}
          />
        </div>
      </div>

      <div className="stats-card-entry">
        <div className="metric-title">System RAM</div>
        <div className="metric-value">{stats.ram_used_gb} / {stats.ram_total_gb} GB ({stats.ram_percent}%)</div>
        <div className="metric-meter-track">
          <div
            className="metric-meter-fill"
            style={{ width: `${stats.ram_percent}%`, background: stats.ram_percent > 80 ? "#f43f5e" : "#10b981" }}
          />
        </div>
      </div>

      <div className="stats-card-entry">
        <div className="metric-title">Storage Drive</div>
        <div className="metric-value">{stats.disk_used_gb} / {stats.disk_total_gb} GB ({stats.disk_percent}%)</div>
        <div className="metric-meter-track">
          <div className="metric-meter-fill" style={{ width: `${stats.disk_percent}%`, background: "#a855f7" }} />
        </div>
      </div>

      {stats.gpu && (
        <div className="stats-card-entry">
          <div className="metric-title">GPU ({stats.gpu.name})</div>
          <div className="metric-value">
            VRAM: {stats.gpu.vram_used_mb} / {stats.gpu.vram_total_mb} MB (
            {Math.round((stats.gpu.vram_used_mb / stats.gpu.vram_total_mb) * 100)}%)
          </div>
          <div className="metric-meter-track">
            <div
              className="metric-meter-fill"
              style={{
                width: `${Math.round((stats.gpu.vram_used_mb / stats.gpu.vram_total_mb) * 100)}%`,
                background: "#f59e0b",
              }}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// ── Research Modal Content View ───────────────────────────────
function ResearchModalView({ items }) {
  const [activeItem, setActiveItem] = useState(null);

  if (items.length === 0) {
    return <div className="empty-state-text">No research reports currently saved.</div>;
  }

  if (activeItem) {
    return (
      <div className="research-article-view">
        <button className="back-nav-trigger" onClick={() => setActiveItem(null)}>
          ← Back to all reports
        </button>
        <h3 className="article-title">{activeItem.topic}</h3>
        <div className="article-date">
          {activeItem.created_at ? new Date(activeItem.created_at).toLocaleString() : ""}
        </div>
        <div
          className="article-body"
          dangerouslySetInnerHTML={{ __html: renderMarkdown(activeItem.report || activeItem.summary) }}
        />
      </div>
    );
  }

  return (
    <div className="research-cards-grid">
      {items.map((it, idx) => (
        <div key={idx} className="research-summary-card" onClick={() => setActiveItem(it)}>
          <div className="summary-topic">{it.topic}</div>
          <div className="summary-date">
            {it.created_at ? new Date(it.created_at).toLocaleDateString() : ""}
          </div>
          <p className="summary-snippet">{it.summary?.slice(0, 160)}...</p>
        </div>
      ))}
    </div>
  );
}