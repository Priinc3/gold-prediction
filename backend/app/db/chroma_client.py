from app.core.config import settings
from loguru import logger
import os

# Density Mapping (g/mm3)
GOLD_DENSITIES = {
    "14K": 0.01307,
    "18K": 0.01558,
    "22K": 0.01750,
    "24K": 0.01930
}

class ChromaDB:
    def __init__(self):
        import chromadb
        os.makedirs(settings.CHROMA_DB_PATH, exist_ok=True)
        self.client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        self.collection = self.client.get_or_create_collection(
            name="ring_designs",
            metadata={"hnsw:space": "cosine"}
        )
        logger.info(f"ChromaDB initialized at {settings.CHROMA_DB_PATH}")

    def add_prediction(self, prediction_id: str, embedding: list, metadata: dict):
        # Filter out None values for Chroma metadata
        clean_metadata = {k: v for k, v in metadata.items() if v is not None}
        self.collection.add(
            ids=[str(prediction_id)],
            embeddings=[embedding],
            metadatas=[clean_metadata]
        )
        logger.info(f"Added record {prediction_id} to ChromaDB")

    def delete_by_id(self, vector_id: str):
        self.collection.delete(ids=[str(vector_id)])
        logger.info(f"Deleted record {vector_id} from ChromaDB")

    def query_similar(self, embedding: list, n_results: int = 5):
        results = self.collection.query(
            query_embeddings=[embedding],
            n_results=n_results
        )
        
        formatted = []
        if results['metadatas'] and results['metadatas'][0]:
            for i, meta in enumerate(results['metadatas'][0]):
                m_id = results['ids'][0][i]
                score = float(results['distances'][0][i]) if results.get('distances') and results['distances'] else 0.0
                
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
                    "params": {
                        "ring_size": meta.get("ring_size"),
                        "stone_ct": stone_ct,
                        "side_stone_count": meta.get("side_stone_count", 0),
                        "metal_color": meta.get("metal_color"),
                        "karat": karat
                    },
                    "actual_weight": weight,
                    "actual_volume_mm3": volume,
                    "score": score
                })
        return formatted

# Singleton instance
vector_db = None

def get_vector_db():
    global vector_db
    if vector_db is None:
        if settings.VECTOR_DB_TYPE == "pinecone":
            from app.db.pinecone_client import PineconeDB
            vector_db = PineconeDB()
        else:
            vector_db = ChromaDB()
    return vector_db
