from fastapi.testclient import TestClient
from sqlmodel import Session, select
from app.models.canon import Rule, Fact, Term, Asset

def test_health_endpoint(client: TestClient):
    """Test /health endpoint returns 200 with accurate seed counts."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert data["rules_count"] >= 12
    assert data["facts_count"] >= 8
    assert data["terms_count"] >= 10

def test_canon_seed_integrity(session: Session):
    """Verify FinEdge brand canon required rules, facts, and terms are present."""
    # Required rule: CMP-004
    cmp_004 = session.get(Rule, "CMP-004")
    assert cmp_004 is not None
    assert cmp_004.severity == "critical"
    assert "guaranteed" in cmp_004.text.lower()
    
    # Required fact: F-017 with keywords
    f_017 = session.get(Fact, "F-017")
    assert f_017 is not None
    assert f_017.value == "38400"
    assert "users" in f_017.keywords
    assert "investors" in f_017.keywords
    
    # Required fact: F-022
    f_022 = session.get(Fact, "F-022")
    assert f_022 is not None
    assert "basic tracking" in f_022.value.lower()
    
    # Required term: TRM-011
    trm_011 = session.get(Term, "TRM-011")
    assert trm_011 is not None
    assert trm_011.preferred == "FinEdge Plus"
    assert "FinEdge Pro" in trm_011.forbidden
    
    # Required asset palette
    assets = session.exec(select(Asset)).all()
    color_assets = [a for a in assets if a.type == "color"]
    assert len(color_assets) >= 5
