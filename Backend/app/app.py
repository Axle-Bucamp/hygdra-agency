from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from enum import Enum
from fastapi import FastAPI, HTTPException, File, UploadFile
from datetime import datetime
import requests
import json
from HygdraAgency.Agent.DeveloperAgent import DeveloperAgent
from HygdraAgency.Agent.DevOpsAgent import DevOpsAgent
from HygdraAgency.Agent.ProjectManagerAgent import ProjectManagerAgent
from HygdraAgency.Agent.TesterAgent import TesterAgent
from HygdraAgency.Agent.TaskAssignmentAgent import TaskAssignmentAgent
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Project import Project 
from HygdraAgency.DataModel.Service import Service 
import uvicorn
import os
import logfire
from typing import Annotated
from elasticsearch import Elasticsearch, helpers
import HygdraAgency.utils.rag as rag

#TODO
# connect retreive project instancce
# rag system per project, task

# add a get all project name
# add a get project properties
# add a file viewer vscode web for generated code
# persistent db project

# Sonarqube create project cmd
# link to jenkins
# link to git
# local cmd checking

# pylint static code analyser
# bandit static code analyser
# simple tchat function with agent
# continue or work on function to target specfic code

# Initialize agents
# --- API Routes ---
app = FastAPI()

logfire.configure()
#logfire.instrument_fastapi(app)

# Initialize agents
pm_agent = ProjectManagerAgent()
task_assigner = TaskAssignmentAgent()
dev_agent = DeveloperAgent()
devops_agent = DevOpsAgent()
tester_agent = TesterAgent()

available_agents = [dev_agent, tester_agent] # devops_agent
active_projects: Dict[str, Project] = {}

@app.post("/projects/")
async def create_project(name: str, description: str):
    """
    Creates a new project and initializes necessary resources for it.

    This endpoint accepts a project name and description, initializes the 
    project using the `pm_agent`, and then creates a directory to store 
    the project's generated code. The new project is added to the list of 
    active projects, and the RAG (Retrieval-Augmented Generation) system 
    is set up with a search index and the initial project document.

    The project details are stored in an internal dictionary of active projects,
    and the RAG system is initialized to facilitate document retrieval and 
    storage.

    Args:
        name (str): The name of the project to be created.
        description (str): A brief description of the project.

    Returns:
        Project: The initialized `Project` object representing the new project.
            This object contains details like `id`, `name`, and `description`.

    Example:
        POST /projects/
        {
            "name": "My New Project",
            "description": "This is a description of my new project."
        }

    Response:
        200 OK
        {
            "id": "12345",
            "name": "My New Project",
            "description": "This is a description of my new project."
            "task" : {}
        }

    Side Effects:
        - A directory is created for the project to store generated code.
        - The project is added to the active projects registry.
        - RAG search index is built for the new project.
        - A document representing the project is stored in the RAG system.

    Raises:
        - Any exception raised by `pm_agent.initialize_project` or `rag` methods 
          will be propagated as an HTTP error response.
    """
    project = await pm_agent.initialize_project(name, description)
    os.mkdir(f"generated_code/{project.id}")
    active_projects[project.id] = project
    
    rr = await rag.build_search_index(str(project.id))
    rr = await rag.store_document(context=rag.Deps(project, 5), document=rag.Document(project.name, "generated_code/{project.id}", project.description))
    return project

@app.post("/projects/{project_id}/ressources/")
async def create_file(project_id: str, file: UploadFile):
    """
    Uploads a file for a specific project and stores it in the RAG system.

    This endpoint allows users to upload a file to a specific project by its `project_id`. 
    The file is stored and indexed in the RAG (Retrieval-Augmented Generation) system for later use. 
    If the project is not currently active, an error message is returned.

    Args:
        project_id (str): The unique identifier of the project to which the file will be uploaded.
        file (UploadFile): The file to be uploaded. This file will be read and its contents stored.

    Returns:
        dict: A message indicating success or an error message if the project is not active.

    Response:
        200 OK
        {
            "message": "File for project {project_id} successfully uploaded!"
        }

        400 Bad Request (if project is not active)
        {
            "error": "Project not active",
            "project_id": "{project_id}"
        }

    Side Effects:
        - If the project is active, the uploaded file is stored and indexed in the RAG system using `rag.store_external_document`.
        - If the project is not active, no file is stored, and an error message is returned.

    Raises:
        - Any exceptions related to the file upload or `rag.store_external_document` may propagate as HTTP error responses.
    """
    contents = await file.read()
    if project_id in active_projects:
        project = active_projects[project_id]
        rag.store_document(rag.Deps(project, 5), rag.Document(project_id, file.filename, contents))
        return {"message": f"File for project {project_id} successfully uploaded!"}
    else:
        # Return an error if the project is not active
        return {"error": "Project not active", "project_id": project_id}

