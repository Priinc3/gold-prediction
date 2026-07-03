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
        
        # If direct host is provided, initialize using host bypass
        if getattr(settings, "PINECONE_INDEX_HOST", None):
            logger.info(f"Connecting directly to Pinecone host index: {settings.PINECONE_INDEX_HOST}")
            self.index = self.pc.Index(name=self.index_name, host=settings.PINECONE_INDEX_HOST)
        else:
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
        import math
        clean_metadata = {}
        for k, v in metadata.items():
            if v is not None and not (isinstance(v, float) and math.isnan(v)):
                clean_metadata[k] = v

        self.index.upsert(
            vectors=[{
                "id": str(prediction_id),
                "values": embedding,
                "metadata": clean_metadata
            }]
        )
        logger.info(f"Added record {prediction_id} to Pinecone")

    def delete_by_id(self, vector_id: str):
        self.index.delete(ids=[str(vector_id)])
        logger.info(f"Deleted record {vector_id} from Pinecone")

    def query_similar(self, embedding: list, n_results: int = 5):
        logger.info(f"Querying Pinecone index {self.index_name} for top {n_results} matches...")
        results = self.index.query(
            vector=embedding,
            top_k=n_results,
            include_metadata=True
        )
        
        formatted = []
        for match in results['matches']:
            # Handle both dict-like and object-like access
            m_id = getattr(match, 'id', None) or match.get('id')
            meta = getattr(match, 'metadata', {}) or match.get('metadata', {})
            score = getattr(match, 'score', 0) or match.get('score', 0)
            
            logger.debug(f"Pinecone Match - ID: {m_id}, Score: {score}")
            
            if not m_id:
                logger.warning(f"Found match without ID: {match}")
                continue

            # Core volume and weight alignment logic
            volume = meta.get("actual_volume_mm3")
            weight = meta.get("actual_weight_g")
            karat = str(meta.get("karat", "18K")).upper()
            
            # Align volume and standardized 18K weights for legacy index structure
            if volume is None:
                if "predicted_weight_18k" in meta:
                    weight_18k = float(meta["predicted_weight_18k"])
                    volume = weight_18k / GOLD_DENSITIES["18K"]
                    weight = weight_18k
                    karat = "18K"
                elif "predicted_weight_14k" in meta:
                    weight_14k = float(meta["predicted_weight_14k"])
                    volume = weight_14k / GOLD_DENSITIES["14K"]
                    weight = volume * GOLD_DENSITIES["18K"]
                    karat = "18K"

            # Enforce strict density alignment, treating weight as the physical source of truth
            if weight is not None:
                density = GOLD_DENSITIES.get(karat, GOLD_DENSITIES["18K"])
                volume = weight / density
            elif volume is not None:
                density = GOLD_DENSITIES.get(karat, GOLD_DENSITIES["18K"])
                weight = volume * density
            
            # Standardize visual RAG prompt anchors to 18K gold purity for LLM stability
            if karat != "18K" and volume is not None:
                weight = volume * GOLD_DENSITIES["18K"]
                karat = "18K"
                
            stone_ct = meta.get("diamond_weight_carats") or meta.get("stone_ct") or 0.0
            
            formatted.append({
                "product_id": str(m_id), 
                "product_name": meta.get("product_name", f"Ring #{m_id}"),
                "karat": karat,
                "params": {
                    "ring_size": meta.get("ring_size"),
                    "stone_ct": stone_ct,
                    "side_stone_count": meta.get("side_stone_count", 0),
                    "metal_color": meta.get("metal_color"),
                    "karat": karat
                },
                "actual_weight": weight,
                "actual_volume_mm3": volume,
                "score": float(score)
            })
        return formatted
