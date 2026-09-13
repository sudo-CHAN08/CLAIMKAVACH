import os
import json
from google import genai
from google.genai import types

def get_client():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable is not set!")
    return genai.Client(api_key=api_key)

def classify_crop_damage(image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
    """Analyzes ground evidence photo/video frame to classify crop damage parameters."""
    client = get_client()

    system_prompt = """
You are an expert agricultural loss assessor evaluating field damage for PMFBY crop insurance claims.
Analyze the uploaded ground evidence photo or video frame carefully for both legitimate damage and potential fraud or exclusions.

1. DAMAGE CLASSIFICATION:
- lodging_percentage: Estimated percentage of crops flattened/bent over (integer 0-100).
- submergence_level: Description of standing water (e.g., "None", "Standing water > 1.5 feet", "Root level waterlogging").
- crop_stage: Exact state ("Prevented Sowing / Un-sown", "Standing Crop", "Post-Harvest Cut-and-Spread", "Off-field Storage / Godown").
- damage_type: Primary cause ("Inundation / Flooding", "Hailstorm Damage", "Landslide / Mudslide", "Cloudburst", "Natural Fire", "Pest / Disease Infestation", "Drought / Dry Spell", "Severe Wind / Lodging", "Man-made / Neglect / Weeds").

2. PMFBY ELIGIBILITY & ANTI-SPOOFING:
- is_eligible_claim: Set to false if damage is due to poor maintenance/weeds, off-field storage, or man-made causes. Otherwise true.
- anti_spoofing_flag: Set to true if the image appears to be a photo of a digital screen, heavily edited/AI-generated, or taken indoors/off-farm.
- rejection_reason: String explaining why it was flagged/rejected, or "None" if valid.

Return ONLY valid JSON matching this schema:
{
  "damage_type": "string",
  "crop_stage": "string",
  "lodging_percentage": int,
  "submergence_level": "string",
  "is_eligible_claim": bool,
  "anti_spoofing_flag": bool,
  "rejection_reason": "string",
  "confidence_score": float
}
"""

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[
            types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
        ],
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.0,
            response_mime_type="application/json"
        ),
    )
    return json.loads(response.text)