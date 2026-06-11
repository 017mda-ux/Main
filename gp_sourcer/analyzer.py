"""Claude-powered GP analysis and outreach generation."""

from __future__ import annotations

import os
from typing import Iterator, Optional

from .models import GP


_DEFAULT_LP_THESIS = (
    "Early-stage LP seeking GPs focused on Seed through Series A in Enterprise SaaS, "
    "AI/ML, Fintech, and Healthcare Tech. Target fund size $50M–$500M. "
    "Priorities: differentiated sourcing, founder-friendliness, proven track record, "
    "and a strong operator network. Targeting 8–12 GP relationships, 2.5x+ net MOIC."
)


def _client():
    try:
        import anthropic
    except ImportError:
        return None
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


def analyze_gp(gp: GP, lp_thesis: Optional[str] = None) -> Iterator[str]:
    """Stream a structured LP due-diligence analysis for a GP."""
    client = _client()
    if client is None:
        yield "  ANTHROPIC_API_KEY not set — AI analysis unavailable.\n"
        return

    thesis = lp_thesis or _DEFAULT_LP_THESIS

    fund_str = f"${gp.fund_size_m:,.0f}M" if gp.fund_size_m else "N/A"
    aum_str = f"${gp.aum_m:,.0f}M" if gp.aum_m else "N/A"
    notes_str = "\n".join(f"- {n}" for n in gp.notes) if gp.notes else "None"

    prompt = f"""LP profile: {thesis}

GP under review:
- Name: {gp.name} | Firm: {gp.firm} | Role: {gp.role}
- Focus: {", ".join(gp.focus_areas)}
- Stage: {", ".join(gp.stage)}
- Geography: {", ".join(gp.geography)}
- Fund size: {fund_str} | AUM: {aum_str}
- Portfolio: {", ".join(gp.portfolio_highlights[:6])}
- Notable exits: {", ".join(gp.notable_exits[:4])}
- Initial fit score: {gp.fit_score}/10
- Bio: {gp.bio}
- LP notes: {notes_str}

Provide a concise LP due-diligence memo covering:

## 1. LP Fit (score X/10)
Alignment with stage, sector, geography, and fund size criteria.

## 2. Track Record
Quality of exits, portfolio construction, and return profile signals.

## 3. Differentiation
What sourcing edge, value-add, or access makes this GP stand out vs peers?

## 4. Key DD Questions
5 critical questions for a first LP meeting.

## 5. Risks & Red Flags
Any concerns about strategy, team, market dynamics, or fund size.

## 6. Suggested Outreach Hook
A single compelling sentence to open a cold email to this GP.

## 7. Verdict
Strong Interest / Moderate Interest / Pass — one-sentence rationale and the single most important monitoring variable.
"""

    import anthropic

    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=1800,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as exc:
        yield f"\nAPI error: {exc}\n"


def generate_outreach(gp: GP) -> Iterator[str]:
    """Stream a short, personalised LP outreach message for a GP."""
    client = _client()
    if client is None:
        yield "  ANTHROPIC_API_KEY not set — AI features unavailable.\n"
        return

    prompt = f"""Write a 3-sentence cold outreach message from an LP to {gp.name} at {gp.firm}.

Context:
- Role: {gp.role}
- Focus: {", ".join(gp.focus_areas[:3])}
- Stage: {", ".join(gp.stage[:2])}
- Notable portfolio: {", ".join(gp.portfolio_highlights[:3])}
- Bio snippet: {gp.bio[:250]}

Rules:
- Reference one specific portfolio company or public thesis point
- Mention LP's early-stage Enterprise/AI/Fintech focus as alignment
- Clear ask: 20-minute introductory call
- Warm but not gushing; peer tone, no flattery
- Output only the message, no preamble
"""

    import anthropic

    try:
        with client.messages.stream(
            model="claude-opus-4-6",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        ) as stream:
            for text in stream.text_stream:
                yield text
    except anthropic.APIError as exc:
        yield f"\nAPI error: {exc}\n"
