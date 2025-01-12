from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import json
from Backend.app.DataModel.Task import Task, TaskStatus
from Backend.app.DataModel.Project import Project 
from Backend.app.DataModel.Service import Service 
from Backend.app.Agent.BaseAgent import BaseAgent
from Backend.app.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse

# --- Task Assignment Agent ---
class TaskAssignmentAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "TaskAssigner", 
            "Task Assignment Manager",
            OllamaModelConfig(model_name="codellama", temperature=0.2)
        )

    async def analyze_task_requirements(self, task: Task, context: str) -> dict:
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Analyze this task and identify the required skills and expertise:
                Task Title: {task.title}
                Task Description: {task.description}
                
                Return the analysis as a JSON object with these fields:
                - primary_skill: The main technical skill needed
                - secondary_skills: List of additional skills required
                - complexity: Low/Medium/High
                - estimated_duration: in hours
                - best_role: Developer/Tester/DevOps

                --- Context Project
                {context}
                """,
                system="You are a technical project coordinator. Analyze tasks and determine required expertise."
            )
            
            result = await ollama.generate(prompt)
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                self.logger.error(f"Failed to parse task analysis: {result}")
                return {
                    "primary_skill": "unknown",
                    "secondary_skills": [],
                    "complexity": "Medium",
                    "estimated_duration": 4,
                    "best_role": "Developer"
                }

    async def evaluate_agent_suitability(self, agent: BaseAgent, task_requirements: dict) -> float:
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Evaluate how well this agent matches the task requirements:
                Agent Role: {agent.role}
                
                Task Requirements:
                {json.dumps(task_requirements, indent=2)}
                
                Return a single number between 0 and 1 representing the match score.
                Higher scores indicate better matches.
                Only return the number, no other text.
                """,
                system="You are an AI task assignment specialist. Evaluate agent-task compatibility."
            )
            
            try:
                score = float(await ollama.generate(prompt))
                return min(max(score, 0), 1)  # Ensure score is between 0 and 1
            except ValueError:
                self.logger.error("Failed to get valid score from LLM")
                return 0.5

    async def assign_next_task(self, project: Project, available_agents: List[BaseAgent]) -> tuple[Task, BaseAgent]:
        # Find tasks that are ready to be worked on (all dependencies completed)
        ready_tasks = [
            task for task in project.tasks 
            if task.status == TaskStatus.TODO and 
            all(dep_task.status == TaskStatus.DONE 
                for dep_task in project.tasks 
                if dep_task.id in task.dependencies)
        ]
        
        if not ready_tasks:
            return None, None

        # Analyze each ready task and find the best task-agent match
        best_match = None
        best_score = -1
        best_task = None
        best_agent = None

        for task in ready_tasks:
            # Get task requirements
            requirements = await self.analyze_task_requirements(task, project.description)
            
            # Evaluate each available agent
            for agent in available_agents:
                score = await self.evaluate_agent_suitability(agent, requirements)
                
                if score > best_score:
                    best_score = score
                    best_task = task
                    best_agent = agent
        
        if best_score >= 0.6:  # Minimum threshold for assignment
            self.logger.info(f"Assigning task '{best_task.title}' to {best_agent.role} (match score: {best_score})")
            return best_task, best_agent
        else:
            # Fallback to basic assignment if no good match found
            task = ready_tasks[0]
            if "dev" in task.id:
                agent = next((a for a in available_agents if a.role == "Developer"), None)
            elif "test" in task.id:
                agent = next((a for a in available_agents if a.role == "Tester"), None)
            elif "deploy" in task.id:
                agent = next((a for a in available_agents if a.role == "DevOps"), None)
            else:
                agent = available_agents[0]
            
            self.logger.warn(f"Using fallback assignment for task '{task.title}' to {agent.role}")
            return task, agent

    async def explain_assignment(self, task: Task, agent: BaseAgent) -> str:
        """Provide explanation for why this agent was chosen for the task"""
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Explain why this agent assignment makes sense:
                Task: {task.title}
                Description: {task.description}
                Assigned to: {agent.role}
                
                Provide a brief, clear explanation of why this is a good match.
                """,
                system="You are a technical project coordinator. Explain task assignments clearly and concisely."
            )
            
            return await ollama.generate(prompt)