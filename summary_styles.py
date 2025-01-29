from typing import Dict

DEFAULT_STYLES = {
    "Concise": {
        "description": "A brief overview of main points",
        "prompt": "Provide a concise summary of the main points from this transcript in 3-4 bullet points."
    },
    "Detailed": {
        "description": "Comprehensive breakdown with examples",
        "prompt": "Provide a detailed summary of the transcript, including key concepts, examples, and any important details mentioned."
    },
    "Academic": {
        "description": "Academic-style analysis",
        "prompt": "Analyze this transcript in an academic style, including: main thesis, key arguments, methodology (if any), and conclusions."
    },
    "ELI5": {
        "description": "Explain Like I'm 5",
        "prompt": "Explain the main concepts from this transcript in simple terms, as if explaining to a child."
    }
}

def get_style_prompt(style_name: str, custom_styles: Dict = None) -> str:
    """Get the prompt for a given style name."""
    all_styles = DEFAULT_STYLES.copy()
    if custom_styles:
        all_styles.update(custom_styles)
    
    return all_styles.get(style_name, DEFAULT_STYLES["Concise"])["prompt"]

def get_style_description(style_name: str, custom_styles: Dict = None) -> str:
    """Get the description for a given style name."""
    all_styles = DEFAULT_STYLES.copy()
    if custom_styles:
        all_styles.update(custom_styles)
    
    return all_styles.get(style_name, DEFAULT_STYLES["Concise"])["description"] 