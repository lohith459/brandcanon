from typing import List, Dict, Any
from sqlmodel import Session, select
from app.models.canon import Rule, Fact, Term, Asset, RuleCategory, Severity, AssetType

SEED_RULES: List[Dict[str, Any]] = [
    {
        "id": "CMP-004",
        "category": RuleCategory.COMPLIANCE.value,
        "severity": Severity.CRITICAL.value,
        "text": "Never promise or imply guaranteed returns, risk-free profits, or assured investment yields.",
        "good_example": "Target potential returns based on disciplined long-term portfolio allocation.",
        "bad_example": "Guaranteed 12% returns!!",
        "pattern": r"(?i)\b(guaranteed\s+\d+%\s+returns?|guaranteed\s+returns?|assured\s+returns?|risk-free\s+profits?)\b",
        "fix_hint": "Replace guaranteed return claims with realistic target expectations and risk disclosures.",
        "active": True
    },
    {
        "id": "DISC-002",
        "category": RuleCategory.COMPLIANCE.value,
        "severity": Severity.HIGH.value,
        "text": "Any post mentioning returns or investing must include the exact disclaimer: 'Investments are subject to market risks.'",
        "good_example": "Explore automated portfolio rebalancing. Investments are subject to market risks.",
        "bad_example": "Invest today and watch your returns grow month after month.",
        "pattern": None,  # Checked via required disclaimer logic in Layer A
        "fix_hint": "Add 'Investments are subject to market risks.' to the post.",
        "active": True
    },
    {
        "id": "CMP-001",
        "category": RuleCategory.COMPLIANCE.value,
        "severity": Severity.CRITICAL.value,
        "text": "Do not provide personalized investment advice or promise tax exemption without disclaimer.",
        "good_example": "Consult a certified financial planner for individual advice.",
        "bad_example": "You should put your entire savings into this tech fund.",
        "pattern": r"(?i)\b(put all your savings|guarantee your retirement|tax-free loophole)\b",
        "fix_hint": "Direct users to consult a certified financial advisor.",
        "active": True
    },
    {
        "id": "TRM-011",
        "category": RuleCategory.TERMINOLOGY.value,
        "severity": Severity.MEDIUM.value,
        "text": "The product name is 'FinEdge Plus'; 'FinEdge Pro' is retired.",
        "good_example": "Upgrade your experience with FinEdge Plus.",
        "bad_example": "Join 50,000+ investors on FinEdge Pro.",
        "pattern": r"(?i)\bFinEdge\s+Pro\b",
        "fix_hint": "Replace 'FinEdge Pro' with 'FinEdge Plus'.",
        "active": True
    },
    {
        "id": "TRM-002",
        "category": RuleCategory.TERMINOLOGY.value,
        "severity": Severity.MEDIUM.value,
        "text": "Refer to users as 'investors' or 'members', never 'punters' or 'gamblers'.",
        "good_example": "Join thousands of fellow investors.",
        "bad_example": "Help day-traders and punters gamble on meme stocks.",
        "pattern": r"(?i)\b(punters|gamblers)\b",
        "fix_hint": "Use 'investors' or 'members'.",
        "active": True
    },
    {
        "id": "TRM-003",
        "category": RuleCategory.TERMINOLOGY.value,
        "severity": Severity.MEDIUM.value,
        "text": "Use 'smart portfolio' instead of 'robo-advisor'.",
        "good_example": "Automate your strategy with our smart portfolio engine.",
        "bad_example": "Let our robo-advisor trade for you.",
        "pattern": r"(?i)\brobo-advis[oe]r\b",
        "fix_hint": "Use 'smart portfolio'.",
        "active": True
    },
    {
        "id": "TON-003",
        "category": RuleCategory.TONE.value,
        "severity": Severity.MEDIUM.value,
        "text": "At most one exclamation mark per post; no ALL-CAPS emphasis.",
        "good_example": "Welcome to your new portfolio dashboard.",
        "bad_example": "Guaranteed 12% returns!! It's FREE forever!",
        "pattern": None,  # Checked via tone analyzer in Layer A
        "fix_hint": "Remove excessive exclamation marks and convert ALL-CAPS words to normal sentence case.",
        "active": True
    },
    {
        "id": "TON-001",
        "category": RuleCategory.TONE.value,
        "severity": Severity.LOW.value,
        "text": "Maintain an encouraging and calm tone. Avoid aggressive FOMO or panic language.",
        "good_example": "Take your time to build your wealth sustainably.",
        "bad_example": "Don't miss out before it's too late! Act NOW or stay broke!",
        "pattern": r"(?i)\b(act now or stay broke|don't miss out before it's too late|stay poor|get in now)\b",
        "fix_hint": "Reframe with encouraging, sustainable financial principles.",
        "active": True
    },
    {
        "id": "TON-002",
        "category": RuleCategory.TONE.value,
        "severity": Severity.LOW.value,
        "text": "Keep sentences concise and readable (under 35 words per sentence).",
        "good_example": "FinEdge automates your asset allocation so you can focus on what matters.",
        "bad_example": "Because our complex financial system is engineered with proprietary math that exceeds standard industry benchmarks retail investors who join our platform can effortlessly achieve compounding without any friction whatsoever.",
        "pattern": None,
        "fix_hint": "Split long compound sentences into concise, clear statements.",
        "active": True
    },
    {
        "id": "ACC-001",
        "category": RuleCategory.ACCESSIBILITY.value,
        "severity": Severity.MEDIUM.value,
        "text": "Text/background contrast must be at least 4.5:1; every image needs descriptive alt text.",
        "good_example": "<img src='growth.png' alt='Historical 5-year growth chart of FinEdge Plus index'>",
        "bad_example": "<img src='growth.png'>",
        "pattern": None,
        "fix_hint": "Ensure images have alt text and colors meet WCAG AA 4.5:1 ratio.",
        "active": True
    },
    {
        "id": "ACC-002",
        "category": RuleCategory.ACCESSIBILITY.value,
        "severity": Severity.LOW.value,
        "text": "Do not rely on color alone to convey meaning or instructions.",
        "good_example": "Select the option marked with the checkmark icon.",
        "bad_example": "Click the green button or see the items in red.",
        "pattern": r"(?i)\b(click the (?:green|red|blue) button|items in (?:red|green|blue))\b",
        "fix_hint": "Include descriptive text labels alongside color indicators.",
        "active": True
    },
    {
        "id": "MSG-001",
        "category": RuleCategory.MESSAGING.value,
        "severity": Severity.HIGH.value,
        "text": "The free tier covers basic tracking only; do not claim the product is 'free forever' or without limits.",
        "good_example": "FinEdge offers free basic portfolio tracking, with optional Plus tiers.",
        "bad_example": "It's FREE forever!",
        "pattern": r"(?i)\bfree\s+forever\b",
        "fix_hint": "Clarify that the free tier covers basic tracking, or state transparent tier pricing.",
        "active": True
    },
    {
        "id": "MSG-002",
        "category": RuleCategory.MESSAGING.value,
        "severity": Severity.MEDIUM.value,
        "text": "Every call-to-action (CTA) must state the destination or purpose clearly. Avoid vague 'Click here'.",
        "good_example": "Join FinEdge Plus today.",
        "bad_example": "Click here to sign up.",
        "pattern": r"(?i)\bclick\s+here\b",
        "fix_hint": "Replace generic 'Click here' with specific action like 'Join FinEdge Plus'.",
        "active": True
    },
    {
        "id": "VIS-001",
        "category": RuleCategory.VISUAL.value,
        "severity": Severity.LOW.value,
        "text": "The FinEdge logo must not be altered, stretched, or displayed with unapproved dropshadows.",
        "good_example": "Use approved SVG vector logo with 24px minimum clear space.",
        "bad_example": "Stretched logo with neon drop shadow.",
        "pattern": None,
        "fix_hint": "Use official brand assets from the Canon asset library.",
        "active": True
    }
]

