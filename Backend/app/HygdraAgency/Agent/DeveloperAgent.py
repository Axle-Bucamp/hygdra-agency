from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime
import json
import os
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Project import Project 
from HygdraAgency.DataModel.Service import Service, CodeFile
from HygdraAgency.Agent.BaseAgent import BaseAgent
from HygdraAgency.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse
from HygdraAgency.utils.rag import retrieve, Deps, Document, store_document

# --- Enhanced Developer Agent with Code Generation ---
class DeveloperAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dev", "Developer", 
                        OllamaModelConfig(model_name="codellama", temperature=0.2))
    
    # add a continue fonction with a loop system thought
    async def work_on_task(self, task: Task, project:Project) -> dict:
        context = project.description
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
            external_ressources = await retrieve(Deps(project, 5), external_ressources)

            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Create a detailed implementation plan.
                Decompose those task into different code file.
                Context: {context}
                external ressources : {external_ressources}
                ---- Important: 
                return only the task list.
                use this CSV format:
                task1-name, task1-description, file1-name, coding langage
                task2-name, task2-description, file2-name, coding langage
                task3-name, task3-description, file3-name, coding langage
                """,
                system="You are a senior software developer. Create a detailed plan."
            )
            implementation_plan = await ollama.generate(plan_prompt)
            print(implementation_plan)

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
            code = []
            for i, line in enumerate(implementation_plan.split("\n")):
                task_infos = line.split(",") # task_name, task_description, file_name, langage
                if len(task_infos) == 4:
                    print(task_infos)
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
                    external_ressources = await retrieve(Deps(project, 5), external_ressources)

                    # Generate code
                    code_prompt = OllamaPrompt(
                        prompt=f"""Task: {task_infos[0]}
                        Description: {task_infos[1]}
                        context : {context}
                        Langage : {task_infos[3]}
                        --- note :
                        Generate the implementation code.
                        ensure the code quality.
                        Generalise key concept into function.
                        --- important :
                        return only the generated code as one main file.
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
                        Return only the name of the code file.
                        external ressources : 
                        {external_ressources}""",
                        system="You are an expert programmer. Generate production-quality code. You prefer python."
                    )
                    generated_code = await ollama.generate(code_prompt)

                    #plus propre plus tard
                    os.mkdir(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}") 
                    os.mkdir(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}/{task.title}")
                    with open(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}/{task.title}/{task_infos[2]}" , 'w') as file:
                        file.write(generated_code)

                    store_document(Deps(project, 5), Document(task_infos[2],task_infos[2],generated_code))
                    codefile = CodeFile(id=task_infos[0], name=task_infos[0], description=task_infos[1], filename=task_infos[2], status="coded", langage=task_infos[3])
                    code.append(codefile)
                
                    # Generate tests
                    test_prompt = OllamaPrompt(
                        prompt=f"Generate unit tests for this code:\n{generated_code}",
                        system="You are a QA engineer. Generate comprehensive tests."
                    )

                    generated_tests = await ollama.generate(test_prompt)
                    with open(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}/{task.title}/test_{task_infos[2]}", 'w') as file:
                        file.write(generated_tests)

                    # task_name, task_description, file_name, langage
            
                    store_document(Deps(project, 5), Document("test_" + task_infos[2],"test_" + task_infos[2],generated_tests))
                    print("new code added")

            task.status = TaskStatus.DONE
            service = Service(id=task.title, name=task.title, doc=task.description, status="coded", description=task.description, code=code)
            project.app.append(service)

            return project
        
    async def enhance(self, request:str, context : str, project:Project) -> dict:
        # get all task file
        # checkout code
        # improve it knowing request and new code
        return {}


    