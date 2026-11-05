// Interactive Document Highlighting & Finding Cards Rendering

function renderHighlightedText(text, findings) {
    const container = document.getElementById("document-text-container");
    container.innerHTML = "";

    // Separate span findings from missing-element findings (anchored to whole text)
    const spanFindings = findings.filter(f => f.quoted_text && f.span_end > f.span_start);
    const missingFindings = findings.filter(f => !f.quoted_text && f.rule_id);

    // If there are missing elements (like missing disclaimer), display notice banner at top
    if (missingFindings.length > 0) {
        const missingBox = document.createElement("div");
        missingBox.style.cssText = "margin-bottom:16px;padding:12px 14px;background:rgba(239,68,68,0.1);border-left:3px solid rgba(239,68,68,0.6);border-radius:0 8px 8px 0;font-size:12px;color:#fca5a5;";
        missingBox.innerHTML = `<strong style="color:#fca5a5;">⚠️ Missing Required Statutory Elements:</strong>`;
        missingFindings.forEach(mf => {
            const item = document.createElement("div");
            item.style.cssText = "display:flex;align-items:center;justify-content:space-between;margin-top:6px;";
            item.innerHTML = `
                <span><strong style="color:#c4b5fd;">[${mf.rule_id}]</strong> ${escapeHtml(mf.explanation)}</span>
                <button onclick="selectFinding('${mf.id}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:#8b5cf6;text-decoration:underline;margin-left:8px;">Inspect Fix</button>
            `;
            missingBox.appendChild(item);
        });
        container.appendChild(missingBox);
    }

    // Build highlighted text by sorting spans by span_start
    // Handle non-overlapping spans
    const sortedSpans = [...spanFindings].sort((a, b) => a.span_start - b.span_start);
    const textWrapper = document.createElement("div");
    textWrapper.style.lineHeight = "2";

    let lastIdx = 0;
    sortedSpans.forEach(f => {
        // Text before highlight
        if (f.span_start > lastIdx) {
            textWrapper.appendChild(document.createTextNode(text.substring(lastIdx, f.span_start)));
        }

        // Highlighted span
        const mark = document.createElement("mark");
        const sevClass = `highlight-${(f.severity || "medium").toLowerCase()}`;
        mark.className = `highlight-span ${sevClass}`;
        mark.id = `highlight-span-${f.id}`;
        mark.tabIndex = 0;
        mark.textContent = text.substring(f.span_start, f.span_end);
        mark.title = `[${f.rule_id || f.fact_id}] ${f.explanation}`;
        mark.onclick = () => selectFinding(f.id);
        mark.onkeydown = (e) => { if (e.key === 'Enter') selectFinding(f.id); };

        textWrapper.appendChild(mark);
        lastIdx = Math.max(lastIdx, f.span_end);
    });

    // Remaining text after last highlight
    if (lastIdx < text.length) {
        textWrapper.appendChild(document.createTextNode(text.substring(lastIdx)));
    }

    container.appendChild(textWrapper);
}