@app.post("/projects/get-all")
async def get_all():   
    return active_projects

@app.post("/projects/get-by-id")
async def get(project_id: str):  
    if project_id in active_projects :
        return active_projects[project_id]
    else :
        return {"error" : "no project with id"}

@app.post("/projects/get-by-name")
async def get(project_title: str):  
    active_projects_title = [project.title for pid, project in active_projects]
    if project_title in active_projects_title :
        return active_projects[active_projects_title.index(project_title)]
    else :
        return {"error" : "no project with title"}

@app.post("/projects/get-by-request")
async def get(request: str):  
    # all project rag and retreiver
    if 1 in [1,2] :
        return {"message" : "todo"}
    else :
        return {"error" : "no project with id"}

# get project per context  
@app.post("/projects/{project_id}/tchat/")
async def tchat_with_context(project_id: str, request:str):
    if project_id in active_projects :
        response = ProjectManagerAgent.tchat(active_projects[project_id], request)

    return {"request" : request, "response": response}

@app.post("/projects/{project_id}/next-task")
async def process_next_task(project_id: str):
    """
    Processes the next available task for a given project and assigns it to an agent.

    This endpoint handles the processing of the next task in the queue for a specific project.
    It assigns the task to an available agent, updates the task's status, and processes the task
    based on the agent's type (e.g., Developer, DevOps, or Tester). Once the task is completed,
    the task's status is updated to `DONE`, and the project task list is updated accordingly.

    If no tasks are available or if the project is not found, an appropriate message or error
    is returned.

    Args:
        project_id (str): The unique identifier of the project for which the next task will be processed.

    Returns:
        dict: A JSON object containing information about the processed task, the assigned agent,
              and the result of the task.

    Response:
        200 OK
        {
            "task": {
                "id": "123",
                "title": "Task Title",
                "status": "DONE",
                "assigned_to": "Agent Name"
            },
            "agent": "Agent Name",
            "result": "Task result or status"
        }

        404 Not Found (if project is not found)
        {
            "detail": "Project not found"
        }

    Side Effects:
        - The task's status is updated to `IN_PROGRESS` and then to `DONE` upon completion.
        - The task is assigned to an available agent, and the agent works on the task depending on their type.
        - The project task list is updated with the new task status.

    Raises:
        - HTTPException: If the project is not found in the `active_projects` registry, a `404 Not Found` error is raised.
    """
    if project_id not in active_projects:
        raise HTTPException(status_code=404, detail="Project not found")
    
    project = active_projects[project_id]
    task, assigned_agent = await task_assigner.assign_next_task(project, available_agents)
    
    if not task or not assigned_agent:
        return {"status": "no_tasks_available"}
    
    # Update task status
    task.status = TaskStatus.IN_PROGRESS
    task.assigned_to = assigned_agent.name
    result = ""

    # Process task based on agent type
    if isinstance(assigned_agent, DeveloperAgent):
        result = await assigned_agent.work_on_task(task, project)

    # work on later TODO
    elif isinstance(assigned_agent, DevOpsAgent):
        #result = await assigned_agent.deploy(task)
        pass

    elif isinstance(assigned_agent, TesterAgent):
        #result = await assigned_agent.run_tests(task)
        pass
    
    # Update task status based on result
    task.status = TaskStatus.DONE
    # project = await pm_agent.update_task_status(project, task.id, TaskStatus.DONE)
    
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