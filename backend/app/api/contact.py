from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from core.database import supabase

router = APIRouter()

class ContactRequest(BaseModel):
    name: str
    email: str
    company: str = None
    message: str

@router.post("/contact")
async def submit_contact(data: ContactRequest):
    supabase.table("leads").insert({
        **data.dict(),
        "created_at": datetime.utcnow().isoformat()
    }).execute()
    return {"status": "success", "message": "Request received"}
