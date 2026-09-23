import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from agents.orchestrator import TravelOrchestrator
from core.schemas import PlanTripResponse

app = FastAPI(title="Travalos Generic Travel OS", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = TravelOrchestrator()

class PlanTripRequest(BaseModel):
    message: str
    conversation_id: str

class ReplanRequest(BaseModel):
    conversation_id: str
    new_budget: Optional[float] = None
    new_deadline_minutes: Optional[int] = None
    new_deadline_str: Optional[str] = None
    new_optimization_mode: Optional[str] = "balanced"

class ConfirmRequest(BaseModel):
    plan_id: str
    conversation_id: str
    authorized_cost: float

@app.get("/health")
def health():
    return {"status": "healthy", "engine": "Travalos Generic Engine v3.0"}

@app.post("/api/plan-trip", response_model=PlanTripResponse)
def plan_trip(req: PlanTripRequest):
    return orchestrator.plan_mission(req.message, req.conversation_id)

@app.post("/api/replan", response_model=PlanTripResponse)
def replan(req: ReplanRequest):
    prior = orchestrator.session_store.get(req.conversation_id)
    if not prior:
        return PlanTripResponse(status="FAILED", why_this_plan="No active session found.")
    
    if req.new_budget:
        prior.has_budget = True
        prior.max_budget = req.new_budget
    if req.new_deadline_minutes:
        prior.has_deadline = True
        prior.deadline_minutes = req.new_deadline_minutes
        prior.arrival_deadline = req.new_deadline_str
    if req.new_optimization_mode:
        prior.optimization_mode = req.new_optimization_mode

    return orchestrator.plan_mission(
        f"Trip from {prior.origin} to {prior.destination} for {prior.travelers.total_count} people under ₹{prior.max_budget or 50000}",
        req.conversation_id
    )

@app.post("/api/confirm")
def confirm(req: ConfirmRequest):
    return {"status": "CONFIRMED", "plan_id": req.plan_id, "authorized_cost": req.authorized_cost}

@app.get("/api/debug/mission/{conversation_id}")
def debug_mission(conversation_id: str):
    m = orchestrator.session_store.get(conversation_id)
    return {"active_mission": m.dict() if m else None}

@app.get("/")
async def serve_index():
    index_file = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "index.html"))
    return FileResponse(index_file)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)