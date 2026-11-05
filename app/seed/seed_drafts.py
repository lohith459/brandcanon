from typing import List, Dict, Any

SAMPLE_DRAFTS: List[Dict[str, Any]] = [
    {
        "id": "draft-bad-001",
        "title": "FinEdge Pro Launch Campaign (Worked Example)",
        "channel": "twitter",
        "audience": "prospective_customers",
        "intent_message": "drive sign-ups with an attractive offer and social proof",
        "intent_cta": "Join FinEdge Plus",
        "text": "Guaranteed 12% returns!! Join 50,000+ investors on FinEdge Pro. It's FREE forever!",
        "description": "High-risk draft violating guaranteed returns (CMP-004), user count fact (F-017), retired product name (TRM-011), free forever scope (F-022 / MSG-001), exclamation count & ALL-CAPS (TON-003), and missing market risks disclaimer (DISC-002)."
    },
    {
        "id": "draft-medium-002",
        "title": "Q4 Platform Expansion Announcement",
        "channel": "linkedin",
        "audience": "existing_investors",
        "intent_message": "announce integration expansions and invite users to explore smart portfolios",
        "intent_cta": "Explore FinEdge Plus",
        "text": "We are proud to share that FinEdge now connects with 25 top brokerages nationwide! Upgrade your account to FinEdge Plus to experience our automated robo-advisor. Start your journey today! Investments are subject to market risks.",
        "description": "Medium-risk draft with retired term 'robo-advisor' (TRM-003) and brokerage count discrepancy (F-004 allows 18, text claims 25)."
    },
    {
        "id": "draft-clean-003",
        "title": "Educational: The Art of Disciplined Rebalancing",
        "channel": "blog",
        "audience": "all_investors",
        "intent_message": "educate investors on the importance of periodic asset allocation rebalancing",
        "intent_cta": "Learn more on FinEdge Plus",
        "text": "Disciplined investing starts with systematic rebalancing. Over 38,000 investors use FinEdge Plus to keep their target asset allocations on track across market cycles. Explore how smart portfolios simplify long-term financial health. Investments are subject to market risks.",
        "description": "Compliant clean draft that adheres to all guidelines, cites accurate facts, and includes the required market risks disclaimer."
    }
]
