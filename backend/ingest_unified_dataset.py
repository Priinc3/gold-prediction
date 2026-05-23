#!/usr/bin/env python3
"""
Ingest the unified jewelry dataset (Tanishq + Orra) into Pinecone Vector DB using CLIP image embeddings.
"""

import os
import sys
import pandas as pd
from tqdm import tqdm
from PIL import Image
import numpy as np

# Add backend to sys.path
WORKSPACE = "/Users/princegondaliya/Learning/Projects/Boostify/Projects/Gold_weight_prediction"
sys.path.append(os.path.join(WORKSPACE, "backend"))

from app.core.embeddings import get_clip_encoder
from app.db.pinecone_client import PineconeDB

# Density Mapping (g/mm3) for Volume derivation
GOLD_DENSITIES = {
    "14K": 0.01307,
    "14KT": 0.01307,
    "18K": 0.01558,
    "18KT": 0.01558,
    "22K": 0.01750,
    "22KT": 0.01750,
    "24K": 0.01930,
    "24KT": 0.01930,
    "950PT": 0.02145 # Platinum density: 21.45 g/cm3 -> 0.02145 g/mm3
}

def ingest():
    csv_path = os.path.join(WORKSPACE, "Tanishq_Jewelry_Dataset_Final/unified_jewelry_dataset.csv")
    if not os.path.exists(csv_path):
        print(f"❌ Error: {csv_path} not found. Run combined dataset script first.")
        return

    print(f"📖 Loading unified dataset from {csv_path}...")
    df = pd.read_csv(csv_path)
    
    print("🧠 Loading CLIP encoder...")
    encoder = get_clip_encoder()
    
    print("🌲 Connecting to Pinecone DB...")
    vdb = PineconeDB()

    print(f"🚀 Starting ingestion of {len(df)} products...")
    success_count = 0
    skip_count = 0
    error_count = 0

    for idx, row in tqdm(df.iterrows(), total=len(df)):
        # 1. Parse primary image path
        local_paths_str = row.get('local_image_paths')
        if not isinstance(local_paths_str, str) or not local_paths_str.strip():
            skip_count += 1
            continue
            
        image_paths = [p.strip() for p in local_paths_str.split('|') if p.strip()]
        if not image_paths:
            skip_count += 1
            continue
            
        primary_image_path = os.path.join(WORKSPACE, image_paths[0])
        
        # Check if local file exists
        if not os.path.exists(primary_image_path):
            # Try a absolute fallback
            if os.path.exists(image_paths[0]):
                primary_image_path = image_paths[0]
            else:
                skip_count += 1
                continue

        try:
            # 2. Load primary image and generate embedding
            with open(primary_image_path, "rb") as f:
                img_bytes = f.read()
                
            embedding = encoder.get_image_embedding(img_bytes)
            
            # 3. Derive volume
            weight = float(row['metal_weight_grams'])
            purity = str(row['metal_purity']).upper()
            density = GOLD_DENSITIES.get(purity, GOLD_DENSITIES["18K"])
            volume = weight / density

            # Helper to safely serialize float values (avoiding NaN in Pinecone)
            def safe_float(val):
                if pd.isna(val) or val is None or np.isnan(val):
                    return None
                return float(val)

            # Helper to safely serialize string values
            def safe_str(val):
                if pd.isna(val) or val is None:
                    return None
                return str(val).strip()

            # 4. Prepare metadata
            metadata = {
                "product_id": safe_str(row['product_id']),
                "product_name": safe_str(row['product_name']),
                "source": safe_str(row['source']),
                "actual_weight_g": safe_float(row['metal_weight_grams']),
                "actual_volume_mm3": safe_float(volume),
                "karat": safe_str(row['metal_purity']),
                "metal_color": safe_str(row['metal_color']),
                "metal_type": safe_str(row['metal_type']),
                "price_inr": safe_float(row['price_inr']),
                "stone_type": safe_str(row['stone_type']),
                
                "diamond_weight_carats": safe_float(row['diamond_weight_ct']),
                "diamond_pcs": safe_float(row['diamond_pcs']),
                "diamond_value_inr": safe_float(row['diamond_value_inr']),
                "diamond_shape": safe_str(row['diamond_shape']),
                
                "ring_size": safe_float(row['ring_size_us']),  # Mapped to 'ring_size' for legacy frontend lookups
                "ring_size_us": safe_float(row['ring_size_us']),
                "gender": safe_str(row['gender']),
                "style": safe_str(row['style']),
                "making_charges": safe_float(row['making_charges']),
                "gross_weight_grams": safe_float(row['gross_weight_grams']),
                "image_url": safe_str(row['image_url'])
            }
            
            # 5. Add to Pinecone Vector DB
            # We use the product_id as the Pinecone vector ID
            vdb.add_prediction(
                prediction_id=str(row['product_id']),
                embedding=embedding,
                metadata=metadata
            )
            success_count += 1
            
        except Exception as e:
            error_count += 1
            # print(f"Error processing {row['product_id']}: {e}")

    print("\n📊 Ingestion Summary:")
    print(f"  - Successfully Ingested: {success_count}")
    print(f"  - Skipped (Missing Image): {skip_count}")
    print(f"  - Errors: {error_count}")
    print("🎉 Ingestion execution finished.")

if __name__ == "__main__":
    ingest()
