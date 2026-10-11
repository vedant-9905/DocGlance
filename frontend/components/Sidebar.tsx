"use client";

import React, { useRef, useState } from "react";
import type { DocumentProfile } from "@/types";
import {
  Upload,
  Plus,
  FileText,
  FileSpreadsheet,
  Layers,
  Sparkles,
  Trash2,
  Presentation,
  FileCode,
  ShieldCheck,
  Settings,
  MessageSquare,
  BookOpen,
  PanelLeftClose,
} from "lucide-react";
import GeminiLogo from "./GeminiLogo";

interface SidebarProps {
  document: DocumentProfile | null;
  onUpload: (file: File) => Promise<void>;
  onClearDocument: () => Promise<void>;
  onNewChat: () => void;
  onOpenMap: () => void;
  onOpenSettings: () => void;
  onSelectPrompt: (prompt: string) => void;
  recentQueries: string[];
  isUploading: boolean;
  uploadStatusText: string;
  isOpen: boolean;
  onToggle: () => void;
}

export default function Sidebar({
  document,
  onUpload,
  onClearDocument,
  onNewChat,
  onOpenMap,
  onOpenSettings,
  onSelectPrompt,
  recentQueries,
  isUploading,
  uploadStatusText,
  isOpen,
  onToggle,
}: SidebarProps) {
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const file = e.dataTransfer.files[0];
    if (file) {
      await onUpload(file);
    }
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      await onUpload(file);
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const getFileIcon = (fileType: string) => {
    const lower = fileType.toLowerCase();
    if (lower.includes("excel") || lower.includes("sheet") || lower.includes("csv")) {
      return <FileSpreadsheet className="w-4 h-4 text-emerald-400" />;
    }
    if (lower.includes("presentation") || lower.includes("powerpoint")) {
      return <Presentation className="w-4 h-4 text-amber-400" />;
    }
    if (lower.includes("code") || lower.includes("html") || lower.includes("json")) {
      return <FileCode className="w-4 h-4 text-blue-400" />;
    }
    return <FileText className="w-4 h-4 text-[#4285f4]" />;
  };

  if (!isOpen) return null;

  return (
    <aside className="w-72 md:w-80 flex-shrink-0 bg-[#1e1f20] border-r border-white/5 flex flex-col h-full overflow-hidden z-30 transition-all duration-300">
      {/* Top Header */}
      <div className="p-4 border-b border-white/5 flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <GeminiLogo size={24} />
          <div>
            <h1 className="font-semibold text-white tracking-tight text-base leading-none flex items-center gap-1.5">
              <span>Gemini</span>
              <span className="text-xs px-1.5 py-0.5 rounded bg-blue-500/15 text-blue-400 font-medium">
                Doc
              </span>
            </h1>
            <span className="text-[10px] text-white/40 block mt-0.5">
              Document Intelligence
            </span>
          </div>
        </div>

        <button
          onClick={onToggle}
          className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/5 transition-colors"
          title="Collapse sidebar"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* New Chat Button */}
      <div className="p-3">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-4 py-3 rounded-full bg-[#282a2c] hover:bg-[#333538] text-white/90 hover:text-white text-xs font-semibold transition-all border border-white/5 shadow-sm"
        >
          <Plus className="w-4 h-4 text-[#4285f4]" />
          <span>New chat</span>
        </button>
      </div>

      {/* Main Scrollable Content */}
      <div className="flex-1 overflow-y-auto px-3 space-y-4 py-2">
        {/* Active Document Card */}
        {document ? (
          <div className="rounded-2xl bg-[#131314] border border-white/10 p-3.5 space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <div className="p-2 rounded-xl bg-white/5 flex-shrink-0">
                  {getFileIcon(document.file_type)}
                </div>
                <div className="min-w-0">
                  <h3 className="text-xs font-semibold text-white truncate" title={document.filename}>
                    {document.filename}
                  </h3>
                  <span className="text-[10px] text-white/40">
                    {document.file_type}
                  </span>
                </div>
              </div>

              <button
                onClick={onClearDocument}
                className="p-1.5 text-white/30 hover:text-red-400 rounded-lg hover:bg-white/5 transition-colors"
                title="Unload document"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>

            {/* Document Metrics */}
            <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/5 text-[11px]">
              <div className="bg-white/[0.02] p-2 rounded-lg">
                <span className="text-white/40 block text-[10px]">Words</span>
                <span className="font-semibold text-white">
                  {document.word_count.toLocaleString()}
                </span>
              </div>
              <div className="bg-white/[0.02] p-2 rounded-lg">
                <span className="text-white/40 block text-[10px]">Read Time</span>
                <span className="font-semibold text-blue-400">
                  ~{document.estimated_read_time_mins} min
                </span>
              </div>
            </div>

            {/* Outline & Map button */}
            <button
              onClick={onOpenMap}
              className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-blue-500/10 hover:bg-blue-500/20 text-blue-300 text-xs font-medium transition-colors border border-blue-500/20"
            >
              <Layers className="w-3.5 h-3.5" />
              <span>Inspect Document Profile & Map</span>
            </button>

            {/* Key Concepts Tags */}
            {document.key_concepts.length > 0 && (
              <div className="space-y-1.5 pt-1">
                <span className="text-[10px] uppercase tracking-wider font-semibold text-white/40 block">
                  Key Document Themes
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {document.key_concepts.slice(0, 6).map((concept, idx) => (
                    <button
                      key={idx}
                      onClick={() => onSelectPrompt(`What does this document explain about ${concept}?`)}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-white/5 hover:bg-white/10 text-white/70 hover:text-white transition-colors border border-white/5"
                    >
                      {concept}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        ) : (
          /* Dropzone when no doc loaded */
          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDragOver(true);
            }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`p-4 rounded-2xl border-2 border-dashed transition-all cursor-pointer text-center space-y-2 ${
              dragOver
                ? "border-[#4285f4] bg-blue-500/10"
                : "border-white/10 hover:border-white/20 bg-[#131314]"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              className="hidden"
              accept=".pdf,.docx,.doc,.xlsx,.xls,.csv,.tsv,.pptx,.ppt,.html,.htm,.txt,.md,.json,.yaml,.xml"
              onChange={handleFileChange}
            />
            <div className="w-10 h-10 rounded-full bg-white/5 mx-auto flex items-center justify-center text-[#4285f4]">
              <Upload className="w-5 h-5" />
            </div>
            <div>
              <p className="text-xs font-semibold text-white">Upload Document</p>
              <p className="text-[10px] text-white/40 mt-0.5">
                PDF, Word, Excel, PPTX, CSV, TXT
              </p>
            </div>
          </div>
        )}

        {/* Upload status indicator */}
        {isUploading && (
          <div className="p-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-xs text-blue-300 flex items-center gap-2">
            <Sparkles className="w-4 h-4 animate-spin text-[#4285f4]" />
            <span>{uploadStatusText || "Processing document..."}</span>
          </div>
        )}

        {/* Recent Queries / Chat History */}
        {recentQueries.length > 0 && (
          <div className="space-y-1.5 pt-2">
            <span className="text-[10px] uppercase tracking-wider font-semibold text-white/40 px-2 block">
              Recent Queries
            </span>
            <div className="space-y-1">
              {recentQueries.slice(0, 5).map((q, qIdx) => (
                <button
                  key={qIdx}
                  onClick={() => onSelectPrompt(q)}
                  className="w-full text-left px-2.5 py-1.5 rounded-lg hover:bg-white/5 text-xs text-white/70 hover:text-white transition-colors truncate flex items-center gap-2"
                >
                  <MessageSquare className="w-3 h-3 text-white/30 flex-shrink-0" />
                  <span className="truncate">{q}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/5 bg-[#18191a] space-y-2">
        <button
          onClick={onOpenSettings}
          className="w-full flex items-center justify-between px-3 py-2 rounded-xl hover:bg-white/5 text-xs text-white/70 hover:text-white transition-colors"
        >
          <div className="flex items-center gap-2">
            <Settings className="w-3.5 h-3.5 text-white/50" />
            <span>Gemini & AI Settings</span>
          </div>
          <span className="text-[10px] text-blue-400 font-medium">Config</span>
        </button>

        <div className="flex items-center gap-1.5 text-[10px] text-white/40 px-1">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span>Grounded strictly to active document</span>
        </div>
      </div>
    </aside>
  );
}
