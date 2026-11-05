import io
from fastapi.testclient import TestClient

def test_empty_text_submission_rejected(client: TestClient):
    """Empty draft submission should be rejected with 422."""
    res = client.post(
        "/api/submissions",
        json={"title": "Empty Post", "text": ""},
        headers={"X-Demo-Role": "Creator"}
    )
    assert res.status_code == 422

def test_unsupported_file_extension_rejected(client: TestClient):
    """Uploading executable or zip files should be rejected with 415."""
    fake_exe = io.BytesIO(b"MZ\x90\x00\x03\x00\x00\x00")
    res = client.post(
        "/api/submissions/upload",
        files={"file": ("malware.exe", fake_exe, "application/octet-stream")},
        headers={"X-Demo-Role": "Creator"}
    )
    assert res.status_code == 415
    assert "Unsupported file extension" in res.json()["detail"]

def test_huge_file_upload_rejected(client: TestClient):
    """Files exceeding 2MB should be rejected with 413 Request Entity Too Large."""
    # 2.5MB payload
    huge_payload = io.BytesIO(b"A" * (2 * 1024 * 1024 + 500_000))
    res = client.post(
        "/api/submissions/upload",
        files={"file": ("huge_doc.txt", huge_payload, "text/plain")},
        headers={"X-Demo-Role": "Creator"}
    )
    assert res.status_code == 413
    assert "exceeds 2 MB limit" in res.json()["detail"]

def test_xss_payload_escaped_and_safe(client: TestClient):
    """XSS payloads must be treated purely as string data without executing or crashing review."""
    xss_draft = "<script>alert('xss')</script><img src='x' onerror='alert(1)'> FinEdge Pro"
    res = client.post(
        "/api/submissions",
        json={"title": "XSS Test", "text": xss_draft},
        headers={"X-Demo-Role": "Creator"}
    )
    assert res.status_code == 201
    data = res.json()
    assert data["submission"]["title"] == "XSS Test"
    # Should catch FinEdge Pro and ACC-001 (missing alt in img) without crashing
    findings = data["findings"]
    assert any(f["rule_id"] in ("TRM-011", "ACC-001") for f in findings)

def test_malformed_json_returns_422(client: TestClient):
    """Malformed body payloads should fail validation gracefully."""
    res = client.post(
        "/api/submissions",
        content=b'{"title": 12345, "text": null}',
        headers={"Content-Type": "application/json", "X-Demo-Role": "Creator"}
    )
    assert res.status_code == 422

def test_rate_limiter_blocks_excessive_traffic(client: TestClient):
    """Rate limiter protects sensitive submission creation endpoint."""
    from app.config import settings
    # Rapidly fire requests to verify rate limit
    blocked = False
    for i in range(settings.RATE_LIMIT_PER_MINUTE + 5):
        res = client.post(
            "/api/submissions",
            json={"title": f"Burst {i}", "text": "Valid text content"},
            headers={"X-Demo-Role": "Creator"}
        )
        if res.status_code == 429:
            blocked = True
            break
    assert blocked is True
