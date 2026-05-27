import base64
import json
from google import genai
from anthropic import Anthropic
from app.core.config import settings
from loguru import logger
from PIL import Image
import io
import os

# Density Mapping (g/mm3)
GOLD_DENSITIES = {
    "14K": 0.01307,
    "18K": 0.01558,
    "22K": 0.01750,
    "24K": 0.01930
}

# Indian Ring Size to Diameter (mm) Mapping (Sizes 1 to 30)
INDIAN_RING_SIZES = {
    1: 13.1, 2: 13.3, 3: 13.7, 4: 13.9, 5: 14.3,
    6: 14.7, 7: 15.1, 8: 15.3, 9: 15.5, 10: 15.9,
    11: 16.3, 12: 16.5, 13: 16.9, 14: 17.3, 15: 17.5,
    16: 17.9, 17: 18.1, 18: 18.5, 19: 18.8, 20: 19.2,
    21: 19.4, 22: 19.8, 23: 20.0, 24: 20.4, 25: 20.6,
    26: 21.0, 27: 21.4, 28: 21.6, 29: 22.0, 30: 22.3
}

def calculate_weights_from_volume(volume_mm3: float):
    """Calculates karat-specific weights from volume in mm3."""
    return {
        "gold14k_g": volume_mm3 * GOLD_DENSITIES["14K"],
        "gold18k_g": volume_mm3 * GOLD_DENSITIES["18K"],
        "gold22k_g": volume_mm3 * GOLD_DENSITIES["22K"]
    }

def get_diameter_for_size(size: float, standard: str = "Indian"):
    """Gets inner diameter (mm) based on standard (Indian or US)"""
    if not size:
        size = 12.0 if standard.lower() == "indian" else 7.0
        
    if standard.lower() == "indian":
        # Round to nearest integer for exact match
        idx = int(round(size))
        return INDIAN_RING_SIZES.get(idx, 16.5) # Default to Indian size 12
    else:
        # US Ring Size to Inner Diameter (mm)
        return (size * 0.8128) + 11.6332

def scale_volume_for_size(base_volume: float, base_size: float, target_size: float, standard: str = "Indian"):
    """
    Scales volume linearly based on inner circumference ratio.
    Default base size is 12.0 for Indian or 7.0 for US.
    """
    if not base_size:
        base_size = 12.0 if standard.lower() == "indian" else 7.0
        
    d_base = get_diameter_for_size(base_size, standard)
    d_target = get_diameter_for_size(target_size, standard)
    
    # Scaling factor based on circumference (linear relation to volume for constant cross-section)
    scaling_factor = d_target / d_base
    return base_volume * scaling_factor

