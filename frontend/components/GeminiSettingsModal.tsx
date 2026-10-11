"use client";

import React, { useState, useEffect } from "react";
import { X, Key, Cpu, ShieldCheck, Check, Sparkles, ExternalLink } from "lucide-react";
import GeminiLogo from "./GeminiLogo";
import { api } from "@/lib/api";

interface GeminiSettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  onConfigChanged: () => void;
}

export default function GeminiSettingsModal({
  isOpen,
  onClose,
  onConfigChanged,
}: GeminiSettingsModalProps) {
  const [apiKey, setApiKey] = useState("");
  const [selectedModel, setSelectedModel] = useState("gemini-2.0-flash");
  const [useLocalEngine, setUseLocalEngine] = useState(false);
  const [saving, setSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [localModelName, setLocalModelName] = useState("Qwen2.5-1.5B");
  const [hasServerKey, setHasServerKey] = useState(false);

  useEffect(() => {
    if (isOpen) {
      const savedKey = localStorage.getItem("gemini_doc_api_key") || "";
      const savedModel = localStorage.getItem("gemini_doc_model") || "gemini-2.0-flash";
      const savedUseLocal = localStorage.getItem("gemini_doc_use_local") === "true";
      setApiKey(savedKey);
      setSelectedModel(savedModel);
      setUseLocalEngine(savedUseLocal);

      api.getConfig().then((cfg) => {
        setHasServerKey(cfg.has_gemini_key);
        setLocalModelName(cfg.local_model);
      }).catch(() => {});
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSave = async () => {
    setSaving(true);
    try {
      localStorage.setItem("gemini_doc_api_key", apiKey.trim());
      localStorage.setItem("gemini_doc_model", selectedModel);
      localStorage.setItem("gemini_doc_use_local", useLocalEngine ? "true" : "false");

      await api.updateConfig({
        gemini_api_key: useLocalEngine ? "" : apiKey.trim(),
        gemini_model: selectedModel,
      });

      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2000);
      onConfigChanged();
    } catch (err) {
      console.error(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-fade-in">
      <div className="w-full max-w-lg bg-[#1e1f20] border border-white/10 rounded-2xl shadow-2xl overflow-hidden flex flex-col">
        {/* Header */}
        <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-[#18191a]">
          <div className="flex items-center gap-2.5">
            <GeminiLogo size={20} />
            <h2 className="text-base font-semibold text-white">AI Engine & Gemini Settings</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 text-white/40 hover:text-white rounded-lg hover:bg-white/5 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5 overflow-y-auto max-h-[75vh]">
          {/* Mode Selector */}
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-white/50">
              Intelligence Engine Mode
            </label>
            <div className="grid grid-cols-2 gap-3">
              <button
                type="button"
                onClick={() => setUseLocalEngine(false)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  !useLocalEngine
                    ? "bg-[#282a2c] border-[#4285f4] shadow-md shadow-blue-500/10"
                    : "bg-[#18191a] border-white/5 hover:border-white/10 text-white/70"
                }`}
              >
                <div className="flex items-center gap-2 font-medium text-xs text-white mb-1">
                  <Sparkles className="w-3.5 h-3.5 text-[#4285f4]" />
                  <span>Google Gemini Cloud</span>
                </div>
                <p className="text-[11px] text-white/50 leading-relaxed">
                  Fastest reasoning with Google Gemini 2.0 / 1.5 Flash.
                </p>
              </button>

              <button
                type="button"
                onClick={() => setUseLocalEngine(true)}
                className={`p-3 rounded-xl border text-left transition-all ${
                  useLocalEngine
                    ? "bg-[#282a2c] border-emerald-500 shadow-md shadow-emerald-500/10"
                    : "bg-[#18191a] border-white/5 hover:border-white/10 text-white/70"
                }`}
              >
                <div className="flex items-center gap-2 font-medium text-xs text-white mb-1">
                  <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                  <span>100% Offline Local</span>
                </div>
                <p className="text-[11px] text-white/50 leading-relaxed">
                  Zero cloud calls. Private local neural synthesis engine.
                </p>
              </button>
            </div>
          </div>

          {/* Gemini API Key input */}
          {!useLocalEngine && (
            <div className="space-y-2 pt-2 border-t border-white/5">
              <div className="flex items-center justify-between">
                <label className="text-xs font-medium text-white/80 flex items-center gap-1.5">
                  <Key className="w-3.5 h-3.5 text-[#4285f4]" />
                  <span>Google Gemini API Key (Optional)</span>
                </label>
                <a
                  href="https://aistudio.google.com/app/apikey"
                  target="_blank"
                  rel="noreferrer"
                  className="text-[11px] text-[#4285f4] hover:underline flex items-center gap-1"
                >
                  Get Free Key <ExternalLink className="w-2.5 h-2.5" />
                </a>
              </div>
              <input
                type="password"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder={hasServerKey ? "Using backend configured API key" : "Paste your Gemini API key (AIzaSy...)"}
                className="w-full px-3.5 py-2.5 rounded-xl bg-[#131314] border border-white/10 text-xs text-white placeholder-white/30 focus:outline-none focus:border-[#4285f4] font-mono"
              />
              <p className="text-[11px] text-white/40 leading-relaxed">
                If no key is provided, Gemini Doc automatically uses the built-in 100% Offline Macro & Neural Engine with zero downtime.
              </p>

              {/* Model Choice */}
              <div className="pt-2">
                <label className="text-xs font-medium text-white/80 block mb-1.5">
                  Gemini Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full px-3 py-2 rounded-xl bg-[#131314] border border-white/10 text-xs text-white focus:outline-none focus:border-[#4285f4]"
                >
                  <option value="gemini-2.0-flash">Gemini 2.0 Flash (Recommended, Ultra Fast)</option>
                  <option value="gemini-1.5-flash">Gemini 1.5 Flash</option>
                  <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep Reasoning)</option>
                </select>
              </div>
            </div>
          )}

          {/* Local Engine Info */}
          {useLocalEngine && (
            <div className="p-3.5 rounded-xl bg-[#131314] border border-white/5 space-y-1.5">
              <div className="flex items-center gap-2 text-xs font-medium text-emerald-400">
                <Cpu className="w-3.5 h-3.5" />
                <span>Active Local Model: {localModelName}</span>
              </div>
              <p className="text-[11px] text-white/50 leading-relaxed">
                Running locally in RAM/CPU. All parsing, document analysis, and answers remain completely on your computer with zero external data transfer.
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-6 py-3.5 border-t border-white/10 flex items-center justify-between bg-[#18191a]">
          <span className="text-[11px] text-white/40">
            {savedSuccess ? (
              <span className="text-emerald-400 flex items-center gap-1 font-medium">
                <Check className="w-3.5 h-3.5" /> Settings Saved!
              </span>
            ) : (
              "Preferences saved to browser & server"
            )}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-1.5 rounded-lg text-xs font-medium text-white/70 hover:text-white hover:bg-white/5 transition-colors"
            >
              Cancel
            </button>
            <button
              type="button"
              disabled={saving}
              onClick={handleSave}
              className="px-4 py-1.5 rounded-lg text-xs font-semibold text-white bg-[#4285f4] hover:bg-[#3367d6] transition-colors shadow-md shadow-blue-500/20"
            >
              {saving ? "Saving..." : "Save Preferences"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
