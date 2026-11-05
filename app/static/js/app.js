// BrandCanon Application State & Router

const state = {
    currentRole: "Creator",
    currentSubmission: null,
    activeVersion: null,
    findings: [],
    confidentialMode: false,
    selectedFindingId: null,
    demoDrafts: []
};

// Initial setup on DOM ready
document.addEventListener("DOMContentLoaded", async () => {
    // Restore or initialize demo role
    const storedRole = localStorage.getItem("brandcanon_role") || "Creator";
    document.getElementById("role-selector").value = storedRole;
    state.currentRole = storedRole;
    updateRoleIndicator();

    // Fetch demo drafts
    try {
        const res = await fetch("/api/tools/demo-drafts");
        if (res.ok) {
            state.demoDrafts = await res.json();
        }
    } catch (e) {
        console.warn("Failed to prefetch demo drafts:", e);
    }

    // Default route
    navigateTo("submit");
});

// Role Switcher
function onRoleChanged() {
    const sel = document.getElementById("role-selector");
    state.currentRole = sel.value;
    localStorage.setItem("brandcanon_role", state.currentRole);
    updateRoleIndicator();
    if (document.getElementById("screen-approval").style.display !== "none" &&
        document.getElementById("screen-approval").style.display !== "") {
        loadApprovalQueue();
    }
}

function updateRoleIndicator() {
    const label = document.getElementById("approval-current-role-label");
    if (label) label.textContent = state.currentRole;
}

