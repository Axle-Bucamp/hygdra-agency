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
                Create a detailed to-do list to build this software project.
                optimized it for other LLM agent.
                The Task list focus only on coding and dev task.
                Break down the project into actionable tasks.
                Provide a clear and structured to-do list that is easy to follow, 
                ensuring each task has a specific goal and actionable steps.
                ]""",
                system="You are a technical project manager."
            )
            
            task_breakdown = await ollama.generate(task_prompt)

            task_prompt = OllamaPrompt(
                prompt=f"""Project Name: {project_name}
                Description: {description}
                
                --- Request
                Create a detailed to-do list to build this software project.
                optimized it for other LLM agent.
                The Task list focus only on coding and dev task.
                Break down the project into actionable tasks.
                Provide a clear and structured to-do list that is easy to follow, 
                ensuring each task has a specific goal and actionable steps.
                
                --- previous work :
                {task_breakdown}
                """,
                system="You are a technical project manager."
            )
            
            task_breakdown = await ollama.generate(task_prompt)

            project = Project(
                id=f"proj-{str(datetime.now().timestamp())}-{project_name}",
                name=project_name,
                description=project_desc,
                tasks=[]
            )
            
            # Parse task breakdown and create Task objects
            tasks = await self.generate_task(project=project, first_though=task_breakdown)
            project.tasks = tasks
            
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

            response = await ollama.generate(plan_prompt) 
            return response

    async def generate_task(self, project:Project, first_though:str) -> str:
        tasks = []
        async with OllamaClient(self.ollama_config) as ollama:
            i = 0
            while i < 20:
                task_prompt = OllamaPrompt(
                        prompt=f"""Project Name: {project.title}
                        Description: {project.description}
                        
                        --- Request
                        Select the next task todo,
                        express what this task depend on.
                        generate the response as a prompt optmised for agent.

                        --- previous work :
                        {first_though}
                        """,
                        system="You are a technical project manager."
                    )
                
                selected_task_description = await ollama.generate(task_prompt)

                task_prompt = OllamaPrompt(
                        prompt=f"""Project Name: {project.title}
                        Description: {project.description}
                        
                        --- Request
                        name this task.

                        --- task description :
                        {selected_task_description}
                        """,
                        system="You are a technical project manager."
                    )
                
                selected_task_title = await ollama.generate(task_prompt)

                task_prompt = OllamaPrompt(
                        prompt=f"""Project Name: {project.title}
                        Description: {project.description}
                        
                        --- Request
                        mark the task done and regenerate the list.
                        Create a detailed to-do list to build this software project.
                        optimized it for other LLM agent.
                        The Task list focus only on coding and dev task.

                        --- task done :
                        {selected_task_title}
                        {selected_task_description}

                        --- task list :
                        {first_though}

                        ---- Important
                        If all task has been generate then mark the project done by returning the words 'break'
                        """,
                        system="You are a technical project manager."
                    )
                
                first_though = await ollama.generate(task_prompt)

                if "break" in first_though:
                    break

                tasks.append(Task(
                                id=f"task-{i}",
                                title=selected_task_title,
                                description=selected_task_description,
                                status=TaskStatus.TODO
                            ))
                i+= 1
            
            return tasks

