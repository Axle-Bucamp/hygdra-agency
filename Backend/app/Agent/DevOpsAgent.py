from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
from Backend.app.DataModel.Task import Task, TaskStatus
from Backend.app.DataModel.Project import Project 
from Backend.app.DataModel.Service import Service 
from Backend.app.Agent.BaseAgent import BaseAgent
from Backend.app.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse

from ansible_runner import run as ansible_run
import jenkins
from pathlib import Path
import yaml
import asyncio
import tempfile
import time
from github import Github

# --- DevOps Agent ---
# until beter version only write the code
class JenkinsConfig(BaseModel):
    url: str = "http://localhost:8080"
    username: str = "admin"
    token: str = ""
    
class GitHubConfig(BaseModel):
    token: str = "your-github-token"
    repo: str = "owner/repository"

class DeploymentConfig(BaseModel):
    environment: str
    ansible_playbook: str
    variables: Dict[str, str] = {}
    
class DeploymentResult(BaseModel):
    status: str
    steps_completed: List[str]
    environment: str
    logs: List[str]
    metrics: Dict[str, Any]

class DevOpsAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "DevOps", 
            "DevOps Engineer",
            OllamaModelConfig(model_name="codellama", temperature=0.2)
        )
        self.jenkins_config = JenkinsConfig()
        self.github_config = GitHubConfig()
    
    # generate but no execution yet   
    async def generate_ansible_playbook(self, task: Task, environment: str) -> str:
        """Generate Ansible playbook using CodeLlama"""
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Create an Ansible playbook for deploying this application:
                Task: {task.title}
                Description: {task.description}
                Environment: {environment}
                
                Include:
                - Host configuration
                - Package installation
                - Application deployment
                - Service configuration
                - Health checks
                
                Return only the YAML content for the playbook.
                """,
                system="You are a DevOps engineer specialized in Ansible automation."
            )
            
            return await ollama.generate(prompt)

    # generate but no execution yet 
    async def generate_jenkins_pipeline(self, task: Task) -> str:
        """Generate Jenkinsfile using CodeLlama"""
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Create a Jenkins pipeline for this deployment:
                Task: {task.title}
                Description: {task.description}
                
                Include stages for:
                - Checkout
                - Build
                - Test
                - Security scan
                - Deploy
                - Post-deployment tests
                
                Use pipeline syntax (Jenkinsfile format).
                """,
                system="You are a DevOps engineer specialized in Jenkins pipelines."
            )
            
            return await ollama.generate(prompt)

    # static code first 
    # local sonar project at worth
    async def run_security_checks(self, task: Task) -> dict:
        """Run security analysis using CodeLlama"""
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Analyze this deployment for security concerns:
                Task: {task.title}
                Description: {task.description}
                
                Check for:
                - Configuration vulnerabilities
                - Common security misconfigurations
                - Dependency vulnerabilities
                - Infrastructure security issues
                
                Return a JSON object with findings and recommendations.
                """,
                system="You are a security engineer specialized in deployment security."
            )
            
            return json.loads(await ollama.generate(prompt))

    # not now or using only known one
    async def run_jenkins_pipeline(self, pipeline_script: str) -> dict:
        """Execute Jenkins pipeline"""
        try:
            server = jenkins.Jenkins(
                self.jenkins_config.url,
                username=self.jenkins_config.username,
                password=self.jenkins_config.token
            )
            
            # Create pipeline job
            job_name = f"deploy-{int(time.time())}"
            server.create_job(job_name, jenkins.EMPTY_CONFIG_XML)
            
            # Update job with pipeline script
            config_xml = f"""
            <?xml version='1.1' encoding='UTF-8'?>
            <flow-definition plugin="workflow-job">
                <definition class="org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition" plugin="workflow-cps">
                    <script>{pipeline_script}</script>
                    <sandbox>true</sandbox>
                </definition>
            </flow-definition>
            """
            server.reconfig_job(job_name, config_xml)
            
            # Build job
            build_number = server.build_job(job_name)
            
            # Wait for build to complete
            while True:
                build_info = server.get_build_info(job_name, build_number)
                if not build_info.get("building"):
                    return {
                        "status": "success" if build_info.get("result") == "SUCCESS" else "failed",
                        "url": build_info.get("url"),
                        "duration": build_info.get("duration"),
                        "logs": server.get_build_console_output(job_name, build_number)
                    }
                await asyncio.sleep(10)
                
        except Exception as e:
            self.logger.error(f"Jenkins pipeline error: {str(e)}")
            return {"status": "failed", "error": str(e)}

    # not now or using known one 
    # git command 
    async def run_ansible_deployment(self, playbook_content: str, config: DeploymentConfig) -> dict:
        """Execute Ansible playbook"""
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.yml') as tmp:
                tmp.write(playbook_content)
                tmp.flush()
                
                # Run ansible-playbook
                result = ansible_run(
                    playbook=tmp.name,
                    inventory=f"{config.environment},",
                    extravars=config.variables,
                    json_mode=True
                )
                
                return {
                    "status": "success" if result.rc == 0 else "failed",
                    "stats": result.stats,
                    "host_events": result.events
                }
                
        except Exception as e:
            self.logger.error(f"Ansible deployment error: {str(e)}")
            return {"status": "failed", "error": str(e)}

    async def update_github_status(self, status: str, description: str):
        # Update GitHub deployment status
        try:
            g = Github(self.github_config.token)
            repo = g.get_repo(self.github_config.repo)
            
            # Create deployment status
            deployment = repo.create_deployment(
                ref="main",
                environment="staging",
                description=description
            )
            
            deployment.create_status(
                state=status,
                description=description,
                environment="staging"
            )
            
        except Exception as e:
            self.logger.error(f"GitHub status update error: {str(e)}")
    

    async def deploy(self, task: Task) -> DeploymentResult:
        """Main deployment method"""
        deployment_steps = []
        logs = []
        
        try:
            # Step 1: Generate deployment configurations
            deployment_steps.append("Generating configurations")
            playbook = await self.generate_ansible_playbook(task, "staging")
            pipeline = await self.generate_jenkins_pipeline(task)
            
            # Step 2: Security checks
            deployment_steps.append("Running security checks")
            security_results = await self.run_security_checks(task)
            if security_results.get("critical_issues", []):
                raise Exception("Critical security issues found")
            
            # Step 3: Run Jenkins pipeline
            deployment_steps.append("Running Jenkins pipeline")
            # await self.update_github_status("pending", "Starting deployment")
            jenkins_result = await self.run_jenkins_pipeline(pipeline)
            logs.extend(jenkins_result.get("logs", []))
            
            if jenkins_result["status"] != "success":
                # await self.update_github_status("failure", "Jenkins pipeline failed")
                raise Exception("Jenkins pipeline failed")
            
            # Step 4: Ansible deployment
            deployment_steps.append("Running Ansible deployment")
            ansible_result = await self.run_ansible_deployment(
                playbook,
                DeploymentConfig(
                    environment="staging",
                    ansible_playbook="deploy.yml",
                    variables={"app_version": task.version}
                )
            )
            
            if ansible_result["status"] != "success":
                # await self.update_github_status("failure", "Ansible deployment failed")
                raise Exception("Ansible deployment failed")
            
            # Step 5: Post-deployment checks
            deployment_steps.append("Running post-deployment checks")
            # Add your post-deployment health checks here
            
            # Update GitHub status
            # await self.update_github_status("success", "Deployment completed successfully")
            
            return DeploymentResult(
                status="deployed",
                steps_completed=deployment_steps,
                environment="staging",
                logs=logs,
                metrics={
                    "duration": jenkins_result.get("duration"),
                    "ansible_stats": ansible_result.get("stats"),
                    "security_issues": len(security_results.get("issues", []))
                }
            )
            
        except Exception as e:
            self.logger.error(f"Deployment error: {str(e)}")
            # await self.update_github_status("failure", str(e))
            return DeploymentResult(
                status="failed",
                steps_completed=deployment_steps,
                environment="staging",
                logs=logs + [str(e)],
                metrics={}
            )