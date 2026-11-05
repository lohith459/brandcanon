from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from app.database import get_session
from app.config import settings
from app.models.canon import Rule, Fact, Term
from app.models.schemas import HealthResponse

router = APIRouter(tags=["Health"])

@router.get("/health", response_model=HealthResponse)
def get_health(session: Session = Depends(get_session)) -> HealthResponse:
    """System health check endpoint verifying database connectivity and configuration."""
    rules_count = session.exec(select(func.count(Rule.id))).one()
    facts_count = session.exec(select(func.count(Fact.id))).one()
    terms_count = session.exec(select(func.count(Term.id))).one()
    
    if settings.GEMINI_API_KEY:
        ai_mode = "online_gemini"
    elif settings.ANTHROPIC_API_KEY:
        ai_mode = "online_anthropic"
    else:
        ai_mode = "offline_deterministic"
        
    return HealthResponse(
        status="ok",
        version=settings.VERSION,
        database="connected",
        ai_mode=ai_mode,
        rules_count=rules_count,
        facts_count=facts_count,
        terms_count=terms_count
    )
