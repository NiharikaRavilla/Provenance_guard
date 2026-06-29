# Provenance Guard Planning

## Project Goal

Provenance Guard is a backend system for a creative writing platform. A user submits a piece of text, and the system gives readers context about whether the text appears likely human-written, likely AI-generated, or uncertain.

The system is not trying to prove authorship. AI detection is not perfect, so the project needs to show uncertainty clearly and give creators a way to appeal if they think the system got it wrong.

The required features are:

1. Content submission endpoint
2. At least two detection signals
3. Confidence scoring with uncertainty
4. Transparency labels
5. Appeals workflow
6. Rate limiting
7. Structured audit logging

---

## Architecture

### Submission flow

When a creator submits text, the request goes to the Flask API. The API checks that the request includes a creator ID, title, and content. After that, the content is sent through two detection signals: an LLM-based signal and a stylometric signal.

Each signal returns an AI-likelihood score. The scoring component combines those scores into one final score. The label component then turns that score into one of three labels: likely AI-generated, likely human-written, or uncertain. The final decision, signals, confidence score, and label are saved to the database and written to the audit log. The API then returns the result to the client.

### Appeal flow

If a creator disagrees with the result, they can submit an appeal. The appeal includes the content ID, creator ID, and a written reason. The system saves the appeal, updates the content status to `under_review`, writes the appeal to the audit log, and returns a confirmation response.

### Submission diagram

