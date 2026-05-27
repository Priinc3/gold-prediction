from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.settings import SystemSetting
from pydantic import BaseModel
from typing import Dict, Optional
from app.core.config import settings as app_settings
from loguru import logger

router = APIRouter()

class SettingsUpdate(BaseModel):
    default_llm: str
    gemini_model: str = "gemini-2.5-flash"
    anthropic_api_key: str = ""
    gemini_api_key: str = ""
    pinecone_api_key: str = ""
    pinecone_index_name: str = ""
    pinecone_index_host: str = ""
    password: str = ""

def mask_key(key: str) -> str:
    if not key or len(key) < 10:
        return "••••••••" if key else ""
    return f"{key[:6]}••••••••{key[-4:]}"

@router.get("/settings")
async def get_system_settings(
    password: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(SystemSetting))
    db_settings = {s.key: s.value for s in result.scalars().all()}
    
    gemini_key = db_settings.get("gemini_api_key", app_settings.GEMINI_API_KEY or "")
    anthropic_key = db_settings.get("anthropic_api_key", app_settings.ANTHROPIC_API_KEY or "")
    pinecone_key = db_settings.get("pinecone_api_key", app_settings.PINECONE_API_KEY or "")
    
    is_authorized = (password == "774623")
    
    return {
        "default_llm": db_settings.get("default_llm", app_settings.DEFAULT_LLM),
        "gemini_model": db_settings.get("gemini_model", getattr(app_settings, "GEMINI_MODEL", "gemini-2.5-flash")),
        
        # Mask keys if not authorized with password 774623
        "gemini_api_key": gemini_key if is_authorized else mask_key(gemini_key),
        "anthropic_api_key": anthropic_key if is_authorized else mask_key(anthropic_key),
        "pinecone_api_key": pinecone_key if is_authorized else mask_key(pinecone_key),
        
        "pinecone_index_name": db_settings.get("pinecone_index_name", app_settings.PINECONE_INDEX_NAME or ""),
        "pinecone_index_host": db_settings.get("pinecone_index_host", app_settings.PINECONE_INDEX_HOST or ""),
        
        "has_anthropic": bool(anthropic_key),
        "has_gemini": bool(gemini_key),
        "has_pinecone": bool(pinecone_key),
        "is_authorized": is_authorized
    }

@router.post("/settings")
async def update_system_settings(update: SettingsUpdate, db: AsyncSession = Depends(get_db)):
    if update.password != "774623":
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid Admin Password")
        
    settings_dict = update.dict()
    # Remove password from dict so it's not stored in DB
    settings_dict.pop("password", None)
    
    for key, value in settings_dict.items():
        # Skip updating API keys if they are submitted as masked values
        if "••••" in value:
            logger.info(f"Skipping update for masked key: {key}")
            continue
            
        # Get existing or create new
        stmt = select(SystemSetting).where(SystemSetting.key == key)
        result = await db.execute(stmt)
        db_setting = result.scalar_one_or_none()
        
        if db_setting:
            db_setting.value = value
        else:
            db_setting = SystemSetting(key=key, value=value)
            db.add(db_setting)
            
    await db.commit()
    return {"message": "Settings updated successfully"}

