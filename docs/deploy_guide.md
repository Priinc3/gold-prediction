# Deployment Guide — Gold Weight Prediction

This is the current working deployment setup. Use this instead of old notes.

## Current Production

- Frontend source folder: `frontend/`
- Frontend URL: `https://gold-weight-frontend.vercel.app`
- Backend source folder: `backend/`
- Backend server: `http://13.207.220.204:8000`
- Backend remote path: `~/gold-prediction/backend`
- Backend runtime: Miniconda env `gold`, Python `3.11`
- API proxy: frontend calls `/api/v1/*`, Vercel rewrites to `http://13.207.220.204:8000/api/v1/*`
- Vector DB: Pinecone `ring-designs-v3`
- Pinecone vector dimension: `512`
- Embedding model: OpenCLIP `ViT-B-32`, pretrained `laion2b_s34b_b79k`

## Important: Backend Choice

Use `backend/` for production.

Do not deploy `backend_aws/` for the current RAG system.

Reason:

- `backend/` uses CLIP embeddings, dimension `512`.
- The populated Pinecone index `ring-designs-v3` is dimension `512`.
- `backend_aws/` uses Gemini embeddings, dimension `3072`.
- Deploying `backend_aws/` against `ring-designs-v3` causes:

```text
[400] Vector dimension 3072 does not match the dimension of the index 512
```

## Important: Frontend Choice

Use `frontend/` for production.

Do not deploy `frontend_aws/` unless intentionally testing the older AWS-specific UI.

Current frontend project:

```text
https://gold-weight-frontend.vercel.app
```

Old frontend project:

```text
https://frontendaws.vercel.app
```

The old project may still exist, but the correct active frontend is `frontend/`.

## Pinecone Configuration

Production `.env` must include:

```env
VECTOR_DB_TYPE=pinecone
PINECONE_INDEX_NAME=ring-designs-v3
PINECONE_INDEX_HOST=https://ring-designs-v3-23qsnml.svc.aped-4627-b74a.pinecone.io
```

`ring-designs-v3` is the populated 512-dim CLIP RAG index. It was verified with Pinecone stats and contained `1614` vectors at verification time.

## Backend Deploy Steps

From project root:

```bash
chmod 600 imagera.pem
```

Package only backend code, not image uploads, Chroma DB, node modules, or model artifacts:

```bash
tar --exclude='__pycache__' \
  --exclude='.DS_Store' \
  --exclude='backend/data/images' \
  --exclude='backend/data/chroma_db' \
  -czf /tmp/backend_clip_deploy.tgz backend .env
```

Upload package:

```bash
scp -i imagera.pem /tmp/backend_clip_deploy.tgz ubuntu@13.207.220.204:~/gold-prediction/backend_clip_deploy.tgz
```

Replace backend on EC2:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "rm -rf ~/gold-prediction/backend && \
   mkdir -p ~/gold-prediction && \
   tar xzf ~/gold-prediction/backend_clip_deploy.tgz -C ~/gold-prediction && \
   cp ~/gold-prediction/.env ~/gold-prediction/backend/.env"
```

Confirm the backend is the CLIP backend:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "cd ~/gold-prediction/backend && grep -n 'get_clip_encoder\|embedding_manager' app/api/endpoints.py app/core/embeddings.py | head -20"
```

Expected output should include `get_clip_encoder`. It should not include `embedding_manager` in `endpoints.py`.

## Backend Runtime Setup

Use Python 3.11, not system Python 3.14.

Install Miniconda if missing:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "test -x ~/miniconda/bin/conda || { \
     wget -q https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \
     bash /tmp/miniconda.sh -b -p \$HOME/miniconda; \
   }"
```

Accept Anaconda channel ToS if needed:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "~/miniconda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/main || true; \
   ~/miniconda/bin/conda tos accept --override-channels --channel https://repo.anaconda.com/pkgs/r || true"
```

Create env:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "~/miniconda/bin/conda create -n gold python=3.11 -y"
```

Install dependencies using CPU-only Torch wheels:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "cd ~/gold-prediction && \
   ~/miniconda/envs/gold/bin/pip install --extra-index-url https://download.pytorch.org/whl/cpu -r backend/requirements.txt"
```

`backend/requirements.txt` must pin CPU Torch like this:

```text
torch==2.4.1+cpu
torchvision==0.19.1+cpu
open-clip-torch==2.26.1
```

Do not let pip install default Linux CUDA Torch on the small EC2 root disk. It can fill the disk.

## Start Backend

