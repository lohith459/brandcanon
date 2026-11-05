import uuid
from fastapi import APIRouter, Depends, HTTPException, Header, status
from sqlmodel import Session

from app.database import get_session
from app.models.submission import (
    Submission, Comment, AuditLog, SubmissionStatus, RiskTier, DemoRole
)
from app.models.schemas import WorkflowActionRequest, CommentCreate
from app.core.roles import get_current_role

router = APIRouter(prefix="/api/submissions", tags=["Workflow & Approvals"])

@router.post("/{submission_id}/submit-approval")
def submit_for_approval(
    submission_id: str,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """Creator submits draft to the review queue, transitioning status to 'in_review'."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    submission.status = SubmissionStatus.IN_REVIEW.value
    session.add(submission)
    
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission_id,
        actor_role=role,
        action="submitted_for_approval",
        detail=f"Content submitted for editorial approval by {role}."
    )
    session.add(audit)
    session.commit()
    
    return {
        "status": "success",
        "submission_id": submission_id,
        "submission_status": submission.status
    }

@router.post("/{submission_id}/decide")
def review_decision(
    submission_id: str,
    payload: WorkflowActionRequest,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """
    Reviewers (Manager, Compliance Reviewer, Admin) approve, request changes, or reject.
    CRITICAL COMPLIANCE ENFORCEMENT:
    Tier 3 submissions CANNOT be approved by Manager alone. They strictly require Compliance Reviewer sign-off.
    """
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    valid_actions = (
        SubmissionStatus.APPROVED.value,
        SubmissionStatus.CHANGES_REQUESTED.value,
        SubmissionStatus.REJECTED.value
    )
    if payload.action not in valid_actions:
        raise HTTPException(status_code=400, detail=f"Invalid action '{payload.action}'.")

    # Creator cannot approve/reject
    if role == DemoRole.CREATOR.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Creators cannot approve or reject submissions. Switch to Manager or Compliance Reviewer role."
        )

    # TIER 3 COMPLIANCE GATE
    if payload.action == SubmissionStatus.APPROVED.value:
        if submission.risk_tier == RiskTier.TIER_3.value:
            if role not in (DemoRole.COMPLIANCE.value, DemoRole.ADMIN.value):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Tier 3 submissions contain critical compliance risks and cannot be approved by a Manager alone. Sign-off from a Compliance Reviewer is required."
                )

    submission.status = payload.action
    session.add(submission)
    
    # Add optional decision comment
    if payload.comment and payload.comment.strip():
        comment = Comment(
            id=f"cmt-{uuid.uuid4().hex[:10]}",
            submission_id=submission_id,
            role=role,
            text=payload.comment.strip()
        )
        session.add(comment)
        
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission_id,
        actor_role=role,
        action=payload.action,
        detail=f"Submission status changed to {payload.action} by {role}. {payload.comment or ''}".strip()
    )
    session.add(audit)
    session.commit()
    
    return {
        "status": "success",
        "submission_id": submission_id,
        "submission_status": submission.status,
        "decided_by": role
    }

@router.post("/{submission_id}/comments")
def add_comment(
    submission_id: str,
    payload: CommentCreate,
    role: str = Depends(get_current_role),
    session: Session = Depends(get_session)
):
    """Adds a review or feedback comment to the submission discussion thread."""
    submission = session.get(Submission, submission_id)
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
        
    comment = Comment(
        id=f"cmt-{uuid.uuid4().hex[:10]}",
        submission_id=submission_id,
        role=role,
        text=payload.text.strip()
    )
    session.add(comment)
    
    audit = AuditLog(
        id=f"aud-{uuid.uuid4().hex[:10]}",
        submission_id=submission_id,
        actor_role=role,
        action="comment_added",
        detail=f"Added comment: {payload.text[:80]}..."
    )
    session.add(audit)
    session.commit()
    
    return comment.model_dump()
