from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import logfire
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Project import Project 
from HygdraAgency.DataModel.Service import Service 
from HygdraAgency.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse
import json
import logging

# --- Enhanced Base Agent with Ollama Support ---
class BaseAgent:
    def __init__(self, name: str, role: str, ollama_config: Optional[OllamaModelConfig] = None):
        self.name = name
        self.role = role
        self.logger = logging.getLogger(name)
        self.ollama_config = ollama_config or OllamaModelConfig()
        logfire.instrument_pydantic() 
        
    async def think(self, context: dict) -> str:
        async with OllamaClient(self.ollama_config) as ollama:
            system_prompt = f"""You are an AI agent with the role of {self.role}. 
            Think step by step about how to approach the given context and task.
            Provide clear reasoning and actionable steps."""
            
            prompt = OllamaPrompt(
                prompt=f"Context: {json.dumps(context)}\nWhat steps should I take to handle this?",
                system=system_prompt
            )
            
            return await ollama.generate(prompt)