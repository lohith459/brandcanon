from fastapi import APIRouter, HTTPException
from app.models.schemas import ContrastRequest, ContrastResponse
from app.core.contrast import calculate_contrast_ratio
from app.seed.seed_drafts import SAMPLE_DRAFTS

router = APIRouter(prefix="/api/tools", tags=["Tools"])

@router.post("/contrast", response_model=ContrastResponse)
def evaluate_contrast(payload: ContrastRequest) -> ContrastResponse:
    """Calculates WCAG 2.1 relative luminance and contrast ratio between foreground and background colors."""
    try:
        return calculate_contrast_ratio(payload.foreground_hex, payload.background_hex)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/demo-drafts")
def get_demo_drafts():
    """Returns pre-seeded sample drafts (Bad worked example, medium-risk, clean) for 1-click loading."""
    return SAMPLE_DRAFTS
