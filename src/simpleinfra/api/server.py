"""REST API server for SimpleInfra.

Allows remote execution via HTTP API.
Useful for CI/CD integration and web dashboards.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, BackgroundTasks
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

from .client import SimpleInfraClient


if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="SimpleInfra API",
        description="REST API for infrastructure automation",
        version="0.1.0",
    )

    # In-memory task execution tracker
    task_results: dict[str, dict[str, Any]] = {}


    class TaskRequest(BaseModel):
        """Request to execute a task."""
        file_path: str
        task_name: str | None = None
        dry_run: bool = False


    class ServerCreate(BaseModel):
        """Create a server definition."""
        name: str
        host: str
        user: str = "root"
        key: str | None = None
        port: int = 22


    class VariableCreate(BaseModel):
        """Set a variable."""
        name: str
        value: str | int | bool


    @app.get("/")
    async def root():
        """API health check."""
        return {"status": "ok", "service": "SimpleInfra API"}


    @app.post("/tasks/execute")
    async def execute_task(request: TaskRequest, background_tasks: BackgroundTasks):
        """Execute a task from a .si file."""
        try:
            client = SimpleInfraClient()
            result = await client.execute_from_file(request.file_path, request.task_name)
            return {"success": True, "result": result}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    @app.post("/tasks/validate")
    async def validate_file(file_path: str):
        """Validate a .si file."""
        try:
            client = SimpleInfraClient()
            document = client.load_from_file(file_path)
            return {
                "valid": True,
                "tasks": len(document.tasks),
                "servers": len(document.servers),
                "variables": len(document.variables),
            }
        except Exception as e:
            return {"valid": False, "error": str(e)}


    @app.post("/servers")
    async def create_server(server: ServerCreate):
        """Create a server definition."""
        # In production, this would persist to database
        return {"success": True, "server": server.dict()}


    @app.post("/variables")
    async def create_variable(variable: VariableCreate):
        """Set a variable."""
        return {"success": True, "variable": variable.dict()}


    @app.get("/tasks/{task_id}/status")
    async def get_task_status(task_id: str):
        """Get status of a running task."""
        if task_id not in task_results:
            raise HTTPException(status_code=404, detail="Task not found")
        return task_results[task_id]


    def run_server(host: str = "0.0.0.0", port: int = 8000):
        """Run the API server."""
        try:
            import uvicorn
            uvicorn.run(app, host=host, port=port)
        except ImportError:
            raise ImportError(
                "uvicorn is required to run the API server. "
                "Install with: pip install 'simpleinfra[api]'"
            )


# Usage:
# python -m simpleinfra.api.server
# Or programmatically:
# from simpleinfra.api.server import run_server
# run_server()

# Example API calls:
# curl -X POST http://localhost:8000/tasks/execute \
#   -H "Content-Type: application/json" \
#   -d '{"file_path": "deploy.si", "task_name": "Deploy App"}'
#
# curl http://localhost:8000/tasks/123/status
