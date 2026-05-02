# Changelog

Format: [YYYY-MM-DD] | [vX.X.X] | [Type: Added/Fixed/Changed/Removed]

---

## [0.3.1] — 2026-05-02

### Added
- **Pinecone Vector DB Support**: 
  - Integrated `pinecone` (v8.1.2) as an alternative vector database provider.
  - Implemented `PineconeDB` client with auto-index creation (cosine similarity, 512 dimensions).
  - Migrated 506 designs from the Tanishq dataset to Pinecone.
  - Added `VECTOR_DB_TYPE` toggle in settings to switch between `chroma` and `pinecone`.

### Changed
- Refactored `get_vector_db()` to use a factory pattern for multi-DB support.
- Updated `ingest_dataset.py` to be vector-database agnostic.

---

## [0.3.0] — 2026-05-02

### Added
- **Data Preparation for RAG**: 
  - Normalized `tanishq_jewelry_dataset.csv` (fixed 500+ image paths, added geometric metadata placeholders).
  - Bulk ingestion script `backend/ingest_dataset.py` for ChromaDB.
  - Successfully ingested 506 designs into the Vector DB with baseline metadata.
- **Improved RAG Retrieval**: Harmonized `VectorDB.query_similar` to handle both historical dataset metadata and new prediction metadata.

### Changed
- Environment: Established Python 3.14 virtual environment with `torch`, `open-clip-torch`, and `chromadb`.

---

## [0.2.0] — 2026-05-01

### Added
- **Gemini API Support**: Added Google Gemini-1.5-Flash as an alternative/default LLM provider.
- **Phase 2: Vector Database complete**.
  - CLIP Encoder integration for generating 512d image embeddings.
  - ChromaDB integration for persistent vector storage.
  - Retrieval-Augmented Prediction (RAP): Similar designs are retrieved and passed to the LLM for better calibration.

### Changed
- LLM fallback logic: System now tries Gemini, then Claude, then returns a dummy prediction.

---

## [0.1.0] — 2026-05-01

### Added
- Project initialized.
- `AI_CONTEXT.md` and `CHANGELOG.md` created.
- Implementation plan drafted and approved.
- **Phase 1: Foundation complete**.
  - FastAPI backend with SQLite and Anthropic Claude-3.5-Sonnet integration.
  - React (Vite + TypeScript) frontend with Tailwind CSS 4.
  - Prediction form for parameters and image upload.
  - Prediction history table.

### Technical Notes
- Architecture established: Hybrid AI (XGBoost + CLIP + LLM).
- Frontend uses Lucide icons and Framer Motion for animations.
- Backend uses SQLAlchemy with aiosqlite for async DB access.
