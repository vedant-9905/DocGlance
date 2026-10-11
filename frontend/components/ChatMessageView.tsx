"use client";

import React, { useState } from "react";
import type { ChatMessage } from "@/types";
import {
  Copy,
  Check,
  Clock,
  FileText,
  Volume2,
  VolumeX,
  ThumbsUp,
  ThumbsDown,
  ExternalLink,
  Sparkles,
  Search,
  Globe,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import GeminiLogo from "./GeminiLogo";

interface ChatMessageViewProps {
  message: ChatMessage;
  onSelectSuggestion?: (prompt: string) => void;
}

export default function ChatMessageView({
  message,
  onSelectSuggestion,
}: ChatMessageViewProps) {
  const [copied, setCopied] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [liked, setLiked] = useState<boolean | null>(null);
  const [showGoogleDetails, setShowGoogleDetails] = useState(false);

  const isAssistant = message.role === "assistant";

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleReadAloud = () => {
    if (!window.speechSynthesis) return;

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    window.speechSynthesis.cancel();
    // Clean markdown symbols for natural speech
    const cleanSpeech = message.content
      .replace(/[#*`>|_-]/g, " ")
      .replace(/\s+/g, " ")
      .trim();

    const utterance = new SpeechSynthesisUtterance(cleanSpeech);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
    setIsSpeaking(true);
  };

  // Helper to format Markdown content into clean React elements
  const renderFormattedContent = (content: string) => {
    const lines = content.split("\n");
    const elements: React.ReactNode[] = [];
    let inTable = false;
    let tableRows: string[][] = [];

    const flushTable = (key: string) => {
      if (tableRows.length > 0) {
        const header = tableRows[0];
        const body = tableRows.slice(1);
        elements.push(
          <div
            key={key}
            className="my-3.5 overflow-x-auto rounded-xl border border-white/10 bg-[#18191a]"
          >
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-white/10 bg-[#202124] font-semibold text-white/90">
                  {header.map((col, cIdx) => (
                    <th key={cIdx} className="px-3.5 py-2.5">
                      {col.trim()}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-[#c4c7c5]">
                {body.map((row, rIdx) => (
                  <tr key={rIdx} className="hover:bg-white/[0.02]">
                    {row.map((cell, cIdx) => (
                      <td key={cIdx} className="px-3.5 py-2">
                        {cell.trim()}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
        tableRows = [];
      }
      inTable = false;
    };

    lines.forEach((line, idx) => {
      const trimmed = line.trim();

      // Check table row
      if (trimmed.startsWith("|") && trimmed.endsWith("|")) {
        if (/^\|[-|:\s]+\|$/.test(trimmed)) {
          return;
        }
        const cells = trimmed.slice(1, -1).split("|");
        tableRows.push(cells);
        inTable = true;
        return;
      } else if (inTable) {
        flushTable(`table-${idx}`);
      }

      // Headers
      if (trimmed.startsWith("### ")) {
        elements.push(
          <h4
            key={idx}
            className="text-sm font-bold text-white mt-4 mb-2 flex items-center gap-1.5"
          >
            <Sparkles className="w-3.5 h-3.5 text-[#4285f4] inline" />
            {formatInline(trimmed.replace(/^###\s+/, ""))}
          </h4>
        );
        return;
      }
      if (trimmed.startsWith("## ")) {
        elements.push(
          <h3 key={idx} className="text-base font-bold text-white mt-5 mb-2.5">
            {formatInline(trimmed.replace(/^##\s+/, ""))}
          </h3>
        );
        return;
      }
      if (trimmed.startsWith("#### ")) {
        elements.push(
          <h5 key={idx} className="text-xs font-bold text-[#c4c7c5] uppercase tracking-wider mt-3 mb-1.5">
            {formatInline(trimmed.replace(/^####\s+/, ""))}
          </h5>
        );
        return;
      }

      // Bullet points
      if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
        elements.push(
          <div key={idx} className="flex items-start gap-2.5 my-1 text-sm text-[#e3e3e3]">
            <span className="w-1.5 h-1.5 rounded-full bg-[#4285f4] mt-2 flex-shrink-0" />
            <div className="flex-1 leading-relaxed">
              {formatInline(trimmed.slice(2))}
            </div>
          </div>
        );
        return;
      }

      // Numbered list
      const numMatch = trimmed.match(/^(\d+)\.\s+(.*)$/);
      if (numMatch) {
        elements.push(
          <div key={idx} className="flex items-start gap-2.5 my-1.5 text-sm text-[#e3e3e3]">
            <span className="text-xs font-semibold text-[#4285f4] w-5 flex-shrink-0 mt-0.5">
              {numMatch[1]}.
            </span>
            <div className="flex-1 leading-relaxed">
              {formatInline(numMatch[2])}
            </div>
          </div>
        );
        return;
      }

      // Blockquotes
      if (trimmed.startsWith("> ")) {
        elements.push(
          <blockquote
            key={idx}
            className="my-3 pl-3.5 border-l-2 border-[#4285f4] bg-white/[0.02] py-1.5 rounded-r-lg text-[#c4c7c5] italic text-sm"
          >
            {formatInline(trimmed.slice(2))}
          </blockquote>
        );
        return;
      }

      // Blank line
      if (!trimmed) {
        elements.push(<div key={idx} className="h-2" />);
        return;
      }

      // Normal paragraph
      elements.push(
        <p key={idx} className="text-sm leading-relaxed text-[#e3e3e3] my-1">
          {formatInline(trimmed)}
        </p>
      );
    });

    if (inTable) {
      flushTable("table-end");
    }

    return elements;
  };

  const formatInline = (text: string): React.ReactNode => {
    const parts = text.split(/(\*\*.*?\*\*|`.*?`)/g);
    return parts.map((part, pIdx) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return (
          <strong key={pIdx} className="font-semibold text-white">
            {part.slice(2, -2)}
          </strong>
        );
      }
      if (part.startsWith("`") && part.endsWith("`")) {
        return (
          <code
            key={pIdx}
            className="px-1.5 py-0.5 rounded bg-white/10 text-blue-300 text-xs font-mono"
          >
            {part.slice(1, -1)}
          </code>
        );
      }
      return part;
    });
  };

  return (
    <div
      className={`group flex gap-4 px-4 py-4 rounded-2xl transition-colors ${
        isAssistant ? "bg-transparent" : "bg-[#1e1f20]/60 max-w-2xl ml-auto border border-white/5"
      }`}
    >
      {/* Avatar */}
      <div className="flex-shrink-0 mt-0.5">
        {isAssistant ? (
          <div className="w-8 h-8 rounded-full flex items-center justify-center bg-[#1e1f20] border border-white/10 shadow-sm">
            <GeminiLogo size={18} />
          </div>
        ) : (
          <div className="w-7 h-7 rounded-full bg-[#303134] text-white flex items-center justify-center text-xs font-medium">
            U
          </div>
        )}
      </div>

      {/* Message Body */}
      <div className="flex-1 min-w-0 space-y-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-white">
            {isAssistant ? "Gemini" : "You"}
          </span>
          <span className="text-[10px] text-white/30">{message.timestamp}</span>

          {isAssistant && message.documentName && (
            <span className="ml-auto text-[10px] px-2 py-0.5 rounded-full bg-white/5 border border-white/10 text-white/50 flex items-center gap-1">
              <FileText className="w-2.5 h-2.5 text-[#4285f4]" />
              {message.documentName}
            </span>
          )}
        </div>

        {/* Formatted Content */}
        <div className="space-y-0.5">{renderFormattedContent(message.content)}</div>

        {/* Assistant Action Toolbar */}
        {isAssistant && (
          <div className="flex items-center gap-2 pt-2 border-t border-white/5 text-xs text-white/40">
            {/* Read Aloud button */}
            <button
              onClick={handleReadAloud}
              className={`p-1.5 rounded-lg hover:bg-white/5 transition-colors ${
                isSpeaking ? "text-[#4285f4] bg-blue-500/10" : "hover:text-white"
              }`}
              title={isSpeaking ? "Stop read aloud" : "Read answer aloud"}
            >
              {isSpeaking ? <VolumeX className="w-3.5 h-3.5" /> : <Volume2 className="w-3.5 h-3.5" />}
            </button>

            {/* Copy button */}
            <button
              onClick={handleCopy}
              className="p-1.5 rounded-lg hover:bg-white/5 hover:text-white transition-colors"
              title="Copy to clipboard"
            >
              {copied ? (
                <Check className="w-3.5 h-3.5 text-emerald-400" />
              ) : (
                <Copy className="w-3.5 h-3.5" />
              )}
            </button>

            {/* Thumbs up / down */}
            <button
              onClick={() => setLiked(liked === true ? null : true)}
              className={`p-1.5 rounded-lg hover:bg-white/5 transition-colors ${
                liked === true ? "text-blue-400" : "hover:text-white"
              }`}
            >
              <ThumbsUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => setLiked(liked === false ? null : false)}
              className={`p-1.5 rounded-lg hover:bg-white/5 transition-colors ${
                liked === false ? "text-red-400" : "hover:text-white"
              }`}
            >
              <ThumbsDown className="w-3.5 h-3.5" />
            </button>

            {message.latencyMs && (
              <span className="ml-auto text-[10px] text-white/30 flex items-center gap-1 font-mono">
                <Clock className="w-3 h-3 text-[#4285f4]" />
                {(message.latencyMs / 1000).toFixed(2)}s
              </span>
            )}
          </div>
        )}

        {/* Dynamic Follow-Up Suggestions Chips */}
        {isAssistant && message.suggestions && message.suggestions.length > 0 && onSelectSuggestion && (
          <div className="pt-2 space-y-1.5">
            <div className="text-[11px] font-medium text-white/50 flex items-center gap-1">
              <Sparkles className="w-3 h-3 text-[#9b72cb]" />
              <span>Related questions in this document:</span>
            </div>
            <div className="flex flex-wrap gap-2">
              {message.suggestions.map((suggestion, sIdx) => (
                <button
                  key={sIdx}
                  onClick={() => onSelectSuggestion(suggestion)}
                  className="text-left text-xs px-3 py-1.5 rounded-full bg-[#1e1f20] hover:bg-[#282a2c] border border-white/10 hover:border-white/20 text-[#c4c7c5] hover:text-white transition-all shadow-sm flex items-center gap-1.5 group"
                >
                  <span className="text-[10px] text-[#4285f4] group-hover:scale-110 transition-transform">
                    ✦
                  </span>
                  <span>{suggestion}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Google Search & Context Recommendations */}
        {isAssistant && message.googleContext && message.googleContext.queries.length > 0 && (
          <div className="pt-2 mt-2 border-t border-white/5 space-y-2">
            <div className="flex items-center justify-between text-[11px] font-medium text-white/50">
              <div className="flex items-center gap-1.5">
                <Search className="w-3 h-3 text-[#4285f4]" />
                <span>Google Search Context & Web Concepts:</span>
              </div>
              <button
                onClick={() => setShowGoogleDetails(!showGoogleDetails)}
                className="text-[10px] text-[#4285f4] hover:underline flex items-center gap-0.5"
              >
                {showGoogleDetails ? "Hide Context" : "Explore Context"}
                {showGoogleDetails ? (
                  <ChevronUp className="w-3 h-3" />
                ) : (
                  <ChevronDown className="w-3 h-3" />
                )}
              </button>
            </div>

            {/* Clickable Google Search Pills */}
            <div className="flex flex-wrap gap-2">
              {message.googleContext.queries.map((q, qIdx) => (
                <a
                  key={qIdx}
                  href={`https://www.google.com/search?q=${encodeURIComponent(q)}`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-xs px-3 py-1.5 rounded-full bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 text-blue-300 hover:text-blue-200 transition-all flex items-center gap-1.5"
                >
                  <Search className="w-3 h-3 text-blue-400" />
                  <span>{q}</span>
                  <ExternalLink className="w-2.5 h-2.5 opacity-60" />
                </a>
              ))}
            </div>

            {/* Expanded Google Context Overview */}
            {showGoogleDetails && (
              <div className="p-3 rounded-xl bg-[#18191a] border border-white/5 text-xs text-[#c4c7c5] leading-relaxed animate-fade-in space-y-1.5">
                <div className="flex items-center gap-1.5 text-white/80 font-medium">
                  <Globe className="w-3.5 h-3.5 text-[#34a853]" />
                  <span>Real-World Domain Context ({message.googleContext.primary_concept})</span>
                </div>
                <p>{message.googleContext.overview}</p>
                {message.googleContext.related_topics.length > 0 && (
                  <div className="pt-1 flex flex-wrap gap-1.5">
                    {message.googleContext.related_topics.map((top, tIdx) => (
                      <span
                        key={tIdx}
                        className="text-[10px] px-2 py-0.5 rounded bg-white/5 text-white/60"
                      >
                        #{top}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
