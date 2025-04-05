import os
from pydantic import BaseModel
from typing import Type, List, Dict, Any
from google import genai

# Ensure API keys are loaded (config takes care of this)
from .config import load_api_keys
load_api_keys()

class LLMService:
    """Handles interactions with the Google Gemini LLM."""
    def __init__(self):
        """Initializes the Gemini client."""
        if not os.environ.get("GEMINI_API_KEY"):
            raise ValueError("GEMINI_API_KEY environment variable not set.")
        
        # Instantiate the client directly
        self.client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
        
    def generate_text(self, prompt: str) -> str:
        """Generates plain text based on a user prompt."""
        try:
            # Use the initialized genai_model
            contents = [prompt]
            response = self.client.models.generate_content(model="gemini-2.0-flash", contents=contents)
            return response.text
        except Exception as e:
            print(f"Error during LLM text generation: {e}")
            return ""

    def generate_structured(self, prompt: str, response_model: Type[BaseModel]  ) -> Type[BaseModel] | None:
        """Generates structured output matching the provided Pydantic model."""
        response = self.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': response_model,
            },
        )
        return response.parsed