def get_prompt(params: dict, similar_examples: list = None, standard: str = "Indian"):
    examples_text = ""
    if similar_examples:
        # Sort by score descending just in case
        sorted_examples = sorted(similar_examples, key=lambda x: x.get('score', 0), reverse=True)
        
        examples_text = "\nRetrieved Visually Similar Examples (Ranked by Visual Match Accuracy):\n"
        for i, ex in enumerate(sorted_examples):
            score = ex.get('score', 0)
            match_percent = score * 100
            
            # Highlight high accuracy matches
            priority_tag = "[PRIORITY MATCH]" if match_percent >= 90 else ""
            
            # Translate default base size nicely if it is 7.0 (which was the default US standard baseline)
            base_size_raw = ex.get('base_ring_size', 7.0)
            if standard.lower() == "indian" and base_size_raw == 7.0:
                size_str = "Indian Size 14 (or US Size 7)"
            else:
                size_str = f"{standard} Size {base_size_raw}"
            
            examples_text += (
                f"{i+1}. {priority_tag} Name: {ex.get('product_name', 'N/A')}, "
                f"Visual Match: {match_percent:.1f}%, "
                f"Base Ring Size: {size_str}, "
                f"Params: {json.dumps(ex['params'])}, "
                f"Actual Weight: {ex['actual_weight']}g\n"
            )

    return f"""
    You are a jewelry manufacturing expert. Your goal is to estimate the GOLD WEIGHT in grams (g) for an 18K Gold ring design based on images.
    
    Input Parameters:
    {json.dumps(params, indent=2)}
    {examples_text}
    
    Calculation Baseline:
    - Use the 'Actual Weight' of visually similar examples as your primary anchor.
    - Note: The visual RAG examples are listed with their actual gold weights. Weight is highly correlated with visual features like thickness, width, and hollow areas.
    - Target Ring Size Standard: {standard}
    
    CRITICAL INSTRUCTIONS FOR RAG WEIGHTING:
    - If any example is marked [PRIORITY MATCH] (Visual Match >= 90%), give it significantly MORE WEIGHT. These designs are nearly identical to the target.
    - If there are multiple priority matches, interpolate between them.
    - If no priority matches exist, look at the visual match percentages and prioritize the highest ones.
    
    General Instructions:
    1. Analyze the images (multiple angles may be provided). Identify number of strands, thickness, prongs, hollow/solid areas, and design complexity.
    2. Estimate the total gold weight in grams (g) for 18K purity.
    3. SAFETY MARGIN: Provide a weight RANGE (min to max in grams). It is better to have a small safety buffer (e.g. 5-10% higher for max_weight) to provide a "Safe Cap" for manufacturing, but keep it tight.
    4. Return your response in JSON format.
    
    Expected JSON format:
    {{
        "min_weight_18k_g": float,
        "max_weight_18k_g": float,
        "explanation": "Detailed reasoning for gold weight estimation, specifically explaining how you weighted the similar examples based on their Match Accuracy",
        "design_notes": "Key observations from images (e.g., solid vs. hollow, number of strands, stone settings)"
    }}
    """

async def get_gemini_prediction(image_bytes_list: list[bytes], params: dict, api_key: str, similar_examples: list = None, standard: str = "Indian", model_id: str = "gemini-2.5-flash"):
    logger.info(f"Initialising Gemini AI ({model_id}) with {len(image_bytes_list)} images...")
    
    try:
        # Using the new google-genai SDK
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        
        logger.info("Generating prompt...")
        prompt = get_prompt(params, similar_examples, standard)
        
        logger.info(f"Requesting content from {model_id}...")
        
        # Prepare content with multiple images
        contents = [prompt]
        for img_bytes in image_bytes_list:
            img = Image.open(io.BytesIO(img_bytes))
            contents.append(img)
        
        response = client.models.generate_content(
            model=model_id,
            contents=contents
        )
        
        if not response or not response.text:
            raise ValueError("Empty response from Gemini API")

        logger.info("Response received from Gemini. Parsing...")
        text = response.text
        start = text.find('{')
        end = text.rfind('}') + 1
        
        if start == -1 or end == 0:
            logger.error(f"Failed to find JSON in response: {text}")
            raise ValueError("Gemini response did not contain valid JSON")

        result = json.loads(text[start:end])
        logger.info("JSON parsed successfully. Calculating weights...")
        
        min_18k = result.get("min_weight_18k_g", 0.0)
        max_18k = result.get("max_weight_18k_g", 0.0)
        
        # Fallback safety for old keys if LLM outputs them by mistake
        if not min_18k and "min_volume_mm3" in result:
            min_18k = result["min_volume_mm3"] * GOLD_DENSITIES["18K"]
            max_18k = result["max_volume_mm3"] * GOLD_DENSITIES["18K"]
            
        # 18K Weight -> Volume (mm3)
        min_vol = min_18k / GOLD_DENSITIES["18K"] if min_18k else 0.0
        max_vol = max_18k / GOLD_DENSITIES["18K"] if max_18k else 0.0
        
        # Calculate Karat weights in Backend for consistency
        min_weights_14k = min_vol * GOLD_DENSITIES["14K"]
        max_weights_14k = max_vol * GOLD_DENSITIES["14K"]
        min_weights_18k = min_18k
        max_weights_18k = max_18k
        min_weights_22k = min_vol * GOLD_DENSITIES["22K"]
        max_weights_22k = max_vol * GOLD_DENSITIES["22K"]
        
        return {
            "estimated_volume_mm3": max_vol,
            "min_weight_14k": min_weights_14k,
            "max_weight_14k": max_weights_14k,
            "min_weight_18k": min_weights_18k,
            "max_weight_18k": max_weights_18k,
            "min_weight_22k": min_weights_22k,
            "max_weight_22k": max_weights_22k,
            "predicted_weight_14k": max_weights_14k,
            "predicted_weight_18k": max_weights_18k,
            "explanation": result.get("explanation", "No explanation provided."),
            "raw": result
        }
    except Exception as e:
        logger.error(f"Gemini API error detail: {str(e)}")
        raise e