Stop old process:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "pkill -f 'uvicorn app.main:app' || true"
```

Start backend:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "cd ~/gold-prediction/backend && \
   nohup ~/miniconda/envs/gold/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 > backend.log 2>&1 &"
```

Check process:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "ps -eo pid,ppid,pcpu,pmem,etime,cmd | grep -E 'uvicorn|python -m uvicorn' | grep -v grep"
```

Check logs:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "cd ~/gold-prediction/backend && tail -120 backend.log"
```

First startup can take 15-30 seconds because CLIP model loads.

Expected startup log:

```text
Pre-loading CLIP model for faster predictions...
Loading CLIP model ViT-B-32 on cpu...
CLIP model loaded successfully.
Application startup complete.
```

## Frontend Deploy Steps

Frontend config:

```ts
// frontend/src/config.ts
export const API_BASE_URL = "/api/v1";
```

Vercel rewrite:

```json
// frontend/vercel.json
{
  "rewrites": [
    {
      "source": "/api/v1/:path*",
      "destination": "http://13.207.220.204:8000/api/v1/:path*"
    }
  ]
}
```

Ignore local build/dependency junk:

```text
// frontend/.vercelignore
node_modules
dist
.vercel
.env.local
```

Deploy only `frontend/`:

```bash
cd frontend
rm -rf .vercel
npx vercel --prod --yes --name gold-weight-frontend
```

Expected production alias:

```text
https://gold-weight-frontend.vercel.app
```

The upload should be small. Last successful deploy uploaded about `43KB`. If Vercel tries uploading GBs, you are deploying from the repo root or including datasets/model files by mistake.

## Verification Commands

Backend direct:

```bash
curl -sS http://13.207.220.204:8000/api/v1/settings
```

Frontend proxy:

```bash
curl -sS https://gold-weight-frontend.vercel.app/api/v1/settings
```

Expected settings include:

```json
{
  "pinecone_index_name": "ring-designs-v3",
  "has_pinecone": true,
  "has_gemini": true
}
```

RAG search smoke test:

```bash
curl -sS --max-time 60 \
  -F "image=@Images/ring.png" \
  http://13.207.220.204:8000/api/v1/search
```

Expected: JSON list with 5 similar examples.

Full prediction smoke test:

```bash
curl -sS --max-time 120 \
  -F "images=@Images/ring.png" \
  -F "ring_size=7" \
  -F "ring_size_standard=US" \
  -F "target_sizes=[]" \
  -F "stone_ct=1" \
  http://13.207.220.204:8000/api/v1/predict
```

Expected: JSON with `prediction` and `similar_examples`.

Feedback smoke test:

```bash
curl -sS --max-time 60 \
  -X POST https://gold-weight-frontend.vercel.app/api/v1/feedback \
  -H 'Content-Type: application/json' \
  -d '{"prediction_id":154,"is_correct":false,"actual_weight_g":10.2,"actual_karat":"18K","actual_diamond_carat":0}'
```

Expected:

```json
{"status":"success","message":"Feedback recorded and indexed"}
```

## Common Problems

### `Vector dimension 3072 does not match 512`

Wrong backend deployed.

Fix: deploy `backend/`, not `backend_aws/`.

### `/feedback` returns 500

Check logs:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 "cd ~/gold-prediction/backend && tail -120 backend.log"
```

Known fixed issue:

```text
Feedback submission failed: No module named 'pandas'
```

Fix is in `backend/app/db/pinecone_client.py`: use `math.isnan`, not `pandas.isna`, for metadata cleanup.

### Frontend shows API JSON instead of UI

You opened backend URL directly:

```text
http://13.207.220.204:8000
```

Use frontend URL:

```text
https://gold-weight-frontend.vercel.app
```

### Prediction takes too long

CLIP and Pinecone are fast after startup. Logs showed Gemini calls take most of the time, typically 15-38 seconds.

Do not change Gemini unless explicitly requested.

### Server disk full

Check disk:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 "df -h /"
```

Clean failed environments/cache:

```bash
ssh -i imagera.pem ubuntu@13.207.220.204 \
  "rm -rf ~/miniconda/envs/gold ~/miniconda/pkgs ~/.cache/pip ~/gold-prediction/venv"
```

Then recreate env with CPU-only Torch install.

## Security Notes

- Do not print `.env` or private keys in chat/logs.
- Rotate keys if exposed.
- `imagera.pem` must be `chmod 600`.
- `/api/v1/settings` masks secrets unless admin password is supplied.
- Avoid committing `.env`, `.pem`, `.vercel/.env.local`, or tokens.
