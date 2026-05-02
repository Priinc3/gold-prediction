import torch
import open_clip
from PIL import Image
import io
from loguru import logger

class CLIPEncoder:
    def __init__(self, model_name="ViT-B-32", pretrained="laion2b_s34b_b79k"):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        logger.info(f"Loading CLIP model {model_name} on {self.device}...")
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model_name, pretrained=pretrained, device=self.device
        )
        self.tokenizer = open_clip.get_tokenizer(model_name)
        logger.info("CLIP model loaded successfully.")

    def get_image_embedding(self, image_bytes: bytes):
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        image_input = self.preprocess(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            image_features = self.model.encode_image(image_input)
            image_features /= image_features.norm(dim=-1, keepdim=True)
            
        return image_features.cpu().numpy().tolist()[0]

# Singleton instance
clip_encoder = None

def get_clip_encoder():
    global clip_encoder
    if clip_encoder is None:
        clip_encoder = CLIPEncoder()
    return clip_encoder
