from typing import Dict, List
from difflib import SequenceMatcher

def compare_trends(a: str, b: str) -> Dict[str, List[str]]:
    a_set = set(tag.strip('-').strip() for tag in a.split('\n') if tag.startswith('-'))
    b_set = set(tag.strip('-').strip() for tag in b.split('\n') if tag.startswith('-'))

    return {
        "shared": sorted(a_set & b_set),
        "only_in_a": sorted(a_set - b_set),
        "only_in_b": sorted(b_set - a_set)
    }

def summarize_difference(text1: str, text2: str) -> str:
    ratio = SequenceMatcher(None, text1, text2).ratio()
    if ratio > 0.85:
        return "Both projects have very similar goals and approaches."
    elif ratio > 0.5:
        return "The projects have some conceptual overlap but target different use cases."
    else:
        return "The projects serve distinct purposes and use different methodologies."