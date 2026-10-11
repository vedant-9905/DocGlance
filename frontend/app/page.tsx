"use client";

import React, { useState, useRef, useEffect } from "react";
import Sidebar from "@/components/Sidebar";
import ChatMessageView from "@/components/ChatMessageView";
import DocumentMapModal from "@/components/DocumentMapModal";
import GeminiSettingsModal from "@/components/GeminiSettingsModal";
import GeminiLogo from "@/components/GeminiLogo";
import { api } from "@/lib/api";
import type { ChatMessage, DocumentProfile } from "@/types";
import {
  Send,
  Loader2,
  Sparkles,
  Layers,
  Trash2,
  BookOpen,
  PieChart,
  HelpCircle,
  Paperclip,
  PanelLeft,
  Settings,
  Mic,
  MicOff,
  BarChart2,
  FileText,
  UploadCloud,
} from "lucide-react";

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputPrompt, setInputPrompt] = useState("");
  const [activeDocument, setActiveDocument] = useState<DocumentProfile | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadStatusText, setUploadStatusText] = useState("");
  const [isMapOpen, setIsMapOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [backendOnline, setBackendOnline] = useState<boolean | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [recentQueries, setRecentQueries] = useState<string[]>([]);
  const [modelMode, setModelMode] = useState<string>("local");

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputHiddenRef = useRef<HTMLInputElement>(null);
  const speechRecognitionRef = useRef<any>(null);

  // Auto-scroll to bottom on new message
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  // Load saved recent queries from localStorage
  useEffect(() => {
    try {
      const saved = localStorage.getItem("gemini_doc_recent_queries");
      if (saved) setRecentQueries(JSON.parse(saved));
      const useLocal = localStorage.getItem("gemini_doc_use_local") === "true";
      const key = localStorage.getItem("gemini_doc_api_key");
      setModelMode(!useLocal && key ? "cloud" : "local");
    } catch {}
  }, []);

  // Initial health check and fetch active document
  useEffect(() => {
    api
      .health()
      .then((h) => {
        setBackendOnline(true);
        if (h.has_gemini_key) setModelMode("cloud");
      })
      .catch(() => setBackendOnline(false));

    api
      .getActiveDocument()
      .then((doc) => {
        if (doc) {
          setActiveDocument(doc);
          setMessages([
            {
              id: "init",
              role: "assistant",
              content: `Hello! I have loaded **${doc.filename}** (${doc.word_count.toLocaleString()} words across ${doc.section_map.length} sections).\n\n**Executive Thesis:**\n> ${doc.executive_summary}\n\nAsk me anything about the document as a whole, or choose one of the quick suggestions below!`,
              timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
              documentName: doc.filename,
              suggestions: [
                `Summarize key takeaways from ${doc.filename}`,
                "Extract all metrics, numbers, and data points",
                "Explain the core methodology and arguments",
              ],
            },
          ]);
        }
      })
      .catch(() => {});
  }, []);

  // Save new query to recent list
  const saveRecentQuery = (query: string) => {
    setRecentQueries((prev) => {
      const updated = [query, ...prev.filter((q) => q !== query)].slice(0, 10);
      try {
        localStorage.setItem("gemini_doc_recent_queries", JSON.stringify(updated));
      } catch {}
      return updated;
    });
  };

  // Handle document upload
  const handleUpload = async (file: File) => {
    setIsUploading(true);
    setUploadStatusText(`Parsing & indexing ${file.name}...`);
    try {
      const doc = await api.upload(file);
      setActiveDocument(doc);
      setMessages([
        {
          id: Date.now().toString(),
          role: "assistant",
          content: `### Document Analyzed & Grounded: ${doc.filename}\n\nI have parsed the complete document (**${doc.word_count.toLocaleString()} words** across **${doc.section_map.length} sections**).\n\n**Executive Macro Summary:**\n> ${doc.executive_summary}\n\n**Key Themes:** ${doc.key_concepts.map((c) => `\`${c}\``).join(" ")}\n\nYou can now ask me to summarize the whole text, analyze specific sections, extract data points, or answer detailed questions!`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          documentName: doc.filename,
          suggestions: [
            `Provide an executive summary of ${doc.filename}`,
            "Extract all numbers, metrics, and data points",
            "What are the main conclusions and takeaways?",
          ],
        },
      ]);
    } catch (err: any) {
      alert(`Upload failed: ${err.message || err}`);
    } finally {
      setIsUploading(false);
      setUploadStatusText("");
    }
  };

  // Handle load sample document
  const handleLoadSample = async () => {
    setIsUploading(true);
    setUploadStatusText("Loading sample JWST document...");
    try {
      const doc = await api.loadSample();
      setActiveDocument(doc);
      setMessages([
        {
          id: Date.now().toString(),
          role: "assistant",
          content: `### Document Analyzed: ${doc.filename}\n\nI have parsed the complete document (**${doc.word_count.toLocaleString()} words**).\n\n**Executive Macro Summary:**\n> ${doc.executive_summary}\n\n**Key Themes:** ${doc.key_concepts.map((c) => `\`${c}\``).join(" ")}\n\nYou can now ask me anything about the telescope's launch, mirrors, orbits, or mission costs!`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          documentName: doc.filename,
          suggestions: [
            "What are the telescope specs and primary mirror details?",
            "What was the total mission cost and launch date?",
            "Summarize the executive takeaways",
          ],
        },
      ]);
    } catch (err: any) {
      alert(`Failed to load sample: ${err.message || err}`);
    } finally {
      setIsUploading(false);
      setUploadStatusText("");
    }
  };

  // Handle clear document
  const handleClearDocument = async () => {
    try {
      await api.clearDocument();
      setActiveDocument(null);
      setMessages([]);
    } catch (err: any) {
      console.error(err);
    }
  };

  // Handle new chat
  const handleNewChat = () => {
    if (activeDocument) {
      setMessages([
        {
          id: Date.now().toString(),
          role: "assistant",
          content: `New chat session started for **${activeDocument.filename}**. What would you like to explore next?`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          documentName: activeDocument.filename,
          suggestions: [
            `Summarize the key points of ${activeDocument.filename}`,
            "Extract quantitative metrics and figures",
            "What are the primary arguments and methodology?",
          ],
        },
      ]);
    } else {
      setMessages([]);
    }
  };

  // Send message
  const handleSendMessage = async (promptOverride?: string) => {
    const textToSend = (promptOverride || inputPrompt).trim();
    if (!textToSend || isLoading) return;

    saveRecentQuery(textToSend);

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: textToSend,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const newHistory = [...messages, userMsg];
    setMessages(newHistory);
    setInputPrompt("");
    setIsLoading(true);

    try {
      const apiMessages = newHistory.map((m) => ({ role: m.role, content: m.content }));
      const savedKey = localStorage.getItem("gemini_doc_api_key") || undefined;
      const useLocal = localStorage.getItem("gemini_doc_use_local") === "true";
      const keyToSend = useLocal ? undefined : savedKey;

      const response = await api.chat(apiMessages, keyToSend);

      const assistantMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.content,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        latencyMs: response.latency_ms,
        documentName: response.document || undefined,
        suggestions: response.suggestions,
        googleContext: response.google_context,
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `**Error generating response:** ${err.message || "Failed to reach backend."}`,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // Voice speech-to-text dictation
  const toggleVoiceInput = () => {
    const windowWithSpeech = window as any;
    const SpeechRecognition =
      windowWithSpeech.SpeechRecognition || windowWithSpeech.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Voice input is not supported in this browser. Try Chrome or Edge!");
      return;
    }

    if (isListening) {
      speechRecognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event: any) => {
      const transcript = event.results[0][0].transcript;
      setInputPrompt((prev) => (prev ? `${prev} ${transcript}` : transcript));
      setIsListening(false);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);

    recognition.start();
    speechRecognitionRef.current = recognition;
    setIsListening(true);
  };

  const starterPrompts = [
    {
      title: "Executive Summary",
      desc: "Provide a comprehensive executive summary of the entire document.",
      icon: <BookOpen className="w-4 h-4 text-[#4285f4]" />,
      prompt: "Provide a comprehensive executive summary of the whole document, outlining its core thesis, objectives, and conclusions.",
    },
    {
      title: "Key Metrics & Data",
      desc: "Extract all numbers, percentages, figures, and data points.",
      icon: <BarChart2 className="w-4 h-4 text-[#34a853]" />,
      prompt: "Extract all key numerical metrics, statistics, costs, and data points from this document into a structured overview.",
    },
    {
      title: "Methodology & Architecture",
      desc: "Analyze the technical framework, workflow, and procedures.",
      icon: <PieChart className="w-4 h-4 text-[#9b72cb]" />,
      prompt: "Explain the proposed methodology, architecture, and workflow described in this document in structured detail.",
    },
    {
      title: "Critique & Limitations",
      desc: "What are the risks, challenges, contradictions, or gaps?",
      icon: <HelpCircle className="w-4 h-4 text-[#fbbc04]" />,
      prompt: "Analyze the potential limitations, risks, contradictions, or missing details in this document.",
    },
  ];

  return (
    <div className="flex h-screen bg-[#131314] text-[#e3e3e3] overflow-hidden font-sans">
      {/* Sidebar */}
      <Sidebar
        document={activeDocument}
        onUpload={handleUpload}
        onClearDocument={handleClearDocument}
        onNewChat={handleNewChat}
        onOpenMap={() => setIsMapOpen(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onSelectPrompt={(p) => handleSendMessage(p)}
        recentQueries={recentQueries}
        isUploading={isUploading}
        uploadStatusText={uploadStatusText}
        isOpen={isSidebarOpen}
        onToggle={() => setIsSidebarOpen(!isSidebarOpen)}
      />

      {/* Main Gemini Chat Area */}
      <div className="flex-1 flex flex-col min-w-0 h-full overflow-hidden bg-[#131314]">
        {/* Top Floating Gemini Header */}
        <header className="h-14 flex-shrink-0 flex items-center justify-between px-4 md:px-6 border-b border-white/5 bg-[#131314]/90 backdrop-blur-md z-10">
          <div className="flex items-center gap-3">
            {!isSidebarOpen && (
              <button
                onClick={() => setIsSidebarOpen(true)}
                className="p-2 rounded-lg text-white/50 hover:text-white hover:bg-white/5 transition-colors"
                title="Open sidebar"
              >
                <PanelLeft className="w-4 h-4" />
              </button>
            )}

            <div className="flex items-center gap-2">
              <GeminiLogo size={20} />
              <span className="font-semibold text-white text-sm tracking-tight hidden sm:inline">
                Gemini
              </span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 font-medium">
                Doc
              </span>
            </div>

            {/* Active Document Pill */}
            {activeDocument ? (
              <button
                onClick={() => setIsMapOpen(true)}
                className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#1e1f20] hover:bg-[#282a2c] border border-white/10 text-xs text-white transition-colors truncate max-w-xs sm:max-w-md"
                title="Click to view Document Profile & Map"
              >
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                <span className="truncate">{activeDocument.filename}</span>
                <span className="text-[10px] text-white/40 hidden md:inline">
                  • {activeDocument.word_count.toLocaleString()} words
                </span>
              </button>
            ) : (
              <span className="text-xs text-white/40 hidden md:inline">
                No document attached
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            {/* Model Badge */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-[#1e1f20] hover:bg-[#282a2c] text-xs text-white/70 hover:text-white border border-white/5 transition-colors"
            >
              <Sparkles className="w-3 h-3 text-[#4285f4]" />
              <span className="hidden sm:inline">
                {modelMode === "cloud" ? "Gemini Cloud" : "Local Neural Core"}
              </span>
            </button>

            {/* Settings Trigger */}
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="p-2 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors"
              title="Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </header>

        {/* Chat Feed */}
        <div className="flex-1 overflow-y-auto px-4 md:px-12 py-6 space-y-4">
          {messages.length === 0 ? (
            /* Gemini Welcome Hero & Starter Cards */
            <div className="max-w-3xl mx-auto py-8 md:py-14 px-4 space-y-8 animate-fade-in">
              <div className="space-y-3">
                <div className="flex items-center gap-2 mb-2">
                  <GeminiLogo size={32} className="gemini-sparkle-anim" />
                </div>
                <h2 className="text-3xl md:text-4xl font-semibold tracking-tight text-white leading-tight">
                  <span className="gemini-gradient-text">Hello,</span>
                  <br />
                  <span>what do you want to explore?</span>
                </h2>
                <p className="text-sm text-[#c4c7c5] max-w-xl leading-relaxed">
                  Ask detailed questions, generate executive summaries, extract numbers, or explore related Google context — strictly grounded in your document.
                </p>
              </div>

              {/* Upload Card or Starter Prompts */}
              {activeDocument ? (
                <div className="space-y-4">
                  <div className="flex items-center justify-between">
                    <span className="text-xs uppercase tracking-wider font-semibold text-white/50">
                      Suggested prompts for {activeDocument.filename}
                    </span>
                    <button
                      onClick={() => setIsMapOpen(true)}
                      className="text-xs text-[#4285f4] hover:underline flex items-center gap-1"
                    >
                      <Layers className="w-3 h-3" /> Inspect Document Map
                    </button>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {starterPrompts.map((card, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSendMessage(card.prompt)}
                        className="text-left p-4 rounded-2xl bg-[#1e1f20] hover:bg-[#282a2c] border border-white/5 hover:border-white/10 transition-all duration-200 group flex flex-col justify-between"
                      >
                        <div className="flex items-center gap-2 mb-1.5">
                          {card.icon}
                          <span className="font-semibold text-xs text-white group-hover:text-blue-300 transition-colors">
                            {card.title}
                          </span>
                        </div>
                        <p className="text-[11px] text-white/50 leading-relaxed">
                          {card.desc}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>
              ) : (
                /* Document Upload Hero Card */
                <div className="space-y-4">
                  <div
                    onClick={() => fileInputHiddenRef.current?.click()}
                    className="p-8 rounded-3xl border-2 border-dashed border-white/10 hover:border-[#4285f4]/60 bg-[#1e1f20]/60 hover:bg-[#1e1f20] transition-all cursor-pointer text-center space-y-3 group shadow-xl"
                  >
                    <div className="w-14 h-14 rounded-2xl bg-blue-500/10 group-hover:bg-blue-500/20 text-[#4285f4] flex items-center justify-center mx-auto transition-transform group-hover:scale-105">
                      <UploadCloud className="w-7 h-7" />
                    </div>
                    <div>
                      <h3 className="text-base font-semibold text-white">
                        Upload a document to start chatting
                      </h3>
                      <p className="text-xs text-white/50 max-w-md mx-auto mt-1">
                        Drag and drop or browse from your computer. Supports PDF, Word (.docx), Excel (.xlsx), PowerPoint (.pptx), CSV, Markdown, and Text.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-center gap-3 pt-2">
                    <button
                      onClick={handleLoadSample}
                      className="px-4 py-2 rounded-full bg-[#1e1f20] hover:bg-[#282a2c] border border-white/10 text-xs font-medium text-white/80 hover:text-white transition-all flex items-center gap-2"
                    >
                      <Sparkles className="w-3.5 h-3.5 text-[#4285f4]" />
                      <span>Or load sample JWST document</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : (
            <div className="max-w-3xl mx-auto space-y-3">
              {messages.map((msg) => (
                <ChatMessageView
                  key={msg.id}
                  message={msg}
                  onSelectSuggestion={(s) => handleSendMessage(s)}
                />
              ))}

              {/* Gemini Thinking Animation */}
              {isLoading && (
                <div className="flex gap-4 px-4 py-3 bg-transparent rounded-2xl animate-fade-in">
                  <div className="w-8 h-8 rounded-full flex items-center justify-center bg-[#1e1f20] border border-white/10">
                    <GeminiLogo size={18} className="animate-spin" />
                  </div>
                  <div className="flex items-center gap-2.5 text-xs text-[#c4c7c5]">
                    <span className="gemini-gradient-text font-medium">
                      Gemini is analyzing document...
                    </span>
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Gemini Bottom Floating Input Dock */}
        <div className="p-4 md:p-6 bg-gradient-to-t from-[#131314] via-[#131314]/95 to-transparent flex-shrink-0">
          <div className="max-w-3xl mx-auto space-y-2">
            {/* Floating Pill Input Bar */}
            <div className="relative rounded-3xl bg-[#1e1f20] border border-white/10 shadow-2xl focus-within:border-white/20 transition-all flex items-end p-2 px-3">
              {/* Hidden file input */}
              <input
                ref={fileInputHiddenRef}
                type="file"
                className="hidden"
                accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.tsv,.pptx,.ppt,.html,.htm,.txt,.md,.json,.yaml,.xml"
                onChange={(e) => {
                  const f = e.target.files?.[0];
                  if (f) handleUpload(f);
                }}
              />

              {/* Attachment Button */}
              <button
                type="button"
                onClick={() => fileInputHiddenRef.current?.click()}
                className="p-2 text-white/40 hover:text-white hover:bg-white/5 rounded-full transition-colors flex-shrink-0 mb-0.5"
                title="Attach document"
              >
                <Paperclip className="w-4 h-4" />
              </button>

              {/* Active Doc Tag inside prompt bar */}
              {activeDocument && (
                <div className="hidden sm:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-white/5 border border-white/5 text-[11px] text-white/70 mr-1.5 mb-1 flex-shrink-0 max-w-xs truncate">
                  <FileText className="w-3 h-3 text-[#4285f4]" />
                  <span className="truncate">{activeDocument.filename}</span>
                </div>
              )}

              {/* Auto-expanding prompt textarea */}
              <textarea
                ref={textareaRef}
                value={inputPrompt}
                onChange={(e) => setInputPrompt(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder={
                  activeDocument
                    ? `Ask Gemini anything about ${activeDocument.filename}...`
                    : "Upload a document to analyze, or ask a question..."
                }
                rows={1}
                className="flex-1 bg-transparent border-0 text-sm text-[#e3e3e3] placeholder-white/30 resize-none focus:outline-none px-2 py-2 max-h-36 overflow-y-auto leading-relaxed"
                style={{ minHeight: "28px" }}
              />

              {/* Microphone voice dictation */}
              <button
                type="button"
                onClick={toggleVoiceInput}
                className={`p-2 rounded-full transition-colors flex-shrink-0 mb-0.5 ${
                  isListening
                    ? "text-red-400 bg-red-500/10 animate-pulse"
                    : "text-white/40 hover:text-white hover:bg-white/5"
                }`}
                title={isListening ? "Stop listening" : "Voice dictation"}
              >
                {isListening ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
              </button>

              {/* Send Button */}
              <button
                type="button"
                disabled={!inputPrompt.trim() || isLoading}
                onClick={() => handleSendMessage()}
                className={`p-2 rounded-full transition-all flex-shrink-0 mb-0.5 ${
                  inputPrompt.trim() && !isLoading
                    ? "bg-[#4285f4] text-white shadow-md shadow-blue-500/20 hover:bg-[#3367d6]"
                    : "bg-white/5 text-white/20 cursor-not-allowed"
                }`}
                title="Send query"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>

            {/* Bottom Disclaimer */}
            <div className="flex items-center justify-between text-[11px] text-white/30 px-3">
              <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for newline</span>
              <span>Gemini Doc answers are grounded strictly in the provided document.</span>
            </div>
          </div>
        </div>
      </div>

      {/* Whole-Document Profile & Map Modal */}
      <DocumentMapModal
        document={activeDocument}
        isOpen={isMapOpen}
        onClose={() => setIsMapOpen(false)}
      />

      {/* Gemini AI & Settings Modal */}
      <GeminiSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        onConfigChanged={() => {
          const useLocal = localStorage.getItem("gemini_doc_use_local") === "true";
          const key = localStorage.getItem("gemini_doc_api_key");
          setModelMode(!useLocal && key ? "cloud" : "local");
        }}
      />
    </div>
  );
}
