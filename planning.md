# Provenance Guard Planning

## Milestone 1: Understand the System and Define Architecture

## Project Purpose

Provenance Guard is a backend system for creative sharing platforms that analyzes submitted text and provides attribution context. The system does not claim to prove whether a person or an AI wrote something. Instead, it combines multiple detection signals, calculates a confidence score, displays a transparency label, logs the decision, and gives creators a way to appeal if they believe the classification is wrong.

The main goal is to protect attribution and trust while avoiding overconfident or unfair claims about authorship.

---

## Required Features Overview

Provenance Guard must include seven required features:

1. A content submission endpoint that accepts text for attribution analysis.
2. A multi-signal detection pipeline using at least two distinct signals.
3. A confidence score that reflects uncertainty instead of forcing a binary answer.
4. A transparency label that explains the result in plain language.
5. An appeals workflow for creators who contest a classification.
6. Rate limiting on the submission endpoint.
7. A structured audit log that records decisions, scores, signals, and appeals.

These features must work together as one complete system rather than as separate pieces.

---

## Architecture Narrative

When a creator submits a piece of text, the request first reaches the Flask API through the submission endpoint. The API validates that the request includes the required fields, such as creator ID, title, and content.

After validation, the raw submitted text is passed into the detection pipeline. The detection pipeline runs two different attribution signals.

The first signal is an LLM-based classifier using Groq. This signal evaluates the text holistically and returns a classification such as AI-generated, human-written, or uncertain, along with a confidence value.

The second signal is a stylometric heuristic analyzer. This signal measures statistical writing patterns such as sentence length variation, vocabulary diversity, punctuation density, and repetition. These features are used to estimate whether the writing pattern looks more human-written or AI-generated.

After both signals return their results, the confidence scoring component combines them into one final AI-likelihood score. This score is not treated as absolute truth. Instead, it is used to decide whether the system has enough evidence to label the content as likely AI-generated, likely human-written, or uncertain.

The label generator then converts the final result into plain-language transparency label text. This label is designed for readers of a creative platform, so it avoids technical language and clearly communicates uncertainty.

The system then stores the decision in the database. It records the submitted content metadata, final classification, confidence score, individual signal results, transparency label, and current status. It also writes a structured audit log entry so the decision can be reviewed later.

Finally, the API returns a structured JSON response to the client. The response includes the content ID, classification result, confidence score, signal details, transparency label, and status.

Client
  |
  | POST /submit
  | raw text, creator_id, title
  v
Flask API
  |
  | validated text
  v
Detection Pipeline
  |
  | raw text
  +------------------------------+
  |                              |
  v                              v
Groq LLM Signal              Stylometric Signal
  |                              |
  | classification + confidence  | heuristic score + confidence
  v                              v
Signal Results Collector
  |
  | llm score + stylometric score
  v
Confidence Scoring Component
  |
  | combined AI-likelihood score
  v
Transparency Label Generator
  |
  | result + label text
  v
Database
  |
  | saved decision + signal details
  v
Audit Log
  |
  | structured classification event
  v
JSON Response to Client
  |
  | content_id, result, confidence, label, signals, status
  v
Reader-facing Transparency Label


If the creator believes the classification is wrong, they can submit an appeal. The appeal endpoint accepts the content ID, creator ID, and the creator's reasoning. The system stores the appeal, updates the content status to `under_review`, and writes another audit log entry connecting the appeal to the original decision.

Creator
  |
  | POST /appeal
  | content_id, creator_id, appeal reason
  v
Flask API
  |
  | validated appeal data
  v
Appeal Handler
  |
  | appeal linked to original decision
  v
Database
  |
  | save appeal
  | update content status to under_review
  v
Audit Log
  |
  | structured appeal event
  v
JSON Response to Creator
  |
  | appeal_id, content_id, status, message
  v
Content Status: under_review
---

## System Components

### 1. Flask API

The Flask API receives HTTP requests and returns JSON responses. It exposes endpoints for submitting content, submitting appeals, viewing logs, and checking that the API is running.

Responsibilities:

- Accept incoming requests
- Validate request data
- Call the detection pipeline
- Return structured JSON responses
- Apply rate limits to prevent abuse

---

### 2. Detection Pipeline

The detection pipeline coordinates the two attribution signals.

Responsibilities:

- Send text to the Groq LLM classifier
- Send text to the stylometric analyzer
- Collect signal outputs
- Pass signal results to the scoring component

---

### 3. Groq LLM Signal

The Groq signal asks an LLM to evaluate whether the text appears human-written, AI-generated, or uncertain.

What it measures:

- Overall writing style
- Semantic coherence
- Tone and naturalness
- Whether the text appears overly polished, generic, or machine-like

Why this may differ between human and AI writing:

AI-generated writing often has smooth structure, predictable transitions, balanced paragraphs, and generic phrasing. Human writing may contain more idiosyncratic choices, uneven rhythm, personal voice, or unexpected phrasing.

Blind spots:

- A skilled human writer may produce polished text that looks AI-generated.
- AI-generated text can be edited by a human to appear more natural.
- The LLM may rely on patterns rather than reliable proof.
- The signal cannot verify actual authorship or writing history.

---

### 4. Stylometric Heuristic Signal

The stylometric signal calculates measurable features from the text.

What it measures:

- Sentence length variation
- Average sentence length
- Vocabulary diversity
- Punctuation density
- Repetition patterns

Why this may differ between human and AI writing:

AI-generated text often has more uniform sentence structure and predictable rhythm. Human writing often has more variation in sentence length, vocabulary choices, punctuation, and structure.

Blind spots:

