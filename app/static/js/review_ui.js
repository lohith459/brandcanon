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
        missingBox.className = "mb-4 p-3 bg-red-50 border-l-4 border-red-500 rounded-r-lg text-xs text-red-800 space-y-1.5";
        missingBox.innerHTML = `<strong>⚠️ Missing Required Statutory Elements:</strong>`;
        missingFindings.forEach(mf => {
            const item = document.createElement("div");
            item.className = "flex items-center justify-between";
            item.innerHTML = `
                <span><strong>[${mf.rule_id}]</strong> ${escapeHtml(mf.explanation)}</span>
                <button onclick="selectFinding('${mf.id}')" class="text-[11px] underline font-semibold ml-2">Inspect Fix</button>
            `;
            missingBox.appendChild(item);
        });
        container.appendChild(missingBox);
    }

    // Build highlighted text by sorting spans by span_start
    // Handle non-overlapping spans
    const sortedSpans = [...spanFindings].sort((a, b) => a.span_start - b.span_start);
    const textWrapper = document.createElement("div");
    textWrapper.className = "leading-loose";

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
            <div class="p-6 bg-emerald-50 border border-emerald-200 rounded-xl text-center text-xs text-emerald-800">
                ✓ No brand guideline violations detected! Content meets all approved standards.
            </div>
        `;
        return;
    }

    findings.forEach(f => {
        const card = document.createElement("div");
        const sev = (f.severity || "medium").toLowerCase();
        let borderClass = "border-slate-200";
        let sevBadgeClass = "bg-blue-100 text-blue-800";
        if (sev === "critical") {
            borderClass = "border-red-300 bg-red-50/30";
            sevBadgeClass = "bg-red-100 text-red-800 border border-red-200";
        } else if (sev === "high") {
            borderClass = "border-amber-300 bg-amber-50/20";
            sevBadgeClass = "bg-amber-100 text-amber-800 border border-amber-200";
        }

        card.className = `finding-card p-4 rounded-xl border ${borderClass} bg-white shadow-sm space-y-3 transition`;
        card.id = `finding-card-${f.id}`;

        const isAccepted = f.decision === "accepted" || f.decision === "edited";
        const isDismissed = f.decision === "dismissed";

        card.innerHTML = `
            <div class="flex items-center justify-between">
                <div class="flex items-center space-x-1.5">
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded uppercase ${sevBadgeClass}">${f.severity}</span>
                    <span class="text-[10px] font-mono bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded font-semibold">${f.rule_id || f.fact_id || f.kind}</span>
                </div>
                <span class="text-[11px] text-slate-400 font-mono">Conf: ${(f.confidence * 100).toFixed(0)}%</span>
            </div>

            <!-- Issue quote & Explanation -->
            <div>
                ${f.quoted_text ? `<div class="text-xs font-semibold text-slate-800 bg-slate-100 px-2 py-1 rounded inline-block mb-1.5 font-mono">"${escapeHtml(f.quoted_text)}"</div>` : ''}
                <p class="text-xs text-slate-700 leading-relaxed">${escapeHtml(f.explanation)}</p>
            </div>

            <!-- Suggested Fix -->
            ${f.suggested_fix ? `
                <div class="p-2.5 bg-emerald-50/80 rounded-lg border border-emerald-200 text-xs">
                    <span class="font-semibold text-emerald-900 block text-[11px] uppercase tracking-wider mb-0.5">Proposed Fix:</span>
                    <code class="text-emerald-800 font-mono text-xs block whitespace-pre-wrap">${escapeHtml(f.suggested_fix)}</code>
                </div>
            ` : ''}

            <!-- Decision Status or Action Buttons -->
            ${isAccepted ? `
                <div class="flex items-center justify-between pt-1 border-t border-slate-100 text-xs text-emerald-700 font-semibold">
                    <span>✓ Fix Accepted (${f.decision})</span>
                    <button onclick="revertFindingDecision('${f.id}')" class="text-slate-400 hover:text-slate-600 text-[11px] font-normal underline">Undo</button>
                </div>
            ` : (isDismissed ? `
                <div class="pt-1 border-t border-slate-100 text-xs text-slate-500">
                    <div class="flex items-center justify-between">
                        <span class="font-semibold text-red-700">✕ Dismissed</span>
                        <button onclick="revertFindingDecision('${f.id}')" class="text-slate-400 hover:text-slate-600 text-[11px] font-normal underline">Undo</button>
                    </div>
                    <p class="text-[11px] text-slate-500 italic mt-0.5">Reason: "${escapeHtml(f.decision_reason || '')}"</p>
                </div>
            ` : `
                <div class="flex items-center space-x-1.5 pt-1 border-t border-slate-100">
                    <button onclick="acceptFindingFix('${f.id}')" class="flex-1 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold py-1.5 px-2 rounded-lg text-xs shadow-sm transition">
                        ✓ Accept Fix
                    </button>
                    <button onclick="editFindingFix('${f.id}')" class="px-2.5 py-1.5 text-xs text-slate-700 hover:bg-slate-100 rounded-lg border border-slate-300 font-medium transition">
                        Edit
                    </button>
                    <button onclick="openDismissModal('${f.id}')" class="px-2.5 py-1.5 text-xs text-red-600 hover:bg-red-50 rounded-lg border border-red-200 font-medium transition">
                        Dismiss
                    </button>
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
    document.querySelectorAll(".finding-card").forEach(el => el.classList.remove("ring-2", "ring-finedge-cyan"));

    // Highlight text span
    const span = document.getElementById(`highlight-span-${findingId}`);
    if (span) {
        span.classList.add("highlight-selected");
        span.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }

    // Highlight card
    const card = document.getElementById(`finding-card-${findingId}`);
    if (card) {
        card.classList.add("ring-2", "ring-finedge-cyan");
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
    document.getElementById("dismiss-modal").classList.remove("hidden");
    document.getElementById("dismiss-reason-input").focus();
}

function closeDismissModal() {
    document.getElementById("dismiss-modal").classList.add("hidden");
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
