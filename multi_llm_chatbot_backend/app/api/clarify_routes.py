from fastapi import APIRouter, Body
from app.llm.mistral_client import MistralClient
from app.models.persona import Persona
from app.core.orchestrator import ChatOrchestrator
from pydantic import BaseModel
from app.core.clarifying_orchestrator import ClarifyingOrchestrator

router = APIRouter()

orchestrator = ClarifyingOrchestrator()

class UserInput(BaseModel):
    message: str

@router.post("/clarify")
async def clarify_input(user_input: UserInput):
    result = orchestrator.process_input(user_input.message)
    return result