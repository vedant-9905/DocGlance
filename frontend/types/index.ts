// types/index.ts — Shared TypeScript types for Gemini Doc

export interface GoogleContext {
  queries: string[];
  related_topics: string[];
  primary_concept: string;
  overview: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: string;
  documentName?: string;
  latencyMs?: number;
  suggestions?: string[];
  googleContext?: GoogleContext;
}

export interface SectionSummary {
  title: string;
  preview: string;
  word_count: number;
  index: number;
}

export interface DocumentProfile {
  filename: string;
  file_type: string;
  word_count: number;
  char_count: number;
  estimated_read_time_mins: number;
  key_concepts: string[];
  executive_summary: string;
  section_map: SectionSummary[];
  message: string;
}

export interface ChatResponse {
  role: string;
  content: string;
  document: string | null;
  latency_ms: number;
  suggestions?: string[];
  google_context?: GoogleContext;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  model_name: string;
  model_status: string;
  has_gemini_key: boolean;
  active_document: string | null;
  allowed_file_types: string[];
}

export interface ConfigResponse {
  has_gemini_key: boolean;
  gemini_model: string;
  local_model: string;
  local_model_status: string;
}
