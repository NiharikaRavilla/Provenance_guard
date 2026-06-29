def get_placeholder_label(attribution):
    if attribution == "likely_ai":
        return "Placeholder label: This content currently appears likely AI-generated based on the first detection signal."

    if attribution == "likely_human":
        return "Placeholder label: This content currently appears likely human-written based on the first detection signal."

    return "Placeholder label: Attribution is currently uncertain based on the first detection signal."