async def get_anthropic_prediction(image_bytes: bytes, params: dict, api_key: str, similar_examples: list = None, standard: str = "Indian"):
    logger.info("Initialising Anthropic AI...")
    if not api_key or api_key == "your_anthropic_key":
        logger.warning("Invalid Anthropic API Key detected!")
        raise ValueError("Invalid Anthropic API Key")

    client = Anthropic(api_key=api_key)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = get_prompt(params, similar_examples, standard)

    try:
        logger.info("Requesting content from Claude API...")
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt
                        }
                    ],
                }
            ],
        )
        text = message.content[0].text
        start = text.find('{')
        end = text.rfind('}') + 1
        result = json.loads(text[start:end])
        
        min_18k = result.get("min_weight_18k_g", 0.0)
        max_18k = result.get("max_weight_18k_g", 0.0)
        
        # Fallback safety for old keys if LLM outputs them by mistake
        if not min_18k and "min_volume_mm3" in result:
            min_18k = result["min_volume_mm3"] * GOLD_DENSITIES["18K"]
            max_18k = result["max_volume_mm3"] * GOLD_DENSITIES["18K"]
            
        # Calculate volume
        min_vol = min_18k / GOLD_DENSITIES["18K"] if min_18k else 0.0
        max_vol = max_18k / GOLD_DENSITIES["18K"] if max_18k else 0.0
        
        return {
            "estimated_volume_mm3": max_vol,
            "min_weight_14k": min_vol * GOLD_DENSITIES["14K"],
            "max_weight_14k": max_vol * GOLD_DENSITIES["14K"],
            "min_weight_18k": min_18k,
            "max_weight_18k": max_18k,
            "min_weight_22k": min_vol * GOLD_DENSITIES["22K"],
            "max_weight_22k": max_vol * GOLD_DENSITIES["22K"],
            "predicted_weight_14k": max_vol * GOLD_DENSITIES["14K"],
            "predicted_weight_18k": max_18k,
            "explanation": result.get("explanation", "No explanation provided."),
            "raw": result
        }
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        raise e

async def get_llm_prediction(image_bytes_list: list[bytes], params: dict, config: dict, similar_examples: list = None, standard: str = "Indian"):
    provider = config.get("default_llm", settings.DEFAULT_LLM)
    gemini_key = config.get("gemini_api_key") or settings.GEMINI_API_KEY
    anthropic_key = config.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY
    gemini_model = config.get("gemini_model") or "gemini-2.5-flash"
    
    try:
        if provider == "gemini" and gemini_key:
            return await get_gemini_prediction(image_bytes_list, params, gemini_key, similar_examples, standard, gemini_model)
        elif provider == "anthropic" and anthropic_key:
            # Anthropic only uses the first image for now
            return await get_anthropic_prediction(image_bytes_list[0], params, anthropic_key, similar_examples, standard)
        else:
            # Fallback
            if gemini_key:
                return await get_gemini_prediction(image_bytes_list, params, gemini_key, similar_examples, standard, gemini_model)
            
            return {
                "predicted_weight_14k": 0.0,
                "predicted_weight_18k": 0.0,
                "explanation": "No API keys set",
                "raw": {}
            }
    except Exception as e:
        logger.error(f"All LLM providers failed: {e}")
        return {
            "predicted_weight_14k": 0.0,
            "predicted_weight_18k": 0.0,
            "explanation": f"Error: {str(e)}",
            "raw": {}
        }
