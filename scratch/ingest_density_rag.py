import pandas as pd
import os
import time
from pinecone import Pinecone, ServerlessSpec
from loguru import logger
import torch
import clip
from PIL import Image
from dotenv import load_dotenv

# Load env vars
load_dotenv("./backend/.env")

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX_NAME = "ring-designs-v2" # New index for density RAG

# CLIP Setup
device = "cuda" if torch.cuda.is_available() else "cpu"
model, preprocess = clip.load("ViT-B/32", device=device)

def get_image_embedding(image_path):
    try:
        image = preprocess(Image.open(image_path)).unsqueeze(0).to(device)
        with torch.no_grad():
            image_features = model.encode_image(image)
        return image_features.cpu().numpy().flatten().tolist()
    except Exception as e:
        logger.error(f"Error processing {image_path}: {e}")
        return None

def ingest_data():
    # Initialize Pinecone
    pc = Pinecone(api_key=PINECONE_API_KEY)
    
    # Create new index if not exists
    if PINECONE_INDEX_NAME not in [idx.name for idx in pc.list_indexes()]:
        logger.info(f"Creating new Pinecone index: {PINECONE_INDEX_NAME}")
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=512,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1")
        )
        while not pc.describe_index(PINECONE_INDEX_NAME).status['ready']:
            time.sleep(1)
            
    index = pc.Index(PINECONE_INDEX_NAME)
    
    # Load the density dataset
    df = pd.read_csv("./backend/data/tanishq_density_dataset.csv")
    
    logger.info(f"Starting ingestion of {len(df)} records...")
    
    batch_size = 50
    vectors = []
    
    for i, row in df.iterrows():
        # Map image path
        # CSV path: output/tanishq_images/uncategorized/51m5c1faumaa002ea000001_1.jpg
        # Local path: Tanishq_Jewelry_Dataset_Final/images/uncategorized/51m5c1faumaa002ea000001_1.jpg
        relative_path = row['local_image_paths'].split('|')[0] # Use first image
        filename = os.path.basename(relative_path)
        actual_path = f"./Tanishq_Jewelry_Dataset_Final/images/uncategorized/{filename}"
        
        if not os.path.exists(actual_path):
            continue
            
        embedding = get_image_embedding(actual_path)
        if embedding:
            meta = {
                "product_name": str(row['product_name']),
                "actual_weight_g": float(row['gold_weight_grams']),
                "actual_volume_mm3": float(row['design_volume_mm3']),
                "karat": str(row['gold_karat_purity']),
                "diamond_weight_carats": float(row['diamond_carat']),
                "is_verified": True
            }
            # Remove nulls/NaNs
            clean_meta = {k: v for k, v in meta.items() if v is not None and not (isinstance(v, float) and pd.isna(v))}
            
            vectors.append({
                "id": str(row['product_id']),
                "values": embedding,
                "metadata": clean_meta
            })
            
        if len(vectors) >= batch_size:
            index.upsert(vectors=vectors)
            logger.info(f"Upserted batch ending at row {i}")
            vectors = []
            
    if vectors:
        index.upsert(vectors=vectors)
        
    logger.info("Ingestion complete!")

if __name__ == "__main__":
    ingest_data()
