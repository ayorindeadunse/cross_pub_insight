from pydoc import text
import re

def is_malformed_readme(text: str) -> bool:
    # Heuristic: strip HTML, check length, look for real text paragraps that are sensible
    if not text or len(text.strip()) < 100:
        return True
    
    # Remove markdown/image/html noise
    cleaned = re.sub(r"<[^>]+>", "", text)  # Remove HTML tags
    cleaned = re.sub(r"\!\[.*?\]\(.*?\)", "", cleaned)  # Markdown images
    cleaned = re.sub(r"\[!\[.*?\]\(.*?\)\]", "", cleaned)  # Markdown badges
    cleaned = re.sub(r"#.*", "", cleaned)  # Headings
    cleaned = cleaned.strip()

    if len(cleaned.split()) < 30:
        return True
    
    # Too many non-alphabetic characters
    alpha_ratio = sum(c.isalpha() for c in cleaned) / (len(cleaned) + 1e-5)
    if alpha_ratio < 0.5:
        return True
    
    return False
