# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Enterprise Copilot Agent — a RAG (Retrieval-Augmented Generation) system that syncs documents from SharePoint, vectorizes them into Qdrant, and answers natural language queries using AWS Bedrock (Claude 3 Sonnet for LLM, Amazon Titan for embeddings).

## Commands

```bash
# Install dependencies (Python 3.11, uses .venv)
pip install -r requirements.txt

# Run the FastAPI backend
uvicorn main:app --reload

# Run the Streamlit UI (connects to FastAPI at http://127.0.0.1:8000)
streamlit run app.py

# One-time setup: create Qdrant collection and payload indexes
python Collections.py

# Utility: find SharePoint drive IDs
python Drive_ID.py

# Utility: subscribe to SharePoint webhook notifications
python subscribe_webhook.py

# Utility: delete all active MS Graph webhook subscriptions
python reset_webhooks.py
```

## Architecture

### Data Flow
1. **Ingestion**: Files arrive via manual upload (`POST /upload`) or SharePoint webhook (`POST /webhook` triggers delta sync)
2. **Storage**: Files are uploaded to SharePoint via MS Graph API (chunked upload for large files)
3. **Metadata**: SQLite (`CopilotAgentDocs.db`) tracks document metadata and version history
4. **Vectorization**: Text is extracted (PDF/DOCX/PPTX/audio/video), chunked (500 chars), embedded via Amazon Titan (`amazon.titan-embed-text-v1`, 1536 dimensions), and stored in Qdrant
5. **Query**: `POST /ask` embeds the question, searches Qdrant (top 5), builds a prompt with context, and calls Claude 3 Sonnet via Bedrock

### Key Components
- **`main.py`** — FastAPI app entrypoint, registers routers
- **`routes/upload.py`** — File upload endpoint + SharePoint webhook listener with delta sync
- **`routes/query.py`** — RAG query endpoint (`/ask`) with contextual and global search modes
- **`routes/browse.py`** — SharePoint folder browser (`/list-folder`)
- **`services/media_processor.py`** — Audio/video transcription using faster-whisper (small.en model, CPU/int8)
- **`services/qdrant_filters.py`** — Builds Qdrant payload filters for contextual vs global search
- **`db.py`** — SQLite schema and CRUD for documents/versions
- **`user.py`** — Standalone earlier version of the upload flow (not used by `main.py`)
- **`app.py`** — Streamlit UI frontend (dark glassmorphism theme)
- **`Collections.py`** — One-time Qdrant collection + index setup script

### External Services
- **Azure AD / MS Graph API** — SharePoint file storage, folder browsing, webhook subscriptions
- **Qdrant Cloud** — Vector database (collection: `CopilotAgentDocs`)
- **AWS Bedrock** — Embeddings (Titan) and LLM (Claude 3 Sonnet), uses named AWS profile

### Required Environment Variables (`.env`)
`TENANT_ID`, `CLIENT_ID`, `CLIENT_SECRET`, `DRIVE_ID`, `VDB_URL`, `VDB_API`, `AWS_PROFILE`

## Important Notes

- Webhook delta sync uses a file-based bookmark (`delta_token.txt`) to track the last sync position
- Chunks are capped at 50 per document to avoid overload
- Qdrant upserts are batched in groups of 10
- `Drive_ID.py`, `subscribe_webhook.py`, and `reset_webhooks.py` have hardcoded credentials — these should be migrated to use `.env`
