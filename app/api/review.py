import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlmodel import Session, select, desc

from app.database import get_session
from app.models.submission import (
    Submission, Version, Finding, AuditLog, FindingDecision, DemoRole
)
from app.models.schemas import FindingDecisionRequest
from app.core.roles import get_current_role
from app.core.fixes import apply_accepted_fixes
from app.core.diff import compute_text_diff
from app.engine.layer_a import run_layer_a_checks
from app.engine.layer_d import verify_and_ground_findings
from app.engine.tiering import calculate_risk_tier

router = APIRouter(prefix="/api/submissions", tags=["Review & Fixes"])

@router.post("/{submission_id}/review")
def rerun_review(
    submission_id: str,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """Re-runs the review engine on the submission's latest active version."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    latest_version = session.exec(
        select(Version).where(Version.submission_id == submission_id).order_by(desc(Version.number))
    ).first()
    if not latest_version:
        raise HTTPException(status_code=400, detail="Submission has no active version.")

    # Remove previous pending findings on this version to avoid duplicates
    existing_findings = session.exec(
        select(Finding).where(Finding.version_id == latest_version.id)
    ).all()
    for ef in existing_findings:
        session.delete(ef)
        
    raw_findings = run_layer_a_checks(latest_version.text, session, version_id=latest_version.id)
    verified, dropped = verify_and_ground_findings(raw_findings, latest_version.text, session)
    
    for f in verified:
        session.add(f)
        
    submission.risk_tier = calculate_risk_tier(verified)
    session.add(submission)
    
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission.id,
        actor_role=role,
        action="reviewed",
        detail=f"Re-ran review. {len(verified)} verified findings, {dropped} dropped. Risk Tier: {submission.risk_tier}."
    )
    session.add(audit)
    session.commit()
    
    return {
        "status": "success",
        "version_id": latest_version.id,
        "findings": [f.model_dump() for f in verified],
        "risk_tier": submission.risk_tier,
        "dropped_count": dropped
    }

@router.post("/{submission_id}/findings/{finding_id}/decision")
def record_finding_decision(
    submission_id: str,
    finding_id: str,
    payload: FindingDecisionRequest,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """
    Records creator or reviewer decision for a specific finding: 'accepted', 'edited', or 'dismissed'.
    Dismissal strictly requires a decision reason.
    """
    finding = session.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found.")
        
    if payload.decision not in ("accepted", "edited", "dismissed", "pending"):
        raise HTTPException(status_code=400, detail=f"Invalid decision '{payload.decision}'.")
        
    # Dismissal strictly requires a reason
    if payload.decision == "dismissed":
        if not payload.decision_reason or not payload.decision_reason.strip():
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="A written reason is required to dismiss a brand guideline finding."
            )
        finding.decision_reason = payload.decision_reason.strip()

    # Edited decision allows custom fix override
    if payload.decision == "edited":
        if payload.edited_fix:
            finding.suggested_fix = payload.edited_fix.strip()
        finding.decision_reason = payload.decision_reason or "Custom edit applied by user."

    finding.decision = payload.decision
    session.add(finding)
    
    # Audit log
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission_id,
        actor_role=role,
        action="finding_decision",
        detail=f"Finding '{finding.quoted_text or finding.rule_id}' marked as {payload.decision}. Reason: {finding.decision_reason or 'None'}."
    )
    session.add(audit)
    session.commit()
    
    return {"status": "success", "finding": finding.model_dump()}

@router.post("/{submission_id}/apply-fixes")
def apply_fixes_and_version(
    submission_id: str,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """
    Applies accepted fixes to create a new Version:
    1. Sorts accepted findings backwards to preserve earlier offsets safely.
    2. Safely handles and skips overlapping spans.
    3. Creates new Version (number = current + 1).
    4. Automatically re-runs the review on the new version.
    5. Computes tracked-changes diff.
    """
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    current_version = session.exec(
        select(Version).where(Version.submission_id == submission_id).order_by(desc(Version.number))
    ).first()
    if not current_version:
        raise HTTPException(status_code=400, detail="Submission has no existing version.")
        
    # Gather accepted findings
    accepted_findings = session.exec(
        select(Finding).where(
            Finding.version_id == current_version.id,
            Finding.decision.in_([FindingDecision.ACCEPTED.value, FindingDecision.EDITED.value])
        )
    ).all()
    
    if not accepted_findings:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No accepted fixes found. Please accept at least one finding fix before applying."
        )

    # Apply fixes backwards
    transformed_text, applied_count, skipped_overlap = apply_accepted_fixes(
        current_version.text, accepted_findings
    )
    
    # Create new version
    new_version_number = current_version.number + 1
    new_version = Version(
        id=f"ver-{uuid.uuid4().hex[:8]}",
        submission_id=submission_id,
        number=new_version_number,
        text=transformed_text
    )
    session.add(new_version)
    session.commit()
    
    # Automatically re-run review on the new version (Requirement 4)
    raw_findings = run_layer_a_checks(transformed_text, session, version_id=new_version.id)
    verified_findings, dropped = verify_and_ground_findings(raw_findings, transformed_text, session)
    for f in verified_findings:
        session.add(f)
        
    # Re-calculate risk tier
    submission.risk_tier = calculate_risk_tier(verified_findings)
    submission.status = "draft"  # Remains draft until creator explicitly submits for approval
    session.add(submission)
    
    # Audit log
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission_id,
        actor_role=role,
        action="fixes_applied",
        detail=f"Created Version {new_version_number} by applying {applied_count} fixes ({skipped_overlap} overlapping skipped). Re-review produced {len(verified_findings)} findings."
    )
    session.add(audit)
    session.commit()
    
    diff_data = compute_text_diff(current_version.text, transformed_text)
    
    return {
        "status": "success",
        "applied_fixes_count": applied_count,
        "skipped_overlap_count": skipped_overlap,
        "new_version": new_version.model_dump(),
        "diff": diff_data,
        "new_findings": [f.model_dump() for f in verified_findings],
        "new_risk_tier": submission.risk_tier
    }
