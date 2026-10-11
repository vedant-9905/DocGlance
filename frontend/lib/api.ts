// lib/api.ts — API client for Gemini Doc backend

import type {
  ChatResponse,
  ConfigResponse,
  DocumentProfile,
  HealthResponse,
} from "@/types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:4000";

class ApiError extends Error {
  constructor(
    public readonly statusCode: number,
    message: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body.detail ?? JSON.stringify(body);
    } catch {
      // ignore JSON parse errors
    }
    throw new ApiError(res.status, message);
  }
  return res.json() as Promise<T>;
}

export const api = {
  /** Check backend health and model status. */
  health(): Promise<HealthResponse> {
    return fetch(`${API_BASE}/api/health`).then((r) =>
      handleResponse<HealthResponse>(r)
    );
  },

  /** Get Gemini Cloud & local model config. */
  getConfig(): Promise<ConfigResponse> {
    return fetch(`${API_BASE}/api/config`).then((r) =>
      handleResponse<ConfigResponse>(r)
    );
  },

  /** Update Gemini API key or model. */
  updateConfig(data: { gemini_api_key?: string; gemini_model?: string }): Promise<{ message: string }> {
    return fetch(`${API_BASE}/api/config`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    }).then((r) => handleResponse<{ message: string }>(r));
  },

  /** Upload any document (PDF, Word, Excel, PPTX, CSV, TXT, MD). */
  upload(file: File): Promise<DocumentProfile> {
    const form = new FormData();
    form.append("file", file);
    return fetch(`${API_BASE}/api/upload`, {
      method: "POST",
      body: form,
    }).then((r) => handleResponse<DocumentProfile>(r));
  },

  /** Load sample document instantly. */
  loadSample(): Promise<DocumentProfile> {
    return fetch(`${API_BASE}/api/sample`, {
      method: "POST",
    }).then((r) => handleResponse<DocumentProfile>(r));
  },

  /** Fetch current active document details. */
  getActiveDocument(): Promise<DocumentProfile | null> {
    return fetch(`${API_BASE}/api/document/active`).then((r) =>
      handleResponse<DocumentProfile | null>(r)
    );
  },

  /** Unload / clear current document. */
  clearDocument(): Promise<{ message: string }> {
    return fetch(`${API_BASE}/api/document`, {
      method: "DELETE",
    }).then((r) => handleResponse<{ message: string }>(r));
  },

  /** Send multi-turn chat messages. */
  chat(
    messages: { role: string; content: string }[],
    apiKey?: string
  ): Promise<ChatResponse> {
    return fetch(`${API_BASE}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        messages,
        stream: false,
        api_key: apiKey || undefined,
      }),
    }).then((r) => handleResponse<ChatResponse>(r));
  },
};

export { ApiError };
