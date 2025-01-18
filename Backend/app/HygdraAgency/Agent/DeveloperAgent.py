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
import re

# --- Enhanced Developer Agent with Code Generation ---
class DeveloperAgent(BaseAgent):
    def __init__(self):
        super().__init__("Dev", "Developer", 
                        OllamaModelConfig(model_name="codellama", temperature=0.2))
    
    # add a continue fonction with a loop system thought
    async def work_on_task(self, task: Task, project:Project) -> dict:
        async with OllamaClient(self.ollama_config) as ollama:
            # Generate implementation plan
            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Which external ressources might be requiered to fullfill this task ?
                Context: {project.description}""",
                system="You are a senior software developer. Create a detailed plan."
            )

            external_ressources = await ollama.generate(plan_prompt)
            external_ressources = await retrieve(Deps(project, 5), external_ressources)

            # do the loop and use regex ?
            plan_prompt = OllamaPrompt(
                prompt=f"""Task: {task.title}
                Description: {task.description}
                Context: {project.description}
                external ressources : {external_ressources}
                ---- request: 
                Create a detailed implementation plan.
                Decompose the task into different code file.
                return file name, small descriptiom, 
                functions header and coding langage into an actionnable list.
                """,
                system="You are a senior software developer. Create a detailed plan."
            )

            implementation_plan = await ollama.generate(plan_prompt)

            # generate file
            i=0
            code = []
            while i < 20:
                plan_prompt = OllamaPrompt(
                    prompt=f"""Task: {task.title}
                    Description: {task.description}
                    Context: {project.description}
                    external ressources : {external_ressources}
                    plan : 
                    {implementation_plan}
                    --- request :
                    select the next file to code.
                    extract the function header,
                    describe it.
                    choose a langage that suit the request.
                    """,
                    system="You are a senior software developer. Create a detailed plan."
                )
                next_file = await ollama.generate(plan_prompt)
                external_ressources = await retrieve(Deps(project, 5), next_file)

                plan_prompt = OllamaPrompt(
                    prompt=f"""Task: {task.title}
                    Description: {task.description}
                    Context: {project.description}
                    external ressources: {external_ressources}
                    todo code : 
                    {next_file}
                    --- request :
                    As an expert you need to code those function and fit them into one file.
                    stucture the request as markdown.
                    """,
                    system="You are a senior software developer. Create a detailed plan."
                )

                code_file = await ollama.generate(plan_prompt)

                plan_prompt = OllamaPrompt(
                    prompt=f"""Task: {task.title}
                    Description: {task.description}
                    Context: {project.description}
                    external ressources: {external_ressources}
                    {code_file}
                    --- request :
                    what is the name of this code file with extension.
                    """,
                    system="You are a senior software developer. Create a detailed plan."
                )

                filename = await ollama.generate(plan_prompt)
                match = re.search(r'([^/\\]+)\.(py|js|java|cpp|html|css|rb|go|ts|php)$', filename)
                if match:
                    filename = match.group(1)
                else:
                    filename=hash(filename)

                pattern = r'^```(?:\w+)?\s*\n(.*?)(?=^```)```'
                result = re.findall(pattern, code_file, re.DOTALL | re.MULTILINE)
                code_file = "\\n".join(result)
                
                #plus propre plus tard
                os.mkdir(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}") 
                os.mkdir(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}/{task.title}")

                with open(f"/home/guidry/Documents/agency/hygdra-agency/Backend/app/generated_code/{project.id}/{task.title}/{filename}" , 'w') as file:
                    file.write(code_file)

                store_document(Deps(project, 5), Document(filename, next_file ,code_file))
                codefile = CodeFile(id=filename, name=filename, description=next_file, filename=filename, status="coded", langage=filename)
                code.append(codefile)

                plan_prompt = OllamaPrompt(
                    prompt=f"""Task: {task.title}
                    Description: {task.description}
                    Context: {project.description}
                    plan : 
                    {implementation_plan}

                    -- task Done:
                    {next_file}
                    --- request:
                    mark the task as done in the plan.
                    update the plan.
                    --- important:
                    if the plan is fully implemented then return 'BREAK'
                    """,
                    system="You are a senior software developer. Create a detailed plan."
                )
                implementation_plan = await ollama.generate(plan_prompt)

                if "BREAK" in str(implementation_plan).upper():
                    break
                i+=1

            task.status = TaskStatus.DONE
            service = Service(id=task.title, name=task.title, doc=task.description, status="coded", description=task.description, code=code)
            project.app.append(service)

            return project
        
    async def enhance(self, request:str, context : str, project:Project) -> dict:
        # get all task file
        # checkout code
        # improve it knowing request and new code
        return {}


    