from fastapi import APIRouter, UploadFile, File, HTTPException
from core.database import supabase
from core.config import GEMINI_API_KEY
import httpx
import base64
import json
import asyncio

router = APIRouter()

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"


async def call_gemini_with_retry(client: httpx.AsyncClient, payload: dict, max_retries: int = 3) -> dict:
    """Call the Gemini API with exponential backoff on 429s."""
    for attempt in range(max_retries):
        response = await client.post(
            GEMINI_URL,
            params={"key": GEMINI_API_KEY},
            json=payload,
        )

        if response.status_code == 429:
            if attempt < max_retries - 1:
                wait = 2 ** attempt  # 1s, 2s, 4s, 8s, 16s
                await asyncio.sleep(wait)
                continue
            raise HTTPException(
                status_code=429,
                detail="AI service rate limit exceeded. Please wait a moment and try again.",
            )

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            raise HTTPException(
                status_code=502,
                detail=f"Upstream Gemini error: {e.response.status_code}",
            )

        return response.json()

    # Should never reach here, but just in case
    raise HTTPException(status_code=429, detail="Rate limit exceeded after retries.")


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
                            "data": base64_file,
                        }
                    },
                    {"text": prompt},
                ]
            }
        ]
    }

    async with httpx.AsyncClient(timeout=30) as client:
        data = await call_gemini_with_retry(client, payload)

    # Parse Gemini response
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        raw = raw.strip().replace("```json", "").replace("```", "").strip()
        result = json.loads(raw)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse Gemini response: {e}")

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