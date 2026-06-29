import os
import json
import re
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


def extract_json_from_text(text):
    """
    Tries to extract a JSON object from model output.
    This helps when the model returns ```json ... ``` or extra text.
    """
    if not text:
        raise ValueError("Empty response from Groq.")

    cleaned = text.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    match = re.search(r"\{.*\}", cleaned, re.DOTALL)

    if not match:
        raise ValueError(f"No JSON object found in Groq response: {cleaned}")

    return json.loads(match.group(0))


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
You are evaluating whether submitted platform content appears more likely AI-generated, human-written, or uncertain.

Classify the text as exactly one of:
- ai
- human
- uncertain

You are NOT judging whether the writing is good.
You are judging whether the writing has signs of AI generation.

Treat these as AI-like signals:
- generic polished explanations
- broad claims without personal details
- phrases like "it is important to note", "furthermore", "in conclusion"
- balanced essay-like structure
- corporate or academic-sounding filler
- predictable transitions
- no specific personal experience
- smooth but generic wording

Treat these as human-like signals:
- specific personal details
- casual or uneven phrasing
- unusual voice
- typos, slang, or informal rhythm
- concrete lived experience
- emotionally specific observations

Use "uncertain" when evidence is mixed.

Return only valid JSON.
Do not use markdown.
Do not wrap the JSON in backticks.
Do not include any explanation outside the JSON.

Required JSON format:
{{
  "classification": "ai",
  "confidence": 0.82,
  "reason": "Short reason here."
}}

Submitted text:
{text}
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "You are a strict JSON API. Return only valid JSON with no markdown."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.0,
        )

        raw_output = response.choices[0].message.content

        parsed = extract_json_from_text(raw_output)

        classification = parsed.get("classification", "uncertain").lower().strip()
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


def combine_signal_scores(llm_signal, stylometric_signal):
    """
    Final AI-likelihood score =
    LLM AI-likelihood * 0.60 + Stylometric AI-likelihood * 0.40
    """

    llm_score = float(llm_signal["ai_likelihood"])
    stylometric_score = float(stylometric_signal["ai_likelihood"])

    combined_score = (llm_score * 0.60) + (stylometric_score * 0.40)
    combined_score = round(combined_score, 2)

    if combined_score >= 0.70:
        attribution = "likely_ai"
    elif combined_score <= 0.39:
        attribution = "likely_human"
    else:
        attribution = "uncertain"

    return {
        "attribution": attribution,
        "confidence": combined_score,
        "llm_score": round(llm_score, 2),
        "stylometric_score": round(stylometric_score, 2),
        "weights": {
            "llm_signal": 0.60,
            "stylometric_signal": 0.40
        }
    }