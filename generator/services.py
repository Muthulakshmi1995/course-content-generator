import asyncio
import json
import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

def build_prompt(topic_title):
    return f"""
You are an expert educational content generator. Create useful, accurate learning
material for a student studying: {topic_title!r}.
Return ONLY valid JSON matching this exact structure:
{{
  "notes": "Detailed, well-organized study notes as plain text. Use headings where useful.",
  "keyPoints": ["Important point 1", "Important point 2"],
  "summary": "A concise summary of the topic.",
  "quiz": {{
    "title": "Knowledge Check",
    "description": "Choose the best answer for each question.",
    "questions": [
      {{
        "questionText": "Question text?",
        "options": [
          {{"text": "Option A", "isCorrect": false}},
          {{"text": "Option B", "isCorrect": true}},
          {{"text": "Option C", "isCorrect": false}},
          {{"text": "Option D", "isCorrect": false}}
        ]
      }}
    ]
  }}
}}
Create 8 multiple-choice questions, each with 4 options and exactly one correct answer.
Do not include markdown fences or commentary outside the JSON.
"""

async def _request_gemini(prompt):
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Gemini API key is missing. Add GEMINI_API_KEY to your .env file.")
    url = f"{settings.GEMINI_API_URL}?key={settings.GEMINI_API_KEY}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.4},
    }
    response = await asyncio.to_thread(
        requests.post, url, json=payload, timeout=settings.GEMINI_TIMEOUT
    )
    if response.status_code >= 400:
        try:
            detail = response.json().get("error", {}).get("message", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"Gemini API error ({response.status_code}): {detail}")
    data = response.json()
    try:
        raw = data["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(raw)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError("Gemini returned an invalid or unexpected JSON response.") from exc
    validate_generated_payload(parsed)
    return parsed

def validate_generated_payload(data):
    if not isinstance(data, dict):
        raise ValueError("AI response must be a JSON object.")
    for key in ("notes", "summary", "keyPoints", "quiz"):
        if key not in data:
            raise ValueError(f"AI response is missing required field: {key}")
    if not isinstance(data["notes"], str) or not isinstance(data["summary"], str):
        raise ValueError("Notes and summary must be strings.")
    if not isinstance(data["keyPoints"], list):
        raise ValueError("Key points must be an array.")
    quiz = data["quiz"]
    if not isinstance(quiz, dict) or not isinstance(quiz.get("questions"), list):
        raise ValueError("Quiz questions are missing or invalid.")
    for question in quiz["questions"]:
        if not isinstance(question.get("questionText"), str) or not isinstance(question.get("options"), list):
            raise ValueError("A quiz question has invalid data.")
        if not question["options"]:
            raise ValueError("A quiz question must have at least one option.")
        if sum(1 for option in question["options"] if option.get("isCorrect") is True) != 1:
            raise ValueError("Each quiz question must have exactly one correct answer.")

def generate_course_payload(topic_title):
    return asyncio.run(_request_gemini(build_prompt(topic_title)))
