# AI Context — Gold Weight Prediction System

## Overview
- **Purpose**: AI-powered gold weight and volume prediction for jewelry designs using direct 18K weight legacy visual RAG anchoring (standardized from legacy index dual predicted weights), dual-standard ring sizing, and density-cohesive conversions.
- **Stack**: FastAPI (Python), React (Vite/TS), CLIP (Embeddings), Pinecone/Chroma (Vector DB), SQLite (Metadata), Gemini 3.1 Flash Lite Preview / Claude 3.5 Sonnet (LLMs).
- **Status**: In Development (v0.5.0)
- **Version**: 0.5.0
- **Last Updated**: 2026-05-23

## Core Logic: Direct Gram Weight Visual RAG Anchoring
To eliminate the "Abstract Unit Trap" where LLMs overestimate cubic millimeters ($mm^3$), the system uses a **Weight-First** visual anchoring approach:
1. **RAG Visual Anchoring:** Retrived catalog items are injected into the LLM prompt with their exact real-world weights, providing explicit anchors.
2. **Direct 18K Gram Weight Prediction:** The LLM predicts the 18K gold weight in grams ($g$) directly.
3. **Density-Cohesive Conversions:** The backend derives the implicit design volume:
   $$V = \frac{W_{18K}}{0.01558}$$
   It then calculates the corresponding 14K and 22K weights using strict density coefficients:
   - 14K: 13.07 g/cm³ ($0.01307 \text{ g/mm}^3$)
   - 18K: 15.58 g/cm³ ($0.01558 \text{ g/mm}^3$)
   - 22K: 17.50 g/cm³ ($0.01750 \text{ g/mm}^3$)
4. **Dual-Standard Ring Scaling:** Ring sizing handles both 🇮🇳 Indian Standard (Sizes 1-30 lookup chart) and 🇺🇸 US Standard (linear size-to-diameter formula). Volume and weights scale linearly based on the ratio of target-to-base inner circumferences (diameters).
5. **Unified Dataset Integration:** Combines Tanishq (504 rings, mostly 22KT) and Orra (1,094 rings, 14KT/18KT/Platinum, US sizes) into a unified, clean database format with mapped schemas and local visual assets.

## Key Components
| Component | File | Purpose |
|-----------|------|---------|
| Prediction Engine | `backend/app/api/llm_utils.py` | Dual-standard lookups, direct gram estimation, and density-cohesive conversions. |
| RAG Retrieval | `backend/app/db/pinecone_client.py` | Visual similarity search for historical anchoring. |
| Unified Schema | `Tanishq_Jewelry_Dataset_Final/unified_jewelry_dataset.csv` | Clean combined database mapping Tanishq + Orra rings. |
| Unified Ingestion | `backend/ingest_unified_dataset.py` | High-performance script to embed unified designs using CLIP and upsert to Pinecone Vector DB. |
| Ingestion API | `backend/app/api/endpoints.py` | Endpoint to add verified designs to training pool with size/standard metadata. |
| Admin Panel | `frontend/src/components/AdminPanel.tsx` | Settings and Training Data entry. |

## Next Steps
- [x] Weight-first visual RAG prediction logic.
- [x] Dual-standard Indian / US ring scaling.
- [x] 22K support.
- [x] Verified data ingestion form.
- [x] Combined dataset cleaning, normalisation, and mapping.
- [x] Multi-angle image downloading scripts with rate limiting.
- [x] Unified schema CLIP embedding and Pinecone ingestion pipeline.
- [ ] XGBoost training on tabular data (Phase 3).
- [ ] Exporting predictions to CSV.