SEED_FACTS: List[Dict[str, Any]] = [
    {
        "id": "F-017",
        "claim": "FinEdge active registered users count",
        "value": "38400",
        "keywords": ["users", "investors", "members", "community", "registered", "subscribers", "active users"],
        "evidence_url": "https://internal.finedge.com/metrics/q3-2026-audit",
        "owner": "Analytics Lead",
        "valid_from": "2026-09-30",
        "expires_on": "2026-12-31"
    },
    {
        "id": "F-022",
        "claim": "Free tier covers basic tracking only (not unlimited/free forever)",
        "value": "Basic tracking only",
        "keywords": ["free", "free forever", "pricing", "cost", "free tier", "unlimited"],
        "evidence_url": "https://finedge.com/pricing-spec-2026",
        "owner": "Head of Product",
        "valid_from": "2026-01-01",
        "expires_on": "2027-01-01"
    },
    {
        "id": "F-001",
        "claim": "Total assets under management (AUM)",
        "value": "145000000",  # $145M
        "keywords": ["aum", "assets", "managed", "under management", "capital"],
        "evidence_url": "https://internal.finedge.com/reports/aum-q3-2026",
        "owner": "VP Finance",
        "valid_from": "2026-09-01",
        "expires_on": "2026-12-31"
    },
    {
        "id": "F-002",
        "claim": "Regulatory licensing: SEC-registered RIA",
        "value": "Registered Investment Advisor (RIA)",
        "keywords": ["sec", "ria", "registered", "regulated", "license", "fiduciary"],
        "evidence_url": "https://sec.gov/edgar/finedge",
        "owner": "Chief Compliance Officer",
        "valid_from": "2025-01-01",
        "expires_on": "2027-01-01"
    },
    {
        "id": "F-003",
        "claim": "Company founding year",
        "value": "2021",
        "keywords": ["founded", "established", "operating since", "started in", "years"],
        "evidence_url": "https://finedge.com/about",
        "owner": "Corporate Secretary",
        "valid_from": "2021-01-01",
        "expires_on": "2035-01-01"
    },
    {
        "id": "F-004",
        "claim": "Supported brokerage integrations count",
        "value": "18",
        "keywords": ["brokerages", "brokers", "banks", "institutions", "connections", "integrations"],
        "evidence_url": "https://finedge.com/integrations",
        "owner": "Head of Engineering",
        "valid_from": "2026-06-01",
        "expires_on": "2026-12-31"
    },
    {
        "id": "F-005",
        "claim": "Platform availability SLA",
        "value": "99.95%",
        "keywords": ["uptime", "availability", "sla", "reliable", "downtime"],
        "evidence_url": "https://status.finedge.com/sla",
        "owner": "Site Reliability Lead",
        "valid_from": "2026-01-01",
        "expires_on": "2026-12-31"
    },
    {
        "id": "F-006",
        "claim": "Customer satisfaction score (Q1 historical)",
        "value": "94%",
        "keywords": ["satisfaction", "csat", "nps", "happy", "rating"],
        "evidence_url": "https://internal.finedge.com/surveys/q1-2026",
        "owner": "Customer Success Lead",
        "valid_from": "2026-01-01",
        "expires_on": "2026-06-30"  # Expired as of Nov 2026 - triggers OUTDATED fact check
    }
]

