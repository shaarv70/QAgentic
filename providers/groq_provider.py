import os

from groq import Groq
from providers.base_provider import BaseProvider


class GroqProvider(BaseProvider):

    def __init__(self):
        self.model = "openai/gpt-oss-120b"

    def generate(self, prompt):

        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable is not set"
            )

        client = Groq(api_key=api_key)

        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        )

        content = response.choices[0].message.content

        if not content:
            raise RuntimeError(
                "Groq returned an empty response"
            )

        return content