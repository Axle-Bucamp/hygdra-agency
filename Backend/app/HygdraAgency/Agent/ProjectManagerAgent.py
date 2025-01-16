from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Project import Project 
from HygdraAgency.DataModel.Service import Service 
from HygdraAgency.Agent.BaseAgent import BaseAgent
from HygdraAgency.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse
from os import mkdir
from HygdraAgency.utils.rag import retrieve, Deps, Document, store_document


# --- Enhanced Project Manager Agent ---
class ProjectManagerAgent(BaseAgent):
    def __init__(self):
        super().__init__("PM", "Project Manager",
                        OllamaModelConfig(model_name="codellama", temperature=0.7))

    async def initialize_project(self, project_name: str, description: str) -> Project:
        project_desc = description
        async with OllamaClient(self.ollama_config) as ollama:
            # Generate task breakdown
            task_prompt = OllamaPrompt(
                prompt=f"""Project Name: {project_name}
                Description: {description}

                --- Request
                plan the action you need to tak to generate the following request :
                [
                Create a detailed to-do list for this software project optimized for other LLM agent.
                The Task list focus only on technical part.
                Break down the project into actionable tasks.
                Provide a clear and structured to-do list that is easy to follow, ensuring each task has a specific goal and actionable steps.
                ]""",
                system="You are a technical project manager."
            )
            
            task_breakdown = await ollama.generate(task_prompt)

            task_prompt = OllamaPrompt(
                prompt=f"""Project Name: {project_name}
                Description: {description}
                
                

                --- Request
                Create a detailed to-do list for this software project optimized for other LLM agent.
                The Task list focus only on technical part.
                Break down the project into actionable tasks.
                Provide a clear and structured to-do list that is easy to follow, ensuring each task has a specific goal and actionable steps.
                
                --- previous work :
                {task_breakdown}
                """,
                system="You are a technical project manager."
            )
            
            task_breakdown = await ollama.generate(task_prompt)

            task_prompt = OllamaPrompt(
                prompt=f"""Project Name: {project_name}
                Description: {description}

                --- Request
                ensure the to-do list for this software project is optimized for other LLM agent.
                The Task list focus only on technical part.
                The task description must be optimised for an LLM agent to build it.
                Format the task list into the following patern:
                1) [taskName] : [TaskDescription]
                2) [taskName] : [TaskDescription]
                3) [taskName] : [TaskDescription]

                --- important
                each task is detailed within only one line.
                return only the task list.

                --- previous work :
                {task_breakdown}
                """,
                system="You are a technical project manager."
            )
            
            task_breakdown = await ollama.generate(task_prompt)

            
            # Parse task breakdown and create Task objects
            tasks = []
            for i, line in enumerate(task_breakdown.split("\n")):
                line = line.strip()
                if line:  # Ignore empty lines
                    # Split by the first occurrence of ":" to avoid issues with descriptions containing ":"
                    if ":" in line:
                        title, description = line.split(":", 1)
                        tasks.append(Task(
                            id=f"task-{i}",
                            title=title.strip(),
                            description=description.strip(),
                            status=TaskStatus.TODO
                        ))
                    else:
                        # In case there's no ":", treat the entire line as the title
                        tasks.append(Task(
                            id=f"task-{i}",
                            title=line,
                            description="No description provided",
                            status=TaskStatus.TODO
                        ))

            project = Project(
                id=f"proj-{str(datetime.now().timestamp())}-{project_name}",
                name=project_name,
                description=project_desc,
                tasks=tasks
            )
            return project
        
    async def tchat(self, project:Project, request:str) -> str:
        async with OllamaClient(self.ollama_config) as ollama:
            # Generate implementation plan
            plan_prompt = OllamaPrompt(
                prompt=f"""request: {request}
                Description: {project.tasks}
                Which external ressources might be requiered to answer this request?
                Context: {project.description}""",
                system="You are a senior software developer. Create a detailed plan."
            )

            external_ressources = await ollama.generate(plan_prompt)
            external_ressources = retrieve(project, external_ressources)

            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {request}
                Create a detailed implementation plan.
                Decompose those task into different code file.
                Context: {project.description}
                external ressources : {external_ressources}
                """,
                system="You are a senior software developer. Create a detailed plan."
            )

            implementation_plan = await ollama.generate(plan_prompt) 
            return implementation_plan

