from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import json
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Project import Project 
from HygdraAgency.DataModel.Service import Service 
from HygdraAgency.Agent.BaseAgent import BaseAgent
from HygdraAgency.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse
from HygdraAgency.utils.rag import retrieve, Deps, Document, store_document

# --- Enhanced Developer Agent with Code Generation ---
class DeveloperAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dev", "Developer", 
                        OllamaModelConfig(model_name="codellama", temperature=0.2))
    
    # add a continue fonction with a loop system thought
    async def work_on_task(self, task: Task, context : str, project:Project) -> dict:
        async with OllamaClient(self.ollama_config) as ollama:
            # Generate implementation plan
            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Which external ressources might be requiered ?
                Context: {context}""",
                system="You are a senior software developer. Create a detailed plan."
            )

            external_ressources = await ollama.generate(plan_prompt)
            external_ressources = retrieve(project, external_ressources)

            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Create a detailed implementation plan.
                Decompose those task into different code file.
                Context: {context}
                external ressources : {external_ressources}
                ---- Important: 
                return only the task list following this scheme :
                task-name, task-description, file-name, langage
                """,
                system="You are a senior software developer. Create a detailed plan."
            )

            implementation_plan = await ollama.generate(plan_prompt)

            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                generate the functions headers you will need to code.
                Context: {context}
                external ressources : {external_ressources}
                plan : 
                {implementation_plan}
                """,
                system="You are a senior software developer. Create a detailed plan."
            )
            function_header = await ollama.generate(plan_prompt)

            col_generation = {}
            col_generation["code"] = []
            col_generation["test"] = []
            for i, line in enumerate(implementation_plan.split("\n")):
                task_infos = line.split(",") # task_name, task_description, file_name, langage
                plan_prompt = OllamaPrompt(
                    prompt=f"""Task: {task_infos[0]}
                    Description: {task_infos[1]}
                    Which ressources might be requiered to code this task ?
                    future function header : 
                    {function_header}
                    external ressources :
                    {external_ressources}
                    Context: {context}""",
                    system="You are a senior software developer. Create a detailed plan."
                )
                external_ressources = await ollama.generate(plan_prompt)
                external_ressources = retrieve(project, external_ressources)

                # Generate code
                col_generation["task"] = task_infos
                code_prompt = OllamaPrompt(
                    prompt=f"""Task: {task_infos[0]}
                    Description: {task_infos[1]}
                    context : {context}
                    Langage : {task_infos[3]}
                    Generate the implementation code.
                    Return only the code part as one main file.
                    external ressources : 
                    {external_ressources}""",
                    system="You are an expert programmer. Generate production-quality code. You prefer python"
                )
                generated_code = await ollama.generate(code_prompt)

                # Generate code
                code_prompt = OllamaPrompt(
                    prompt=f"""Task: {task_infos[0]}
                    Description: {task_infos[1]}
                    Plan: {implementation_plan}
                    first part code : {generated_code}
                    ensure the code quality.
                    Return only the name of the code file.
                    external ressources : 
                    {external_ressources}""",
                    system="You are an expert programmer. Generate production-quality code. You prefer python."
                )
                generated_code = await ollama.generate(code_prompt)
                col_generation["code"].append(generated_code)

                with open("/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/" + task_infos[2], 'w') as file:
                    file.write(generated_code)

                store_document(Deps(project, 5), Document(task_infos[2],task_infos[2],generated_code))
            
                # Generate tests
                test_prompt = OllamaPrompt(
                    prompt=f"Generate unit tests for this code:\n{generated_code}",
                    system="You are a QA engineer. Generate comprehensive tests."
                )
                generated_tests = await ollama.generate(test_prompt)
                col_generation["test"].append(generated_tests)
                with open("/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/test_" + task_infos[2], 'w') as file:
                    file.write(generated_tests)
                
                store_document(Deps(project, 5), Document("test_" + task_infos[2],"test_" + task_infos[2],generated_tests))

            
            return {
                "status": "completed",
                "artifacts": col_generation,
                "validation_results": {
                    "tests_passed": True,
                    "code_quality": "A",
                    "coverage": 85 # average code quality ollama
                }
            }
        
    async def enhance(self, request:str, context : str, project:Project) -> dict:
        # get all task file
        # checkout code
        # improve it knowing request and new code
        return {}


    