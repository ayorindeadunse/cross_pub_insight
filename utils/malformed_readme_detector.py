from pydoc import text
import re

def is_malformed_readme(text: str) -> bool:
    # Heuristic: strip HTML, check length, look for real text paragraps that are sensible
    if not text or len(text.strip()) < 100:
        return True
    
    text = re.sub(r"<(script|style).*?>.*?</\1>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\!\[.*?\]\(.*?\)", "", text)
    text = re.sub(r"\[!\[.*?\]\(.*?\)\]", "", text)
    text = re.sub(r"#.*", "", text)
    
    if len(text.split()) < 30:
        return True
    
    # Too many non-alphabetic characters
    alpha_ratio = sum(c.isalpha() for c in text) / (len(text) + 1e-5)
    if alpha_ratio < 0.5:
        return True
    
    return False
