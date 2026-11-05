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
    if (!document.getElementById("screen-approval").classList.contains("hidden")) {
        loadApprovalQueue();
    }
}

function updateRoleIndicator() {
    const label = document.getElementById("approval-current-role-label");
    if (label) label.textContent = state.currentRole;
}

// Navigation Stepper
function navigateTo(screenId) {
    document.querySelectorAll(".screen-view").forEach(el => el.classList.add("hidden"));
    const target = document.getElementById(`screen-${screenId}`);
    if (target) target.classList.remove("hidden");

    // Stepper button styles
    ["submit", "review", "diff", "approval"].forEach(step => {
        const btn = document.getElementById(`step-btn-${step}`);
        if (!btn) return;
        if (step === screenId) {
            btn.className = "nav-step-btn px-3 py-1.5 rounded-md text-sm font-medium text-white bg-slate-800 border-b-2 border-finedge-cyan flex items-center space-x-1.5";
        } else {
            btn.className = "nav-step-btn px-3 py-1.5 rounded-md text-sm font-medium text-slate-300 hover:text-white hover:bg-slate-800 flex items-center space-x-1.5 transition";
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
        riskBadge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-red-100 text-red-800 border border-red-300";
        riskBadge.innerHTML = "<span>⚠️ Tier 3 (Critical Compliance)</span>";
    } else if (tier === "Tier 2") {
        riskBadge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-amber-100 text-amber-800 border border-amber-300";
        riskBadge.innerHTML = "<span>Tier 2 (High Risk)</span>";
    } else {
        riskBadge.className = "px-3 py-1 rounded-full text-xs font-bold uppercase tracking-wider bg-emerald-100 text-emerald-800 border border-emerald-300";
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
            tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-xs text-slate-500">No submissions found. Submit content to populate the queue.</td></tr>`;
            return;
        }

        submissions.forEach(item => {
            const s = item.submission;
            const tr = document.createElement("tr");
            tr.className = "hover:bg-slate-50/80 cursor-pointer transition";
            tr.onclick = () => selectApprovalSubmission(s.id);

            let statusBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-slate-100 text-slate-700">${s.status}</span>`;
            if (s.status === "approved") statusBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-100 text-emerald-800">Approved</span>`;
            if (s.status === "in_review") statusBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-800">In Review</span>`;
            if (s.status === "changes_requested") statusBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-amber-100 text-amber-800">Changes Req</span>`;
            if (s.status === "rejected") statusBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-800">Rejected</span>`;

            let tierBadge = `<span class="px-2 py-0.5 rounded text-xs font-bold ${s.risk_tier === 'Tier 3' ? 'bg-red-100 text-red-800' : (s.risk_tier === 'Tier 2' ? 'bg-amber-100 text-amber-800' : 'bg-emerald-100 text-emerald-800')}">${s.risk_tier}</span>`;

            tr.innerHTML = `
                <td class="px-6 py-3 font-semibold text-slate-800">${escapeHtml(s.title)}</td>
                <td class="px-6 py-3 text-slate-600 capitalize">${s.channel}</td>
                <td class="px-6 py-3">${tierBadge}</td>
                <td class="px-6 py-3">${statusBadge}</td>
                <td class="px-6 py-3 text-slate-500 font-mono text-xs">${item.findings_count} issues</td>
                <td class="px-6 py-3 text-right">
                    <button class="text-xs text-blue-600 font-semibold hover:underline">Inspect →</button>
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
        panel.classList.remove("hidden");

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
            alertBox.classList.remove("hidden");
        } else {
            alertBox.classList.add("hidden");
        }

        // Render timeline
        const timeline = document.getElementById("approval-timeline-container");
        timeline.innerHTML = "";
        detail.audit_logs.forEach(log => {
            const div = document.createElement("div");
            div.className = "flex items-start space-x-2 border-l-2 border-slate-300 pl-2.5 py-1";
            div.innerHTML = `
                <div class="text-[11px]">
                    <span class="font-semibold text-slate-800">${escapeHtml(log.actor_role)}</span>
                    <span class="text-slate-400">(${log.action})</span>:
                    <span class="text-slate-600">${escapeHtml(log.detail)}</span>
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
            btn.className = "canon-tab py-2 px-3 text-sm font-semibold border-b-2 border-finedge-navy text-finedge-navy";
        } else {
            btn.className = "canon-tab py-2 px-3 text-sm font-medium text-slate-500 hover:text-slate-800";
        }
    });

    const container = document.getElementById("canon-content-container");
    container.innerHTML = `<div class="text-center py-6 text-xs text-slate-500">Loading ${tab}...</div>`;

    try {
        const res = await fetch(`/api/canon/${tab}`);
        if (!res.ok) return;
        const data = await res.json();

        if (tab === "rules") {
            let html = `<div class="space-y-3">`;
            data.forEach(r => {
                html += `
                    <div class="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
                        <div class="flex items-center justify-between mb-1">
                            <span class="font-mono text-xs font-bold text-slate-800">${r.id} (${r.category})</span>
                            <span class="text-[11px] font-semibold px-2 py-0.5 rounded ${r.severity === 'critical' ? 'bg-red-100 text-red-800' : 'bg-blue-100 text-blue-800'}">${r.severity}</span>
                        </div>
                        <p class="text-xs text-slate-700">${escapeHtml(r.text)}</p>
                        ${r.fix_hint ? `<p class="text-[11px] text-emerald-700 mt-1"><strong>Fix:</strong> ${escapeHtml(r.fix_hint)}</p>` : ''}
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;

        } else if (tab === "facts") {
            let html = `<div class="space-y-3">`;
            data.forEach(f => {
                html += `
                    <div class="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
                        <div class="flex items-center justify-between mb-1">
                            <span class="font-mono text-xs font-bold text-slate-800">${f.id} — ${escapeHtml(f.claim)}</span>
                            ${f.is_expired ? '<span class="bg-red-100 text-red-800 text-[10px] font-bold px-2 py-0.5 rounded">EXPIRED</span>' : '<span class="bg-emerald-100 text-emerald-800 text-[10px] font-bold px-2 py-0.5 rounded">ACTIVE</span>'}
                        </div>
                        <div class="text-xs text-slate-700"><strong>Approved Metric:</strong> ${escapeHtml(f.value)}</div>
                        <div class="text-[11px] text-slate-500 mt-0.5">Linked Keywords: ${(f.keywords || []).join(', ')}</div>
                        <div class="text-[11px] text-slate-400 mt-0.5">Valid: ${f.valid_from} to ${f.expires_on} | Owner: ${f.owner}</div>
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;

        } else if (tab === "terms") {
            let html = `<div class="space-y-3">`;
            data.forEach(t => {
                html += `
                    <div class="p-3.5 bg-slate-50 rounded-lg border border-slate-200">
                        <div class="text-xs font-bold text-emerald-700">✓ Preferred: ${escapeHtml(t.preferred)}</div>
                        <div class="text-xs text-red-700 mt-0.5">✕ Forbidden: ${(t.forbidden || []).join(', ')}</div>
                        <div class="text-[11px] text-slate-500 mt-1">${escapeHtml(t.note || '')}</div>
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;

        } else if (tab === "assets") {
            let html = `<div class="grid grid-cols-1 md:grid-cols-2 gap-4">`;
            data.forEach(a => {
                const isColor = a.type === "color";
                html += `
                    <div class="p-3.5 bg-slate-50 rounded-lg border border-slate-200 flex items-start space-x-3">
                        ${isColor ? `<div class="w-10 h-10 rounded-lg shadow-sm border border-slate-300 flex-shrink-0" style="background-color: ${a.value}"></div>` : ''}
                        <div>
                            <div class="text-xs font-bold text-slate-800">${escapeHtml(a.name)}</div>
                            <div class="font-mono text-[11px] text-slate-600">${a.value}</div>
                            <p class="text-[11px] text-slate-500 mt-1">${escapeHtml(a.usage_rule || '')}</p>
                        </div>
                    </div>
                `;
            });
            html += `</div>`;
            container.innerHTML = html;
        }

    } catch (e) {
        container.innerHTML = `<div class="text-xs text-red-600">Failed to load canon tab: ${e.message}</div>`;
    }
}

// Contrast Modal
function openContrastModal() {
    document.getElementById("contrast-modal").classList.remove("hidden");
}
function closeContrastModal() {
    document.getElementById("contrast-modal").classList.add("hidden");
}
async function runContrastCheck() {
    const fg = document.getElementById("contrast-fg").value.trim();
    const bg = document.getElementById("contrast-bg").value.trim();
    const box = document.getElementById("contrast-result-box");
    box.classList.remove("hidden");

    try {
        const res = await fetch("/api/tools/contrast", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ foreground_hex: fg, background_hex: bg })
        });
        const data = await res.json();
        if (res.ok) {
            box.innerHTML = `
                <div class="font-bold text-sm ${data.wcag_aa_normal_pass ? 'text-emerald-700' : 'text-red-700'}">
                    Ratio: ${data.ratio}:1 — ${data.wcag_aa_normal_pass ? '✓ PASSES WCAG AA' : '✕ FAILS WCAG AA'}
                </div>
                <div class="text-[11px] text-slate-600 mt-1">${data.explanation}</div>
            `;
        } else {
            box.innerHTML = `<div class="text-red-600">${data.detail}</div>`;
        }
    } catch (e) {
        box.innerHTML = `<div class="text-red-600">${e.message}</div>`;
    }
}

function openAddRuleModal() {
    if (state.currentRole !== "Admin") {
        alert("Rule creation requires Admin permissions. Switching demo role to Admin...");
        document.getElementById("role-selector").value = "Admin";
        onRoleChanged();
    }
    document.getElementById("add-rule-modal").classList.remove("hidden");
}

function closeAddRuleModal() {
    document.getElementById("add-rule-modal").classList.add("hidden");
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
    document.getElementById("add-fact-modal").classList.remove("hidden");
}

function closeAddFactModal() {
    document.getElementById("add-fact-modal").classList.add("hidden");
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
