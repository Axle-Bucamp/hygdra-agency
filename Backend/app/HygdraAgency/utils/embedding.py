import requests
from typing import List, Optional, Dict
import os

async def embedding(content: List[str], provider: str="Ollama"):
    if provider == 'Ollama':
        url = os.env("OLLAMA_URL") + "/v1/embeddings"
        headers = {"Content-Type": "application/json"}
        data = {
            "model": "nomic-embed-text", 
            "texts": content  
        }

        response = requests.post(url, json=data, headers=headers)
        embeddings = response.json().get("data", [])
        return embeddings
    
