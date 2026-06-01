from fastapi import APIRouter, UploadFile, File
from core.database import supabase
from core.config import GEMINI_API_KEY
import httpx
import base64
import json
import os

router = APIRouter()

@router.post("/visionops/analyze")
async def analyze_document(file: UploadFile = File(...)):
    contents = await file.read()
    base64_file = base64.b64encode(contents).decode("utf-8")
    mime_type = file.content_type or "application/pdf"

    prompt = """Analyze this operational document and respond ONLY with a JSON object, no preamble or markdown backticks:
{
  "document_type": "Invoice | Shipping Manifest | Purchase Order | Delivery Report | Other",
  "extracted": {
    "shipment_id": "",
    "customer": "",
    "amount": "",
    "destination": "",
    "date": ""
  },
  "risk_score": 0,
  "status": "On Track | At Risk | Delayed | Critical",
  "missing_items": [],
  "recommended_action": "",
  "summary": ""
}"""

    payload = {
        "contents": [
            {
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": base64_file
                        }
                    },
                    {"text": prompt}
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={GEMINI_API_KEY}",
            json=payload
        )
        response.raise_for_status()
        data = response.json()

    raw = data["candidates"][0]["content"]["parts"][0]["text"]
    raw = raw.strip().replace("```json", "").replace("```", "").strip()
    result = json.loads(raw)

    # Save to Supabase
    doc = supabase.table("documents").insert({
        "filename": file.filename,
        "document_type": result.get("document_type"),
        "extracted_data": result.get("extracted"),
    }).execute()

    doc_id = doc.data[0]["id"]

    supabase.table("insights").insert({
        "document_id": doc_id,
        "risk_score": result.get("risk_score"),
        "status": result.get("status"),
        "recommended_action": result.get("recommended_action"),
        "summary": result.get("summary"),
    }).execute()

    return {
        "document_id": doc_id,
        "document_type": result.get("document_type"),
        "extracted": result.get("extracted"),
        "risk_score": result.get("risk_score"),
        "status": result.get("status"),
        "missing_items": result.get("missing_items"),
        "recommended_action": result.get("recommended_action"),
        "summary": result.get("summary"),
    }