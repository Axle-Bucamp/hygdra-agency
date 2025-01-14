from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from fastapi import HTTPException
import json
import aiohttp
import asyncio
import os

# --- Ollama Models ---
class OllamaModelConfig(BaseModel):
    model_name: str = "codellama"
    base_url: HttpUrl = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")# ollama url
    temperature: float = 0.7
    top_p: float = 0.9
    max_tokens: int = 2048

class OllamaPrompt(BaseModel):
    prompt: str
    system: Optional[str] = None
    template: Optional[str] = None
    context: Optional[str] = None
    options: Optional[dict] = None

class OllamaResponse(BaseModel):
    model: str
    created_at: str
    response: str
    done: bool
    context: Optional[List[int]] = None
    total_duration: Optional[int] = None
    load_duration: Optional[int] = None
    prompt_eval_duration: Optional[int] = None
    eval_duration: Optional[int] = None

class OllamaClient:
    def __init__(self, config: OllamaModelConfig):
        self.config = config
        self.base_url = str(config.base_url)
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def generate(self, prompt: OllamaPrompt) -> str:
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.config.model_name,
            "prompt": prompt.prompt,
            "system": prompt.system,
            "template": prompt.template,
            "context": prompt.context,
            "options": {
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "max_tokens": self.config.max_tokens,
                **(prompt.options or {})
            }
        }

        async with self.session.post(url, json=payload) as response:
            if response.status != 200:
                raise HTTPException(
                    status_code=response.status,
                    detail=f"Ollama API error: {await response.text()}"
                )
            
            full_response = ""
            async for line in response.content:
                try:
                    data = json.loads(line)
                    response_obj = OllamaResponse(**data)
                    if response_obj.response:
                        full_response += response_obj.response
                except json.JSONDecodeError:
                    continue
                
            return full_response

# Running the test
async def main():
    print("test")
    model = OllamaClient(OllamaModelConfig(model_name="codellama", temperature=0.7))
    async with model:
        response = await model.generate(OllamaPrompt(prompt="hey"))
        print(response)

# Entry point
if __name__ == "__main__":
    asyncio.run(main())  # This properly runs the async function
