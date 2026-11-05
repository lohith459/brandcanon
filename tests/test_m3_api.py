from fastapi.testclient import TestClient
from sqlmodel import Session
from app.models.submission import FindingDecision, RiskTier, SubmissionStatus

def test_full_m3_submission_review_fix_approval_lifecycle(client: TestClient):
    """
    Tests the complete end-to-end API workflow:
    1. Create submission with bad worked example
    2. Check findings and Tier 3 classification
    3. Dismiss a finding with reason (and verify failure without reason)
    4. Accept fixes
    5. Apply fixes backwards -> auto creates Version 2 + auto re-runs review
    6. Verify diff endpoint
    7. Submit for approval
    8. Attempt approval as Manager -> blocked by Tier 3 compliance gate (403)
    9. Approve as Compliance Reviewer -> succeeds (200)
    10. Verify audit log trail
    """
    bad_draft = "Guaranteed 12% returns!! Join 50,000+ investors on FinEdge Pro. It's FREE forever!"
    
    # 1. Create submission
    res = client.post(
        "/api/submissions",
        json={
            "title": "FinEdge Pro Worked Example",
            "text": bad_draft,
            "channel": "twitter",
            "audience": "prospective_customers",
            "intent_message": "drive sign-ups",
            "intent_cta": "Join FinEdge Plus"
        },
        headers={"X-Demo-Role": "Creator"}
    )
    assert res.status_code == 201
    data = res.json()
    sub_id = data["submission"]["id"]
    findings = data["findings"]
    assert len(findings) >= 5
    assert data["submission"]["risk_tier"] == RiskTier.TIER_3.value
    
    # 2. Test Dismissal validation: Reason is required!
    sample_finding = findings[0]
    dismiss_no_reason = client.post(
        f"/api/submissions/{sub_id}/findings/{sample_finding['id']}/decision",
        json={"decision": "dismissed", "decision_reason": ""},
        headers={"X-Demo-Role": "Creator"}
    )
    assert dismiss_no_reason.status_code == 422
    
    # Dismiss with reason succeeds
    dismiss_with_reason = client.post(
        f"/api/submissions/{sub_id}/findings/{sample_finding['id']}/decision",
        json={"decision": "dismissed", "decision_reason": "Approved exception for internal test"},
        headers={"X-Demo-Role": "Creator"}
    )
    assert dismiss_with_reason.status_code == 200
    assert dismiss_with_reason.json()["finding"]["decision"] == "dismissed"
    
    # 3. Accept fixes for terminology (FinEdge Pro -> FinEdge Plus) and disclaimer
    term_finding = next((f for f in findings if "FinEdge Pro" in f["quoted_text"]), None)
    assert term_finding is not None
    client.post(
        f"/api/submissions/{sub_id}/findings/{term_finding['id']}/decision",
        json={"decision": "accepted"},
        headers={"X-Demo-Role": "Creator"}
    )
    
    disc_finding = next((f for f in findings if f["rule_id"] == "DISC-002"), None)
    assert disc_finding is not None
    client.post(
        f"/api/submissions/{sub_id}/findings/{disc_finding['id']}/decision",
        json={"decision": "accepted"},
        headers={"X-Demo-Role": "Creator"}
    )
    
    # 4. Apply fixes backwards (Requirement 4)
    apply_res = client.post(
        f"/api/submissions/{sub_id}/apply-fixes",
        headers={"X-Demo-Role": "Creator"}
    )
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["new_version"]["number"] == 2
    assert "FinEdge Plus" in apply_data["new_version"]["text"]
    assert "Investments are subject to market risks." in apply_data["new_version"]["text"]
    assert apply_data["applied_fixes_count"] >= 2
    # Verify auto re-review was run
    assert "new_findings" in apply_data
    
    # 5. Check version diff endpoint
    diff_res = client.get(f"/api/submissions/{sub_id}/diff")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert diff_data["has_diff"] is True
    assert diff_data["from_version"] == 1
    assert diff_data["to_version"] == 2
    
    # 6. Submit for approval
    submit_res = client.post(
        f"/api/submissions/{sub_id}/submit-approval",
        headers={"X-Demo-Role": "Creator"}
    )
    assert submit_res.status_code == 200
    assert submit_res.json()["submission_status"] == "in_review"
    
    # 7. Creator cannot approve/reject
    creator_decide = client.post(
        f"/api/submissions/{sub_id}/decide",
        json={"action": "approved"},
        headers={"X-Demo-Role": "Creator"}
    )
    assert creator_decide.status_code == 403
    
    # 8. Tier 3 Gate: Manager cannot approve Tier 3 submission
    # Note: Guaranteed 12% returns is still present in text, so it remains Tier 3
    mgr_decide = client.post(
        f"/api/submissions/{sub_id}/decide",
        json={"action": "approved", "comment": "Looks good from manager side"},
        headers={"X-Demo-Role": "Manager"}
    )
    assert mgr_decide.status_code == 403
    assert "Compliance Reviewer" in mgr_decide.json()["detail"]
    
    # 9. Compliance Reviewer CAN approve Tier 3 submission
    comp_decide = client.post(
        f"/api/submissions/{sub_id}/decide",
        json={"action": "approved", "comment": "Approved by Chief Compliance Officer after manual review"},
        headers={"X-Demo-Role": "Compliance Reviewer"}
    )
    assert comp_decide.status_code == 200
    assert comp_decide.json()["submission_status"] == "approved"
    
    # 10. Verify submission detail, comments, and audit trail
    detail_res = client.get(f"/api/submissions/{sub_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["submission"]["status"] == "approved"
    assert len(detail["versions"]) == 2
    assert len(detail["comments"]) >= 1
    assert any(a["action"] == "fixes_applied" for a in detail["audit_logs"])
    assert any(a["action"] == "approved" for a in detail["audit_logs"])