// Navigation Stepper
function navigateTo(screenId) {
    // Hide all screens
    document.querySelectorAll(".screen-view").forEach(el => {
        el.style.display = "none";
        el.classList.remove("active");
    });
    // Show target screen
    const target = document.getElementById(`screen-${screenId}`);
    if (target) {
        target.style.display = "block";
        target.classList.add("active", "fade-up");
    }

    // Update stepper button active states
    ["submit", "review", "diff", "approval", "canon"].forEach(step => {
        const btn = document.getElementById(`step-btn-${step}`);
        if (!btn) return;
        if (step === screenId) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    if (screenId === "approval") {
        loadApprovalQueue();
    } else if (screenId === "canon") {
        switchCanonTab("rules");
    }
}

// 1-Click "Try the demo" Worked Example
async function loadWorkedExampleDemo() {
    const badDraft = state.demoDrafts.find(d => d.id === "draft-bad-001") || {
        title: "FinEdge Pro Worked Example",
        channel: "twitter",
        audience: "prospective_customers",
        intent_message: "drive sign-ups with an attractive offer and social proof",
        intent_cta: "Join FinEdge Plus",
        text: "Guaranteed 12% returns!! Join 50,000+ investors on FinEdge Pro. It's FREE forever!"
    };

    // Populate input fields
    document.getElementById("input-title").value = badDraft.title;
    document.getElementById("input-channel").value = badDraft.channel;
    document.getElementById("input-audience").value = badDraft.audience;
    document.getElementById("input-cta").value = badDraft.intent_cta;
    document.getElementById("input-intent").value = badDraft.intent_message;
    document.getElementById("input-text").value = badDraft.text;

    // Immediately submit and run review in 1 click
    await submitContentForReview();
}

function loadSampleDraft(type) {
    let draft;
    if (type === "bad") {
        draft = state.demoDrafts.find(d => d.id === "draft-bad-001");
    } else if (type === "medium") {
        draft = state.demoDrafts.find(d => d.id === "draft-medium-002");
    } else {
        draft = state.demoDrafts.find(d => d.id === "draft-clean-003");
    }
    if (!draft) return;

    document.getElementById("input-title").value = draft.title;
    document.getElementById("input-channel").value = draft.channel;
    document.getElementById("input-audience").value = draft.audience;
    document.getElementById("input-cta").value = draft.intent_cta;
    document.getElementById("input-intent").value = draft.intent_message;
    document.getElementById("input-text").value = draft.text;
}

// File Upload Handler
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    document.getElementById("file-name-display").textContent = `Selected: ${file.name} (${(file.size / 1024).toFixed(1)} KB)`;
    if (file.name.endsWith(".txt") || file.name.endsWith(".md")) {
        const text = await file.text();
        document.getElementById("input-text").value = text;
    }
}

function handleFileDrop(event) {
    event.preventDefault();
    document.getElementById("drop-zone").classList.remove("drag-over");
    const file = event.dataTransfer.files[0];
    if (file) handleFileUpload({ target: { files: [file] } });
}

// Submit Content & Run Review Engine
async function submitContentForReview() {
    const title = document.getElementById("input-title").value.trim() || "Untitled Content";
    const text = document.getElementById("input-text").value.trim();
    const channel = document.getElementById("input-channel").value;
    const audience = document.getElementById("input-audience").value.trim() || "general";
    const intent_cta = document.getElementById("input-cta").value.trim() || "";
    const intent_message = document.getElementById("input-intent").value.trim() || "";
    const confidential = document.getElementById("confidential-mode-toggle").checked;

    if (!text) {
        alert("Please enter draft copy or upload a file to review.");
        return;
    }

    const btn = document.getElementById("btn-run-review");
    btn.disabled = true;
    btn.innerHTML = `<span>Analyzing against Canon...</span>`;

    try {
        const res = await fetch("/api/submissions", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Demo-Role": state.currentRole
            },
            body: JSON.stringify({
                title,
                text,
                channel,
                audience,
                intent_cta,
                intent_message,
                confidential_mode: confidential
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Review failed: ${err.detail || "Server error"}`);
            return;
        }

        const data = await res.json();
        state.currentSubmission = data.submission;
        state.activeVersion = data.active_version;
        state.findings = data.findings;

        // Render Review Screen & navigate
        renderReviewScreen();
        navigateTo("review");

    } catch (err) {
        alert(`Network error during review: ${err.message}`);
    } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Run Brand Review</span><span>→</span>`;
    }
}

// Render Review Screen (Text with Highlights + Cards)
function renderReviewScreen() {
    if (!state.currentSubmission || !state.activeVersion) return;

    document.getElementById("review-title").textContent = state.currentSubmission.title;
    document.getElementById("review-version-badge").textContent = `Version ${state.activeVersion.number}`;
    document.getElementById("review-channel-badge").textContent = `Channel: ${state.currentSubmission.channel}`;
    document.getElementById("review-cta-badge").textContent = `CTA: ${state.currentSubmission.intent_cta || "None specified"}`;

    // Update Risk Tier Badge
    const riskBadge = document.getElementById("review-risk-badge");
    const tier = state.currentSubmission.risk_tier;
    if (tier === "Tier 3") {
        riskBadge.className = "tier-3";
        riskBadge.style.cssText = "font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:4px 12px;border-radius:20px;";
        riskBadge.innerHTML = "<span>⚠️ Tier 3 (Critical)</span>";
    } else if (tier === "Tier 2") {
        riskBadge.className = "tier-2";
        riskBadge.style.cssText = "font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:4px 12px;border-radius:20px;";
        riskBadge.innerHTML = "<span>Tier 2 (High Risk)</span>";
    } else {
        riskBadge.className = "tier-1";
        riskBadge.style.cssText = "font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:0.08em;padding:4px 12px;border-radius:20px;";
        riskBadge.innerHTML = "<span>Tier 1 (Low Risk)</span>";
    }

    // Counts by severity
    const counts = { critical: 0, high: 0, medium: 0, low: 0 };
    state.findings.forEach(f => {
        const sev = (f.severity || "medium").toLowerCase();
        if (counts[sev] !== undefined) counts[sev]++;
    });
    document.getElementById("badge-count-critical").textContent = `${counts.critical} Critical`;
    document.getElementById("badge-count-high").textContent = `${counts.high} High`;
    document.getElementById("badge-count-medium").textContent = `${counts.medium} Medium`;
    document.getElementById("badge-count-low").textContent = `${counts.low} Low`;

    // Render interactive text highlights & finding cards
    renderHighlightedText(state.activeVersion.text, state.findings);
    renderFindingCards(state.findings);
    updateAcceptedCountBadge();
}

function updateAcceptedCountBadge() {
    const acceptedCount = state.findings.filter(f => f.decision === "accepted" || f.decision === "edited").length;
    document.getElementById("accepted-count-badge").textContent = acceptedCount;
}

// Apply Accepted Fixes -> Generates new version & diff
async function applyAcceptedFixes() {
    if (!state.currentSubmission) return;

    const acceptedCount = state.findings.filter(f => f.decision === "accepted" || f.decision === "edited").length;
    if (acceptedCount === 0) {
        alert("Please accept at least one suggested fix before applying.");
        return;
    }

    try {
        const res = await fetch(`/api/submissions/${state.currentSubmission.id}/apply-fixes`, {
            method: "POST",
            headers: { "X-Demo-Role": state.currentRole }
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Failed to apply fixes: ${err.detail || "Error"}`);
            return;
        }

        const data = await res.json();
        state.activeVersion = data.new_version;
        state.findings = data.new_findings;
        state.currentSubmission.risk_tier = data.new_risk_tier;

        // Render diff screen
        renderDiffScreen(data.diff);
        navigateTo("diff");

    } catch (err) {
        alert(`Error applying fixes: ${err.message}`);
    }
}

// Render Diff Screen
function renderDiffScreen(diff) {
    const container = document.getElementById("diff-output-container");
    container.innerHTML = "";

    document.getElementById("diff-word-change-badge").textContent = `${diff.word_change > 0 ? '+' : ''}${diff.word_change} words change (${diff.old_word_count} → ${diff.new_word_count})`;

    diff.chunks.forEach(chunk => {
        const span = document.createElement("span");
        if (chunk.type === "equal") {
            span.textContent = chunk.text + " ";
        } else if (chunk.type === "delete") {
            span.className = "diff-del";
            span.textContent = chunk.text + " ";
        } else if (chunk.type === "insert") {
            span.className = "diff-ins";
            span.textContent = chunk.text + " ";
        }
        container.appendChild(span);
    });
}

// Submit Draft for Approval
async function submitDraftForApproval() {
    if (!state.currentSubmission) return;
    try {
        const res = await fetch(`/api/submissions/${state.currentSubmission.id}/submit-approval`, {
            method: "POST",
            headers: { "X-Demo-Role": state.currentRole }
        });
        if (res.ok) {
            alert("Draft successfully submitted to approval queue!");
            navigateTo("approval");
        } else {
            const err = await res.json();
            alert(`Failed: ${err.detail}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

// Approval Queue Loader
async function loadApprovalQueue() {
    try {
        const res = await fetch("/api/submissions");
        if (!res.ok) return;
        const submissions = await res.json();
        const tbody = document.getElementById("approval-table-body");
        tbody.innerHTML = "";

        if (submissions.length === 0) {
            tbody.innerHTML = `<tr><td colspan="6" style="padding:32px;text-align:center;font-size:12px;color:#6b7280;">No submissions found. Submit content to populate the queue.</td></tr>`;
            return;
        }

        submissions.forEach(item => {
            const s = item.submission;
            const tr = document.createElement("tr");
            tr.style.cursor = "pointer";
            tr.onclick = () => selectApprovalSubmission(s.id);

            const statusColors = {
                approved: { bg: 'rgba(6,214,160,0.15)', color: '#6ee7b7' },
                in_review: { bg: 'rgba(76,201,240,0.15)', color: '#93c5fd' },
                changes_requested: { bg: 'rgba(245,158,11,0.15)', color: '#fcd34d' },
                rejected: { bg: 'rgba(239,68,68,0.15)', color: '#fca5a5' }
            };
            const sc = statusColors[s.status] || { bg: 'rgba(255,255,255,0.08)', color: '#a0a0c8' };
            const statusBadge = `<span style="font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;background:${sc.bg};color:${sc.color};">${s.status}</span>`;

            const tierColors = { 'Tier 3': '#fca5a5', 'Tier 2': '#fcd34d', 'Tier 1': '#6ee7b7' };
            const tierBg = { 'Tier 3': 'rgba(239,68,68,0.15)', 'Tier 2': 'rgba(245,158,11,0.15)', 'Tier 1': 'rgba(6,214,160,0.15)' };
            const tierBadge = `<span style="font-size:10px;font-weight:700;padding:3px 8px;border-radius:6px;background:${tierBg[s.risk_tier]||'rgba(255,255,255,0.08)'};color:${tierColors[s.risk_tier]||'#a0a0c8'};">${s.risk_tier}</span>`;

            tr.innerHTML = `
                <td style="padding:12px 16px;font-weight:600;color:#f0f0ff;">${escapeHtml(s.title)}</td>
                <td style="padding:12px 16px;color:#a0a0c8;text-transform:capitalize;">${s.channel}</td>
                <td style="padding:12px 16px;">${tierBadge}</td>
                <td style="padding:12px 16px;">${statusBadge}</td>
                <td style="padding:12px 16px;color:#6b7280;font-family:monospace;font-size:11px;">${item.findings_count} issues</td>
                <td style="padding:12px 16px;text-align:right;">
                    <button style="background:none;border:none;cursor:pointer;font-size:11px;color:#8b5cf6;font-weight:600;" onmouseover="this.style.textDecoration='underline'" onmouseout="this.style.textDecoration='none'">Inspect →</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        // Automatically inspect the first submission or currently selected
        if (submissions.length > 0) {
            selectApprovalSubmission(state.currentSubmission ? state.currentSubmission.id : submissions[0].submission.id);
        }

    } catch (e) {
        console.error("Failed to load approval queue:", e);
    }
}

// Select & Inspect Submission in Approval Queue
async function selectApprovalSubmission(subId) {
    try {
        const res = await fetch(`/api/submissions/${subId}`);
        if (!res.ok) return;
        const detail = await res.json();
        const panel = document.getElementById("approval-detail-panel");
        panel.style.display = "block";

        const s = detail.submission;
        const activeVer = detail.active_version;
        state.currentSubmission = s;

        document.getElementById("approval-detail-title").textContent = s.title;
        document.getElementById("approval-detail-status").textContent = `Status: ${s.status.toUpperCase()}`;
        document.getElementById("approval-detail-tier-badge").textContent = s.risk_tier;
        document.getElementById("approval-detail-text").textContent = activeVer ? activeVer.text : "No text content.";

        // Check Tier 3 Compliance Gate Alert
        const alertBox = document.getElementById("tier3-compliance-alert");
        if (s.risk_tier === "Tier 3") {
            alertBox.style.display = "block";
        } else {
            alertBox.style.display = "none";
        }

        // Render timeline
        const timeline = document.getElementById("approval-timeline-container");
        timeline.innerHTML = "";
        detail.audit_logs.forEach(log => {
            const div = document.createElement("div");
            div.style.cssText = "display:flex;align-items:flex-start;gap:10px;border-left:2px solid rgba(139,92,246,0.3);padding-left:12px;padding-bottom:8px;";
            div.innerHTML = `
                <div style="font-size:11px;color:#a0a0c8;">
                    <span style="font-weight:700;color:#c4b5fd;">${escapeHtml(log.actor_role)}</span>
                    <span style="color:#6b7280;">(${log.action})</span>:
                    <span>${escapeHtml(log.detail)}</span>
                </div>
            `;
            timeline.appendChild(div);
        });

    } catch (e) {
        console.error("Error inspecting submission:", e);
    }
}

// Reviewer Workflow Verdict Decision (Approve / Changes / Reject)
async function executeWorkflowDecision(action) {
    if (!state.currentSubmission) return;
    const comment = document.getElementById("approval-comment-input").value.trim();

    try {
        const res = await fetch(`/api/submissions/${state.currentSubmission.id}/decide`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Demo-Role": state.currentRole
            },
            body: JSON.stringify({ action, comment })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`⚠️ Action Blocked: ${err.detail}`);
            return;
        }

        alert(`Submission successfully marked as '${action}'!`);
        document.getElementById("approval-comment-input").value = "";
        loadApprovalQueue();

    } catch (e) {
        alert(`Error executing decision: ${e.message}`);
    }
}

// Canon Registry Browser
async function switchCanonTab(tab) {
    ["rules", "facts", "terms", "assets"].forEach(t => {
        const btn = document.getElementById(`canon-tab-${t}`);
        if (!btn) return;
        if (t === tab) {
            btn.classList.add("active");
        } else {
            btn.classList.remove("active");
        }
    });

    const container = document.getElementById("canon-content-container");
    container.innerHTML = `<div style="text-align:center;padding:32px;font-size:12px;color:#6b7280;">Loading ${tab}...</div>`;

    try {
        const res = await fetch(`/api/canon/${tab}`);
        if (!res.ok) return;
        const data = await res.json();

        if (tab === "rules") {
            let html = `<div style="display:flex;flex-direction:column;gap:10px;">`;
            data.forEach(r => {
                const sevColor = r.severity === 'critical' ? 'rgba(239,68,68,0.15)' : r.severity === 'high' ? 'rgba(245,158,11,0.15)' : 'rgba(76,201,240,0.1)';
                const sevText = r.severity === 'critical' ? '#fca5a5' : r.severity === 'high' ? '#fcd34d' : '#93c5fd';
                html += `
                    <div style="padding:14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                            <span style="font-family:monospace;font-size:12px;font-weight:700;color:#c4b5fd;">${r.id} <span style="color:#6b7280;font-weight:400;">(${r.category})</span></span>
                            <span style="font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;background:${sevColor};color:${sevText};">${r.severity}</span>
                        </div>
                        <p style="font-size:12px;color:#a0a0c8;margin:0 0 4px;">${escapeHtml(r.text)}</p>
                        ${r.fix_hint ? `<p style="font-size:11px;color:#6ee7b7;margin:0;"><strong>Fix:</strong> ${escapeHtml(r.fix_hint)}</p>` : ''}
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;

        } else if (tab === "facts") {
            let html = `<div style="display:flex;flex-direction:column;gap:10px;">`;
            data.forEach(f => {
                html += `
                    <div style="padding:14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;">
                        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">
                            <span style="font-family:monospace;font-size:12px;font-weight:700;color:#c4b5fd;">${f.id} — <span style="color:#a0a0c8;font-weight:400;">${escapeHtml(f.claim)}</span></span>
                            ${f.is_expired ? '<span style="background:rgba(239,68,68,0.15);color:#fca5a5;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">EXPIRED</span>' : '<span style="background:rgba(6,214,160,0.15);color:#6ee7b7;font-size:10px;font-weight:700;padding:2px 8px;border-radius:6px;">ACTIVE</span>'}
                        </div>
                        <div style="font-size:12px;color:#a0a0c8;margin-bottom:4px;"><strong style="color:#f0f0ff;">Approved Metric:</strong> ${escapeHtml(f.value)}</div>
                        <div style="font-size:11px;color:#6b7280;margin-bottom:2px;">Keywords: ${(f.keywords || []).join(', ') || 'none'}</div>
                        <div style="font-size:11px;color:#4b5563;">Valid: ${f.valid_from} to ${f.expires_on} | Owner: ${f.owner}</div>
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;

        } else if (tab === "terms") {
            let html = `<div style="display:flex;flex-direction:column;gap:10px;">`;
            data.forEach(t => {
                html += `
                    <div style="padding:14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;">
                        <div style="font-size:12px;font-weight:700;color:#6ee7b7;margin-bottom:4px;">✓ Preferred: ${escapeHtml(t.preferred)}</div>
                        <div style="font-size:12px;color:#fca5a5;margin-bottom:4px;">✕ Forbidden: ${(t.forbidden || []).join(', ')}</div>
                        <div style="font-size:11px;color:#6b7280;">${escapeHtml(t.note || '')}</div>
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;

        } else if (tab === "assets") {
            let html = `<div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;">`;
            data.forEach(a => {
                const isColor = a.type === "color";
                html += `
                    <div style="padding:14px;background:rgba(255,255,255,0.03);border:1px solid rgba(255,255,255,0.07);border-radius:10px;display:flex;align-items:flex-start;gap:12px;">
                        ${isColor ? `<div style="width:40px;height:40px;border-radius:8px;flex-shrink:0;border:1px solid rgba(255,255,255,0.1);background-color:${a.value};box-shadow:0 0 10px rgba(0,0,0,0.3);"></div>` : ''}
                        <div>
                            <div style="font-size:12px;font-weight:700;color:#f0f0ff;margin-bottom:2px;">${escapeHtml(a.name)}</div>
                            <div style="font-family:monospace;font-size:11px;color:#8b5cf6;">${a.value}</div>
                            <p style="font-size:11px;color:#6b7280;margin:4px 0 0;">${escapeHtml(a.usage_rule || '')}</p>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;
        }

    } catch (e) {
        container.innerHTML = `<div style="font-size:12px;color:#fca5a5;">Failed to load canon tab: ${e.message}</div>`;
    }
}

// Contrast Modal
function openContrastModal() {
    document.getElementById("contrast-modal").style.display = "flex";
}
function closeContrastModal() {
    document.getElementById("contrast-modal").style.display = "none";
}
async function runContrastCheck() {
    const fg = document.getElementById("contrast-fg").value.trim();
    const bg = document.getElementById("contrast-bg").value.trim();
    const box = document.getElementById("contrast-result-box");
    box.style.display = "block";

    try {
        const res = await fetch("/api/tools/contrast", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ foreground_hex: fg, background_hex: bg })
        });
        const data = await res.json();
        if (res.ok) {
            box.innerHTML = `
                <div style="font-weight:700;font-size:13px;color:${data.wcag_aa_normal_pass ? '#6ee7b7' : '#fca5a5'};">
                    Ratio: ${data.ratio}:1 — ${data.wcag_aa_normal_pass ? '✓ PASSES WCAG AA' : '✕ FAILS WCAG AA'}
                </div>
                <div style="font-size:11px;color:#a0a0c8;margin-top:4px;">${data.explanation}</div>
            `;
        } else {
            box.innerHTML = `<div style="color:#fca5a5;">${data.detail}</div>`;
        }
    } catch (e) {
        box.innerHTML = `<div style="color:#fca5a5;">${e.message}</div>`;
    }
}

function openAddRuleModal() {
    if (state.currentRole !== "Admin") {
        alert("Rule creation requires Admin permissions. Switching demo role to Admin...");
        document.getElementById("role-selector").value = "Admin";
        onRoleChanged();
    }
    document.getElementById("add-rule-modal").style.display = "flex";
}

function closeAddRuleModal() {
    document.getElementById("add-rule-modal").style.display = "none";
}

async function submitNewRule() {
    const id = document.getElementById("new-rule-id").value.trim();
    const category = document.getElementById("new-rule-category").value;
    const severity = document.getElementById("new-rule-severity").value;
    const text = document.getElementById("new-rule-text").value.trim();
    const pattern = document.getElementById("new-rule-pattern").value.trim() || null;
    const fix_hint = document.getElementById("new-rule-fix").value.trim() || null;

    if (!id || !text) {
        alert("Please provide both Rule ID and Rule text.");
        return;
    }

    try {
        const res = await fetch("/api/canon/rules", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Demo-Role": state.currentRole
            },
            body: JSON.stringify({ id, category, severity, text, pattern, fix_hint, active: true })
        });
        if (res.ok) {
            alert(`Rule ${id} added successfully!`);
            closeAddRuleModal();
            switchCanonTab("rules");
        } else {
            const err = await res.json();
            alert(`Failed to add rule: ${err.detail}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

function openAddFactModal() {
    if (state.currentRole !== "Admin") {
        alert("Fact registration requires Admin permissions. Switching demo role to Admin...");
        document.getElementById("role-selector").value = "Admin";
        onRoleChanged();
    }
    document.getElementById("add-fact-modal").style.display = "flex";
}

function closeAddFactModal() {
    document.getElementById("add-fact-modal").style.display = "none";
}

async function submitNewFact() {
    const id = document.getElementById("new-fact-id").value.trim();
    const claim = document.getElementById("new-fact-claim").value.trim();
    const value = document.getElementById("new-fact-value").value.trim();
    const keywordsRaw = document.getElementById("new-fact-keywords").value.trim();
    const keywords = keywordsRaw ? keywordsRaw.split(",").map(k => k.trim()).filter(Boolean) : [];
    const valid_from = document.getElementById("new-fact-valid").value;
    const expires_on = document.getElementById("new-fact-expires").value;
    const owner = document.getElementById("new-fact-owner").value.trim();

    if (!id || !claim || !value) {
        alert("Please provide Fact ID, Claim description, and Approved value.");
        return;
    }

    try {
        const res = await fetch("/api/canon/facts", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Demo-Role": state.currentRole
            },
            body: JSON.stringify({ id, claim, value, keywords, valid_from, expires_on, owner })
        });
        if (res.ok) {
            alert(`Fact ${id} registered successfully!`);
            closeAddFactModal();
            switchCanonTab("facts");
        } else {
            const err = await res.json();
            alert(`Failed to add fact: ${err.detail}`);
        }
    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}

function escapeHtml(text) {
    if (!text) return "";
    return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}
