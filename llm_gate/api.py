import os
import uvicorn
from contextlib import asynccontextmanager
try:
    from fastapi import FastAPI, HTTPException, Depends
    from pydantic import BaseModel
except ImportError:
    raise ImportError("FastAPI is required for the web server mode. Install with `pip install llm-gate[server]`")

from llm_gate.gate import Gate

# Singleton Gate instance
gate_instance = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global gate_instance
    config_path = os.getenv("LLMGATE_CONFIG", "llm-gate.yaml")
    # Initialize the engine on startup
    gate_instance = Gate(primary_model=os.getenv("LLMGATE_PRIMARY", "anthropic/claude-3-opus-20240229"))
    yield
    # Cleanup on shutdown
    gate_instance = None

app = FastAPI(
    title="llm-gate API",
    description="Microservice for Tier-based LLM Routing",
    version="0.2.0",
    lifespan=lifespan
)

class RouteRequest(BaseModel):
    task: str
    criticality: str = "medium"

@app.post("/v1/route")
async def route_task(req: RouteRequest):
    if not gate_instance:
        raise HTTPException(status_code=500, detail="Gate engine not initialized")
    
    decision = gate_instance.route(req.task, criticality=req.criticality)
    return decision.__dict__

@app.get("/health")
async def health():
    return {"status": "healthy", "engine": "llm-gate"}


@app.post("/route")
async def route_task_alias(req: RouteRequest):
    """Convenience alias matching the integration test client path."""
    return await route_task(req)


def start_server(port: int = 8000, host: str = "0.0.0.0") -> None:
    """Boot the uvicorn server for the llm-gate microservice."""
    uvicorn.run(app, host=host, port=port)
