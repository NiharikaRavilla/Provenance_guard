import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def _parse_model_json(raw_output):
    cleaned = raw_output.strip()

    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        cleaned = "\n".join(lines).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(cleaned[start:end + 1])
        raise


def classify_with_groq(text):
    """
    First detection signal.

    Returns:
    {
        "classification": "ai" | "human" | "uncertain",
        "confidence": float,
        "ai_likelihood": float,
        "reason": str
    }
    """

    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        return {
            "classification": "uncertain",
            "confidence": 0.5,
            "ai_likelihood": 0.5,
            "reason": "GROQ_API_KEY was not found, so the system returned an uncertain fallback result."
        }

    client = Groq(api_key=api_key)

    prompt = f"""
You are part of a content attribution system for a creative writing platform.

Analyze the submitted text and decide whether it appears:
- ai
- human
- uncertain

Important:
- Do not claim proof of authorship.
- Be conservative about labeling human creative work as AI-generated.
- Return only valid JSON.
- Confidence must be between 0.0 and 1.0.

Return this exact JSON structure:
{{
  "classification": "ai OR human OR uncertain",
  "confidence": 0.0,
  "reason": "short explanation"
}}

Text to analyze:
\"\"\"
{text}
\"\"\"
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You return only valid JSON for content attribution analysis."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.2,
        )

        raw_output = response.choices[0].message.content.strip()
        parsed = _parse_model_json(raw_output)

        classification = parsed.get("classification", "uncertain").lower()
        confidence = float(parsed.get("confidence", 0.5))
        reason = parsed.get("reason", "No reason provided.")

        if classification not in ["ai", "human", "uncertain"]:
            classification = "uncertain"

        confidence = max(0.0, min(confidence, 1.0))

        if classification == "ai":
            ai_likelihood = confidence
        elif classification == "human":
            ai_likelihood = 1 - confidence
        else:
            ai_likelihood = 0.5

        return {
            "classification": classification,
            "confidence": round(confidence, 2),
            "ai_likelihood": round(ai_likelihood, 2),
            "reason": reason
        }

    except Exception as error:
        return {
            "classification": "uncertain",
            "confidence": 0.5,
            "ai_likelihood": 0.5,
            "reason": f"Groq classification failed, so the system returned an uncertain fallback result. Error: {str(error)}"
        }


def convert_signal_to_attribution(signal_result):
    ai_likelihood = signal_result["ai_likelihood"]

    if ai_likelihood >= 0.70:
        return "likely_ai"

    if ai_likelihood <= 0.39:
        return "likely_human"

    return "uncertain"
