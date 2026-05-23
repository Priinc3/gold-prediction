from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.prediction import Prediction
from app.models.schemas import PredictionResponse, UnifiedPredictionResponse, VerifiedDesignCreate, VerifiedDesignResponse, PredictionFeedback
from app.api.llm_utils import get_llm_prediction, GOLD_DENSITIES
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

from typing import List

@router.post("/predict", response_model=UnifiedPredictionResponse)
async def predict_gold_weight(
    ring_size: float = Form(None),
    ring_size_standard: str = Form("Indian"), # New: Ring size standard selection
    target_sizes: str = Form("[]"), # New: JSON string of numbers [5, 6, 7]
    inner_diameter_mm: float = Form(None),
    band_width_mm: float = Form(None),
    band_thickness_mm: float = Form(None),
    stone_length_mm: float = Form(None),
    stone_width_mm: float = Form(None),
    stone_ct: float = Form(None),
    side_stone_count: int = Form(0),
    side_stone_ct: float = Form(0.0),
    images: List[UploadFile] = File(default=[]), # Modified: Default to empty list
    image_url: str = Form(None), # New: Optional image URL form parameter
    db: AsyncSession = Depends(get_db)
):
    # Parse target_sizes
    import json
    try:
        requested_sizes = json.loads(target_sizes)
        if not isinstance(requested_sizes, list):
            requested_sizes = []
    except:
        requested_sizes = []

    # Save images and/or download image from URL
    os.makedirs("data/images", exist_ok=True)
    image_paths = []
    all_image_bytes = []
    
    # Process uploaded local images
    for img_file in images[:3]: # Limit to 3 images
        if img_file.filename: # Ensure filename is not empty (browser artifact)
            image_ext = os.path.splitext(img_file.filename)[1]
            if not image_ext:
                continue
            image_filename = f"{uuid.uuid4()}{image_ext}"
            image_path = f"data/images/{image_filename}"
            
            content = await img_file.read()
            if not content:
                continue
            all_image_bytes.append(content)
            with open(image_path, "wb") as f:
                f.write(content)
            image_paths.append(image_path)
            
    # Process image URL if provided
    if image_url:
        logger.info(f"Downloading image from URL: {image_url}")
        try:
            import httpx
            from PIL import Image
            import io
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            async with httpx.AsyncClient() as client:
                response = await client.get(image_url, headers=headers, timeout=12.0)
                if response.status_code != 200:
                    raise HTTPException(status_code=400, detail=f"Failed to fetch image from URL: HTTP {response.status_code}")
                content = response.content
                
                # Validate it's a real, parseable image
                try:
                    img = Image.open(io.BytesIO(content))
                    img.verify()
                except Exception as img_err:
                    raise HTTPException(status_code=400, detail="The URL does not point to a valid image file.")
                
                # Guess extension based on content type or URL path
                image_ext = ".jpg"
                content_type = response.headers.get("content-type", "").lower()
                if "png" in content_type:
                    image_ext = ".png"
                elif "webp" in content_type:
                    image_ext = ".webp"
                elif "jpeg" in content_type or "jpg" in content_type:
                    image_ext = ".jpg"
                else:
                    _, url_ext = os.path.splitext(image_url.split("?")[0])
                    if url_ext.lower() in [".png", ".jpg", ".jpeg", ".webp"]:
                        image_ext = url_ext.lower()
                
                image_filename = f"{uuid.uuid4()}{image_ext}"
                image_path = f"data/images/{image_filename}"
                with open(image_path, "wb") as f:
                    f.write(content)
                
                # Append to lists
                all_image_bytes.append(content)
                image_paths.append(image_path)
                logger.info(f"Successfully downloaded and saved URL image to {image_path}")
        except HTTPException as he:
            raise he
        except Exception as e:
            logger.error(f"Failed to fetch image URL: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to download image from the provided URL. Error: {str(e)}")

    if not all_image_bytes:
        raise HTTPException(status_code=400, detail="Please upload at least one image file or provide a valid image URL.")
        
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
        logger.info(f"Starting prediction process with {len(all_image_bytes)} images...")
        # Phase 2: Vector Search
        clip = get_clip_encoder()
        vdb = get_vector_db()
        
        logger.info("Encoding primary image...")
        # We use the first image for visual RAG
        embedding = clip.get_image_embedding(all_image_bytes[0])
        
        logger.info("Querying similar rings...")
        similar_examples = vdb.query_similar(embedding)
        
        # Inject Volume into examples if missing (for legacy data)
        for ex in similar_examples:
            if "actual_volume_mm3" not in ex:
                density = GOLD_DENSITIES.get(ex.get("karat", "18K").upper(), GOLD_DENSITIES["18K"])
                ex["actual_volume_mm3"] = ex["actual_weight"] / density
            # Ensure ring_size is explicitly handled
            ex["base_ring_size"] = ex.get("params", {}).get("ring_size") or 7.0

        logger.info(f"Retrieved {len(similar_examples)} similar examples from Vector DB")
        for i, ex in enumerate(similar_examples):
            logger.debug(f"Example {i}: ID={ex.get('product_id')}, Name={ex.get('product_name')}")
        
        # Fetch dynamic settings from DB
        logger.info("Fetching system settings...")
        from sqlalchemy import select
        from app.models.settings import SystemSetting
        stmt = select(SystemSetting)
        result = await db.execute(stmt)
        config = {s.key: s.value for s in result.scalars().all()}

        # Call LLM with all images
        logger.info(f"Calling LLM ({config.get('default_llm', 'default')})...")
        # NOTE: get_llm_prediction must be updated to handle List[bytes]
        prediction_data = await get_llm_prediction(all_image_bytes, params, config, similar_examples, ring_size_standard)
        
        # Phase 3: Mathematical Size Scaling
        size_variations = []
        base_vol = prediction_data.get("estimated_volume_mm3", 0)
        
        from app.api.llm_utils import scale_volume_for_size
        
        for t_size in requested_sizes:
            scaled_vol = scale_volume_for_size(base_vol, ring_size, t_size, ring_size_standard)
            size_variations.append({
                "ring_size": float(t_size),
                "volume_mm3": float(scaled_vol),
                "weight_14k": float(scaled_vol * GOLD_DENSITIES["14K"]),
                "weight_18k": float(scaled_vol * GOLD_DENSITIES["18K"]),
                "weight_22k": float(scaled_vol * GOLD_DENSITIES["22K"])
            })

        logger.info("Saving prediction to database...")
        # Save to SQL DB (store first image path as primary)
        new_prediction = Prediction(
            **params,
            image_path=image_paths[0],
            estimated_volume_mm3=prediction_data.get("estimated_volume_mm3"),
            predicted_weight_14k=prediction_data["predicted_weight_14k"],
            predicted_weight_18k=prediction_data["predicted_weight_18k"],
            min_weight_14k=prediction_data.get("min_weight_14k"),
            max_weight_14k=prediction_data.get("max_weight_14k"),
            min_weight_18k=prediction_data.get("min_weight_18k"),
            max_weight_18k=prediction_data.get("max_weight_18k"),
            min_weight_22k=prediction_data.get("min_weight_22k"),
            max_weight_22k=prediction_data.get("max_weight_22k"),
            llm_explanation=prediction_data["explanation"],
            size_variations=size_variations,
            raw_response={
                "llm_raw": prediction_data["raw"],
                "rag_results": similar_examples
            }
        )
        
        db.add(new_prediction)
        await db.commit()
        await db.refresh(new_prediction)

        # Return prediction + RAG results
        return {
            "prediction": new_prediction,
            "similar_examples": similar_examples
        }
    except Exception as e:
        logger.error(f"Prediction failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/feedback")
