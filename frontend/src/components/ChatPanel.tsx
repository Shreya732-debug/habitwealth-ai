import React, { useState, useRef, useEffect, useCallback } from "react";
import { Send, Bot, User, Paperclip, Trash2 } from "lucide-react";
import API from "../api";

interface Message {
  role: "user" | "assistant";
  content: string;
  toolUsed?: string | null;
}

interface Props {
  onAnswered?: () => void;
}

export default function ChatPanel({ onAnswered }: Props) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content:
        'Hi! I\'m FinanceGPT. Ask me anything about your budget — "Can I afford dinner tonight?" or "How am I doing this month?"',
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [showDocs, setShowDocs] = useState(false);
  const [docs, setDocs] = useState<
    Array<{ filename: string; type: string } | string>
  >([]);
  const [uploading, setUploading] = useState(false);
  const [uploadMsg, setUploadMsg] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    loadDocs();
  }, []);

  const sendMessage = useCallback(
    async (questionOverride?: string) => {
      const question = (questionOverride ?? input).trim();
      if (!question || loading) return;

      // Clear input immediately
      setInput("");

      // Add user message to chat
      setMessages((prev) => [...prev, { role: "user", content: question }]);
      setLoading(true);

      try {
        const res = await API.post("/agent/ask", { question });
        const answer = res.data?.answer ?? "No response received.";
        const toolUsed = res.data?.tool_used ?? null;

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: answer,
            toolUsed,
          },
        ]);

        // Refresh dashboard data after agent answers
        // Small delay before refreshing so chat response renders first
        setTimeout(() => onAnswered?.(), 500);
      } catch (err: any) {
        const errMsg =
          err.response?.data?.detail ??
          err.message ??
          "Something went wrong. Please try again.";

        setMessages((prev) => [
          ...prev,
          {
            role: "assistant",
            content: `Error: ${errMsg}`,
          },
        ]);
      } finally {
        setLoading(false);
        // Refocus input after response
        setTimeout(() => inputRef.current?.focus(), 100);
      }
    },
    [input, loading, onAnswered],
  );

  // Handle Enter key — preventDefault stops any form submission
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault(); // ← this is critical
      e.stopPropagation(); // ← belt and suspenders
      sendMessage();
    }
  };

  // Handle button click — also preventDefault just in case
  const handleButtonClick = (e: React.MouseEvent<HTMLButtonElement>) => {
    e.preventDefault();
    e.stopPropagation();
    sendMessage();
  };

  const handleQuickQuestion = (
    e: React.MouseEvent<HTMLButtonElement>,
    q: string,
  ) => {
    e.preventDefault();
    e.stopPropagation();
    sendMessage(q);
  };

  const QUICK_QUESTIONS = [
    "How am I doing this month?",
    "How much can I spend today?",
    "Will I meet my savings goal?",
  ];

  const loadDocs = async () => {
    try {
      const res = await API.get("/rag/documents");
      // API returns array of {filename, type} objects
      setDocs(res.data.documents || []);
    } catch {
      setDocs([]);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setUploadMsg("Uploading and indexing...");

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await API.post("/rag/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setUploadMsg(
        `✅ ${res.data.stats.filename} indexed (${res.data.stats.chunks} chunks)`,
      );
      loadDocs();
    } catch (err: any) {
      setUploadMsg(`❌ ${err.response?.data?.detail ?? "Upload failed"}`);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const handleDeleteDoc = async (filename: string) => {
    try {
      // Encode filename in URL path — no body needed
      await API.delete(`/rag/document/${encodeURIComponent(filename)}`);
      setUploadMsg("");
      // Remove from local state immediately — no need to wait for reload
      setDocs((prev) =>
        prev.filter((d) => {
          const name = typeof d === "object" ? d.filename : d;
          return name !== filename;
        }),
      );
      // Then reload from server to confirm
      loadDocs();
    } catch (err: any) {
      console.error("Delete failed:", err.response?.data ?? err.message);
    }
  };

  return (
    // IMPORTANT: No <form> tag anywhere — just a plain div
    <div className="bg-white border border-cardBorder rounded-xl flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-cardBorder flex-shrink-0">
        <Bot size={16} className="text-coral" />
        <span className="text-sm font-medium">FinanceGPT</span>
        <div className="ml-auto flex items-center gap-1.5">
          <span className="w-2 h-2 bg-sage rounded-full" />
          <span className="text-xs text-sage">Online</span>
        </div>
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4 min-h-0">
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-2 ${msg.role === "user" ? "flex-row-reverse" : "flex-row"}`}
          >
            {/* Avatar */}
            <div
              className={`w-6 h-6 rounded-full flex items-center justify-center flex-shrink-0 mt-0.5 ${
                msg.role === "user"
                  ? "bg-coral"
                  : "bg-cream border border-cardBorder"
              }`}
            >
              {msg.role === "user" ? (
                <User size={11} className="text-white" />
              ) : (
                <Bot size={11} className="text-coral" />
              )}
            </div>

            {/* Bubble */}
            <div
              className={`max-w-[82%] rounded-xl px-3 py-2 text-xs leading-relaxed ${
                msg.role === "user"
                  ? "bg-coral text-white rounded-tr-none"
                  : "bg-cream text-gray-800 rounded-tl-none border border-cardBorder"
              }`}
            >
              <p className="whitespace-pre-wrap break-words">{msg.content}</p>
              {msg.toolUsed && (
                <p className="text-xs opacity-50 mt-1.5 font-mono">
                  🔧 {msg.toolUsed}
                </p>
              )}
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {loading && (
          <div className="flex gap-2 flex-row">
            <div className="w-6 h-6 rounded-full bg-cream border border-cardBorder flex items-center justify-center flex-shrink-0 mt-0.5">
              <Bot size={11} className="text-coral" />
            </div>
            <div className="bg-cream border border-cardBorder rounded-xl rounded-tl-none px-3 py-2.5">
              <div className="flex items-center gap-1">
                {[0, 150, 300].map((delay) => (
                  <span
                    key={delay}
                    className="w-1.5 h-1.5 bg-coral rounded-full animate-bounce"
                    style={{ animationDelay: `${delay}ms` }}
                  />
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Auto-scroll anchor */}
        <div ref={bottomRef} />
      </div>

      {/* Quick question chips — only shown at start */}
      {messages.length <= 2 && !loading && (
        <div className="px-4 pb-2 flex flex-wrap gap-1.5 flex-shrink-0">
          {QUICK_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={(e) => handleQuickQuestion(e, q)}
              className="text-xs bg-cream border border-cardBorder rounded-full px-3 py-1
                         text-muted hover:text-coral hover:border-coral transition-all"
            >
              {q}
            </button>
          ))}
        </div>
      )}
      {/* Document knowledge base panel */}
      <div className="border-t border-cardBorder flex-shrink-0">
        {/* Toggle header */}
        <button
          type="button"
          onClick={() => {
            setShowDocs((d) => !d);
            if (!showDocs) loadDocs();
          }}
          className="w-full flex items-center justify-between px-4 py-2.5
               text-xs text-muted hover:text-coral hover:bg-cream transition-all"
        >
          <div className="flex items-center gap-2">
            <Paperclip size={13} />
            <span>Document knowledge base</span>
            {docs.length > 0 && (
              <span className="bg-coral text-white rounded-full px-1.5 py-0.5 text-xs leading-none">
                {docs.length}
              </span>
            )}
          </div>
          <span className="text-muted">{showDocs ? "▲" : "▼"}</span>
        </button>

        {/* Expanded panel */}
        {showDocs && (
          <div className="px-4 pb-4 space-y-3">
            {/* Upload area — always visible, allows multiple uploads */}
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.doc,.pptx,.ppt,.xlsx,.xls,.csv,.png,.jpg,.jpeg,.webp,.bmp,.tiff,.tif,.txt"
                onChange={handleUpload}
                className="hidden"
                id="doc-upload"
              />
              <label
                htmlFor="doc-upload"
                className={`flex flex-col gap-1 cursor-pointer border border-dashed
                      border-cardBorder rounded-lg px-3 py-3 transition-all
                      hover:border-coral hover:bg-cream/50
                      ${uploading ? "opacity-60 pointer-events-none" : ""}`}
              >
                <div className="flex items-center gap-2 text-xs font-medium text-gray-700">
                  <Paperclip size={13} className="text-coral flex-shrink-0" />
                  {uploading
                    ? "Indexing — please wait..."
                    : "Upload another document"}
                </div>
                <span className="text-xs text-muted leading-relaxed">
                  PDF · Word · Excel · PowerPoint · CSV · Images · TXT
                </span>
              </label>

              {/* Upload status message */}
              {uploadMsg && (
                <div
                  className={`mt-2 text-xs px-3 py-2 rounded-lg border ${
                    uploadMsg.startsWith("✅")
                      ? "bg-green-50 text-green-700 border-green-200"
                      : "bg-red-50 text-red-600 border-red-200"
                  }`}
                >
                  {uploadMsg}
                </div>
              )}
            </div>

            {/* Document list */}
            {docs.length === 0 ? (
              <p className="text-xs text-muted px-1">
                No documents yet. Upload any file above to let FinanceGPT answer
                questions from its content.
              </p>
            ) : (
              <div className="space-y-1.5">
                <p className="text-xs text-muted font-medium px-1">
                  {docs.length} document{docs.length > 1 ? "s" : ""} in
                  knowledge base
                </p>

                {docs.map((doc, idx) => {
                  // doc is now {filename, type} — extract safely
                  const filename =
                    typeof doc === "object" ? doc.filename : String(doc);
                  const filetype = typeof doc === "object" ? doc.type : "";

                  // Color-code by file type
                  const typeColor: Record<string, string> = {
                    PDF: "text-red-500  bg-red-50  border-red-200",
                    DOCX: "text-blue-500 bg-blue-50 border-blue-200",
                    DOC: "text-blue-500 bg-blue-50 border-blue-200",
                    XLSX: "text-green-600 bg-green-50 border-green-200",
                    XLS: "text-green-600 bg-green-50 border-green-200",
                    CSV: "text-green-600 bg-green-50 border-green-200",
                    PPTX: "text-orange-500 bg-orange-50 border-orange-200",
                    PPT: "text-orange-500 bg-orange-50 border-orange-200",
                    PNG: "text-purple-500 bg-purple-50 border-purple-200",
                    JPG: "text-purple-500 bg-purple-50 border-purple-200",
                    JPEG: "text-purple-500 bg-purple-50 border-purple-200",
                    TXT: "text-gray-500  bg-gray-50  border-gray-200",
                  };

                  const badgeClass =
                    typeColor[filetype] ||
                    "text-gray-500 bg-gray-50 border-gray-200";

                  return (
                    <div
                      key={idx}
                      className="flex items-center gap-2 bg-cream border border-cardBorder
                           rounded-lg px-3 py-2 group"
                    >
                      {/* File type badge */}
                      <span
                        className={`text-xs font-medium px-1.5 py-0.5 rounded border
                                  flex-shrink-0 ${badgeClass}`}
                      >
                        {filetype || "FILE"}
                      </span>

                      {/* Filename */}
                      <span
                        className="text-xs text-gray-700 flex-1 truncate min-w-0"
                        title={filename}
                      >
                        {filename}
                      </span>

                      {/* Ask about this file button */}
                      <button
                        type="button"
                        onClick={() => {
                          sendMessage(
                            `What information is in the document "${filename}"?`,
                          );
                          setShowDocs(false);
                        }}
                        className="text-xs text-teal hover:text-teal/70 flex-shrink-0
                             opacity-0 group-hover:opacity-100 transition-all
                             whitespace-nowrap"
                        title="Ask FinanceGPT about this file"
                      >
                        Ask ↗
                      </button>

                      {/* Delete button */}
                      <button
                        type="button"
                        onClick={() => handleDeleteDoc(filename)}
                        className="text-muted hover:text-red-500 transition-colors
                             flex-shrink-0 opacity-0 group-hover:opacity-100"
                        title={`Remove ${filename}`}
                      >
                        <Trash2 size={12} />
                      </button>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        )}
      </div>
      {/* Input row — NO form tag */}
      <div className="p-3 border-t border-cardBorder flex-shrink-0">
        <div className="flex gap-2 items-center">
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about your finances..."
            disabled={loading}
            autoComplete="off"
            className="flex-1 bg-cream border border-cardBorder rounded-lg px-3 py-2.5
                       text-xs text-gray-800 placeholder-muted
                       focus:outline-none focus:border-coral transition-colors
                       disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <button
            type="button"
            onClick={handleButtonClick}
            disabled={loading || !input.trim()}
            className="bg-coral hover:bg-coral/90 disabled:bg-gray-200 disabled:cursor-not-allowed
                       text-white rounded-lg p-2.5 transition-all flex-shrink-0"
          >
            <Send size={13} />
          </button>
        </div>
        <p className="text-xs text-muted mt-1.5 text-center">
          Press Enter or click send
        </p>
      </div>
    </div>
  );
}