SEED_TERMS: List[Dict[str, Any]] = [
    {
        "id": "TRM-011",
        "preferred": "FinEdge Plus",
        "forbidden": ["FinEdge Pro", "FinEdge Professional"],
        "note": "FinEdge Pro product line was retired in favour of FinEdge Plus."
    },
    {
        "id": "TRM-001",
        "preferred": "FinEdge",
        "forbidden": ["FineEdge", "Fin-Edge", "fin edge"],
        "note": "Always camel-case FinEdge as one word without hyphen."
    },
    {
        "id": "TRM-002",
        "preferred": "investors",
        "forbidden": ["punters", "gamblers", "speculators"],
        "note": "Respect our users as informed, disciplined investors."
    },
    {
        "id": "TRM-003",
        "preferred": "smart portfolio",
        "forbidden": ["robo-advisor", "black-box algorithm", "bot trader"],
        "note": "Highlight intelligent human-governed automation."
    },
    {
        "id": "TRM-004",
        "preferred": "market risks",
        "forbidden": ["risk-free", "zero risk", "guaranteed profits"],
        "note": "Mandated compliance terminology."
    },
    {
        "id": "TRM-005",
        "preferred": "basic tracking",
        "forbidden": ["free forever", "unlimited free"],
        "note": "The free tier is scoped specifically to basic tracking."
    },
    {
        "id": "TRM-006",
        "preferred": "annual percentage yield",
        "forbidden": ["get rich quick", "easy money"],
        "note": "Use standard financial nomenclature."
    },
    {
        "id": "TRM-007",
        "preferred": "portfolio rebalancing",
        "forbidden": ["stock flipping", "auto-gambling"],
        "note": "Reflect sound, disciplined asset allocation."
    },
    {
        "id": "TRM-008",
        "preferred": "bank-grade encryption",
        "forbidden": ["unhackable", "bulletproof security"],
        "note": "No platform may claim absolute infallibility."
    },
    {
        "id": "TRM-009",
        "preferred": "automated deposits",
        "forbidden": ["mindless investing"],
        "note": "Reinforce positive agency and financial discipline."
    },
    {
        "id": "TRM-010",
        "preferred": "long-term horizon",
        "forbidden": ["overnight riches", "instant millionaire"],
        "note": "Align with sustainable wealth creation."
    }
]