async def submit_prediction_feedback(
    feedback: PredictionFeedback,
    db: AsyncSession = Depends(get_db)
):
    """
    User feedback endpoint: Converts actual weight to volume/density 
    and updates the Vector DB for better future RAG accuracy.
    """
    try:
        from sqlalchemy import select
        result = await db.execute(select(Prediction).where(Prediction.id == feedback.prediction_id))
        prediction = result.scalar_one_or_none()

        if not prediction:
            raise HTTPException(status_code=404, detail="Prediction not found")

        # 1. Update SQL record if weight provided
        if feedback.actual_weight_g and feedback.actual_karat:
            # Capture ALL data before commit to avoid expired object issues in async session
            image_path = prediction.image_path
            prediction_id = prediction.id
            p_ring_size = prediction.ring_size
            p_stone_ct = prediction.stone_ct
            p_side_stone_count = prediction.side_stone_count
            
            density = GOLD_DENSITIES.get(feedback.actual_karat.upper(), GOLD_DENSITIES["18K"])
            actual_volume = feedback.actual_weight_g / density

            # Use specific log field or update existing (simplified for now)
            prediction.llm_explanation += f"\n\n[USER FEEDBACK]: Actual weight {feedback.actual_weight_g}g ({feedback.actual_karat})."
            await db.commit()

            # 2. Re-encode and update Vector DB with CORRECT data
            # This makes the "memory" much more accurate
            if image_path and os.path.exists(image_path):
                with open(image_path, "rb") as f:
                    image_bytes = f.read()

                clip = get_clip_encoder()
                vdb = get_vector_db()
                embedding = clip.get_image_embedding(image_bytes)

                vdb.add_prediction(
                    prediction_id=str(prediction_id),
                    embedding=embedding,
                    metadata={
                        "product_id": f"fb_{prediction_id}",
                        "product_name": f"Feedback-Corrected-{prediction_id}",
                        "actual_weight_g": feedback.actual_weight_g,
                        "actual_volume_mm3": actual_volume,
                        "karat": feedback.actual_karat,
                        "diamond_weight_carats": feedback.actual_diamond_carat,
                        "ring_size": p_ring_size,
                        "stone_ct": p_stone_ct,
                        "side_stone_count": p_side_stone_count,
                        "is_verified": True
                    }
                )
                logger.info(f"Updated Vector DB with user feedback for prediction {prediction_id}")

        return {"status": "success", "message": "Feedback recorded and indexed"}
    except Exception as e:
        logger.error(f"Feedback submission failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=list[PredictionResponse])
async def get_prediction_history(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    result = await db.execute(select(Prediction).order_by(Prediction.created_at.desc()))
    return result.scalars().all()

@router.delete("/rag/{item_id}")
async def delete_rag_item(item_id: str):
    """Removes an item from the Vector DB (Pinecone/Chroma) memory."""
    logger.info(f"Received request to delete RAG item: '{item_id}'")
    try:
        vdb = get_vector_db()
        vdb.delete_by_id(item_id)
        return {"status": "success", "message": f"Item {item_id} removed from memory"}
    except Exception as e:
        logger.error(f"Failed to delete RAG item: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest", response_model=VerifiedDesignResponse)
async def ingest_verified_design(
    product_name: str = Form(...),
    karat: str = Form(...), # e.g. "18K", "14K"
    actual_weight_g: float = Form(...),
    ring_size: float = Form(None),
    stone_ct: float = Form(0.0),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
):
    """Adds a verified design to the training pool (RAG)."""
    # 1. Save Image
    os.makedirs("data/images", exist_ok=True)
    image_filename = f"{uuid.uuid4()}{os.path.splitext(image.filename)[1]}"
    image_path = os.path.join("data/images", image_filename)
    image_bytes = await image.read()
    
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    # 2. Calculate Volume from Weight/Karat (for internal reference)
    density = GOLD_DENSITIES.get(karat.upper(), GOLD_DENSITIES["18K"])
    estimated_volume = actual_weight_g / density

    # 3. Save to SQL
    from app.models.prediction import VerifiedDesign
    new_design = VerifiedDesign(
        product_name=product_name,
        karat=karat,
        actual_weight_g=actual_weight_g,
        estimated_volume_mm3=estimated_volume,
        ring_size=ring_size,
        stone_ct=stone_ct,
        image_path=image_path
    )
    db.add(new_design)
    await db.commit()
    await db.refresh(new_design)

    # 4. Add to Vector DB (RAG)
    clip = get_clip_encoder()
    vdb = get_vector_db()
    embedding = clip.get_image_embedding(image_bytes)
    
    vdb.add_prediction(
        prediction_id=f"verified_{new_design.id}",
        embedding=embedding,
        metadata={
            "product_id": f"v_{new_design.id}",
            "product_name": product_name,
            "actual_weight_g": actual_weight_g,
            "actual_volume_mm3": estimated_volume,
            "karat": karat,
            "ring_size": ring_size,
            "stone_ct": stone_ct
        }
    )

    return new_design
