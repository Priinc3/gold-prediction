# Progress — Gold Weight Prediction

## Active Tasks
- [x] Configure remote VM environment with partitioned GPU (NVIDIA A10-24Q) support
- [x] Setup Python virtual environment, install PyTorch + CUDA, and install Hugging Face PEFT training libraries
- [x] Extract dataset splits and copy model fine-tuning pipeline to VM
- [x] Run full fine-tuning training (3 epochs) on GPU VM (completed successfully)
- [x] Deploy AWS FastAPI backend to EC2 `13.207.220.204:8000`
- [x] Replace EC2 backend with `backend/` CLIP variant using populated `ring-designs-v3` Pinecone index
- [x] Deploy `frontend/` to Vercel at `https://gold-weight-frontend.vercel.app`
- [ ] Evaluate final trained model adapters (`adapters.safetensors`) on the test split
- [ ] Deploy vLLM server or offline inference module using the trained adapters

## Done
- [x] Weight-first visual RAG prediction logic
- [x] Dual-standard Indian / US ring scaling
- [x] 22K gold support
- [x] Combined dataset cleaning, normalisation, and mapping
- [x] Multi-angle image downloading scripts with rate limiting
- [x] Unified schema CLIP embedding and Pinecone ingestion pipeline
- [x] AWS backend deployment verified at `http://13.207.220.204:8000/`
- [x] Vercel frontend verified with `/api/v1` proxy to backend
- [x] RAG `/api/v1/search` and full `/api/v1/predict` verified against `ring-designs-v3`
