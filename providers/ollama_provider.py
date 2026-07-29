from providers.base_provider import BaseProvider
import requests,json
from config import OLLAMA_URL, MODEL_NAME,MAX_EXECUTION_RETRIES 
from utils.logger import logger


class OllamaProvider(BaseProvider):

    def generate(self, prompt) -> str:
       
        # Prepare Request Body
            payload = {
               "model": MODEL_NAME,
               "prompt": prompt,
               "stream": False
               }
            for attempt in range(MAX_EXECUTION_RETRIES): 
               
               try:
               
                   # Send HTTP Request
                   response = requests.post(OLLAMA_URL,json=payload)
       
                   # Validate HTTP Response
                   if response.status_code == 200:
       
                       result = response.json()
                       return result["response"]    
                   logger.error(f"Attempt {attempt + 1} failed. Status Code: {response.status_code}")
       
               except Exception as e:
       
                   logger.error(f"Retry {attempt+1}: {e}")
             
            raise RuntimeError("Failed to get response from Ollama after 3 attempts.")      
                      