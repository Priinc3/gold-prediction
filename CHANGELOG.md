# Changelog

Format: [YYYY-MM-DD] | [vX.X.X] | [Type: Added/Fixed/Changed/Removed]

---

## [Unreleased]

---

## [0.5.0] — 2026-05-23

### Added
- **Unified Dataset Integration:** Cleaned, normalized, and combined the Tanishq (504 rings) and Orra (1,094 rings) datasets into a single unified schema (`unified_jewelry_dataset.csv`).
- **Parallel Image Retrieval Pipeline:** Orchestrated parallel subagents to concurrently run deep statistical analyses and download over 3,300+ multi-angle ring images from Orra's CDN with robust rate limiting and resume support.
- **Unified CLIP Vector Ingestion:** Implemented a high-performance vector ingestion pipeline (`ingest_unified_dataset.py`) to generate standardized CLIP embeddings and populate the Pinecone index (`ring-designs`) with rich filterable metadata.
- **Standardized Chroma DB Adapter Layers:** Re-architected both Chroma client query routines (`backend/app/db/chroma_client.py` and `backend_aws/app/db/chroma_client.py`) to fully support legacy metadata parsing, dual 14K/18K predicted weights, strict weight-first density alignment, and standardized 18K gold purity visual anchors.
- **Synchronized AWS Pinecone Adapter:** Ported the strict density-cohesive weight-first calculation into the AWS Pinecone client (`backend_aws/app/db/pinecone_client.py`) to align completely with the main environment.
- **Root-Level Karat Fields:** Exposed `karat` at the root of `SimilarExample` Pydantic models in both `backend` and `backend_aws` schemas to fully satisfy frontend mapping expectations.
- **Frontend Karat Fallback:** Added a safe, fallback-aware karat rendering logic in frontend `PredictionForm.tsx` to read `ex.karat` or `ex.params.karat` gracefully.

### Fixed
- **Volume Misalignment Across Vector DBs:** Corrected latent volume misalignment vulnerabilities where mismatched karat densities and legacy predicted-weight columns could output mathematically incoherent cubic volumes ($mm^3$) to the LLM context.
- **FastAPI 422 Request Error on URL Predictions:** Corrected `/predict` endpoint signature to treat the `images` multipart file list as optional via `File(default=[])` instead of a required form-data body parameter.
- **React Child Render Crash:** Replaced raw axios error assignment with a robust, recursive validation-error formatter inside the Axios catch blocks of both frontends, resolving the `Objects are not valid as a React child` crash.

---

## [0.4.0] — 2026-05-22

### Added
- **Direct Legacy Index Host Support:** Implemented explicit host bypass initialization in Pinecone DB client so it can target any direct custom serverless index URL.
- **Purity-Aligned RAG Anchoring:** Re-engineered visual RAG metadata parser to correctly handle dual 14K/18K predicted weights of legacy index records.

### Fixed
- **RAG Volume Misalignment Loophole:** Corrected vector DB query parser to align item volumes using their actual original karat density ratios, standardizing retrieved prompt anchors to a clean, uniform 18K purity baseline.

---

## [0.3.0] — 2026-05-22

### Added
- **Remote Image URL Sourcing:** Added backend-side async fetching of external image URLs using `httpx`, bypassing browser CORS constraints completely and validating downloaded image buffers with Pillow.
- **Interactive URL Previews:** Built a premium segmented controller to toggle between "Upload Photos" and "Paste Image URL" in the frontend, complete with live visual preview cards and custom fallback placeholders for broken URLs.
- **Direct Weight-First RAG Anchoring:** Migrated from abstract volume estimation ($mm^3$) to direct 18K weight estimation in grams ($g$) to solve the "Abstract Unit Trap" and improve model accuracy.
- **Dual-Standard Sizing:** Implemented support for both 🇮🇳 Indian Ring Sizes (Sizes 1-30 lookup chart) and 🇺🇸 US Ring Sizes, addressing the systematic +30% weight overestimation caused by US/Indian size scaling mismatches.
- **Premium Frontend Sizing Toggles:** Added flag-labeled "🇮🇳 Indian Standard" / "🇺🇸 US Standard" selection tab system, dynamic target size lists, and interactive local size scaling slider on results.

### Fixed
- **Claude Parser Crash:** Unified LLM output JSON schema and backend extraction keys to resolve silent `None` prediction parsing errors on Anthropic/Claude responses.
- **Visual RAG scaling:** Added size mapping translators for historical US Size 7 baselines compared to Indian Size 12/14 models to scale visual examples accurately.

---

## [0.2.0] — 2026-05-02

### Added
- **Volume-Based Prediction:** AI now predicts base volume (mm³) instead of weights directly. Backend handles karat conversion (14K, 18K, 22K) using standard densities.
- **Training Data Ingestion:** New endpoint and UI to upload verified ring designs (image + actual weight) to the training pool (RAG).
- **Weight Ranges:** Predictions now return a "Min-Max" range with a safety overestimation bias for manufacturing.
- **22K Support:** Added calculations and UI support for 22K Gold.

### Changed
- Refactored LLM prompt for Gemini 3 Flash Preview to prioritize RAG-based volume anchoring.
- Updated database schema to include volume and range fields.
- Admin Panel now includes a "Add Verified Training Design" form.

---

## [0.1.0] — 2026-05-02

### Added
- Project initialized
- Visual RAG with CLIP and Pinecone
- Gold weight prediction using Gemini 3 Flash Preview
