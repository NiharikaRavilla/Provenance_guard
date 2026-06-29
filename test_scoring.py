from detector import classify_with_groq, combine_signal_scores
from stylometry import analyze_stylometry
from labels import get_transparency_label


samples = [
    {
        "name": "Clearly AI-generated",
        "text": """Artificial intelligence represents a transformative paradigm shift in modern society.
It is important to note that while the benefits of AI are numerous, it is equally
essential to consider the ethical implications. Furthermore, stakeholders across
various sectors must collaborate to ensure responsible deployment."""
    },
    {
        "name": "Clearly human-written",
        "text": """ok so i finally tried that new ramen place downtown and honestly?
underwhelming. the broth was fine but they put WAY too much sodium in it and
i was thirsty for like three hours after. my friend got the spicy version and
said it was better. probably won't go back unless someone drags me there"""
    },
    {
        "name": "Borderline formal human writing",
        "text": """The relationship between monetary policy and asset price inflation has been
extensively studied in the literature. Central banks face a fundamental tension
between their mandate for price stability and the unintended consequences of
prolonged low interest rates on equity and real estate valuations."""
    },
    {
        "name": "Borderline lightly edited AI output",
        "text": """I've been thinking a lot about remote work lately. There are genuine tradeoffs —
flexibility and no commute on one side, isolation and blurred work-life boundaries
on the other. Studies show productivity varies widely by individual and role type."""
    }
]


for sample in samples:
    print("=" * 80)
    print(sample["name"])
    print("=" * 80)

    llm_signal = classify_with_groq(sample["text"])
    stylometric_signal = analyze_stylometry(sample["text"])
    scoring = combine_signal_scores(llm_signal, stylometric_signal)
    label = get_transparency_label(scoring["attribution"])

    print("LLM signal:")
    print(llm_signal)

    print("\nStylometric signal:")
    print(stylometric_signal)

    print("\nCombined scoring:")
    print(scoring)

    print("\nLabel:")
    print(label)

    print()