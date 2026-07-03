# AI Context — Gold Weight Prediction System

## Overview
- **Purpose**: AI-powered gold weight and volume prediction for jewelry designs using direct 18K weight legacy visual RAG anchoring (standardized from legacy index dual predicted weights), dual-standard ring sizing, and density-cohesive conversions.
- **Stack**: FastAPI (Python), React (Vite/TS), CLIP (Embeddings), Pinecone/Chroma (Vector DB), SQLite (Metadata), Gemini 3.1 Flash Lite Preview / Claude 3.5 Sonnet (LLMs).
- **Status**: Backend deployed on AWS EC2 (v0.6.1)
- **Version**: 0.6.1
- **Last Updated**: 2026-07-03

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
| AWS Backend | `backend/` | FastAPI CLIP backend deployed to EC2 at `http://13.207.220.204:8000`, using 512-dim `ring-designs-v3` Pinecone RAG. |
| Vercel Frontend | `frontend/` | React frontend deployed at `https://gold-weight-frontend.vercel.app` with `/api/v1/*` rewrites to the EC2 backend. |
| 3D Local Generator | `3D_model/local_generator.py` | Runs Hunyuan3D-2 locally using CPU or Apple Silicon MPS device. |
| 3D API Generator | `3D_model/gradio_generator.py` | Fallback Gradio API client to generate 3D models using HF Spaces. |
| Qwen2.5-VL Dataset Generator | `Tanishq_Jewelry_Dataset_Final/prepare_qwen_dataset.py` | Parsers unified catalog and generates training dataset splits. |
| Qwen2.5-VL Trainer Script | `scratch/train_qwen_lora.py` | LoRA fine-tuning script for training Qwen2.5-VL-3B-Instruct model. |
| Qwen2.5-VL MLX Trainer | `scratch/train_qwen_mlx.py` | Native Apple Silicon LoRA fine-tuning script with W&B logging. |

## Next Steps
- [x] Weight-first visual RAG prediction logic.
- [x] Dual-standard Indian / US ring scaling.
- [x] 22K support.
- [x] Verified data ingestion form.
- [x] Combined dataset cleaning, normalisation, and mapping.
- [x] Multi-angle image downloading scripts with rate limiting.
- [x] Unified schema CLIP embedding and Pinecone ingestion pipeline.
- [x] AWS backend deployment on EC2 port 8000.
- [x] Vercel frontend deployment from `frontend/` connected to EC2 backend through same-domain rewrites.
- [x] Corrected EC2 deployment from `backend_aws` Gemini-embedding backend to `backend` CLIP backend for the populated 512-dim Pinecone RAG index.
- [ ] XGBoost training on tabular data (Phase 3).
- [ ] Exporting predictions to CSV.
