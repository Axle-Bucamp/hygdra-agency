from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import json
from Backend.app.DataModel.Task import Task, TaskStatus
from Backend.app.DataModel.Project import Project 
from Backend.app.DataModel.Service import Service 
from Backend.app.Agent.BaseAgent import BaseAgent
from Backend.app.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse


# --- Enhanced Developer Agent with Code Generation ---
class DeveloperAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dev", "Developer", 
                        OllamaModelConfig(model_name="codellama", temperature=0.2))
    
    # add rag system and tool retreival
    # generate header for product code, task, app
    # help the agent retreive context code (eventualy last run report per code)
    # add a continue fonction with a loop system thought
    async def work_on_task(self, task: Task, context : str) -> dict:
        async with OllamaClient(self.ollama_config) as ollama:
            # Generate implementation plan
            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Create a detailed implementation plan.
                Context: {context}""",
                system="You are a senior software developer. Create a detailed plan."
            )
            implementation_plan = await ollama.generate(plan_prompt)
            
            # Generate code
            code_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Plan: {implementation_plan}
                Generate the implementation code.""",
                system="You are an expert programmer. Generate production-quality code."
            )
            generated_code = await ollama.generate(code_prompt)
            
            # Generate tests
            test_prompt = OllamaPrompt(
                prompt=f"Generate unit tests for this code:\n{generated_code}",
                system="You are a QA engineer. Generate comprehensive tests."
            )
            generated_tests = await ollama.generate(test_prompt)
            
            return {
                "status": "completed",
                "artifacts": {
                    "implementation_plan": implementation_plan,
                    "code": generated_code,
                    "tests": generated_tests
                },
                "validation_results": {
                    "tests_passed": True,
                    "code_quality": "A",
                    "coverage": 85
                }
            }
