# Project Management API

This project provides an API to manage the lifecycle of software development projects. The API uses FastAPI and integrates with several agents, such as ProjectManagerAgent, DeveloperAgent, DevOpsAgent, TesterAgent, and others. The system assigns tasks to agents, processes them, and updates project statuses based on task results. It also integrates with various tools like Jenkins, GitHub, and SonarQube.

## Features

- **Create and manage projects**: Initialize and track projects.
- **Assign tasks to agents**: Automatically assign tasks to agents based on availability.
- **Process tasks**: Developers, DevOps, and Testers work on tasks, and their results are tracked.
- **Integration with Jenkins, GitHub, and SonarQube**: For DevOps tasks and code quality checks.
- **Logging**: The project integrates with `logfire` for structured logging.

## Setup

### Prerequisites

1. **Python 3.8+**
2. **Virtual Environment (Optional but recommended)**

To set up the project, clone the repository and install dependencies as follows:

### Install Dependencies

```bash
# Clone the repository
git clone <repository_url>
cd <project_directory>

# Create a virtual environment (optional)
python3 -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

# Install dependencies from requirements.txt
pip install -r requirements.txt
```

### Environment Variables

The project requires several environment variables for configuring external services. Create a `.env` file or set the variables directly in your terminal.

```env
HOST=0.0.0.0
PORT=8000
OLLAMA_HOST=http://localhost:11434
JENKINS_URL=http://localhost:8080
JENKINS_USER=admin
JENKINS_TOKEN=sM]tVzQ+b*kWfP6
GITHUB_TOKEN=your_github_token
SONAR_TOKEN=your_sonar_token
SONAR_URL=http://localhost:9000
```

### Running the Application

#### Using local python

To start the application:

```bash
# Run the application
python Backend/app.py
```

#### Using docker

To start the application:

```bash
# Run the application
docker compose up -d
```

The application will be accessible at `http://0.0.0.0:7060` by default, or use the port you configured via the environment variables.

## API Documentation

You can interact with the API directly via the automatically generated FastAPI documentation. Once the server is running, visit the following URL:

[http://localhost:7060/docs](http://localhost:7060/docs)

### Endpoints

#### Create Project

**POST** `/projects/`

Creates a new project with the given name and description.

**Request Body:**
```json
{
  "name": "Project Name",
  "description": "Project description"
}
```

**Response:**
```json
{
  "id": "project_id",
  "name": "Project Name",
  "description": "Project description",
  "status": "initialized"
}
```

#### Process Next Task

**POST** `/projects/{project_id}/next-task`

Assigns and processes the next available task for the project specified by `project_id`. If no tasks are available, it returns a `no_tasks_available` status.

**Response:**
```json
{
  "task": {
    "id": "task_id",
    "name": "Task name",
    "status": "DONE",
    "assigned_to": "Agent Name"
  },
  "agent": "Agent Name",
  "result": "result_of_task_processing"
}
```

#### Available Agents

- **ProjectManagerAgent**: Responsible for initializing and managing projects.
- **TaskAssignmentAgent**: Assigns tasks to available agents.
- **DeveloperAgent**: Works on development-related tasks.
- **DevOpsAgent**: Handles DevOps tasks, such as deployments.
- **TesterAgent**: Runs tests and quality checks.

## Logging

The project uses `logfire` for structured logging, and logs will be automatically captured and sent to a centralized log management service if configured.

## Project Structure

```
/Agent               # Contains all agent implementations (ProjectManagerAgent, DeveloperAgent, etc.)
/DataModel           # Contains data models like Task, Project, and Service
app.py               # Main entry point for the FastAPI application
requirements.txt     # List of required Python dependencies
setup.py             # Python package setup script
README.md            # Project documentation
```

## Contribution

Feel free to contribute by submitting issues or pull requests. Make sure to follow the coding standards and write tests for any new features you add.

## License

This project is licensed under the MIT License.

## TODO
- finalise the agent chain of thought and key concept
- Dockerisation
- prepare for distant environment and cloud server

## Updated at:
2025-01-25T07:48:25.338-05:00