```text
Client
  |
  | POST /submit
  | creator_id, title, raw text
  v
Flask API
  |
  | validated text
  v
Detection Pipeline
  |
  +------------------------------+
  |                              |
  v                              v
Groq LLM Signal              Stylometric Signal
  |                              |
  | AI-likelihood score          | AI-likelihood score
  v                              v
Confidence Scoring
  |
  | combined score
  v
Transparency Label
  |
  | label text
  v
Database
  |
  | saved decision
  v
Audit Log
  |
  | classification event
  v
JSON Response
Appeal diagram
Creator
  |
  | POST /appeal
  | content_id, creator_id, reason
  v
Flask API
  |
  | validated appeal request
  v
Appeal Handler
  |
  | save appeal
  | update status to under_review
  v
Database
  |
  | appeal record + status update
  v
Audit Log
  |
  | appeal event
  v
JSON Response
API Plan
GET /

This endpoint checks whether the API is running.

Example response:

{
  "message": "Provenance Guard API is running",
  "status": "ok"
}
POST /submit

This endpoint accepts a piece of text and returns an attribution result.

Example request:

{
  "creator_id": "creator_123",
  "title": "Moonlit River",
  "content": "The river moved like silver beneath the tired moon."
}

Example response:

{
  "content_id": 1,
  "result": "uncertain",
  "confidence": 0.62,
  "label": "Attribution uncertain: Our system found mixed signals about whether this piece was AI-generated or human-written. This label is not a final judgment, and the creator may appeal.",
  "signals": {
    "llm_signal": {
      "classification": "human",
      "confidence": 0.68,
      "ai_likelihood": 0.32
    },
    "stylometric_signal": {
      "classification": "ai",
      "confidence": 0.56,
      "ai_likelihood": 0.56
    }
  },
  "status": "classified"
}
POST /appeal

This endpoint lets a creator appeal a classification.

Example request:

{
  "content_id": 1,
  "creator_id": "creator_123",
  "reason": "I wrote this myself and can provide earlier drafts."
}

Example response:

{
  "appeal_id": 1,
  "content_id": 1,
  "status": "under_review",
  "message": "Appeal submitted successfully. The content status has been updated to under_review."
}
GET /log

This endpoint returns recent audit log entries.

Example response:

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
    "creator_id": "creator_123",
    "reason": "I wrote this myself and can provide earlier drafts.",
    "new_status": "under_review",
    "timestamp": "2026-06-28T14:25:33"
  }
]
Detection Signals

I am using two signals because the project requires the system to look at more than one kind of evidence. One signal looks at the text more holistically, and the other looks at measurable writing patterns.

Signal 1: Groq LLM classifier

The first signal uses Groq with llama-3.3-70b-versatile. The model will be asked whether the text appears AI-generated, human-written, or uncertain.

This signal measures things like:

tone
naturalness
generic phrasing
coherence
whether the writing feels overly polished or predictable

The output should look like this:

{
  "classification": "ai",
  "confidence": 0.82,
  "ai_likelihood": 0.82,
  "reason": "The writing has polished structure and generic phrasing."
}

The ai_likelihood value is always between 0.0 and 1.0.

If the model says the text is AI-generated, the AI-likelihood is the model confidence. If the model says the text is human-written, the AI-likelihood is 1 - confidence. If the model is uncertain, the AI-likelihood is 0.5.

This signal is useful because an LLM can judge style and meaning better than a simple formula. However, it has blind spots. It cannot prove who wrote the text. It might call a polished human essay AI-generated, and it might miss AI text that was edited by a human.

Signal 2: Stylometric heuristics

The second signal uses basic Python calculations to measure the structure of the writing.

This signal measures:

word count
sentence count
average sentence length
sentence length variance
vocabulary diversity
punctuation density
repetition

The output should look like this:

{
  "classification": "human",
  "confidence": 0.64,
  "ai_likelihood": 0.36,
  "features": {
    "word_count": 142,
    "sentence_count": 8,
    "avg_sentence_length": 17.75,
    "sentence_length_variance": 42.3,
    "type_token_ratio": 0.71,
    "punctuation_density": 0.08
  },
  "reason": "The text has varied sentence lengths and strong vocabulary diversity."
}

This signal is useful because AI-generated text often has smoother and more uniform patterns. Human writing often has more uneven rhythm and more variation.

This signal also has blind spots. It may not work well on short poems, song lyrics, simple stories, or intentionally repetitive writing. It also cannot understand meaning or authorship.

Combining the Signals

The final score will be an AI-likelihood score from 0.0 to 1.0.

Formula:

final_score = (llm_ai_likelihood * 0.60) + (stylometric_ai_likelihood * 0.40)

I am giving the LLM signal more weight because it can understand style and meaning. I am still giving stylometry a large weight because it gives a separate structural signal.

Example:

LLM AI-likelihood = 0.80
Stylometric AI-likelihood = 0.55

final_score = (0.80 * 0.60) + (0.55 * 0.40)
final_score = 0.70

A final score of 0.70 would be labeled as likely AI-generated.

Uncertainty and Thresholds

The score is not proof. It is only the system’s estimate based on the two signals.

A score of 0.60 means the text has some AI-like signs, but the evidence is not strong enough to label it likely AI-generated. That should be shown as uncertain.

A score of 0.95 means the evidence strongly points toward AI-generated text.

A score of 0.20 means the evidence strongly points toward human-written text.

The thresholds will be:

Score range	Result	Label
0.00 to 0.39	likely_human	High-confidence human
0.40 to 0.69	uncertain	Uncertain
0.70 to 1.00	likely_ai	High-confidence AI

I am not using 0.50 as the AI cutoff because that would be too risky. A false positive can hurt a real creator, so the system should require stronger evidence before showing a likely AI-generated label.

Transparency Labels

These are the exact three label variants the system will return.

High-confidence AI label
"Likely AI-generated: Our system found strong signals that this content may have been generated by AI. This label is based on automated analysis and may be appealed by the creator."
High-confidence human label
"Likely human-written: Our system found strong signals that this content was written by a person. This label is based on automated analysis and is not a guarantee of authorship."
Uncertain label
"Attribution uncertain: Our system found mixed signals about whether this piece was AI-generated or human-written. This label is not a final judgment, and the creator may appeal."
Appeals Workflow

A creator can appeal a classification if they believe the system labeled their work incorrectly.

For this class project, there is no full login system. The creator will submit:

content_id
creator_id
reason

When an appeal is received, the system will:

Check that the required fields exist.
Check that the content ID exists.
Save the appeal.
Change the content status to under_review.
Add an appeal event to the audit log.
Return a confirmation message.

A human reviewer should be able to see:

content ID
creator ID
original title
original content
original classification
original confidence score
signal outputs
label text
creator’s appeal reason
current status
appeal timestamp

The system does not need to automatically reclassify the content after an appeal. The main requirement is to capture the appeal and connect it to the original decision.

Audit Log Plan

Every classification decision and appeal should be recorded.

For a classification, the audit log should store:

event type
content ID
result
confidence score
signals used
label text
timestamp

For an appeal, the audit log should store:

event type
content ID
creator ID
reason
previous status
new status
timestamp

This matters because automated attribution decisions should be reviewable later.

Database Plan

I will use SQLite because it is built into Python and does not require another service.

content_decisions table

This table stores submitted content and the classification result.

Fields:

id
creator_id
title
content
result
confidence
label
signals_json
status
created_at
appeals table

This table stores creator appeals.

Fields:

id
content_id
creator_id
reason
status
created_at
audit_log table

This table stores classification and appeal events.

Fields:

id
event_type
content_id
event_json
created_at
Rate Limiting Plan

The /submit endpoint will be rate limited.

Chosen limits:

10 submissions per minute per IP
100 submissions per day per IP

I chose these limits because a normal creator probably will not submit more than a few pieces in a minute. The per-minute limit helps stop spam. The daily limit still allows testing and active use, but it reduces abuse from automated scripts.

Edge Cases
Edge case 1: Very short poems

A short poem may only have a few words or lines. The stylometric signal may not have enough text to calculate useful sentence variance or vocabulary diversity.

Example:

Rain falls.
I wait.
The street forgets me.

This might produce an unstable score, so short content should usually lean toward uncertain unless the signals are very strong.

Edge case 2: Human writing with repetition

Some human writing uses repetition on purpose.

Example:

I waited.
I waited.
The rain waited too.

The stylometric signal might treat this as AI-like because it is repetitive and simple. The system should avoid relying only on the heuristic score.

Edge case 3: Polished human writing

A strong human writer may write in a smooth and polished style. That could look similar to AI-generated writing.

This is why the label says “likely AI-generated” instead of “AI-generated,” and why creators can appeal.

Edge case 4: AI text edited by a person

AI-generated text can be edited by a human until it looks more natural. The system may miss this because it only sees the final text, not the writing process.

The label should not claim proof of authorship.

Edge case 5: Non-native English writing

A non-native English writer may use repeated phrases, simple grammar, or unusual sentence structure. The system might treat this as suspicious even though it is human-written.

This is another reason to keep an uncertain range and allow appeals.

AI Tool Plan
M3: Submission endpoint and first signal

For Milestone 3, I will use these sections:

Architecture
API Plan
Groq LLM classifier
Database Plan

I will ask the AI tool to generate:

a Flask app skeleton
the POST /submit endpoint
validation for creator_id, title, and content
the Groq LLM classification function
a basic database insert

I will verify it by:

Running the Flask app locally.
Testing GET /.
Sending a valid POST /submit request.
Sending a bad request missing content.
Checking that the response includes classification, confidence, and AI-likelihood.
M4: Second signal and confidence scoring

For Milestone 4, I will use these sections:

Detection Signals
Combining the Signals
Uncertainty and Thresholds
Architecture

I will ask the AI tool to generate:

the stylometric analysis function
feature extraction logic
AI-likelihood scoring
final weighted scoring
threshold-based result selection

I will verify it by:

Testing with polished generic text.
Testing with personal human-like writing.
Testing with a short or ambiguous poem.
Checking that different inputs produce different scores.
Checking that scores in the middle range return the uncertain label.
M5: Production layer

For Milestone 5, I will use these sections:

Transparency Labels
Appeals Workflow
Audit Log Plan
Rate Limiting Plan
Database Plan
Architecture

I will ask the AI tool to generate:

label generation logic
the /appeal endpoint
status update logic
audit log writing
the /log endpoint
Flask-Limiter setup for /submit

I will verify it by:

Confirming all three label variants can appear.
Submitting an appeal.
Checking that the content status changes to under_review.
Checking that the appeal is saved.
Checking that classification and appeal events appear in /log.
Confirming rate limiting is configured.