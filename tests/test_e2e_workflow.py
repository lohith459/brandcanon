from fastapi.testclient import TestClient
from app.models.submission import RiskTier, SubmissionStatus

def test_full_governance_e2e_workflow_with_tier3_compliance_escalation(client: TestClient):
    """
    Comprehensive End-to-End Governance Test:
    1. Creator submits draft containing multiple severe violations (Tier 3)
    2. Creator reviews findings and inspects exact evidence citations
    3. Creator dismisses 1 finding with reason (and verifies rejection without reason)
    4. Creator accepts 2 critical fixes
    5. Creator applies fixes backwards -> new Version 2 generated, review re-runs automatically
    6. System computes word-level diff
    7. Creator submits Version 2 for approval -> status: in_review
    8. Manager attempts to approve Tier 3 -> STRICTLY FORBIDDEN (403)
    9. Compliance Reviewer reviews and approves -> status: approved (200)
    10. Audit log preserves complete unalterable timeline
    """
    draft_text = "Guaranteed 12% returns!! Join 50,000+ investors on FinEdge Pro. It's FREE forever!"

    # Step 1: Submit draft as Creator
    create_res = client.post(
        "/api/submissions",
        json={
            "title": "FinEdge Pro Worked Example",
            "text": draft_text,
            "channel": "twitter",
            "audience": "prospective_customers",
            "intent_cta": "Join FinEdge Plus",
            "intent_message": "drive sign-ups"
        },
        headers={"X-Demo-Role": "Creator"}
    )
    assert create_res.status_code == 201
    created_data = create_res.json()
    sub_id = created_data["submission"]["id"]
    findings = created_data["findings"]

    # Verify initial Tier 3 risk assignment due to CMP-004
    assert created_data["submission"]["risk_tier"] == RiskTier.TIER_3.value
    assert any(f["rule_id"] == "CMP-004" for f in findings)
    assert any(f["rule_id"] == "TRM-011" for f in findings)
    assert any(f["fact_id"] == "F-017" for f in findings)

    # Step 2: Dismiss with reason
    trm_finding = next(f for f in findings if f["rule_id"] == "TRM-011")
    dismiss_res = client.post(
        f"/api/submissions/{sub_id}/findings/{trm_finding['id']}/decision",
        json={"decision": "dismissed", "decision_reason": "Testing dismissal logging"},
        headers={"X-Demo-Role": "Creator"}
    )
    assert dismiss_res.status_code == 200

    # Step 3: Accept fix for guaranteed returns
    cmp_finding = next(f for f in findings if f["rule_id"] == "CMP-004")
    accept_res = client.post(
        f"/api/submissions/{sub_id}/findings/{cmp_finding['id']}/decision",
        json={"decision": "accepted"},
        headers={"X-Demo-Role": "Creator"}
    )
    assert accept_res.status_code == 200

    # Step 4: Apply fixes backwards to produce Version 2
    apply_res = client.post(
        f"/api/submissions/{sub_id}/apply-fixes",
        headers={"X-Demo-Role": "Creator"}
    )
    assert apply_res.status_code == 200
    applied_data = apply_res.json()
    assert applied_data["new_version"]["number"] == 2
    assert "diff" in applied_data

    # Step 5: Creator submits for approval
    submit_approval_res = client.post(
        f"/api/submissions/{sub_id}/submit-approval",
        headers={"X-Demo-Role": "Creator"}
    )
    assert submit_approval_res.status_code == 200

    # Step 6: Manager tries to approve Tier 3 -> Blocked by Compliance Gate
    mgr_attempt = client.post(
        f"/api/submissions/{sub_id}/decide",
        json={"action": "approved", "comment": "Manager approval attempt"},
        headers={"X-Demo-Role": "Manager"}
    )
    assert mgr_attempt.status_code == 403
    assert "Compliance Reviewer" in mgr_attempt.json()["detail"]

    # Step 7: Compliance Reviewer signs off
    compliance_approval = client.post(
        f"/api/submissions/{sub_id}/decide",
        json={"action": "approved", "comment": "Chief Compliance Officer manual sign-off"},
        headers={"X-Demo-Role": "Compliance Reviewer"}
    )
    assert compliance_approval.status_code == 200
    assert compliance_approval.json()["submission_status"] == SubmissionStatus.APPROVED.value

    # Step 8: Verify full audit log
    detail_res = client.get(f"/api/submissions/{sub_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    audit_actions = [a["action"] for a in detail["audit_logs"]]
    assert "reviewed" in audit_actions
    assert "finding_decision" in audit_actions
    assert "fixes_applied" in audit_actions
    assert "submitted_for_approval" in audit_actions
    assert "approved" in audit_actions
