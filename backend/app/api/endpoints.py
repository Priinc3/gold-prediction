from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.prediction import Prediction
from app.models.schemas import PredictionResponse, UnifiedPredictionResponse
from app.api.llm_utils import get_llm_prediction
from app.core.embeddings import get_clip_encoder
from app.db.chroma_client import get_vector_db
import json
import os
import uuid
from loguru import logger

router = APIRouter()

@router.post("/search", response_model=list[dict])
async def search_similar_rings(
    image: UploadFile = File(...)
):
    """
    RAG Endpoint: Send an image to find the top-5 visually similar rings 
    from the Tanishq dataset and previous predictions.
    """
    try:
        image_bytes = await image.read()
        clip = get_clip_encoder()
        vdb = get_vector_db()
        
        embedding = clip.get_image_embedding(image_bytes)
        similar_examples = vdb.query_similar(embedding)
        
        return similar_examples
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/predict", response_model=UnifiedPredictionResponse)
async def predict_gold_weight(
    ring_size: float = Form(None),
    inner_diameter_mm: float = Form(None),
    band_width_mm: float = Form(None),
    band_thickness_mm: float = Form(None),
    stone_length_mm: float = Form(None),
    stone_width_mm: float = Form(None),
    stone_ct: float = Form(None),
    side_stone_count: int = Form(0),
    side_stone_ct: float = Form(0.0),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    # Save image
    os.makedirs("data/images", exist_ok=True)
    image_ext = os.path.splitext(image.filename)[1]
    image_filename = f"{uuid.uuid4()}{image_ext}"
    image_path = f"data/images/{image_filename}"
    
    image_bytes = await image.read()
    with open(image_path, "wb") as f:
        f.write(image_bytes)
        
    params = {
        "ring_size": ring_size,
        "inner_diameter_mm": inner_diameter_mm,
        "band_width_mm": band_width_mm,
        "band_thickness_mm": band_thickness_mm,
        "stone_length_mm": stone_length_mm,
        "stone_width_mm": stone_width_mm,
        "stone_ct": stone_ct,
        "side_stone_count": side_stone_count,
        "side_stone_ct": side_stone_ct
    }
    
    try:
        logger.info("Starting prediction process...")
        # Phase 2: Vector Search
        clip = get_clip_encoder()
        vdb = get_vector_db()
        
        logger.info("Encoding image...")
        embedding = clip.get_image_embedding(image_bytes)
        
        logger.info("Querying similar rings...")
        similar_examples = vdb.query_similar(embedding)
        
        logger.info(f"Retrieved {len(similar_examples)} similar examples from Vector DB")
        
        # Fetch dynamic settings from DB
        logger.info("Fetching system settings...")
        from sqlalchemy import select
        from app.models.settings import SystemSetting
        stmt = select(SystemSetting)
        result = await db.execute(stmt)
        config = {s.key: s.value for s in result.scalars().all()}

        # Call LLM with retrieved examples and config
        logger.info(f"Calling LLM ({config.get('default_llm', 'default')})...")
        prediction_data = await get_llm_prediction(image_bytes, params, config, similar_examples)
        
        logger.info("Saving prediction to database...")
        # Save to SQL DB
        new_prediction = Prediction(
            **params,
            image_path=image_path,
            predicted_weight_14k=prediction_data["predicted_weight_14k"],
            predicted_weight_18k=prediction_data["predicted_weight_18k"],
            llm_explanation=prediction_data["explanation"],
            raw_response={
                "llm_raw": prediction_data["raw"],
                "rag_results": similar_examples
            }
        )
        
        db.add(new_prediction)
        await db.commit()
        await db.refresh(new_prediction)
        
        logger.info(f"Prediction saved with ID: {new_prediction.id}")
        
        # Phase 2: Add to Vector DB for future retrieval (only if prediction succeeded)
        if prediction_data["predicted_weight_14k"] > 0:
            chroma_metadata = {k: v for k, v in params.items() if v is not None}
            chroma_metadata.update({
                "predicted_weight_14k": float(prediction_data["predicted_weight_14k"]),
                "predicted_weight_18k": float(prediction_data["predicted_weight_18k"])
            })

            vdb.add_prediction(
                prediction_id=str(new_prediction.id),
                embedding=embedding,
                metadata=chroma_metadata
            )
        else:
            logger.warning("Prediction weight is 0.0, skipping Vector DB update.")
        
        # Return prediction + RAG results
        return {
            "prediction": new_prediction,
            "similar_examples": similar_examples
        }
        
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history", response_model=list[PredictionResponse])
async def get_prediction_history(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Prediction).order_by(Prediction.created_at.desc()))
    return result.scalars().all()
