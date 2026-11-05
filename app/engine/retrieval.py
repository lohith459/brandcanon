import re
from typing import List, Tuple
from rank_bm25 import BM25Okapi
from app.models.canon import Rule, Fact

def tokenize(text: str) -> List[str]:
    """Simple alphanumeric tokenizer for BM25."""
    return re.findall(r"\w+", text.lower())

def retrieve_top_k_canon(
    query_text: str,
    rules: List[Rule],
    facts: List[Fact],
    k: int = 5
) -> Tuple[List[Rule], List[Fact]]:
    """
    Retrieves the top-k most relevant rules and facts for a given draft query
    using BM25 Okapi retrieval. This provides concise, focused context to the LLM.
    """
    if not rules and not facts:
        return [], []

    query_tokens = tokenize(query_text)
    if not query_tokens:
        return rules[:k], facts[:k]

    # 1. Retrieve top rules
    selected_rules: List[Rule] = []
    if rules:
        corpus = [tokenize(f"{r.id} {r.category} {r.text} {r.good_example} {r.bad_example}") for r in rules]
        bm25_rules = BM25Okapi(corpus)
        scores = bm25_rules.get_scores(query_tokens)
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        selected_rules = [rules[i] for i in top_indices if scores[i] > 0]
        if not selected_rules:
            selected_rules = rules[:min(3, len(rules))]

    # 2. Retrieve top facts
    selected_facts: List[Fact] = []
    if facts:
        corpus_facts = [tokenize(f"{f.id} {f.claim} {' '.join(f.keywords)} {f.value}") for f in facts]
        bm25_facts = BM25Okapi(corpus_facts)
        f_scores = bm25_facts.get_scores(query_tokens)
        top_f_indices = sorted(range(len(f_scores)), key=lambda i: f_scores[i], reverse=True)[:k]
        selected_facts = [facts[i] for i in top_f_indices if f_scores[i] > 0]
        if not selected_facts:
            selected_facts = facts[:min(2, len(facts))]

    return selected_rules, selected_facts
