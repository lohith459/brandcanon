import uuid
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header, status
from sqlmodel import Session, select, desc

from app.database import get_session
from app.models.submission import (
    Submission, Version, Finding, Comment, AuditLog,
    SubmissionStatus, RiskTier, DemoRole
)
from app.models.schemas import SubmissionCreate
from app.core.roles import get_current_role
from app.core.parsers import extract_text_from_file
from app.core.diff import compute_text_diff
from app.engine.layer_a import run_layer_a_checks
from app.engine.layer_d import verify_and_ground_findings
from app.engine.tiering import calculate_risk_tier

router = APIRouter(prefix="/api/submissions", tags=["Submissions"])

def _execute_review_for_version(version: Version, submission: Submission, session: Session) -> List[Finding]:
    """Runs deterministic Layer A + Layer D Verifier + Risk Tier calculation on a version."""
    raw_findings = run_layer_a_checks(version.text, session, version_id=version.id)
    verified_findings, dropped_count = verify_and_ground_findings(raw_findings, version.text, session)
    
    # Save verified findings to database
    for f in verified_findings:
        session.add(f)
        
    # Update submission risk tier based on verified findings
    new_risk_tier = calculate_risk_tier(verified_findings)
    submission.risk_tier = new_risk_tier
    session.add(submission)
    
    # Audit log entry for review execution
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission.id,
        actor_role="System (Review Engine)",
        action="reviewed",
        detail=f"Generated {len(verified_findings)} verified findings ({dropped_count} dropped by verifier). Assessed as {new_risk_tier}."
    )
    session.add(audit)
    session.commit()
    return verified_findings

@router.post("", status_code=status.HTTP_201_CREATED)
def create_submission(
    payload: SubmissionCreate,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """Creates a new submission, initializes Version 1, and immediately executes review."""
    sub_id = f"sub-{uuid.uuid4().hex[:8]}"
    ver_id = f"ver-{uuid.uuid4().hex[:8]}"
    
    submission = Submission(
        id=sub_id,
        title=payload.title,
        channel=payload.channel,
        audience=payload.audience,
        intent_message=payload.intent_message or "",
        intent_cta=payload.intent_cta or "",
        risk_tier=RiskTier.TIER_1.value,
        status=SubmissionStatus.DRAFT.value,
        created_by_role=role
    )
    session.add(submission)
    
    version = Version(
        id=ver_id,
        submission_id=sub_id,
        number=1,
        text=payload.text
    )
    session.add(version)
    session.commit()
    
    # Run immediate review
    findings = _execute_review_for_version(version, submission, session)
    
    return {
        "submission": submission.model_dump(),
        "active_version": version.model_dump(),
        "findings": [f.model_dump() for f in findings],
        "findings_count": len(findings)
    }

@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_submission(
    file: UploadFile = File(...),
    title: str = Form("Uploaded Document"),
    channel: str = Form("web"),
    audience: str = Form("general"),
    intent_message: str = Form(""),
    intent_cta: str = Form(""),
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """Uploads document file (.txt/.md/.docx/.pdf/.html <= 2MB), extracts text, and creates submission."""
    file_bytes = await file.read()
    extracted_text = extract_text_from_file(file.filename or "upload.txt", file_bytes)
    
    payload = SubmissionCreate(
        title=title,
        text=extracted_text,
        channel=channel,
        audience=audience,
        intent_message=intent_message,
        intent_cta=intent_cta
    )
    return create_submission(payload=payload, role=role, session=session)

@router.get("")
def list_submissions(
    status_filter: Optional[str] = None,
    risk_filter: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """List submissions with optional status or risk tier filtering."""
    query = select(Submission).order_by(desc(Submission.updated_at))
    if status_filter:
        query = query.where(Submission.status == status_filter)
    if risk_filter:
        query = query.where(Submission.risk_tier == risk_filter)
        
    submissions = session.exec(query).all()
    results = []
    for s in submissions:
        latest_ver = session.exec(
            select(Version).where(Version.submission_id == s.id).order_by(desc(Version.number))
        ).first()
        findings_count = 0
        if latest_ver:
            findings = session.exec(select(Finding).where(Finding.version_id == latest_ver.id)).all()
            findings_count = len(findings)
        results.append({
            "submission": s.model_dump(),
            "version_number": latest_ver.number if latest_ver else 1,
            "findings_count": findings_count
        })
    return results

@router.get("/{submission_id}")
def get_submission_detail(
    submission_id: str,
    session: Session = Depends(get_session)
):
    """Fetches submission, active version, findings, comments, and audit timeline."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    versions = session.exec(
        select(Version).where(Version.submission_id == submission_id).order_by(Version.number)
    ).all()
    
    active_version = versions[-1] if versions else None
    findings = []
    if active_version:
        findings = session.exec(
            select(Finding).where(Finding.version_id == active_version.id)
        ).all()
        
    comments = session.exec(
        select(Comment).where(Comment.submission_id == submission_id).order_by(Comment.created_at)
    ).all()
    
    audit_logs = session.exec(
        select(AuditLog).where(AuditLog.submission_id == submission_id).order_by(AuditLog.created_at)
    ).all()
    
    return {
        "submission": submission.model_dump(),
        "active_version": active_version.model_dump() if active_version else None,
        "versions": [v.model_dump() for v in versions],
        "findings": [f.model_dump() for f in findings],
        "comments": [c.model_dump() for c in comments],
        "audit_logs": [a.model_dump() for a in audit_logs]
    }

@router.get("/{submission_id}/diff")
def get_version_diff(
    submission_id: str,
    from_version: Optional[int] = None,
    to_version: Optional[int] = None,
    session: Session = Depends(get_session)
):
    """Computes word-level diff between two versions (defaults to latest vs previous)."""
    versions = session.exec(
        select(Version).where(Version.submission_id == submission_id).order_by(Version.number)
    ).all()
    
    if len(versions) < 2 and (from_version is None or to_version is None):
        return {
            "has_diff": False,
            "message": "Only one version exists. Apply fixes to generate version diff.",
            "chunks": []
        }
        
    v_old = None
    v_new = None
    
    if from_version and to_version:
        for v in versions:
            if v.number == from_version:
                v_old = v
            if v.number == to_version:
                v_new = v
    else:
        v_old = versions[-2]
        v_new = versions[-1]
        
    if not v_old or not v_new:
        raise HTTPException(status_code=400, detail="Specified versions not found for diff.")
        
    diff_data = compute_text_diff(v_old.text, v_new.text)
    return {
        "has_diff": True,
        "from_version": v_old.number,
        "to_version": v_new.number,
        **diff_data
    }
