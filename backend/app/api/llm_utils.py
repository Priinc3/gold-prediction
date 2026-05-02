import base64
import json
from google import genai
from anthropic import Anthropic
from app.core.config import settings
from loguru import logger
from PIL import Image
import io

def get_prompt(params: dict, similar_examples: list = None):
    examples_text = ""
    if similar_examples:
        examples_text = "\nRetrieved Visually Similar Examples (Historical Data):\n"
        for i, ex in enumerate(similar_examples):
            examples_text += f"{i+1}. Name: {ex.get('product_name', 'N/A')}, Params: {json.dumps(ex['params'])}, Actual Weight: {ex['actual_weight']}g\n"

    return f"""
    You are a jewelry manufacturing expert. Predict the gold weight required for this ring design.
    
    Input Parameters:
    {json.dumps(params, indent=2)}
    {examples_text}
    
    Geometric Calculation Rules:
    - Gold 14k Density: ~13.5 g/cm³
    - Gold 18k Density: ~15.5 g/cm³
    - Volume Calculation: Shank (cylinder segment), Head (prongs + gallery), Side stone settings.
    
    Instructions:
    1. Carefully analyze the image. Identify the number of strands, thickness of the band, and any hollow/solid parts.
    2. Use the provided parameters (if any) to calculate estimated volume in mm³. If ring_size is not provided, assume a standard US women's size 6.5 (17mm inner diameter) as a baseline.
    3. IMPORTANT: The 'Retrieved Visually Similar Examples' are historically verified designs that look very similar to the image you see. Use their 'Actual Weight' as your primary anchor. If a similar example has a weight significantly different from your geometric estimate, lean towards the historical weight.
    4. Provide the predicted weight in grams with 3-decimal precision.
    5. Return your response in JSON format.
    
    Expected JSON format:
    {{
        "gold14k_g": float,
        "gold18k_g": float,
        "explanation": "Detailed step-by-step reasoning, including how similar examples influenced the result",
        "totalVolume_mm3": float
    }}
    """

async def get_gemini_prediction(image_bytes: bytes, params: dict, api_key: str, similar_examples: list = None):
    logger.info(f"Initialising Gemini AI (gemini-3-flash-preview) with key starting with: {api_key[:4]}...")
    
    try:
        # Using the new google-genai SDK
        client = genai.Client(api_key=api_key, http_options={'api_version': 'v1beta'})
        model_id = 'gemini-3-flash-preview'
        
        logger.info("Generating prompt...")
        prompt = get_prompt(params, similar_examples)
        
        logger.info(f"Requesting content from {model_id}...")
        
        img = Image.open(io.BytesIO(image_bytes))
        
        response = client.models.generate_content(
            model=model_id,
            contents=[prompt, img]
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
        logger.info("JSON parsed successfully.")
        
        return {
            "predicted_weight_14k": result.get("gold14k_g", 0.0),
            "predicted_weight_18k": result.get("gold18k_g", 0.0),
            "explanation": result.get("explanation", "No explanation provided."),
            "raw": result
        }
    except Exception as e:
        logger.error(f"Gemini API error detail: {str(e)}")
        raise e

async def get_anthropic_prediction(image_bytes: bytes, params: dict, api_key: str, similar_examples: list = None):
    logger.info("Initialising Anthropic AI...")
    if not api_key or api_key == "your_anthropic_key":
        logger.warning("Invalid Anthropic API Key detected!")
        raise ValueError("Invalid Anthropic API Key")

    client = Anthropic(api_key=api_key)
    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    prompt = get_prompt(params, similar_examples)

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
        return {
            "predicted_weight_14k": result.get("gold14k_g"),
            "predicted_weight_18k": result.get("gold18k_g"),
            "explanation": result.get("explanation"),
            "raw": result
        }
    except Exception as e:
        logger.error(f"Anthropic API error: {e}")
        raise e

async def get_llm_prediction(image_bytes: bytes, params: dict, config: dict, similar_examples: list = None):
    provider = config.get("default_llm", settings.DEFAULT_LLM)
    gemini_key = config.get("gemini_api_key") or settings.GEMINI_API_KEY
    anthropic_key = config.get("anthropic_api_key") or settings.ANTHROPIC_API_KEY
    
    try:
        if provider == "gemini" and gemini_key:
            return await get_gemini_prediction(image_bytes, params, gemini_key, similar_examples)
        elif provider == "anthropic" and anthropic_key:
            return await get_anthropic_prediction(image_bytes, params, anthropic_key, similar_examples)
        else:
            # Fallback
            logger.warning(f"Preferred provider {provider} not available, using fallback")
            if gemini_key:
                return await get_gemini_prediction(image_bytes, params, gemini_key, similar_examples)
            if anthropic_key:
                return await get_anthropic_prediction(image_bytes, params, anthropic_key, similar_examples)
            
            return {
                "predicted_weight_14k": 2.15,
                "predicted_weight_18k": 2.58,
                "explanation": "Dummy prediction (No API keys set)",
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
