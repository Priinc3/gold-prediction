from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class PredictionCreate(BaseModel):
    ring_size: Optional[float] = None
    inner_diameter_mm: Optional[float] = None
    band_width_mm: Optional[float] = None
    band_thickness_mm: Optional[float] = None
    stone_length_mm: Optional[float] = None
    stone_width_mm: Optional[float] = None
    stone_ct: Optional[float] = None
    side_stone_count: Optional[int] = 0
    side_stone_ct: Optional[float] = 0.0

class PredictionResponse(BaseModel):
    id: int
    predicted_weight_14k: float
    predicted_weight_18k: float
    llm_explanation: Optional[str] = None
    created_at: datetime
    image_path: Optional[str] = None

    class Config:
        from_attributes = True

class SimilarExample(BaseModel):
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    params: Dict[str, Any]
    actual_weight: float
    score: float

class UnifiedPredictionResponse(BaseModel):
    prediction: PredictionResponse
    similar_examples: List[SimilarExample]
