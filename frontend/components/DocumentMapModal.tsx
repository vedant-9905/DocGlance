"use client";

import React from "react";
import type { DocumentProfile } from "@/types";
import { X, Layers, Sparkles, BookOpen, Clock, FileText, CheckCircle2 } from "lucide-react";
import GeminiLogo from "./GeminiLogo";

interface DocumentMapModalProps {
  document: DocumentProfile | null;
  isOpen: boolean;
  onClose: () => void;
}

export default function DocumentMapModal({
  document,
  isOpen,
  onClose,
}: DocumentMapModalProps) {
  if (!isOpen || !document) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fade-in">
      <div className="bg-[#1e1f20] border border-white/10 rounded-2xl w-full max-w-3xl max-h-[85vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-[#18191a]">
          <div className="flex items-center gap-3">
            <GeminiLogo size={24} />
            <div>
              <h2 className="font-semibold text-white text-base leading-tight">
                Document Profile & Structural Map
              </h2>
              <p className="text-xs text-white/50 truncate max-w-md">
                {document.filename} · {document.file_type}
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-white/40 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Key Metrics Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <div className="p-3.5 rounded-xl bg-[#131314] border border-white/5">
              <span className="text-[11px] font-medium text-white/40 uppercase tracking-wider block">
                Total Words
              </span>
              <span className="text-xl font-bold text-white mt-1 block">
                {document.word_count.toLocaleString()}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#131314] border border-white/5">
              <span className="text-[11px] font-medium text-white/40 uppercase tracking-wider block">
                Reading Time
              </span>
              <span className="text-xl font-bold text-[#4285f4] mt-1 block">
                ~{document.estimated_read_time_mins} min
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#131314] border border-white/5">
              <span className="text-[11px] font-medium text-white/40 uppercase tracking-wider block">
                Sections / Pages
              </span>
              <span className="text-xl font-bold text-[#9b72cb] mt-1 block">
                {document.section_map.length}
              </span>
            </div>
            <div className="p-3.5 rounded-xl bg-[#131314] border border-white/5">
              <span className="text-[11px] font-medium text-white/40 uppercase tracking-wider block">
                Grounding Status
              </span>
              <span className="text-sm font-semibold text-emerald-400 mt-1.5 flex items-center gap-1.5">
                <CheckCircle2 className="w-3.5 h-3.5" /> 100% Grounded
              </span>
            </div>
          </div>

          {/* Key Concepts Cloud */}
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <Sparkles className="w-4 h-4 text-[#4285f4]" />
              <h3 className="text-sm font-semibold text-white">Extracted Topical Concepts</h3>
            </div>
            <div className="flex flex-wrap gap-2">
              {document.key_concepts.map((concept, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-lg text-xs font-medium bg-blue-500/10 text-blue-300 border border-blue-500/20"
                >
                  {concept}
                </span>
              ))}
            </div>
          </div>

          {/* Executive Summary Spine */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="w-4 h-4 text-emerald-400" />
              <h3 className="text-sm font-semibold text-white">Executive Macro Spine</h3>
            </div>
            <div className="p-4 rounded-xl bg-[#131314] border border-white/5 text-xs text-[#c4c7c5] leading-relaxed">
              <p>{document.executive_summary}</p>
            </div>
          </div>

          {/* Structural Section Map */}
          <div>
            <div className="flex items-center gap-2 mb-2.5">
              <Layers className="w-4 h-4 text-[#9b72cb]" />
              <h3 className="text-sm font-semibold text-white">
                Structural Section Breakdown ({document.section_map.length})
              </h3>
            </div>
            <div className="space-y-2">
              {document.section_map.map((sec, idx) => (
                <div
                  key={idx}
                  className="p-3.5 rounded-xl bg-[#131314] border border-white/5 hover:border-white/10 transition-colors"
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <span className="text-xs font-semibold text-white">
                      {idx + 1}. {sec.title}
                    </span>
                    <span className="text-[10px] text-white/40 bg-white/5 px-2 py-0.5 rounded-full">
                      {sec.word_count} words
                    </span>
                  </div>
                  <p className="text-xs text-[#c4c7c5] line-clamp-2 leading-relaxed">
                    {sec.preview}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-white/10 bg-[#18191a] flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-xl bg-[#4285f4] hover:bg-[#3367d6] text-white text-xs font-semibold transition-colors"
          >
            Close Document Profile
          </button>
        </div>
      </div>
    </div>
  );
}
