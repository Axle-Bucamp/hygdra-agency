from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
from datetime import datetime
import json
from HygdraAgency.DataModel.Task import Task, TaskStatus
from HygdraAgency.DataModel.Project import Project 
from HygdraAgency.DataModel.Service import Service 
from HygdraAgency.Agent.BaseAgent import BaseAgent
from HygdraAgency.Agent.Ollama import OllamaClient, OllamaModelConfig, OllamaPrompt, OllamaResponse
from pathlib import Path
import subprocess
import os
import pytest
import asyncio


# --- Tester Agent ---
# until better version only do static test
class TestResult(BaseModel):
    passed: int
    failed: int
    skipped: int
    duration: float
    details: List[Dict]

class SonarQubeConfig(BaseModel):
    host_url: str = "http://127.0.0.1:9000"
    token: str = ""
    project_key: str = "brawl-anything"
    sources: str = "."

class TesterAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            "QA", 
            "Quality Assurance",
            OllamaModelConfig(model_name="codellama", temperature=0.2)
        )
        self.sonar_config = SonarQubeConfig()
        
    async def generate_tests(self, task: Task, code_content: str) -> str:
        """Generate test cases using CodeLlama"""
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Create pytest test cases for this code:
                
                Task Description: {task.description}
                
                Code:
                {code_content}
                
                Generate comprehensive pytest test cases including:
                - Unit tests
                - Integration tests if applicable
                - Edge cases
                - Error scenarios
                Include proper assertions and documentation.
                """,
                system="You are a QA engineer specializing in Python testing. Write comprehensive, production-quality tests."
            )
            
            return await ollama.generate(prompt)

    async def run_pytest(self, test_file: str) -> TestResult:
        """Run pytest and collect results"""
        try:
            # Create a temporary pytest configuration
            pytest_args = [
                "-v",
                "--json-report",
                "--json-report-file=test_results.json",
                test_file
            ]
            
            # Run pytest in a separate process
            process = await asyncio.create_subprocess_exec(
                "pytest",
                *pytest_args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Parse the JSON report
            try:
                with open("test_results.json") as f:
                    results = json.load(f)
                
                return TestResult(
                    passed=results.get("summary", {}).get("passed", 0),
                    failed=results.get("summary", {}).get("failed", 0),
                    skipped=results.get("summary", {}).get("skipped", 0),
                    duration=results.get("duration", 0),
                    details=results.get("tests", [])
                )
            except FileNotFoundError:
                self.logger.error("Test results file not found")
                return TestResult(passed=0, failed=1, skipped=0, duration=0, details=[])
                
        except Exception as e:
            self.logger.error(f"Error running pytest: {str(e)}")
            return TestResult(passed=0, failed=1, skipped=0, duration=0, details=[])

    async def run_fastapi_tests(self, app_module: str) -> TestResult:
        """Run FastAPI endpoint tests"""
        async with OllamaClient(self.ollama_config) as ollama:
            # Generate API tests
            prompt = OllamaPrompt(
                prompt=f"""
                Create FastAPI test cases using TestClient for the module: {app_module}
                Include tests for:
                - Different HTTP methods
                - Status codes
                - Response validation
                - Error cases
                Use pytest fixtures and proper assertions.
                """,
                system="You are a QA engineer specializing in FastAPI testing."
            )
            
            api_tests = await ollama.generate(prompt)
            
            # Save generated tests to a temporary file
            test_file = "test_api.py"
            with open(test_file, "w") as f:
                f.write(api_tests)
            
            # Run the tests
            return await self.run_pytest(test_file)

    async def run_sonar_analysis(self) -> dict:
        """Run SonarQube analysis"""
        try:
            cmd = [
                "sonar-scanner",
                f"-Dsonar.projectKey={self.sonar_config.project_key}",
                f"-Dsonar.sources={self.sonar_config.sources}",
                f"-Dsonar.host.url={self.sonar_config.host_url}",
                f"-Dsonar.token={self.sonar_config.token}",
                "-Dsonar.python.coverage.reportPaths=coverage.xml",
                "-Dsonar.python.xunit.reportPath=test-results.xml"
            ]
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            # Get analysis results from SonarQube API
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.sonar_config.host_url}/api/measures/component",
                    params={
                        "component": self.sonar_config.project_key,
                        "metricKeys": "bugs,vulnerabilities,code_smells,coverage,duplicated_lines_density"
                    },
                    headers={"Authorization": f"Bearer {self.sonar_config.token}"}
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            measure["metric"]: measure["value"]
                            for measure in data.get("component", {}).get("measures", [])
                        }
                    else:
                        return {"error": "Failed to fetch SonarQube results"}
                        
        except Exception as e:
            self.logger.error(f"Error running SonarQube analysis: {str(e)}")
            return {"error": str(e)}

    async def run_tests(self, task: Task) -> dict:
        """Main testing method"""
        try:
            # Get code content from task artifacts or repository
            code_content = task.artifacts.get("code", "")
            
            # Generate and run unit tests
            unit_tests = await self.generate_tests(task, code_content)
            with open("test_unit.py", "w") as f:
                f.write(unit_tests)
            
            unit_results = await self.run_pytest("test_unit.py")
            
            # Run FastAPI tests if applicable
            api_results = None
            if "fastapi" in code_content.lower():
                api_results = await self.run_fastapi_tests(task.artifacts.get("app_module", "main"))
            
            # Run SonarQube analysis
            sonar_results = await self.run_sonar_analysis()
            
            # Compile comprehensive test report
            test_report = {
                "unit_tests": {
                    "passed": unit_results.passed,
                    "failed": unit_results.failed,
                    "skipped": unit_results.skipped,
                    "duration": unit_results.duration,
                    "details": unit_results.details
                },
                "api_tests": {
                    "passed": api_results.passed,
                    "failed": api_results.failed,
                    "skipped": api_results.skipped,
                    "duration": api_results.duration,
                    "details": api_results.details
                } if api_results else None,
                "code_quality": sonar_results,
                "recommendations": await self.generate_recommendations(
                    unit_results, 
                    api_results, 
                    sonar_results
                )
            }
            
            return test_report
            
        except Exception as e:
            self.logger.error(f"Error in test execution: {str(e)}")
            return {
                "error": str(e),
                "unit_tests": {"passed": 0, "failed": 1, "skipped": 0},
                "api_tests": None,
                "code_quality": {"error": "Analysis failed"}
            }

    async def generate_recommendations(
        self,
        unit_results: TestResult,
        api_results: Optional[TestResult],
        sonar_results: dict
    ) -> str:
        """Generate recommendations based on test results"""
        async with OllamaClient(self.ollama_config) as ollama:
            prompt = OllamaPrompt(
                prompt=f"""
                Based on these test results, provide recommendations for improvement:
                
                Unit Test Results:
                {json.dumps(unit_results.dict(), indent=2)}
                
                API Test Results:
                {json.dumps(api_results.dict(), indent=2) if api_results else "N/A"}
                
                Code Quality Results:
                {json.dumps(sonar_results, indent=2)}
                
                Provide specific, actionable recommendations for:
                1. Improving test coverage
                2. Fixing failures
                3. Addressing code quality issues
                4. Enhancing overall code reliability
                """,
                system="You are a senior QA engineer providing technical recommendations."
            )
            
            return await ollama.generate(prompt)