import os
from google import genai
from providers.base_provider import BaseProvider


class GeminiProvider(BaseProvider):

    def __init__(self):

        self.model = "gemini-3.5-flash"


    def generate(self, prompt):

        api_key = os.getenv("GEMINI_API_KEY")

        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY environment variable is not set"
            )

        client = genai.Client(
            api_key=api_key
        )

        response = client.models.generate_content(
            model=self.model,
            contents=prompt
        )

        if not response.text:
            raise RuntimeError(
                "Gemini returned an empty response"
            )

        return response.text