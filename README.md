# DocGlance

**Google Gemini Document-Grounded Conversational Intelligence**  
*Clean Chatbot UI/UX • Simple Universal Document Upload • Strictly Grounded Detailed Answers • Dynamic Follow-up Suggestions • Google Search Context*

---

## 🌟 Overview

**DocGlance** delivers the full conversational experience and design aesthetics of **Google Gemini**, strictly grounded to your uploaded document. Whether you need a deep macro summary, precise numerical data extraction, cross-section comparative analysis, or related Google Search and web context, DocGlance provides articulate, thoroughly explained answers with zero hallucinations outside your file.

### Key Capabilities:
- **True Google Gemini UI/UX**:
  - Google Gemini signature dark theme (`#131314` base canvas, iridescent Gemini sparkle gradients, and fluid typography).
  - Collapsible sidebar drawer with active document passport, section outline, key themes, and recent chat history.
  - Floating bottom input dock with file attachment pill, auto-expanding textarea, voice dictation (microphone), and send actions.
- **Simple Universal Document Upload**:
  - Single-click or drag-and-drop ingestion of Microsoft 365, Google Workspace, and open formats:
    - 📄 **Documents**: PDF (`.pdf`), Word (`.docx`, `.doc`), Google Docs
    - 📊 **Spreadsheets**: Excel (`.xlsx`, `.xls`), CSV (`.csv`), TSV (`.tsv`), Google Sheets
    - 📽️ **Presentations**: PowerPoint (`.pptx`, `.ppt`), Google Slides
    - 🌐 **Text & Code**: Markdown (`.md`), HTML (`.html`), Plain Text (`.txt`), JSON (`.json`), YAML (`.yaml`)
- **Strictly Grounded, Detailed Explained Answers**:
  - Responses analyze complete documents as a whole rather than disjointed chunks.
  - Formatted with bold headings, structured comparison tables, direct document quotes, and citations.
- **Dynamic Follow-Up Suggestions**:
  - Every answer dynamically suggests 3-4 interactive follow-up question pills based on the document's content and themes.
- **Google Search & Real-World Web Context**:
  - Suggests clickable Google Search queries and domain context cards connecting document themes to broader industry standards.
- **Dual Engine Architecture**:
  - ⚡ **Google Gemini Cloud**: Real-time integration with `gemini-2.0-flash` or `gemini-1.5-flash` via optional Gemini API key.
  - 🔒 **100% Free & Offline Local Engine**: Local CPU neural inference (Qwen2.5) and instant Macro NLP synthesis for private, offline data sovereignty.

---

## 🏗️ System Architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│               Frontend: Next.js 16 + React 19 + Tailwind CSS           │
│  - Google Gemini Floating Input Dock       - Document Grounding Badges │
│  - Collapsible Sidebar Drawer              - Follow-up Suggestion Chips│
│  - Voice Dictation (SpeechRecognition)     - Google Search Pills       │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP / Server-Sent Events (SSE)
┌───────────────────────────────────▼────────────────────────────────────┐
│                    Backend: FastAPI + Python 3.11                      │
│                                                                        │
│  ┌──────────────────────┐  ┌────────────────────────────────────────┐  │
│  │ Universal Parsers    │  │ Dual Intelligence Engine               │  │
│  │ • PDF (pypdf)        │  │ • Google Gemini Cloud (2.0 / 1.5 Flash)│  │
│  │ • Word (python-docx) │  │ • Local Offline Neural (Qwen2.5)       │  │
│  │ • Excel (openpyxl)   │  │ • High-Fidelity Macro Synthesizer      │  │
│  │ • PPTX (python-pptx) │  └────────────────────────────────────────┘  │
│  │ • CSV/TSV (pandas)   │  ┌────────────────────────────────────────┐  │
│  │ • HTML (bs4)         │  │ Context & Recommendation Generator     │  │
│  └──────────────────────┘  │ • Dynamic Follow-up Suggestions        │  │
│                            │ • Google Search & Web Concept Pills    │  │
│                            └────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### 1. Launch Everything in 1 Click

```powershell
.\start.ps1
```
This automatically launches:
- **Backend API**: `http://localhost:4000` (API Docs: `http://localhost:4000/docs`)
- **Frontend Web App**: `http://localhost:3100`

### 2. Manual Setup

#### Backend:
```powershell
cd backend
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 4000 --reload
```

#### Frontend:
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:3100` in your browser.

---

## ⚙️ Configuration & Model Settings

DocGlance works out of the box with **zero configuration required** using the built-in local engine.

To use Google Gemini Cloud directly:
1. Open the web interface at `http://localhost:3100`.
2. Click the **Gear icon** (or "Gemini & AI Settings" in the sidebar).
3. Paste your [Google AI Studio API Key](https://aistudio.google.com/app/apikey) and select `Gemini 2.0 Flash`.
4. Click **Save Preferences**.