- Short texts may not provide enough data for reliable analysis.
- Some human writing is intentionally simple or repetitive.
- Some AI text can be prompted to imitate human variation.
- Stylometry cannot understand meaning, intent, or originality.

---

### 5. Confidence Scoring Component

The confidence scoring component combines the signal outputs into a final score.

The system treats the final score as an AI-likelihood score:

- 0.00 means strongly human-likely
- 1.00 means strongly AI-likely
- Around 0.50 means uncertain or mixed evidence

Planned weighting:

- Groq LLM signal: 60%
- Stylometric heuristic signal: 40%

The LLM receives slightly more weight because it can evaluate meaning and style holistically. The stylometric signal still has significant weight because it provides measurable structural evidence independent of the LLM.

---

### 6. Transparency Label Generator

The label generator converts the final score into reader-facing text.

Planned thresholds:

- 0.70 to 1.00: likely AI-generated
- 0.40 to 0.69: uncertain
- 0.00 to 0.39: likely human-written

The AI threshold is intentionally conservative because falsely labeling a human creator's work as AI-generated can damage trust and attribution.

---

### 7. Database

The database stores decisions, appeals, and audit log entries.

Planned storage:

- SQLite database
- `content_decisions` table
- `appeals` table
- `audit_log` table

Responsibilities:

- Save each submitted content decision
- Save signal scores and final classification
- Save creator appeals
- Track content status
- Preserve audit history

---

### 8. Audit Log

The audit log records every important system event.

It should capture:

- Classification decisions
- Confidence scores
- Signals used
- Transparency label returned
- Appeals submitted
- Status changes
- Timestamps

The audit log is important because attribution decisions should be reviewable and explainable.

---

### 9. Appeals Workflow

The appeals workflow allows creators to contest a classification.

When an appeal is submitted:

1. The creator provides a content ID and explanation.
2. The system stores the appeal.
3. The original content status changes to `under_review`.
4. The appeal is written to the audit log.
5. The API returns confirmation.

The project does not require automated reclassification after an appeal. The important requirement is that the appeal is captured, connected to the original decision, and logged.

---

## False Positive Scenario

A false positive happens when a human writer's work is labeled as AI-generated.

This is the highest-risk failure case for this project because it could unfairly damage a creator's reputation or discourage them from sharing original work.

Example scenario:

A creator submits a polished short story excerpt. The LLM signal says the text looks likely AI-generated because the prose is smooth and structured. The stylometric signal also detects low sentence length variation. The combined score is 0.72, which crosses the threshold for likely AI-generated.

To reduce harm, the system handles this carefully:

1. The confidence score is shown instead of only a binary label.
2. The transparency label says “likely AI-generated,” not “definitely AI-generated.”
3. The label explains that the result is based on automated analysis.
4. The creator can appeal the decision.
5. The appeal updates the content status to `under_review`.
6. The original decision and appeal are saved in the audit log.

This scenario influences the system design by making the AI threshold conservative. The system requires stronger evidence before applying the AI-generated label. Scores in the middle range become `uncertain` instead of forcing a harmful classification.

---

## API Surface

### GET /

Purpose:

Check whether the API is running.

Response example:

```json
{
  "message": "Provenance Guard API is running",
  "status": "ok"
}
POST /submit

Purpose:

Submit text content for attribution analysis.

Request body:

{
  "creator_id": "creator_123",
  "title": "Moonlit River",
  "content": "The river moved like silver beneath the tired moon..."
}

Response body:

{
  "content_id": 1,
  "result": "uncertain",
  "confidence": 0.62,
  "label": "Attribution uncertain: Our system found mixed signals about whether this piece was AI-generated or human-written. This label is not a final judgment, and the creator may appeal.",
  "signals": {
    "llm_signal": {
      "classification": "human",
      "confidence": 0.68
    },
    "stylometric_signal": {
      "classification": "ai",
      "confidence": 0.56
    }
  },
  "status": "classified"
}
POST /appeal

Purpose:

Allow a creator to contest a classification.

Request body:

{
  "content_id": 1,
  "creator_id": "creator_123",
  "reason": "I wrote this piece myself and can provide earlier drafts showing my revision process."
}

Response body:

{
  "appeal_id": 1,
  "content_id": 1,
  "status": "under_review",
  "message": "Appeal submitted successfully. The content status has been updated to under_review."
}
GET /log

Purpose:

Return recent audit log entries.

Response body:

[
  {
    "event_type": "classification",
    "content_id": 1,
    "result": "uncertain",
    "confidence": 0.62,
    "signals_used": ["llm_signal", "stylometric_signal"],
    "timestamp": "2026-06-28T14:22:10"
  },
  {
    "event_type": "appeal",
    "content_id": 1,
    "appeal_reason": "I wrote this piece myself and can provide earlier drafts.",
    "timestamp": "2026-06-28T14:25:33"
  }
]

Detection Signal Decision Summary

The system will use two required detection signals:
| Signal                  | What it captures                                                  | Why it helps                                                          | Blind spot                                                     |
| ----------------------- | ----------------------------------------------------------------- | --------------------------------------------------------------------- | -------------------------------------------------------------- |
| Groq LLM classification | Holistic style, tone, coherence, naturalness                      | Can evaluate semantic and stylistic patterns beyond simple statistics | Cannot prove authorship and may misread polished human writing |
| Stylometric heuristics  | Sentence variation, vocabulary diversity, punctuation, repetition | Gives measurable structural evidence independent of the LLM           | Weak on short texts and cannot understand meaning              |
These signals are distinct because one is semantic and holistic, while the other is statistical and structural.