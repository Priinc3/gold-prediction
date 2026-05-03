# AWS Deployment Guide — Gold Weight Prediction System

This guide outlines the exact steps to deploy and maintain the high-accuracy visual RAG system on an AWS EC2 instance.

## 1. Instance Configuration (Recommended)
- **AMI:** Ubuntu 24.04 LTS
- **Instance Type:** `t3.medium` (4GB RAM) or higher. 
- **Storage:** 30GB+ (CLIP models and datasets are large).
- **Swapfile:** Mandatory for PyTorch (CLIP) memory spikes on 4GB RAM.

```bash
# Setup 4GB Swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

## 2. Environment Setup (Miniconda)
Python 3.11 is the current stable version for `torchvision` compatibility on EC2.

```bash
# Install Miniconda
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
bash Miniconda3-latest-Linux-x86_64.sh -b -p $HOME/miniconda

# Create Environment
$HOME/miniconda/bin/conda create -n gold python=3.11 -y
source $HOME/miniconda/bin/activate gold

# Install Dependencies
pip install fastapi uvicorn torch torchvision clip-by-openai pinecone-client loguru python-multipart pydantic-settings sqlalchemy aiosqlite pandas google-generativeai
```

## 3. Backend Deployment
The backend serves both the API and the static frontend files.

- **Directory Structure:**
  - `~/gold-prediction/backend/`
  - `~/gold-prediction/backend/static/` (Vite build folder)

- **Execution:**
  Use the `start.sh` script to run the server in the background.
  ```bash
  cd ~/gold-prediction/backend
  chmod +x start.sh
  ./start.sh
  ```

## 4. Port & Networking
- **Port:** 8000
- **Security Group:** Ensure Port 8000 is open in the AWS Console.

## 5. Environment Variables (.env)
Required in `~/gold-prediction/backend/.env`:
```env
PROJECT_NAME=Gold Weight Prediction API
API_V1_STR=/api/v1
DATABASE_URL=sqlite+aiosqlite:///./gold_weight.db
GEMINI_API_KEY=your_key
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=ring-designs
VECTOR_DB_TYPE=pinecone
```

## 6. Common Troubleshooting
- **ModuleNotFoundError: pandas**: Run `pip install pandas`.
- **RuntimeError: operator torchvision::nms**: Ensure you are using Python 3.11 and the correct conda environment.
- **Connection Refused**: Check if uvicorn is running (`ps aux | grep uvicorn`) and if the `.env` file exists.
- **ChromaDB Error**: Ensure `VECTOR_DB_TYPE=pinecone` is set in `.env` if not using local storage.
