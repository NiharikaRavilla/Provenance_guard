import re
import string


def split_sentences(text):
    sentences = re.split(r"[.!?]+", text)
    return [sentence.strip() for sentence in sentences if sentence.strip()]


def tokenize_words(text):
    return re.findall(r"\b[a-zA-Z']+\b", text.lower())


def calculate_variance(numbers):
    if len(numbers) <= 1:
        return 0.0

    mean = sum(numbers) / len(numbers)
    squared_diffs = [(number - mean) ** 2 for number in numbers]
    return sum(squared_diffs) / len(numbers)


def clamp(value, minimum=0.0, maximum=1.0):
    return max(minimum, min(value, maximum))


def analyze_stylometry(text):
    """
    Second detection signal.

    Returns:
    {
        "classification": "ai" | "human" | "uncertain",
        "confidence": float,
        "ai_likelihood": float,
        "features": {...},
        "reason": str
    }
    """

    sentences = split_sentences(text)
    words = tokenize_words(text)

    word_count = len(words)
    sentence_count = len(sentences)

    if word_count == 0:
        return {
            "classification": "uncertain",
            "confidence": 0.5,
            "ai_likelihood": 0.5,
            "features": {
                "word_count": 0,
                "sentence_count": 0,
                "avg_sentence_length": 0,
                "sentence_length_variance": 0,
                "type_token_ratio": 0,
                "punctuation_density": 0
            },
            "reason": "No analyzable words were found."
        }

    sentence_lengths = [len(tokenize_words(sentence)) for sentence in sentences]
    avg_sentence_length = sum(sentence_lengths) / len(sentence_lengths) if sentence_lengths else word_count
    sentence_length_variance = calculate_variance(sentence_lengths)

    unique_words = set(words)
    type_token_ratio = len(unique_words) / word_count

    punctuation_count = sum(1 for char in text if char in string.punctuation)
    punctuation_density = punctuation_count / max(len(text), 1)

    repeated_words = word_count - len(unique_words)
    repetition_ratio = repeated_words / word_count

    ai_points = 0.0
    reasons = []

    # Very uniform sentence lengths often look more AI-like.
    if sentence_count >= 3 and sentence_length_variance < 10:
        ai_points += 0.25
        reasons.append("low sentence length variation")
    elif sentence_length_variance > 35:
        ai_points -= 0.15
        reasons.append("varied sentence lengths")

    # Low vocabulary diversity can indicate generic or repetitive writing.
    if type_token_ratio < 0.55:
        ai_points += 0.25
        reasons.append("low vocabulary diversity")
    elif type_token_ratio > 0.70:
        ai_points -= 0.15
        reasons.append("high vocabulary diversity")

    # Very low punctuation density can indicate smooth, plain generated text.
    if punctuation_density < 0.025 and word_count > 40:
        ai_points += 0.15
        reasons.append("low punctuation variation")
    elif punctuation_density > 0.06:
        ai_points -= 0.10
        reasons.append("more punctuation variation")

    # Repetition can be AI-like, but this is weak because poetry can repeat intentionally.
    if repetition_ratio > 0.45 and word_count > 30:
        ai_points += 0.15
        reasons.append("high repetition")
    elif repetition_ratio < 0.25:
        ai_points -= 0.05
        reasons.append("low repetition")

    # Short text is hard to judge, so pull it toward uncertain.
    if word_count < 35:
        ai_likelihood = 0.50 + (ai_points * 0.40)
        reasons.append("short text limits confidence")
    else:
        ai_likelihood = 0.50 + ai_points

    ai_likelihood = clamp(ai_likelihood)

    if ai_likelihood >= 0.70:
        classification = "ai"
        confidence = ai_likelihood
    elif ai_likelihood <= 0.39:
        classification = "human"
        confidence = 1 - ai_likelihood
    else:
        classification = "uncertain"
        confidence = 1 - abs(ai_likelihood - 0.5)

    if not reasons:
        reasons.append("mixed stylometric evidence")

    return {
        "classification": classification,
        "confidence": round(confidence, 2),
        "ai_likelihood": round(ai_likelihood, 2),
        "features": {
            "word_count": word_count,
            "sentence_count": sentence_count,
            "avg_sentence_length": round(avg_sentence_length, 2),
            "sentence_length_variance": round(sentence_length_variance, 2),
            "type_token_ratio": round(type_token_ratio, 2),
            "punctuation_density": round(punctuation_density, 3),
            "repetition_ratio": round(repetition_ratio, 2)
        },
        "reason": ", ".join(reasons)
    }