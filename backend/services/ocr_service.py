import json
import os
from typing import Dict, Any
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential

class OCRService:
    def __init__(self):
        # Initializes using standard GEMINI_API_KEY environment variable
        self.client = genai.Client()

    async def extract_712_data(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> Dict[str, Any]:
        """
        Extracts structured parameters from a Maharashtra 7/12 land record using Gemini 3.6 Flash.
        """
        system_prompt = """
        You are a specialized land records data extractor for Indian agricultural documents.
        Extract the relevant PMFBY claim parameters from this Maharashtra Digital 7/12 extract.

        CRITICAL INSTRUCTIONS FOR FARMER NAMES:
        1. Extract Marathi Devanagari names exactly as written character-for-character.
        2. Do not invent or guess surnames if they are not explicitly present in the document.
        3. If multiple joint landholders (सह-भोगवटादार) are listed, return ALL names in the 'farmer_names' array.

        Return ONLY valid JSON matching this schema:
        {
          "farmer_names": ["string"],
          "survey_number": "string",
          "village": "string",
          "taluka": "string",
          "district": "string",
          "state": "Maharashtra",
          "plot_area_ha": 0.0,
          "declared_crop": "string",
          "ulpin": "string"
        }
        """

        try:
            return await self._call_gemini_with_retry(image_bytes, mime_type, system_prompt)
        except Exception as e:
            raise RuntimeError(f"OCR Extraction failed: {str(e)}")

    @retry(
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        reraise=True
    )
    async def _call_gemini_with_retry(self, image_bytes: bytes, mime_type: str, system_prompt: str) -> Dict[str, Any]:
        """
        Executes Gemini API call with exponential backoff retries on 503/429 errors.
        """
        response = self.client.models.generate_content(
            model="gemini-3.6-flash",
            contents=[
                types.Part.from_bytes(data=image_bytes, mime_type=mime_type),
                system_prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        return json.loads(response.text)