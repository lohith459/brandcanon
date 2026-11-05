import difflib
from typing import List, Dict, Any

def compute_text_diff(old_text: str, new_text: str) -> Dict[str, Any]:
    """
    Computes word-level diff between two text versions for tracked-changes rendering.
    Returns structured chunks categorized as 'equal', 'insert', or 'delete'.
    """
    old_words = old_text.split()
    new_words = new_text.split()
    
    matcher = difflib.SequenceMatcher(None, old_words, new_words)
    chunks: List[Dict[str, str]] = []
    
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            chunks.append({
                "type": "equal",
                "text": " ".join(old_words[i1:i2])
            })
        elif tag == "delete":
            chunks.append({
                "type": "delete",
                "text": " ".join(old_words[i1:i2])
            })
        elif tag == "insert":
            chunks.append({
                "type": "insert",
                "text": " ".join(new_words[j1:j2])
            })
        elif tag == "replace":
            chunks.append({
                "type": "delete",
                "text": " ".join(old_words[i1:i2])
            })
            chunks.append({
                "type": "insert",
                "text": " ".join(new_words[j1:j2])
            })
            
    return {
        "chunks": chunks,
        "old_word_count": len(old_words),
        "new_word_count": len(new_words),
        "word_change": len(new_words) - len(old_words)
    }
