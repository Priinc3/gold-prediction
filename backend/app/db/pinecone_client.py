from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings
from loguru import logger
import time
import json

# Density Mapping (g/mm3)
GOLD_DENSITIES = {
    "14K": 0.01307,
    "18K": 0.01558,
    "22K": 0.01750,
    "24K": 0.01930
}

class PineconeDB:
    def __init__(self):
        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY not set in environment")
            
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self.index_name = settings.PINECONE_INDEX_NAME
        
        # Check if index exists, create if not
        existing_indexes = [index.name for index in self.pc.list_indexes()]
        if self.index_name not in existing_indexes:
            logger.info(f"Creating Pinecone index: {self.index_name}")
            self.pc.create_index(
                name=self.index_name,
                dimension=512, # CLIP ViT-B-32 dimension
                metric="cosine",
                spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                )
            )
            # Wait for index to be ready
            while not self.pc.describe_index(self.index_name).status['ready']:
                time.sleep(1)
                
        self.index = self.pc.Index(self.index_name)
        logger.info(f"PineconeDB initialized with index {self.index_name}")

    def add_prediction(self, prediction_id: str, embedding: list, metadata: dict):
        import pandas as pd
        clean_metadata = {}
        for k, v in metadata.items():
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                clean_metadata[k] = v

        self.index.upsert(
            vectors=[{
                "id": str(prediction_id),
                "values": embedding,
                "metadata": clean_metadata
            }]
        )
        logger.info(f"Added record {prediction_id} to Pinecone")

    def query_similar(self, embedding: list, n_results: int = 5):
        results = self.index.query(
            vector=embedding,
            top_k=n_results,
            include_metadata=True
        )
        
        formatted = []
        for match in results['matches']:
            meta = match['metadata']
            
            # Priority 1: Use actual_volume_mm3 (Density-Independent)
            # Priority 2: Calculate from weight and karat
            volume = meta.get("actual_volume_mm3")
            weight = meta.get("actual_weight_g") or meta.get("predicted_weight_14k")
            karat = str(meta.get("karat", "18K")).upper()
            stone_ct = meta.get("diamond_weight_carats") or meta.get("stone_ct") or 0.0

            if volume is None and weight is not None:
                density = GOLD_DENSITIES.get(karat, GOLD_DENSITIES["18K"])
                volume = weight / density
            
            formatted.append({
                "product_id": meta.get("product_id"),
                "product_name": meta.get("product_name", "Unknown Ring"),
                "params": {
                    "ring_size": meta.get("ring_size"),
                    "stone_ct": stone_ct,
                    "side_stone_count": meta.get("side_stone_count", 0),
                    "metal_color": meta.get("metal_color"),
                    "karat": karat
                },
                "actual_weight": weight,
                "actual_volume_mm3": volume,
                "score": match['score']
            })
        return formatted