function renderFindingCards(findings) {
    const container = document.getElementById("finding-cards-container");
    container.innerHTML = "";
    document.getElementById("findings-total-label").textContent = `${findings.length} issues found`;

    if (findings.length === 0) {
        container.innerHTML = `
            <div style="padding:24px;background:rgba(6,214,160,0.08);border:1px solid rgba(6,214,160,0.25);border-radius:12px;text-align:center;font-size:12px;color:#6ee7b7;">
                ✓ No brand guideline violations detected! Content meets all approved standards.
            </div>
        `;
        return;
    }

    findings.forEach(f => {
        const card = document.createElement("div");
        const sev = (f.severity || "medium").toLowerCase();
        card.className = `finding-card severity-${sev}`;
        card.id = `finding-card-${f.id}`;

        const sevBadge = `<span class="sev-badge sev-${sev}">${f.severity}</span>`;
        const idBadge = `<span style="font-size:10px;font-family:monospace;background:rgba(255,255,255,0.08);color:#a0a0c8;padding:2px 7px;border-radius:6px;font-weight:600;">${f.rule_id || f.fact_id || f.kind}</span>`;
        const isAccepted = f.decision === "accepted" || f.decision === "edited";
        const isDismissed = f.decision === "dismissed";

        card.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;">
                <div style="display:flex;align-items:center;gap:6px;">
                    ${sevBadge}
                    ${idBadge}
                </div>
                <span style="font-size:10px;color:#6b7280;font-family:monospace;">Conf: ${(f.confidence * 100).toFixed(0)}%</span>
            </div>

            <div style="margin-bottom:10px;">
                ${f.quoted_text ? `<div style="font-size:11px;font-family:monospace;background:rgba(255,255,255,0.05);color:#c4b5fd;padding:5px 9px;border-radius:7px;margin-bottom:7px;border:1px solid rgba(139,92,246,0.2);">"${escapeHtml(f.quoted_text)}"</div>` : ''}
                <p style="font-size:12px;color:#a0a0c8;line-height:1.6;margin:0;">${escapeHtml(f.explanation)}</p>
            </div>

            ${f.suggested_fix ? `
                <div style="padding:10px;background:rgba(6,214,160,0.08);border-radius:8px;border:1px solid rgba(6,214,160,0.2);margin-bottom:10px;">
                    <span style="font-size:10px;font-weight:700;color:#6ee7b7;text-transform:uppercase;letter-spacing:0.06em;display:block;margin-bottom:4px;">Proposed Fix:</span>
                    <code style="font-size:11px;color:#a7f3d0;font-family:monospace;display:block;white-space:pre-wrap;">${escapeHtml(f.suggested_fix)}</code>
                </div>
            ` : ''}

            ${isAccepted ? `
                <div style="display:flex;align-items:center;justify-content:space-between;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);">
                    <span style="font-size:11px;color:#6ee7b7;font-weight:700;">✓ Fix Accepted (${f.decision})</span>
                    <button onclick="revertFindingDecision('${f.id}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:#6b7280;text-decoration:underline;" onmouseover="this.style.color='#a0a0c8'" onmouseout="this.style.color='#6b7280'">Undo</button>
                </div>
            ` : (isDismissed ? `
                <div style="padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);">
                    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:4px;">
                        <span style="font-size:11px;color:#fca5a5;font-weight:700;">✕ Dismissed</span>
                        <button onclick="revertFindingDecision('${f.id}')" style="background:none;border:none;cursor:pointer;font-size:11px;color:#6b7280;text-decoration:underline;" onmouseover="this.style.color='#a0a0c8'" onmouseout="this.style.color='#6b7280'">Undo</button>
                    </div>
                    <p style="font-size:11px;color:#6b7280;font-style:italic;margin:0;">Reason: "${escapeHtml(f.decision_reason || '')}"</p>
                </div>
            ` : `
                <div style="display:flex;align-items:center;gap:6px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.06);">
                    <button onclick="acceptFindingFix('${f.id}')" class="btn-accept" style="flex:1;">✓ Accept Fix</button>
                    <button onclick="editFindingFix('${f.id}')" class="btn-dismiss" style="padding:5px 10px;">Edit</button>
                    <button onclick="openDismissModal('${f.id}')" class="btn-dismiss" style="padding:5px 10px;color:#fca5a5;">Dismiss</button>
                </div>
            `)}
        `;
        container.appendChild(card);
    });
}


// Select finding card and scroll corresponding element into view
function selectFinding(findingId) {
    state.selectedFindingId = findingId;

    // Remove active highlight from all
    document.querySelectorAll(".highlight-span").forEach(el => el.classList.remove("highlight-selected"));
    document.querySelectorAll(".finding-card").forEach(el => {
        el.style.outline = "";
        el.style.boxShadow = "";
    });

    // Highlight text span
    const span = document.getElementById(`highlight-span-${findingId}`);
    if (span) {
        span.classList.add("highlight-selected");
        span.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Highlight card
    const card = document.getElementById(`finding-card-${findingId}`);
    if (card) {
        card.style.outline = "1px solid rgba(139,92,246,0.6)";
        card.style.boxShadow = "0 0 20px rgba(139,92,246,0.25)";
        card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
}

// Accept Fix Action
async function acceptFindingFix(findingId) {
    await updateFindingDecision(findingId, "accepted");
}

// Edit Fix Action
async function editFindingFix(findingId) {
    const f = state.findings.find(item => item.id === findingId);
    if (!f) return;
    const customFix = prompt("Edit the replacement text for this finding:", f.suggested_fix || f.quoted_text || "");
    if (customFix === null) return;
    await updateFindingDecision(findingId, "edited", "User custom replacement", customFix);
}

// Revert Finding Decision back to pending
async function revertFindingDecision(findingId) {
    await updateFindingDecision(findingId, "pending");
}

// Dismissal Modal Handlers
function openDismissModal(findingId) {
    document.getElementById("dismiss-finding-id").value = findingId;
    document.getElementById("dismiss-reason-input").value = "";
    document.getElementById("dismiss-modal").style.display = "flex";
    document.getElementById("dismiss-reason-input").focus();
}

function closeDismissModal() {
    document.getElementById("dismiss-modal").style.display = "none";
}

async function confirmDismissFinding() {
    const findingId = document.getElementById("dismiss-finding-id").value;
    const reason = document.getElementById("dismiss-reason-input").value.trim();

    if (!reason) {
        alert("A written reason is strictly required to dismiss or override a brand finding.");
        return;
    }

    closeDismissModal();
    await updateFindingDecision(findingId, "dismissed", reason);
}

// Update Finding Decision API call
async function updateFindingDecision(findingId, decision, reason = null, customFix = null) {
    if (!state.currentSubmission) return;

    try {
        const res = await fetch(`/api/submissions/${state.currentSubmission.id}/findings/${findingId}/decision`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-Demo-Role": state.currentRole
            },
            body: JSON.stringify({
                decision,
                decision_reason: reason,
                edited_fix: customFix
            })
        });

        if (!res.ok) {
            const err = await res.json();
            alert(`Failed: ${err.detail}`);
            return;
        }

        const data = await res.json();
        // Update local finding
        const idx = state.findings.findIndex(f => f.id === findingId);
        if (idx !== -1) {
            state.findings[idx] = data.finding;
        }

        // Re-render
        renderFindingCards(state.findings);
        updateAcceptedCountBadge();

    } catch (e) {
        alert(`Error: ${e.message}`);
    }
}
