# Changelog

Format: [YYYY-MM-DD] | [vX.X.X] | [Type: Added/Fixed/Changed/Removed]

---

## [0.6.1] — 2026-07-03

### Added
- **AWS Backend Deployment:** Deployed `backend_aws` FastAPI service to EC2 `13.207.220.204` and verified public access on port `8000`.
- **Vercel Frontend Deployment:** Deployed `frontend/` to Vercel at `https://gold-weight-frontend.vercel.app`.
- **Same-Domain API Proxy:** Added Vercel rewrites so `/api/v1/*` proxies to the EC2 backend without browser mixed-content blocking.
- **Deployment Runbook:** Added `docs/deploy_guide.md` with the current working backend/frontend folders, Pinecone index, EC2 commands, Vercel deploy steps, verification commands, and known failure fixes.

### Fixed
- **Public Settings Secret Exposure:** Updated the backend settings endpoint to return provider availability flags without returning API key values.
- **Python 3.14 Deploy Compatibility:** Relaxed `backend_aws` dependency pins for Pydantic and Pillow so the EC2 default Python runtime can install binary wheels instead of failing source builds.
- **Environment Parsing:** Configured backend settings to ignore unrelated `.env` keys during startup.
- **RAG Dimension Mismatch:** Replaced the EC2 `backend_aws` deployment, which produced 3072-dim Gemini embeddings, with the `backend/` CLIP deployment that produces 512-dim vectors matching the populated `ring-designs-v3` Pinecone index.
- **CPU Torch Deployment:** Forced CPU-only Torch/Torchvision wheels in `backend/requirements.txt` to avoid pulling multi-GB CUDA packages on the small EC2 root volume.
- **Frontend Deployment Target:** Switched the active Vercel frontend from `frontend_aws/` to the correct `frontend/` folder and added `.vercelignore` to avoid uploading `node_modules`.

---

## [0.6.0] — 2026-07-02

### Added
- **NVIDIA GRID GPU Driver Configuration:** Resolved NVML initialization errors on the partitioned remote Azure VM (20.211.122.9) by purging standard NVIDIA drivers, disabling Secure Boot, and installing the correct vGPU 18.5 (570.195.03) GRID driver, enabling the virtual NVIDIA A10-24Q GPU with 24.5 GB VRAM.
- **Remote PyTorch/CUDA Virtual Environment:** Created a virtual environment on the VM, installing PyTorch aligned with CUDA 12 and required training libraries (transformers, accelerate, peft, trl, bitsandbytes, datasets, tensorboard).
- **Hugging Face Hub Authentication:** Authenticated the remote VM with the user's Hugging Face credentials for rate-limit-free downloads.
- **Dynamic Training Script Arguments:** Integrated `argparse` into `train_qwen_lora.py` to allow overriding parameters like epochs, steps, batch sizes, and data workers from the command line.
- **Successful Training Dry Run:** Verified the full pipeline on the remote GPU by completing a 5-step test run (forward passes, loss calculations, backprop updates, checkpoint saving) in under 30 seconds.
- **Full Fine-Tuning Execution (3 Epochs):** Successfully executed the full fine-tuning run (267 steps, representing 3 epochs over 1,421 items) in 2 hours 57 minutes on the A10 GPU. The training loss converged to `6.765`, and the validation loss (`eval_loss`) settled at `6.626` (indicating steady generalization without overfitting). Final adapter checkpoints were successfully saved on the VM.

### Fixed
- **Missing PIL Import:** Added the missing `from PIL import Image` statement in `train_qwen_lora.py` to fix NameError crashes during batch compilation.
- **SSH Unicode Decoding Error:** Implemented `LANG=C.UTF-8` and `LC_ALL=C.UTF-8` environment variables during execution to prevent Hugging Face's model card generator from crashing on non-ASCII characters inside non-interactive SSH terminals.

