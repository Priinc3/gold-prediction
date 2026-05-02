from sqlalchemy import Column, Integer, Float, String, DateTime, JSON
from datetime import datetime
from app.db.session import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    ring_size = Column(Float, nullable=True)
    inner_diameter_mm = Column(Float, nullable=True)
    band_width_mm = Column(Float, nullable=True)
    band_thickness_mm = Column(Float, nullable=True)
    stone_length_mm = Column(Float, nullable=True)
    stone_width_mm = Column(Float, nullable=True)
    stone_ct = Column(Float, nullable=True)
    side_stone_count = Column(Integer, nullable=True)
    side_stone_ct = Column(Float, nullable=True)
    
    image_path = Column(String)
    
    predicted_weight_14k = Column(Float)
    predicted_weight_18k = Column(Float)
    
    llm_explanation = Column(String)
    raw_response = Column(JSON)
    
    created_at = Column(DateTime, default=datetime.utcnow)
