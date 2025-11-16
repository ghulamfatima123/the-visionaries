# app.py
import os
import re
import json
import logging
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
load_dotenv()   

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from google import genai
from google.genai import types

# --- CONFIG ---
API_KEY = os.getenv("GEMINI_API_KEY")  # set this in your deployment environment
if not API_KEY:
    raise RuntimeError("Missing GEMINI_API_KEY environment variable")

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB - tune per your needs
MODEL_NAME = "gemini-2.5-flash"      # change if you have another model

# --- CLIENT SETUP ---
client = genai.Client(api_key=API_KEY)

# --- FASTAPI SETUP ---
app = FastAPI(title="CrowdDetector API", version="1.0")
logger = logging.getLogger("uvicorn.error")


class CrowdResult(BaseModel):
    people_count: Optional[int]
    crowd_score: Optional[int]            # 1-10
    crowd_label: Optional[str]            # e.g., "Low", "Medium", "High"
    confidence: Optional[float]           # 0-100
    rationale: Optional[str]
    # Departure board detection fields
    screen_detected: Optional[bool]       # Whether a screen/monitor/board was detected
    departure_type: Optional[str]         # e.g., "flight", "train", "bus", "none"
    departure_info: Optional[List[Dict[str, Any]]]  # List of departure entries with details


def extract_first_json(text: str):
    """
    Try to find a JSON object inside the response text.
    Returns Python object or raises ValueError.
    """
    # Greedy-ish regex to capture the first balanced-looking JSON object
    m = re.search(r"(\{[\s\S]*\})", text)
    if not m:
        raise ValueError("No JSON object found in model response")
    candidate = m.group(1)

    # Try progressive trimming in case of trailing commas or minor issues
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        # attempt to strip trailing commas that often break JSON
        cleaned = re.sub(r",\s*}", "}", candidate)
        cleaned = re.sub(r",\s*]", "]", cleaned)
        return json.loads(cleaned)


SYSTEM_PROMPT = """
You are a safety-first multimodal vision assistant. Analyze the provided image and return ONLY a JSON object (no surrounding explanation or markdown).

Required fields:
 - people_count: integer (estimated number of people visible in the image)
 - crowd_score: integer 1-10 (1 = empty, 10 = extremely crowded)
 - crowd_label: string ("Low", "Medium", or "High")
 - confidence: float 0-100 (how confident you are about the count & score)
 - rationale: short string (1-2 sentences) explaining how you derived the result

Additional fields for departure board detection:
 - screen_detected: boolean (true if any screen, monitor, display board, or information board is visible in the image)
 - departure_type: string (one of: "flight", "train", "bus", "subway", "ferry", or "none" if no departure board detected)
 - departure_info: array of objects (only if screen_detected is true). Each object should contain:
   * flight_number or train_number or route_number: string (the identifier)
   * destination: string (destination city/station name)
   * departure_time: string (scheduled departure time if visible)
   * status: string (e.g., "On Time", "Delayed", "Boarding", "Gate", "Platform", etc.)
   * gate or platform: string (if visible on the board)
   
   If multiple departures are visible, include all of them in the array. If only partial information is visible, include what you can read.

If uncertain, set confidence lower and approximate the people_count as best as possible.
If no screen/board is detected, set screen_detected to false, departure_type to "none", and departure_info to an empty array.

Return the JSON object and nothing else.
"""

@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/analyze-image", response_model=CrowdResult)
async def analyze_image(file: UploadFile = File(...), user_id: Optional[str] = None):
    """
    Accepts multipart/form-data with a single image file.
    Returns a structured JSON with crowd analysis and departure board information (if detected).
    Fields include: people_count, crowd_score, crowd_label, confidence, rationale,
    screen_detected, departure_type, and departure_info.
    """
    # 1) Basic validations
    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"File too large. Max {MAX_UPLOAD_BYTES} bytes allowed.")

    # 2) Build image PART for Gemini
    try:
        image_part = types.Part.from_bytes(data=contents, mime_type=file.content_type or "image/jpeg")
    except Exception as e:
        logger.exception("Failed to create image part")
        raise HTTPException(status_code=500, detail="Failed to prepare image for analysis")

    # 3) Prompt + call Gemini (synchronous)
    prompt = SYSTEM_PROMPT.strip()
    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=[prompt, image_part],
            # optionally set other params like temperature, max_output_tokens if SDK supports them:
            # temperature=0.0, max_output_tokens=400
        )
        raw_text = response.text or ""
    except Exception as e:
        logger.exception("Gemini API call failed")
        raise HTTPException(status_code=502, detail="Vision model request failed")

    # 4) Extract JSON from response text robustly
    try:
        parsed = extract_first_json(raw_text)
    except Exception as e:
        logger.exception("Failed to parse JSON from model response", exc_info=e)
        # As a fallback, return a structured error payload that the frontend can handle
        raise HTTPException(status_code=502, detail="Model returned unexpected output format")

    # 5) Sanitize/normalize the parsed data into expected fields
    try:
        people_count = parsed.get("people_count")
        # try to coerce numeric types
        if people_count is not None:
            people_count = int(people_count)

        crowd_score = parsed.get("crowd_score")
        if crowd_score is not None:
            crowd_score = int(crowd_score)
            crowd_score = max(1, min(10, crowd_score))

        crowd_label = parsed.get("crowd_label")
        confidence = parsed.get("confidence")
        if confidence is not None:
            confidence = float(confidence)

        rationale = parsed.get("rationale", "")

        # Departure board fields
        screen_detected = parsed.get("screen_detected")
        if screen_detected is not None:
            screen_detected = bool(screen_detected)
        
        departure_type = parsed.get("departure_type")
        if departure_type and isinstance(departure_type, str):
            departure_type = departure_type.lower()
            valid_types = ["flight", "train", "bus", "subway", "ferry", "none"]
            if departure_type not in valid_types:
                departure_type = "none"
        else:
            departure_type = "none" if not screen_detected else None

        departure_info = parsed.get("departure_info")
        if departure_info is None:
            departure_info = []
        elif not isinstance(departure_info, list):
            departure_info = []
        else:
            # Ensure each entry is a dict
            departure_info = [entry for entry in departure_info if isinstance(entry, dict)]

        result = CrowdResult(
            people_count=people_count,
            crowd_score=crowd_score,
            crowd_label=crowd_label,
            confidence=confidence,
            rationale=rationale,
            screen_detected=screen_detected,
            departure_type=departure_type,
            departure_info=departure_info
        )
    except Exception as e:
        logger.exception("Failed to normalize model JSON")
        raise HTTPException(status_code=500, detail="Failed to normalize model response")

    return JSONResponse(status_code=200, content=result.dict())
