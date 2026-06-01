from fastapi import APIRouter, UploadFile, File
from core.database import supabase
from core.config import GEMINI_API_KEY
import google.generativeai as genai
import json
import tempfile
import os

router = APIRouter()
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-1.5-flash")

@router.post("/visionops/analyze")
async def analyze_document(file: UploadFile = File(...)):
    # Save file temporarily
    contents = await file.read()
    suffix = os.path.splitext(file.filename)[1] or ".pdf"
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        # Upload to Gemini
        uploaded = genai.upload_file(tmp_path, mime_type=file.content_type)

        # Analyze with Gemini
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

        response = model.generate_content([uploaded, prompt])
        raw = response.text.strip().replace("```json", "").replace("```", "")
        result = json.loads(raw)

    finally:
        os.unlink(tmp_path)

    # Save document to Supabase
    doc = supabase.table("documents").insert({
        "filename": file.filename,
        "document_type": result.get("document_type"),
        "extracted_data": result.get("extracted"),
    }).execute()

    doc_id = doc.data[0]["id"]

    # Save insight
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