from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.database import get_session
from app.models.canon import Rule, Fact, Term, Asset
from app.models.schemas import RuleCreate, FactCreate, TermCreate, AssetCreate
from app.core.roles import get_current_role

router = APIRouter(prefix="/api/canon", tags=["Brand Canon"])

# RULES
@router.get("/rules", response_model=List[Rule])
def list_rules(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List brand guidelines and compliance rules."""
    query = select(Rule)
    if category:
        query = query.where(Rule.category == category)
    if severity:
        query = query.where(Rule.severity == severity)
    return session.exec(query).all()

@router.post("/rules", response_model=Rule, status_code=status.HTTP_201_CREATED)
def create_rule(
    payload: RuleCreate,
    session: Session = Depends(get_session)
):
    """Creates a new rule in the brand canon."""
    existing = session.get(Rule, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule ID '{payload.id}' already exists.")
    rule = Rule(**payload.model_dump())
    session.add(rule)
    session.commit()
    session.refresh(rule)
    return rule

# FACTS
@router.get("/facts")
def list_facts(session: Session = Depends(get_session)):
    """List brand facts with live expiration status."""
    facts = session.exec(select(Fact)).all()
    results = []
    for f in facts:
        results.append({
            "id": f.id,
            "claim": f.claim,
            "value": f.value,
            "keywords": f.keywords,
            "evidence_url": f.evidence_url,
            "owner": f.owner,
            "valid_from": f.valid_from,
            "expires_on": f.expires_on,
            "is_expired": f.is_expired()
        })
    return results

@router.post("/facts", response_model=Fact, status_code=status.HTTP_201_CREATED)
def create_fact(
    payload: FactCreate,
    session: Session = Depends(get_session)
):
    """Creates a new brand fact in the registry."""
    existing = session.get(Fact, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Fact ID '{payload.id}' already exists.")
    fact = Fact(**payload.model_dump())
    session.add(fact)
    session.commit()
    session.refresh(fact)
    return fact

# TERMS
@router.get("/terms", response_model=List[Term])
def list_terms(session: Session = Depends(get_session)):
    """List approved terminology and forbidden synonyms."""
    return session.exec(select(Term)).all()

@router.post("/terms", response_model=Term, status_code=status.HTTP_201_CREATED)
def create_term(
    payload: TermCreate,
    session: Session = Depends(get_session)
):
    """Creates an approved terminology mapping."""
    existing = session.get(Term, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Term ID '{payload.id}' already exists.")
    term = Term(**payload.model_dump())
    session.add(term)
    session.commit()
    session.refresh(term)
    return term

# ASSETS
@router.get("/assets", response_model=List[Asset])
def list_assets(
    asset_type: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List approved design assets (palette colors, logos, typography)."""
    query = select(Asset)
    if asset_type:
        query = query.where(Asset.type == asset_type)
    return session.exec(query).all()

@router.post("/assets", response_model=Asset, status_code=status.HTTP_201_CREATED)
def create_asset(
    payload: AssetCreate,
    session: Session = Depends(get_session)
):
    """Adds a new brand asset to the registry."""
    existing = session.get(Asset, payload.id)
    if existing:
        raise HTTPException(status_code=400, detail=f"Asset ID '{payload.id}' already exists.")
    asset = Asset(**payload.model_dump())
    session.add(asset)
    session.commit()
    session.refresh(asset)
    return asset
