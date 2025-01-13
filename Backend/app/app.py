from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from fastapi import FastAPI, HTTPException, File, UploadFile
from datetime import datetime
import requests
import json
from Backend.app.Agent.DeveloperAgent import DeveloperAgent
from Backend.app.Agent.DevOpsAgent import DevOpsAgent
from Backend.app.DataModel.Task import Task, TaskStatus
from Backend.app.DataModel.Project import Project 
from Backend.app.DataModel.Service import Service 
from Backend.app.Agent.ProjectManagerAgent import ProjectManagerAgent
from Backend.app.Agent.TaskAssignmentAgent import TaskAssignmentAgent
from Backend.app.Agent.TesterAgent import TesterAgent
import uvicorn
import os
import logfire
from fastapi.middleware.cors import CORSMiddleware
from typing import Annotated
from elasticsearch import Elasticsearch, helpers

# initialise elastic search
#TODO
# connect retreive project instancce
# rag system per project, task
# external ile to enbeding per project

#TODO
# add a get all project name
# add a get project properties
# add a file viewer vscode web for generated code
# add an external file management
# code to embeding (header file func resune )
# file to enbeding 

# Allow all origins for now (you can configure this more securely for production)
origins = [
    "http://0.0.0.0:3000",  # React default port
]

# Initialize agents
# --- API Routes ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logfire.configure()
logfire.instrument_fastapi(app)

# Initialize agents
pm_agent = ProjectManagerAgent()
task_assigner = TaskAssignmentAgent()
dev_agent = DeveloperAgent()
devops_agent = DevOpsAgent()
tester_agent = TesterAgent()

available_agents = [dev_agent, devops_agent, tester_agent]
active_projects: Dict[str, Project] = {}

@app.post("/projects/")
async def create_project(name: str, description: str):
    project = await pm_agent.initialize_project(name, description)
    os.mkdir("project/" + project.id)
    active_projects[project.id] = project

    json.dump(project)
    return project

# post file to collection
# make local rag collection system or logfire
@app.post("/projects/{project_id}/ressources/")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}

@app.post("/projects/{project_id}/next-task")
async def process_next_task(project_id: str):
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = active_projects[project_id]
    task, assigned_agent = await task_assigner.assign_next_task(project, available_agents)
    
    if not task or not assigned_agent:
        return {"status": "no_tasks_available"}
    
    # Update task status
    task.status = TaskStatus.IN_PROGRESS
    task.assigned_to = assigned_agent.name
    
    # Process task based on agent type
    # add ragged data + API doc + web tool + react
    # ragged external ressources external_ressources
    if isinstance(assigned_agent, DeveloperAgent):
        result = await assigned_agent.work_on_task(task, project.description)

    # work on later TODO
    elif isinstance(assigned_agent, DevOpsAgent):
        result = await assigned_agent.deploy(task)

    elif isinstance(assigned_agent, TesterAgent):
        result = await assigned_agent.run_tests(task)
    
    # Update task status based on result
    task.status = TaskStatus.DONE
    project = await pm_agent.update_task_status(project, task.id, TaskStatus.DONE)
    
    return {
        "task": task,
        "agent": assigned_agent.name,
        "result": result
    }

def start():
    """Start the application"""
    # Load configurations
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "7060"))
    
    # Configure Ollama
    os.environ["OLLAMA_HOST"] = os.getenv("OLLAMA_HOST", "http://localhost:11434")
    
    # Configure Jenkins
    devops_agent.jenkins_config.url = os.getenv("JENKINS_URL", "http://localhost:8080")
    devops_agent.jenkins_config.username = os.getenv("JENKINS_USER", "admin")
    devops_agent.jenkins_config.token = os.getenv("JENKINS_TOKEN", "sM]tVzQ+b*kWfP6")

    # Configure GitHub
    devops_agent.github_config.token = os.getenv("GITHUB_TOKEN", "")

    #configure sonar cube
    tester_agent.sonar_config.token = os.getenv("SONAR_TOKEN", "")
    tester_agent.sonar_config.host_url = os.getenv("SONAR_URL", "http://localhost:9000")
    
    #TODO
    # Sonarqube create project cmd
    # link to jenkins
    # link to git
    # local cmd checking

    #TODO : 
    # pylint static code analyser
    # bandit static code analyser
    
    # Start the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        reload=True,
        workers=1
    )

if __name__ == "__main__":
    start()