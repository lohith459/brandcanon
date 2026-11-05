from fastapi.testclient import TestClient

def test_ui_serves_html_page(client: TestClient):
    """Verifies that root '/' serves the main SPA html interface with workflow stepper and role switcher."""
    res = client.get("/")
    assert res.status_code == 200
    assert "BrandCanon" in res.text
    assert "Try the demo" in res.text
    assert "role-selector" in res.text

def test_static_assets_deliver_200(client: TestClient):
    """Verifies that custom CSS and JS assets are cleanly accessible."""
    css_res = client.get("/static/css/custom.css")
    assert css_res.status_code == 200
    assert ".highlight-span" in css_res.text

    js_app_res = client.get("/static/js/app.js")
    assert js_app_res.status_code == 200
    assert "loadWorkedExampleDemo" in js_app_res.text

    js_review_res = client.get("/static/js/review_ui.js")
    assert js_review_res.status_code == 200
    assert "renderHighlightedText" in js_review_res.text

def test_demo_drafts_endpoint(client: TestClient):
    """Verifies that /api/tools/demo-drafts delivers the 3 pre-seeded drafts."""
    res = client.get("/api/tools/demo-drafts")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    bad_draft = next((d for d in data if d["id"] == "draft-bad-001"), None)
    assert bad_draft is not None
    assert "Guaranteed 12% returns" in bad_draft["text"]
