# AI Context — Gold Weight Prediction System

## Overview
- **Purpose**: AI-powered system to predict gold weight for jewelry designs based on images and parameters.
- **Stack**: React (Frontend), FastAPI (Backend), XGBoost (ML), Pinecone/ChromaDB (Vector DB), Gemini/Claude (LLM).
- **Status**: Phase 2 Complete (transitioning to Phase 3)
- **Version**: 0.3.1
- **Last Updated**: 2026-05-02

## File Structure
- `backend/`: FastAPI application, ML models, and database.
- `frontend/`: React application with Tailwind CSS.
- `project_guide.md`: Detailed project specification.
- `AI_CONTEXT.md`: This file.
- `CHANGELOG.md`: Project change history.

## Key Components
| Component | File | Purpose |
|-----------|------|---------|
| Prediction API | `backend/app/api/endpoints.py` | Main entry point for prediction and RAG. |
| Vector DB | `backend/app/db/` | Factory for Pinecone and ChromaDB clients. |
| CLIP Encoder | `backend/app/core/embeddings.py` | Image embedding generator (ViT-B-32). |
| LLM Utils | `backend/app/api/llm_utils.py` | Prompt engineering and API logic. |

## Environment Variables
| Variable | Description | Required? |
|----------|-------------|-----------|
| `ANTHROPIC_API_KEY` | API key for Claude LLM | Optional |
| `GEMINI_API_KEY` | API key for Gemini LLM | Optional |
| `PINECONE_API_KEY` | API key for Pinecone Vector DB | Yes (for Pinecone) |
| `VECTOR_DB_TYPE` | `pinecone` or `chroma` | Yes |
| `DATABASE_URL` | SQLite connection string | Yes |

## API Endpoints
| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/predict | Ensemble prediction (LLM + RAP context). |
| POST | /api/v1/search | RAG Search: Image -> Top-5 similar rings. |
| GET | /api/v1/history | Prediction history retrieval. |

## Known Issues
- XGBoost model (Phase 3) is the next focus.

## Next Steps
- [x] Phase 1: Foundation (Backend + Frontend).
- [x] Phase 2: Vector Database (CLIP + Chroma/Pinecone).
- [ ] Phase 3: XGBoost Model training on enriched dataset.
