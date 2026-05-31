from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from core.database import supabase
from core.config import RESEND_API_KEY, ADMIN_EMAIL
import resend

router = APIRouter()
resend.api_key = RESEND_API_KEY

class ContactRequest(BaseModel):
    name: str
    email: str
    company: str = None
    message: str

@router.post("/contact")
async def submit_contact(data: ContactRequest):
    # Save to Supabase
    supabase.table("leads").insert({
        **data.dict(),
        "created_at": datetime.utcnow().isoformat()
    }).execute()

    # Send email notification
    resend.Emails.send({
        "from": "Vision Logistics <onboarding@resend.dev>",
        "to": ADMIN_EMAIL,
        "subject": f"New Consultation Request from {data.company or data.name}",
        "html": f"""
            <h2>New Lead</h2>
            <p><strong>Name:</strong> {data.name}</p>
            <p><strong>Email:</strong> {data.email}</p>
            <p><strong>Company:</strong> {data.company or 'N/A'}</p>
            <p><strong>Message:</strong> {data.message}</p>
        """
    })

    return {"status": "success", "message": "Request received"}