SEED_ASSETS: List[Dict[str, Any]] = [
    {
        "id": "AST-001",
        "type": AssetType.COLOR.value,
        "name": "FinEdge Navy (Primary)",
        "value": "#0A192F",
        "usage_rule": "Primary background and heading color. Delivers 16:1 contrast ratio against white."
    },
    {
        "id": "AST-002",
        "type": AssetType.COLOR.value,
        "name": "Emerald Cyan (Accent)",
        "value": "#00D2A0",
        "usage_rule": "Accent CTA buttons and positive financial gains. Contrast 4.6:1 on dark navy."
    },
    {
        "id": "AST-003",
        "type": AssetType.COLOR.value,
        "name": "Slate Gray (Secondary)",
        "value": "#4A5568",
        "usage_rule": "Secondary body text and subtle dividers. Meets 4.7:1 WCAG AA on white."
    },
    {
        "id": "AST-004",
        "type": AssetType.COLOR.value,
        "name": "Pure White (Canvas)",
        "value": "#FFFFFF",
        "usage_rule": "Standard card backgrounds and light mode canvas."
    },
    {
        "id": "AST-005",
        "type": AssetType.COLOR.value,
        "name": "Alert Coral (Warning)",
        "value": "#E53E3E",
        "usage_rule": "Compliance warnings, risk highlights, and critical badges."
    },
    {
        "id": "AST-006",
        "type": AssetType.LOGO.value,
        "name": "FinEdge Primary Wordmark",
        "value": "/static/assets/logo.svg",
        "usage_rule": "Maintain minimum 24px clear margin around mark. Do not compress or stretch."
    },
    {
        "id": "AST-007",
        "type": AssetType.FONT.value,
        "name": "Inter Modern Typography",
        "value": "Inter, system-ui, -apple-system, sans-serif",
        "usage_rule": "Primary interface typography for clear legibility and accessibility."
    }
]

def seed_canon_data(session: Session) -> None:
    """Populates database with initial FinEdge brand canon if not already present."""
    existing_rule = session.exec(select(Rule)).first()
    if not existing_rule:
        for r_data in SEED_RULES:
            session.add(Rule(**r_data))
        for f_data in SEED_FACTS:
            session.add(Fact(**f_data))
        for t_data in SEED_TERMS:
            session.add(Term(**t_data))
        for a_data in SEED_ASSETS:
            session.add(Asset(**a_data))
        session.commit()