### Added
- **Fresh MLX Fine-Tuning Run (160 Iterations):** Successfully completed a fresh 1-hour local training run (160 iterations) using MLX with `--max-seq-length 2048`. Loss decreased steadily from `11.77` to `6.98`, with final validation loss at `7.20`.
- **W&B Log Syncing:** Uploaded the offline training metrics for run `tvb70dd5` to the cloud Weights & Biases dashboard.
- **Adapter Checkpoints Created:** Saved progressive adapter checkpoints (`0000050`, `0000100`, `0000150`) and final `adapters.safetensors` under `Tanishq_Jewelry_Dataset_Final/qwen2.5_vl_lora_output_mlx/`.

### Added
- **Tokenization Caching to Google Drive:** Implemented pre-tokenization caching for Qwen2.5-VL training dataset splits using Hugging Face's `save_to_disk` and `load_from_disk`. This allows Google Colab and local training scripts to skip tokenization overhead on subsequent runs, loading the processed inputs in under 1 second.
- **Custom Batch Collator for Multimodal Tensors:** Created a robust `collate_fn` that dynamically pads token lists (`input_ids`, `attention_mask`, `labels`) and stacks/concatenates multimodal image patch inputs (`pixel_values`, `image_grid_thw`) along dimension 0. This bypasses the default SFTTrainer column removal crash and supports pre-tokenized inputs out-of-the-box.
- **3D Model Generation Pipeline:** Cloned Tencent Hunyuan3D-2 locally into the new `3D_model/` directory.
- **Local Mac Inference Support:** Created [local_generator.py](file:///Users/princegondaliya/Learning/Projects/Boostify/Projects/Gold_weight_prediction/3D_model/local_generator.py) to execute image-to-3D shape generation on local CPU/MPS devices.
- **API Fallback Generator:** Implemented [gradio_generator.py](file:///Users/princegondaliya/Learning/Projects/Boostify/Projects/Gold_weight_prediction/3D_model/gradio_generator.py) to trigger remote mesh generation via Hugging Face Gradio client.
- **Predefined Weights Calibration:** Researched and established mathematical scaling calculations for ring models to achieve >99% gold weight prediction precision.
- **Qwen2.5-VL Dataset Formatting:** Implemented [prepare_qwen_dataset.py](file:///Users/princegondaliya/Learning/Projects/Boostify/Projects/Gold_weight_prediction/Tanishq_Jewelry_Dataset_Final/prepare_qwen_dataset.py) to parse the unified catalog, validate 3,700+ local images, and output train/val conversational splits.
- **Qwen2.5-VL LoRA Training Template:** Created [train_qwen_lora.py](file:///Users/princegondaliya/Learning/Projects/Boostify/Projects/Gold_weight_prediction/scratch/train_qwen_lora.py) to enable custom visual SFT fine-tuning with transformers and PEFT/trl on cloud GPUs.
- **Hugging Face Version Support:** Added try/except fallback loaders for vision models supporting both transformers v4.x (`AutoModelForVision2Seq`) and v5.x (`AutoModelForImageTextToText` / `Qwen2_5_VLForConditionalGeneration`) to prevent training crashes on Google Colab runtimes.
- **Hugging Face Parameter Compatibility:** Changed `evaluation_strategy` to `eval_strategy` in `TrainingArguments` to align with the deprecation/removal of the old parameter name in `transformers` v5.0+.
- **TRL SFTTrainer Double PEFT Wrapper Fix:** Removed duplicate `peft_config` parameter from `SFTTrainer` to prevent double-wrapping errors when passing pre-wrapped QLoRA PEFT models.
- **Cross-Platform File Casing Fix:** Resolved a case-sensitivity mismatch between macOS and Google Colab Linux by dynamically matching filenames case-insensitively and writing the exact physical filesystem casing to the JSON splits, avoiding tokenization image-loading crashes.

### Changed
- **Cleaned Up Local Weights:** Removed the ~11 GB cached model checkpoints (`~/.cache/huggingface/hub/models--tencent--Hunyuan3D-2` and `~/.cache/hy3dgen`) because local M4 CPU/MPS inference took too long for active batch prediction.
- **Optimized Local Generator:** Enabled FlashVDM and set `num_inference_steps=20` for faster local generation in `local_generator.py`.

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
