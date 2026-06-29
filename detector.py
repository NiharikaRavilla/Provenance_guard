import os
import json
from groq import Groq
from dotenv import load_dotenv

load_dotenv()


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
        parsed = json.loads(raw_output)

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


def combine_signal_scores(llm_signal, stylometric_signal):
    """
    Combines both signal scores using the Milestone 2 spec.

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