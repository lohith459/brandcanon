from fastapi.testclient import TestClient

def test_create_and_list_canon_rule(client: TestClient):
    """Verifies adding a new brand rule and listing it with category filter."""
    new_rule = {
        "id": "TON-004",
        "category": "tone",
        "severity": "low",
        "text": "Avoid passive voice when describing product capabilities.",
        "good_example": "FinEdge updates your balances in real time.",
        "bad_example": "Balances are updated in real time by FinEdge.",
        "pattern": None,
        "fix_hint": "Use active voice.",
        "active": True
    }
    create_res = client.post("/api/canon/rules", json=new_rule)
    assert create_res.status_code == 201
    assert create_res.json()["id"] == "TON-004"

    # Duplicate ID should be rejected
    dup_res = client.post("/api/canon/rules", json=new_rule)
    assert dup_res.status_code == 400

    # Filter by category=tone
    list_res = client.get("/api/canon/rules?category=tone")
    assert list_res.status_code == 200
    rules = list_res.json()
    assert any(r["id"] == "TON-004" for r in rules)

def test_create_and_list_canon_fact_with_expiry(client: TestClient):
    """Verifies adding a fact with keywords and checking live is_expired computation."""
    new_fact = {
        "id": "F-030",
        "claim": "European institutional investor count",
        "value": "120",
        "keywords": ["institutional", "europe", "funds", "partners"],
        "evidence_url": "https://internal.finedge.com/reports/eu-q3",
        "owner": "Head of Institutional Sales",
        "valid_from": "2026-01-01",
        "expires_on": "2026-06-01"  # Already expired relative to Nov 2026
    }
    create_res = client.post("/api/canon/facts", json=new_fact)
    assert create_res.status_code == 201
    assert create_res.json()["id"] == "F-030"

    list_res = client.get("/api/canon/facts")
    assert list_res.status_code == 200
    facts = list_res.json()
    f30 = next((f for f in facts if f["id"] == "F-030"), None)
    assert f30 is not None
    assert f30["is_expired"] is True
    assert "institutional" in f30["keywords"]
